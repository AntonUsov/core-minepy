"""Protocol layer - network connection and packet handling."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import struct
import zlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from minepy.types import Position
from minepy.vec3 import Vec3

if TYPE_CHECKING:
    from minepy.bot import Bot

logger = logging.getLogger(__name__)


class ConnectionState:
    """Connection state constants."""

    HANDSHAKING = "handshaking"
    STATUS = "status"
    LOGIN = "login"
    PLAY = "play"
    CLOSED = "closed"


@dataclass
class PacketHandler:
    """Packet handler registration."""

    packet_id: int
    handler: callable
    versions: list[int] | None = None  # None = all versions


class PacketReader:
    """Helper class for reading packet data."""

    __slots__ = ("data", "offset")

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0

    def read_byte(self) -> int:
        result = self.data[self.offset]
        self.offset += 1
        return result

    def read_ubyte(self) -> int:
        return self.read_byte() & 0xFF

    def read_short(self) -> int:
        result = struct.unpack_from(">h", self.data, self.offset)[0]
        self.offset += 2
        return result

    def read_ushort(self) -> int:
        result = struct.unpack_from(">H", self.data, self.offset)[0]
        self.offset += 2
        return result

    def read_int(self) -> int:
        result = struct.unpack_from(">i", self.data, self.offset)[0]
        self.offset += 4
        return result

    def read_long(self) -> int:
        result = struct.unpack_from(">q", self.data, self.offset)[0]
        self.offset += 8
        return result

    def read_float(self) -> float:
        result = struct.unpack_from(">f", self.data, self.offset)[0]
        self.offset += 4
        return result

    def read_double(self) -> float:
        result = struct.unpack_from(">d", self.data, self.offset)[0]
        self.offset += 8
        return result

    def read_boolean(self) -> bool:
        return self.read_byte() != 0

    def read_varint(self) -> int:
        result = 0
        shift = 0
        while True:
            byte = self.read_byte()
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7
            if shift >= 32:
                raise ValueError("VarInt too big")
        return result

    def read_varlong(self) -> int:
        result = 0
        shift = 0
        while True:
            byte = self.read_byte()
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7
            if shift >= 64:
                raise ValueError("VarLong too big")
        return result

    def read_string(self, max_length: int = 32767) -> str:
        length = self.read_varint()
        if length > max_length * 4:
            raise ValueError(f"String too long: {length}")
        result = self.data[self.offset : self.offset + length].decode("utf-8")
        self.offset += length
        if len(result) > max_length:
            raise ValueError(f"String too long: {len(result)}")
        return result

    def read_uuid(self) -> str:
        uuid_bytes = self.data[self.offset : self.offset + 16]
        self.offset += 16
        # Format as UUID string
        hex_str = uuid_bytes.hex()
        return f"{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:]}"

    def read_position(self) -> tuple[int, int, int]:
        val = self.read_long()
        x = val >> 38
        y = (val >> 26) & 0xFFF
        z = val << 38 >> 38
        # Sign extension for negative values
        if x >= 2**25:
            x -= 2**26
        if y >= 2**11:
            y -= 2**12
        if z >= 2**25:
            z -= 2**26
        return (x, y, z)

    def read_double_position(self) -> tuple[float, float, float]:
        x = self.read_double()
        y = self.read_double()
        z = self.read_double()
        return (x, y, z)

    def read_bytes(self, length: int) -> bytes:
        result = self.data[self.offset : self.offset + length]
        self.offset += length
        return result

    def read_byte_array(self) -> bytes:
        length = self.read_varint()
        return self.read_bytes(length)

    def remaining(self) -> int:
        return len(self.data) - self.offset

    def read_remaining(self) -> bytes:
        result = self.data[self.offset :]
        self.offset = len(self.data)
        return result


class Connection:
    """
    Manages the network connection to a Minecraft server.
    Handles packet reading, writing, and protocol state management.
    """

    def __init__(self, bot: Bot) -> None:
        self._bot = bot
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._state: str = ConnectionState.HANDSHAKING
        self._compression_threshold: int = -1
        self._receive_task: asyncio.Task | None = None
        self._protocol_version: int = 765  # Default 1.20.4

        # Server state
        self._keep_alive_task: asyncio.Task | None = None
        self._last_keep_alive: int = 0
        self._server_brand: str = ""

        # Movement tracking
        self._control_states: dict[str, bool] = {
            "forward": False,
            "back": False,
            "left": False,
            "right": False,
            "jump": False,
            "sprint": False,
            "sneak": False,
        }

        # Sequence IDs
        self._teleport_id: int = 0
        self._transaction_id: int = 0

        # Packet handlers registry
        self._packet_handlers: dict[int, list[callable]] = {}

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    @property
    def state(self) -> str:
        return self._state

    @property
    def protocol_version(self) -> int:
        return self._protocol_version

    # ==================== Connection Management ====================

    async def connect(self) -> None:
        """Connect to the Minecraft server."""
        logger.info(f"Connecting to {self._bot.host}:{self._bot.port}...")

        try:
            self._reader, self._writer = await asyncio.open_connection(
                self._bot.host, self._bot.port
            )
        except OSError as e:
            raise ConnectionError(
                f"Failed to connect to {self._bot.host}:{self._bot.port}: {e}"
            ) from e

        # Auto-detect protocol version if not specified
        if not self._bot.version:
            detected = await self._ping_server()
            if detected:
                self._protocol_version = detected
            else:
                self._protocol_version = 769  # Default to 1.21.4
        else:
            self._protocol_version = self._get_protocol_version(self._bot.version)

        logger.info(f"Using protocol version {self._protocol_version}")

        # Perform handshake and login
        await self._handshake()
        await self._login()

        # Start receiving packets
        self._receive_task = asyncio.create_task(self._receive_loop())

        await self._bot.emit("connect")

    async def _ping_server(self) -> int | None:
        """Ping server to get protocol version."""
        try:
            reader, writer = await asyncio.open_connection(self._bot.host, self._bot.port)

            # Handshake for status
            data = self._write_varint(769)
            data += self._write_string(self._bot.host)
            data += struct.pack(">H", self._bot.port)
            data += self._write_varint(1)  # Status state

            await self._send_packet_raw(writer, 0x00, data)
            await self._send_packet_raw(writer, 0x00, b"")

            # Read response
            length = await self._read_varint_stream(reader)
            packet_data = await reader.readexactly(length)

            packet_id, offset = self._read_varint_with_offset(packet_data, 0)
            if packet_id == 0x00:
                json_len, offset = self._read_varint_with_offset(packet_data, offset)
                json_data = packet_data[offset : offset + json_len].decode("utf-8")
                status = json.loads(json_data)
                protocol = status.get("version", {}).get("protocol", 0)
            else:
                protocol = 0

            writer.close()
            await writer.wait_closed()
            return protocol

        except Exception:
            logger.debug("Failed to ping server")
            return None

    async def _send_packet_raw(
        self, writer: asyncio.StreamWriter, packet_id: int, data: bytes
    ) -> None:
        """Send a packet without compression."""
        packet_data = self._write_varint(packet_id) + data
        writer.write(self._write_varint(len(packet_data)) + packet_data)
        await writer.drain()

    def disconnect(self, reason: str = "disconnecting") -> None:
        """Disconnect from the server."""
        if self._keep_alive_task:
            self._keep_alive_task.cancel()
            self._keep_alive_task = None

        if self._receive_task:
            self._receive_task.cancel()
            self._receive_task = None

        if self._writer:
            self._writer.close()
            with contextlib.suppress(Exception):
                asyncio.get_event_loop().run_until_complete(self._writer.wait_closed())
            self._writer = None

        self._state = ConnectionState.CLOSED
        asyncio.create_task(self._bot.emit("end", reason))

    # ==================== Handshake & Login ====================

    async def _handshake(self) -> None:
        """Send handshake packet."""
        data = self._write_varint(self._protocol_version)
        data += self._write_string(self._bot.host)
        data += struct.pack(">H", self._bot.port)
        data += self._write_varint(2)  # Login state

        await self._send_packet(0x00, data)
        self._state = ConnectionState.LOGIN

    async def _login(self) -> None:
        """Send login start packet."""
        import uuid as uuid_module

        data = self._write_string(self._bot.username)

        if self._bot.auth == "offline":
            player_uuid = uuid_module.uuid3(
                uuid_module.NAMESPACE_OID, f"OfflinePlayer:{self._bot.username}"
            )
            data += player_uuid.bytes
        else:
            # TODO: Microsoft auth
            player_uuid = uuid_module.uuid4()
            data += player_uuid.bytes

        await self._send_packet(0x00, data)

    # ==================== Packet Receiving ====================

    async def _receive_loop(self) -> None:
        """Main loop for receiving packets."""
        logger.debug("Starting packet receive loop")

        try:
            while self.connected:
                packet = await self._read_packet()
                if packet:
                    await self._handle_packet(packet)
        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")
        except Exception as e:
            logger.exception("Exception in receive loop")
            await self._bot.emit("error", e)
            self.disconnect(f"Connection error: {e}")

    async def _read_packet(self) -> tuple[int, bytes] | None:
        """Read a packet from the server."""
        if not self._reader:
            return None

        try:
            length = await self._read_varint()
            if length <= 0:
                return None

            data = await self._reader.readexactly(length)

            # Decompress if needed
            if self._compression_threshold >= 0:
                reader = PacketReader(data)
                data_length = reader.read_varint()
                data = reader.read_remaining()
                if data_length > 0:
                    data = zlib.decompress(data)

            reader = PacketReader(data)
            packet_id = reader.read_varint()
            packet_data = reader.read_remaining()

            return packet_id, packet_data

        except asyncio.IncompleteReadError:
            logger.debug("Incomplete read, connection closing")
            return None

    async def _handle_packet(self, packet: tuple[int, bytes]) -> None:
        """Route packet to appropriate handler."""
        packet_id, data = packet

        if self._state == ConnectionState.LOGIN:
            await self._handle_login_packet(packet_id, data)
        elif self._state == ConnectionState.PLAY:
            await self._handle_play_packet(packet_id, data)

    # ==================== Login Packet Handlers ====================

    async def _handle_login_packet(self, packet_id: int, data: bytes) -> None:
        """Handle login state packets."""
        if packet_id == 0x00:  # Disconnect
            reader = PacketReader(data)
            reason = reader.read_string()
            logger.warning(f"Disconnected during login: {reason}")
            self.disconnect(reason)

        elif packet_id == 0x01:  # Encryption Request
            logger.warning("Encryption requested but not implemented")

        elif packet_id == 0x02:  # Login Success
            reader = PacketReader(data)
            uuid = reader.read_uuid()
            username = reader.read_string()
            logger.info(f"Login successful: {username} ({uuid})")
            self._state = ConnectionState.PLAY
            await self._bot.emit("login")

        elif packet_id == 0x03:  # Set Compression
            reader = PacketReader(data)
            self._compression_threshold = reader.read_varint()
            logger.debug(f"Compression threshold: {self._compression_threshold}")

    # ==================== Play Packet Handlers ====================

    async def _handle_play_packet(self, packet_id: int, data: bytes) -> None:
        """Handle play state packets."""
        reader = PacketReader(data)
        pv = self._protocol_version

        # Keep Alive (clientbound) - varies by version
        keep_alive_id = self._get_packet_id("keep_alive_clientbound", pv)
        if packet_id == keep_alive_id:
            await self._handle_keep_alive(reader)

        # Join Game / Login
        join_id = self._get_packet_id("join_game", pv)
        if packet_id == join_id:
            await self._handle_join_game(reader)

        # Player Position
        position_id = self._get_packet_id("player_position", pv)
        if packet_id == position_id:
            await self._handle_player_position(reader)

        # Chat Message
        chat_id = self._get_packet_id("chat_message", pv)
        if packet_id == chat_id:
            await self._handle_chat_message(reader)

        # Health Update
        health_id = self._get_packet_id("health_update", pv)
        if packet_id == health_id:
            await self._handle_health_update(reader)

        # Entity packets
        await self._handle_entity_packets(packet_id, reader)

        # Chunk Data
        chunk_id = self._get_packet_id("chunk_data", pv)
        if packet_id == chunk_id:
            await self._handle_chunk_data(reader)

        # Block Change
        block_change_id = self._get_packet_id("block_change", pv)
        if packet_id == block_change_id:
            await self._handle_block_change(reader)

        # Window packets
        await self._handle_window_packets(packet_id, reader)

    async def _handle_keep_alive(self, reader: PacketReader) -> None:
        """Handle keep alive packet."""
        keep_alive_id = reader.read_long()
        self._last_keep_alive = keep_alive_id

        # Respond immediately
        data = struct.pack(">Q", keep_alive_id)
        response_id = self._get_packet_id("keep_alive_serverbound", self._protocol_version)
        await self._send_packet(response_id, data)

        logger.debug(f"Responded to keep alive: {keep_alive_id}")

    async def _handle_join_game(self, reader: PacketReader) -> None:
        """Handle join game packet."""
        pv = self._protocol_version

        if pv >= 767:  # 1.21+
            reader.read_int()  # entity ID
            reader.read_boolean()  # hardcore
            reader.read_byte()  # gamemode
            reader.read_byte()  # previous gamemode

            # Dimensions list
            dim_count = reader.read_varint()
            for _ in range(dim_count):
                reader.read_string()

            # More data...
            reader.read_string()  # world name
            # ... lots more fields

        logger.info("Joined game")
        await self._bot.emit("spawn")

    async def _handle_player_position(self, reader: PacketReader) -> None:
        """Handle player position sync from server."""
        x = reader.read_double()
        y = reader.read_double()
        z = reader.read_double()
        yaw = reader.read_float()
        pitch = reader.read_float()
        flags = reader.read_byte()
        teleport_id = reader.read_varint()

        # Apply position (respecting flags)
        if not (flags & 0x01):
            self._bot.position["x"] = x
        if not (flags & 0x02):
            self._bot.position["y"] = y
        if not (flags & 0x04):
            self._bot.position["z"] = z
        if not (flags & 0x08):
            self._bot.yaw = yaw
        if not (flags & 0x10):
            self._bot.pitch = pitch

        self._teleport_id = teleport_id

        # Confirm teleport
        confirm_id = self._get_packet_id("teleport_confirm", self._protocol_version)
        await self._send_packet(confirm_id, self._write_varint(teleport_id))

        await self._bot.emit("move", (x, y, z))

    async def _handle_chat_message(self, reader: PacketReader) -> None:
        """Handle chat message packet."""
        pv = self._protocol_version

        if pv >= 760:  # 1.19.3+
            # Signed chat format
            message = reader.read_string()
            # Skip the rest for now (signatures, etc.)
            logger.debug(f"Chat message: {message}")
            await self._bot.emit("chat", "", message, None)
        else:
            json_data = reader.read_string()
            try:
                parsed = json.loads(json_data)
                message = self._extract_text(parsed)
                # Extract sender from json
                username = ""
                await self._bot.emit("chat", username, message, None)
            except json.JSONDecodeError:
                await self._bot.emit("chat", "", json_data, None)

    def _extract_text(self, component: dict | str) -> str:
        """Extract plain text from JSON chat component."""
        if isinstance(component, str):
            return component

        text = component.get("text", "")

        for extra in component.get("extra", []):
            text += self._extract_text(extra)

        return text

    async def _handle_health_update(self, reader: PacketReader) -> None:
        """Handle health update packet."""
        health = reader.read_float()
        food = reader.read_varint()
        saturation = reader.read_float()

        old_health = self._bot.health
        self._bot.health = health
        self._bot.food = food
        self._bot.food_saturation = saturation

        if health <= 0 and old_health > 0:
            await self._bot.emit("death")
        elif health != old_health:
            await self._bot.emit("health")

        logger.debug(f"Health: {health}, Food: {food}, Saturation: {saturation}")

    async def _handle_entity_packets(self, packet_id: int, reader: PacketReader) -> None:
        """Handle entity-related packets."""
        pv = self._protocol_version

        # Entity Spawn
        spawn_id = self._get_packet_id("entity_spawn", pv)
        if packet_id == spawn_id:
            entity_id = reader.read_varint()
            uuid = reader.read_uuid()
            entity_type = reader.read_varint()
            x = reader.read_double()
            y = reader.read_double()
            z = reader.read_double()
            yaw = reader.read_byte()
            pitch = reader.read_byte()
            # ... more data

            entity_data = {
                "id": entity_id,
                "uuid": uuid,
                "type": entity_type,
                "position": {"x": x, "y": y, "z": z},
                "yaw": yaw * 360 / 256,
                "pitch": pitch * 360 / 256,
            }
            self._bot.entities[entity_id] = entity_data
            await self._bot.emit("entity_spawn", entity_data)

        # Entity Destroy
        destroy_id = self._get_packet_id("entity_destroy", pv)
        if packet_id == destroy_id:
            count = reader.read_varint()
            for _ in range(count):
                entity_id = reader.read_varint()
                entity = self._bot.entities.pop(entity_id, None)
                if entity:
                    await self._bot.emit("entity_gone", entity)

        # Entity Move
        move_id = self._get_packet_id("entity_move", pv)
        if packet_id == move_id:
            entity_id = reader.read_varint()
            dx = reader.read_short() / 4096
            dy = reader.read_short() / 4096
            dz = reader.read_short() / 4096
            yaw = reader.read_byte()
            pitch = reader.read_byte()
            on_ground = reader.read_boolean()

            if entity_id in self._bot.entities:
                entity = self._bot.entities[entity_id]
                entity["position"]["x"] += dx
                entity["position"]["y"] += dy
                entity["position"]["z"] += dz
                await self._bot.emit("entity_moved", entity)

    async def _handle_chunk_data(self, reader: PacketReader) -> None:
        """Handle chunk data packet."""
        chunk_x = reader.read_int()
        chunk_z = reader.read_int()
        # ... parse chunk data

        await self._bot.emit("chunk_column_load", (chunk_x, chunk_z))

    async def _handle_block_change(self, reader: PacketReader) -> None:
        """Handle block change packet."""
        x, y, z = reader.read_position()
        block_id = reader.read_varint()

        await self._bot.emit(
            "block_update", None, {"position": {"x": x, "y": y, "z": z}, "id": block_id}
        )

    async def _handle_window_packets(self, packet_id: int, reader: PacketReader) -> None:
        """Handle window-related packets."""
        pv = self._protocol_version

        # Window Open
        open_id = self._get_packet_id("window_open", pv)
        if packet_id == open_id:
            window_id = reader.read_varint()
            window_type = reader.read_varint()
            title = reader.read_string()
            await self._bot.emit(
                "window_open", {"id": window_id, "type": window_type, "title": title}
            )

        # Window Close
        close_id = self._get_packet_id("window_close", pv)
        if packet_id == close_id:
            window_id = reader.read_ubyte()
            await self._bot.emit("window_close", {"id": window_id})

        # Window Items
        items_id = self._get_packet_id("window_items", pv)
        if packet_id == items_id:
            window_id = reader.read_ubyte()
            count = reader.read_short()
            items = []
            for _ in range(count):
                items.append(self._read_slot(reader))
            # Update inventory

        # Set Slot
        slot_id = self._get_packet_id("set_slot", pv)
        if packet_id == slot_id:
            window_id = reader.read_ubyte()
            state = reader.read_varint()
            slot = reader.read_short()
            item = self._read_slot(reader)
            # Update slot

    def _read_slot(self, reader: PacketReader) -> dict | None:
        """Read an item slot from packet data."""
        count = reader.read_boolean() if self._protocol_version >= 766 else reader.read_short()

        if not count or (isinstance(count, int) and count <= 0):
            return None

        if isinstance(count, bool):
            count = reader.read_ubyte()

        item_id = reader.read_varint()
        slot_data = {"id": item_id, "count": count, "nbt": None}

        # Read NBT if present
        nbt_byte = reader.read_byte()
        if nbt_byte != 0:
            # Skip NBT for now
            pass

        return slot_data

    # ==================== Packet Sending ====================

    async def _send_packet(self, packet_id: int, data: bytes) -> None:
        """Send a packet to the server."""
        if not self._writer:
            return

        packet_data = self._write_varint(packet_id) + data

        # Compress if needed
        if self._compression_threshold >= 0:
            if len(packet_data) >= self._compression_threshold:
                compressed = zlib.compress(packet_data)
                packet_data = self._write_varint(len(packet_data)) + compressed
            else:
                packet_data = self._write_varint(0) + packet_data

        self._writer.write(self._write_varint(len(packet_data)) + packet_data)
        await self._writer.drain()

    # ==================== Public Send Methods ====================

    def send_chat(self, message: str) -> None:
        """Send a chat message packet."""
        data = self._write_string(message)
        data += struct.pack(">Q", 0)  # timestamp
        data += struct.pack(">Q", 0)  # salt
        data += self._write_varint(0)  # signature length
        data += self._write_varint(0)  # message count
        data += bytes(3)  # acknowledged bitset

        asyncio.create_task(self._send_packet(0x06, data))

    async def send_position(self, x: float, y: float, z: float, on_ground: bool = True) -> None:
        """Send player position packet."""
        packet_id = self._get_packet_id("position_serverbound", self._protocol_version)
        data = struct.pack(">dddB", x, y, z, on_ground)
        await self._send_packet(packet_id, data)

    async def send_position_look(
        self, x: float, y: float, z: float, yaw: float, pitch: float, on_ground: bool = True
    ) -> None:
        """Send player position and look packet."""
        packet_id = self._get_packet_id("position_look_serverbound", self._protocol_version)
        data = struct.pack(">dddffB", x, y, z, yaw, pitch, on_ground)
        await self._send_packet(packet_id, data)

    async def send_look(self, yaw: float, pitch: float, on_ground: bool = True) -> None:
        """Send player look packet."""
        packet_id = self._get_packet_id("look_serverbound", self._protocol_version)
        data = struct.pack(">ffB", yaw, pitch, on_ground)
        await self._send_packet(packet_id, data)

    async def send_dig_packet(self, position: dict, action: int, sequence: int = 0) -> None:
        """
        Send player digging packet.

        Args:
            position: Block position {x, y, z}
            action: 0=start, 1=cancel, 2=finish
            sequence: Sequence number for 1.19.3+
        """
        packet_id = self._get_packet_id("player_digging", self._protocol_version)
        data = self._write_varint(action)
        data += self._write_position(position["x"], position["y"], position["z"])
        data += self._write_varint(0)  # face
        data += self._write_varint(sequence)
        await self._send_packet(packet_id, data)

    async def send_block_placement(
        self,
        position: dict,
        face: int = 1,
        hand: int = 0,
        cursor_x: float = 0.5,
        cursor_y: float = 0.5,
        cursor_z: float = 0.5,
        inside_block: bool = False,
        sequence: int = 0,
    ) -> None:
        """Send block placement packet."""
        packet_id = self._get_packet_id("block_placement", self._protocol_version)
        data = self._write_varint(hand)
        data += self._write_position(position["x"], position["y"], position["z"])
        data += self._write_varint(face)
        data += struct.pack(">fff", cursor_x, cursor_y, cursor_z)
        data += self._write_varint(sequence)
        await self._send_packet(packet_id, data)

    async def send_use_item(self, hand: int = 0, sequence: int = 0) -> None:
        """Send use item packet."""
        packet_id = self._get_packet_id("use_item", self._protocol_version)
        data = self._write_varint(hand)
        data += self._write_varint(sequence)
        await self._send_packet(packet_id, data)

    async def send_click_window(
        self,
        window_id: int,
        slot: int,
        button: int,
        mode: int,
        item: dict | None,
        state: int = 0,
    ) -> None:
        """Send window click packet."""
        packet_id = self._get_packet_id("click_window", self._protocol_version)
        data = self._write_varint(window_id)
        data += self._write_varint(state)
        data += struct.pack(">h", slot)
        data += self._write_varint(button)
        data += self._write_varint(mode)
        # Write changed slots (simplified)
        data += self._write_varint(0)  # changed slots count
        # Write carried item
        data += self._write_slot(item)
        await self._send_packet(packet_id, data)

    async def send_close_window(self, window_id: int) -> None:
        """Send close window packet."""
        packet_id = self._get_packet_id("close_window_serverbound", self._protocol_version)
        data = self._write_varint(window_id)
        await self._send_packet(packet_id, data)

    async def send_held_item_change(self, slot: int) -> None:
        """Send held item change packet."""
        packet_id = self._get_packet_id("held_item_change", self._protocol_version)
        data = struct.pack(">h", slot)
        await self._send_packet(packet_id, data)

    async def send_entity_action(self, entity_id: int, action: int, jump_boost: int = 0) -> None:
        """
        Send entity action packet.

        Args:
            entity_id: Player entity ID
            action: 0=start sneaking, 1=stop sneaking, 2=leave bed,
                    3=start sprinting, 4=stop sprinting, 5=start horse jump,
                    6=stop horse jump, 7=open horse inventory, 8=start elytra flying
            jump_boost: Jump boost for horses (0-100)
        """
        packet_id = self._get_packet_id("entity_action", self._protocol_version)
        data = self._write_varint(entity_id)
        data += self._write_varint(action)
        data += self._write_varint(jump_boost)
        await self._send_packet(packet_id, data)

    async def send_interact_entity(
        self, entity_id: int, action: int, hand: int = 0, sneaking: bool = False
    ) -> None:
        """
        Send interact entity packet.

        Args:
            entity_id: Target entity ID
            action: 0=interact, 1=attack, 2=interact at
            hand: Hand to use (0=main, 1=off)
            sneaking: Whether player is sneaking
        """
        packet_id = self._get_packet_id("interact_entity", self._protocol_version)
        data = self._write_varint(entity_id)
        data += self._write_varint(action)

        if action == 0 or action == 2:
            data += self._write_varint(hand)

        data += self._write_boolean(sneaking)
        await self._send_packet(packet_id, data)

    async def send_swing_arm(self, hand: int = 0) -> None:
        """Send swing arm animation packet."""
        packet_id = self._get_packet_id("swing_arm", self._protocol_version)
        data = self._write_varint(hand)
        await self._send_packet(packet_id, data)

    def set_control_state(self, control: str, state: bool) -> None:
        """Set a movement control state."""
        self._control_states[control] = state

    def get_control_state(self, control: str) -> bool:
        """Get a movement control state."""
        return self._control_states.get(control, False)

    def clear_control_states(self) -> None:
        """Clear all movement control states."""
        for control in self._control_states:
            self._control_states[control] = False

    async def activate_block(self, position: Position) -> None:
        """Activate (right-click) a block."""
        await self.send_block_placement(position)

    async def look_at_position(self, target: Vec3) -> None:
        """Look at a target position."""
        eye_pos = Vec3(
            self._bot.position["x"], self._bot.position["y"] + 1.62, self._bot.position["z"]
        )
        direction = target - eye_pos
        horizontal_dist = (direction.x**2 + direction.z**2) ** 0.5

        import math

        yaw = math.degrees(math.atan2(-direction.x, direction.z))
        pitch = math.degrees(math.atan2(-direction.y, horizontal_dist))

        await self.send_look(yaw, pitch)

    # ==================== Packet ID Maps ====================

    def _get_packet_id(self, name: str, protocol_version: int) -> int:
        """Get packet ID for a named packet at a specific protocol version."""
        # Packet IDs for 1.20.4 (765) - default
        packets_765 = {
            "keep_alive_clientbound": 0x24,
            "keep_alive_serverbound": 0x14,
            "join_game": 0x26,
            "player_position": 0x36,
            "chat_message": 0x39,
            "health_update": 0x52,
            "entity_spawn": 0x01,
            "entity_destroy": 0x3D,
            "entity_move": 0x29,
            "chunk_data": 0x24,
            "block_change": 0x09,
            "window_open": 0x2F,
            "window_close": 0x61,
            "window_items": 0x12,
            "set_slot": 0x13,
            "position_serverbound": 0x14,
            "position_look_serverbound": 0x15,
            "look_serverbound": 0x16,
            "player_digging": 0x1C,
            "block_placement": 0x2E,
            "use_item": 0x2F,
            "click_window": 0x0D,
            "close_window_serverbound": 0x0D,
            "held_item_change": 0x1F,
            "entity_action": 0x1C,
            "interact_entity": 0x0E,
            "swing_arm": 0x30,
            "teleport_confirm": 0x00,
        }

        # Packet IDs for 1.21+ (767+)
        packets_767 = {
            "keep_alive_clientbound": 0x26,
            "keep_alive_serverbound": 0x15,
            "join_game": 0x2B,
            "player_position": 0x3B,
            "chat_message": 0x3C,
            "health_update": 0x5B,
            "entity_spawn": 0x01,
            "entity_destroy": 0x3F,
            "entity_move": 0x2B,
            "chunk_data": 0x27,
            "block_change": 0x0A,
            "window_open": 0x31,
            "window_close": 0x68,
            "window_items": 0x13,
            "set_slot": 0x14,
            "position_serverbound": 0x15,
            "position_look_serverbound": 0x16,
            "look_serverbound": 0x17,
            "player_digging": 0x1E,
            "block_placement": 0x30,
            "use_item": 0x31,
            "click_window": 0x0F,
            "close_window_serverbound": 0x0F,
            "held_item_change": 0x20,
            "entity_action": 0x1E,
            "interact_entity": 0x10,
            "swing_arm": 0x32,
            "teleport_confirm": 0x00,
        }

        # Select appropriate packet map
        if protocol_version >= 767:
            return packets_767.get(name, packets_765.get(name, 0))
        return packets_765.get(name, 0)

    # ==================== Utility Methods ====================

    def _get_protocol_version(self, version: str) -> int:
        """Get protocol version number from version string."""
        versions = {
            "1.21.4": 769,
            "1.21.3": 768,
            "1.21.1": 767,
            "1.21": 767,
            "1.20.6": 766,
            "1.20.5": 766,
            "1.20.4": 765,
            "1.20.2": 764,
            "1.20.1": 763,
            "1.19.4": 762,
            "1.19.3": 761,
            "1.19.2": 760,
            "1.18.2": 758,
            "1.17.1": 756,
            "1.16.5": 754,
            "1.15.2": 578,
            "1.14.4": 498,
            "1.13.2": 404,
            "1.12.2": 340,
            "1.11.2": 316,
            "1.10.2": 210,
            "1.9.4": 110,
            "1.8.9": 47,
        }
        return versions.get(version, 765)

    @staticmethod
    def _write_varint(value: int) -> bytes:
        """Write a varint to bytes."""
        result = bytearray()
        while True:
            byte = value & 0x7F
            value >>= 7
            if value:
                result.append(byte | 0x80)
            else:
                result.append(byte)
                break
        return bytes(result)

    @staticmethod
    def _write_varlong(value: int) -> bytes:
        """Write a varlong to bytes."""
        result = bytearray()
        while True:
            byte = value & 0x7F
            value >>= 7
            if value:
                result.append(byte | 0x80)
            else:
                result.append(byte)
                break
        return bytes(result)

    @staticmethod
    def _write_string(value: str, max_length: int = 32767) -> bytes:
        """Write a string to bytes."""
        encoded = value.encode("utf-8")
        if len(encoded) > max_length * 4:
            raise ValueError("String too long")
        return Connection._write_varint(len(encoded)) + encoded

    @staticmethod
    def _write_position(x: int, y: int, z: int) -> bytes:
        """Write a block position to bytes."""
        val = ((x & 0x3FFFFFF) << 38) | ((y & 0xFFF) << 26) | (z & 0x3FFFFFF)
        return struct.pack(">Q", val)

    @staticmethod
    def _write_boolean(value: bool) -> bytes:
        """Write a boolean to bytes."""
        return bytes([1 if value else 0])

    def _write_slot(self, item: dict | None) -> bytes:
        """Write an item slot to bytes."""
        if item is None:
            return self._write_boolean(False)

        data = self._write_boolean(True)
        data += self._write_varint(item.get("id", 0))
        data += struct.pack(">B", item.get("count", 1))
        # NBT (0 for no NBT)
        data += bytes([0])
        return data

    @staticmethod
    def _read_varint_from_bytes(data: bytes) -> int:
        """Read a varint from bytes."""
        result = 0
        shift = 0
        for byte in data:
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7
        return result

    @staticmethod
    def _read_varint_with_offset(data: bytes, offset: int) -> tuple[int, int]:
        """Read a varint from bytes with offset."""
        result = 0
        shift = 0
        while offset < len(data):
            byte = data[offset]
            result |= (byte & 0x7F) << shift
            offset += 1
            if not (byte & 0x80):
                break
            shift += 7
        return result, offset

    async def _read_varint(self) -> int:
        """Read a varint from the stream."""
        result = 0
        shift = 0
        while True:
            byte = await self._reader.readexactly(1)
            b = byte[0]
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        return result

    async def _read_varint_stream(self, reader: asyncio.StreamReader) -> int:
        """Read a varint from a stream."""
        result = 0
        shift = 0
        while True:
            byte = await reader.readexactly(1)
            b = byte[0]
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        return result

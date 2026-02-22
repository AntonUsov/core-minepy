"""Protocol layer - network connection and packet handling."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import struct
from typing import TYPE_CHECKING

from minepy.types import Position

if TYPE_CHECKING:
    from minepy.bot import Bot

logger = logging.getLogger(__name__)


class ConnectionState:
    """Connection state enum."""

    HANDSHAKING = "handshaking"
    STATUS = "status"
    LOGIN = "login"
    PLAY = "play"
    CLOSED = "closed"


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

        logger.debug(
            f"[Connection.__init__] Bot: {bot.username}, Host: {bot.host}:{bot.port}"
        )

        # Control states for movement
        self._control_states: dict[str, bool] = {
            "forward": False,
            "back": False,
            "left": False,
            "right": False,
            "jump": False,
            "sprint": False,
            "sneak": False,
        }

    @property
    def connected(self) -> bool:
        """Check if connection is active."""
        return self._writer is not None and not self._writer.is_closing()

    @property
    def state(self) -> str:
        """Current protocol state."""
        return self._state

    async def connect(self) -> None:
        """Connect to the Minecraft server."""
        logger.debug(
            f"[Connection.connect] Connecting to {self._bot.host}:{self._bot.port}..."
        )
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self._bot.host, self._bot.port
            )
            logger.debug(
                "[Connection.connect] Connection established, starting handshake"
            )
        except OSError as e:
            logger.exception(
                f"[Connection.connect] Failed to connect to {self._bot.host}:{self._bot.port}"
            )
            raise ConnectionError(
                f"Failed to connect to {self._bot.host}:{self._bot.port}: {e}"
            )

        # Auto-detect protocol version if not specified
        if not self._bot.version:
            protocol_version = await self._ping_server()
            if protocol_version:
                self._protocol_version = protocol_version
            else:
                self._protocol_version = 769  # Default to 1.21.4
        else:
            self._protocol_version = self._get_protocol_version(self._bot.version)

        # Perform handshake and login
        await self._handshake()
        await self._login()

        # Start receiving packets
        self._receive_task = asyncio.create_task(self._receive_loop())

        await self._bot.emit("connect")

    async def _ping_server(self) -> int | None:
        """Ping server to get protocol version."""
        import json as json_module

        try:
            # Create new connection for ping
            reader, writer = await asyncio.open_connection(
                self._bot.host, self._bot.port
            )

            # Send handshake for status (state=1)
            data = self._write_varint(769)  # Use latest version for ping
            data += self._write_string(self._bot.host)
            data += struct.pack(">H", self._bot.port)
            data += self._write_varint(1)  # Status state

            await self._send_packet_raw(writer, 0x00, data)

            # Send status request
            await self._send_packet_raw(writer, 0x00, b"")

            # Read response
            length = await self._read_varint_stream(reader)
            packet_data = await reader.readexactly(length)

            # Handle potential compression in status
            packet_id, offset = self._read_varint_from_bytes_with_offset(packet_data, 0)

            if packet_id == 0x00:  # Status response
                json_len, offset = self._read_varint_from_bytes_with_offset(
                    packet_data, offset
                )
                json_data = packet_data[offset : offset + json_len].decode("utf-8")
                status = json_module.loads(json_data)
                protocol = status.get("version", {}).get("protocol", 0)

            writer.close()
            await writer.wait_closed()

            return protocol

        except Exception:
            logger.exception("[Connection._ping_server] Failed to ping server")
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

    async def _handshake(self) -> None:
        """Send handshake packet."""
        # Use detected or configured protocol version
        protocol_version = getattr(self, "_protocol_version", 769)

        # Handshake packet (0x00)
        data = self._write_varint(protocol_version)
        data += self._write_string(self._bot.host)
        data += struct.pack(">H", self._bot.port)
        data += self._write_varint(2)  # Next state: login

        await self._send_packet(0x00, data)
        self._state = ConnectionState.LOGIN

    async def _login(self) -> None:
        """Send login start packet."""
        import uuid as uuid_module

        # Login Start packet (0x00) - 1.21.x format
        # String username + UUID (16 bytes raw, not string!)
        data = self._write_string(self._bot.username)

        # Generate UUID for offline mode based on username
        if self._bot.auth == "offline":
            # Generate deterministic UUID for offline mode
            player_uuid = uuid_module.uuid3(
                uuid_module.NAMESPACE_OID, f"OfflinePlayer:{self._bot.username}"
            )
            data += player_uuid.bytes  # 16 raw bytes
        else:
            # TODO: Microsoft auth - get UUID from auth
            player_uuid = uuid_module.uuid4()
            data += player_uuid.bytes

        await self._send_packet(0x00, data)

    async def _receive_loop(self) -> None:
        """Main loop for receiving packets."""
        logger.debug("[Connection._receive_loop] Starting receive loop")
        try:
            packet_count = 0
            while self.connected:
                packet = await self._read_packet()
                if packet:
                    packet_count += 1
                    logger.debug(
                        f"[Connection._receive_loop] Received packet #{packet_count}: ID=0x{packet[0]:02X}"
                    )
                    await self._handle_packet(packet)
                else:
                    logger.debug("[Connection._receive_loop] No packet received")
        except asyncio.CancelledError:
            logger.debug("[Connection._receive_loop] Receive loop cancelled")
            pass
        except Exception as e:
            logger.exception("[Connection._receive_loop] Exception in receive loop")
            await self._bot.emit("error", e)
            self.disconnect(f"Connection error: {e}")

    async def _read_packet(self) -> tuple[int, bytes] | None:
        """Read a packet from the server."""
        if not self._reader:
            return None

        try:
            # Read packet length
            length = await self._read_varint()
            if length <= 0:
                return None

            # Read packet data
            data = await self._reader.readexactly(length)

            # Decompress if needed
            if self._compression_threshold >= 0:
                data_length = self._read_varint_from_bytes(data)
                data = data[self._varint_size(data_length) :]
                if data_length > 0:
                    import zlib

                    data = zlib.decompress(data)

            # Extract packet ID
            packet_id = self._read_varint_from_bytes(data)
            packet_data = data[self._varint_size(packet_id) :]

            return packet_id, packet_data

        except asyncio.IncompleteReadError:
            logger.debug(
                "[Connection._read_packet] Incomplete read, connection closing"
            )
            return None

    async def _handle_packet(self, packet: tuple[int, bytes]) -> None:
        """Handle a received packet."""
        logger.debug(
            f"[Connection._handle_packet] Called with packet, current state: {self._state}"
        )
        packet_id, data = packet

        if self._state == ConnectionState.LOGIN:
            logger.debug(
                f"[Connection._handle_packet] Calling _handle_login_packet for ID: 0x{packet_id:02X}"
            )
            await self._handle_login_packet(packet_id, data)
        elif self._state == ConnectionState.PLAY:
            logger.debug(
                f"[Connection._handle_packet] Calling _handle_play_packet for ID: 0x{packet_id:02X}"
            )
            await self._handle_play_packet(packet_id, data)
        else:
            logger.warning(f"[Connection._handle_packet] Unknown state: {self._state}")

    async def _handle_login_packet(self, packet_id: int, data: bytes) -> None:
        """Handle login packets."""
        logger.debug(
            f"[Connection._handle_login_packet] Handling packet ID: 0x{packet_id:02X}"
        )
        if packet_id == 0x02:  # Login Success
            self._state = ConnectionState.PLAY
            await self._bot.emit("login")
            logger.debug(
                "[Connection._handle_login_packet] Login successful, state changed to PLAY"
            )
        elif packet_id == 0x01:  # Encryption Request
            # TODO: Implement encryption
            pass
        elif packet_id == 0x03:  # Set Compression
            self._compression_threshold = self._read_varint_from_bytes(data)

    async def _handle_play_packet(self, packet_id: int, data: bytes) -> None:
        """Handle play state packets."""
        logger.debug(
            f"[Connection._handle_play_packet] Handling packet ID: 0x{packet_id:02X}"
        )
        # Packet IDs vary by version. For 1.21.x:
        # 0x2B = Login (Join Game)
        # 0x38 = Synchronize Player Position
        # 0x3C = Player Chat Message

        protocol = getattr(self, "_protocol_version", 765)

        if protocol >= 767:  # 1.21+
            if packet_id == 0x2B:  # Login (Join Game)
                logger.debug(
                    "[Connection._handle_play_packet] Received Join Game packet"
                )
                await self._handle_join_game(data)
            elif packet_id == 0x3B:  # Synchronize Player Position
                await self._handle_player_position(data)
            elif packet_id == 0x3C:  # Player Chat Message
                await self._handle_chat_message(data)
            elif packet_id == 0x26:  # Keep Alive
                pass  # TODO: respond to keep alive
        else:  # 1.20.x and earlier
            if packet_id == 0x26:  # Join Game (1.20.4)
                logger.debug(
                    "[Connection._handle_play_packet] Received Join Game packet (1.20.4)"
                )
                await self._handle_join_game(data)
            elif packet_id == 0x38:  # Player Position (1.20.4)
                await self._handle_player_position(data)
            elif packet_id == 0x3E:  # Chat Message (1.20.4)
                await self._handle_chat_message(data)

        # Emit spawn on any join/login packet
        if packet_id in (0x26, 0x2B, 0x27, 0x25):
            logger.debug(
                f"[Connection._handle_play_packet] Emitting spawn event for packet ID: 0x{packet_id:02X}"
            )
            await self._bot.emit("spawn")

    async def _handle_join_game(self, data: bytes) -> None:
        """Handle join game packet."""
        # Parse join game data (simplified)
        await self._bot.emit("spawn")

    async def _handle_player_position(self, data: bytes) -> None:
        """Handle player position packet."""
        offset = 0
        x = struct.unpack(">d", data[offset : offset + 8])[0]
        offset += 8
        y = struct.unpack(">d", data[offset : offset + 8])[0]
        offset += 8
        z = struct.unpack(">d", data[offset : offset + 8])[0]
        offset += 8

        self._bot.position = {"x": x, "y": y, "z": z}
        self._bot.on_ground = bool(data[offset])

        await self._bot.emit("move", (x, y, z))

    async def _handle_chat_message(self, data: bytes) -> None:
        """Handle chat message packet."""
        # Simplified - would need proper JSON parsing
        logger.debug(
            "[Connection._handle_chat_message] Received chat message (simplified)"
        )
        await self._bot.emit("chat", "Player", "Message", None)

    async def _send_packet(self, packet_id: int, data: bytes) -> None:
        """Send a packet to the server."""
        if not self._writer:
            return

        # Build packet
        packet_data = self._write_varint(packet_id) + data

        # Compress if needed
        if self._compression_threshold >= 0:
            if len(packet_data) >= self._compression_threshold:
                import zlib

                compressed = zlib.compress(packet_data)
                packet_data = self._write_varint(len(packet_data)) + compressed
            else:
                packet_data = self._write_varint(0) + packet_data

        # Send with length prefix
        self._writer.write(self._write_varint(len(packet_data)) + packet_data)
        await self._writer.drain()

    # ==================== Public Methods ====================

    def send_chat(self, message: str) -> None:
        """Send a chat message packet."""
        logger.debug(f"[Connection.send_chat] Sending chat message: {message}")
        # Chat packet format for 1.19.3+ / 1.21.x (0x06)
        data = self._write_string(message)
        data += struct.pack(">Q", 0)  # timestamp = 0
        data += struct.pack(">Q", 0)  # salt = 0
        data += self._write_varint(0)  # signature length = 0 (unsigned)
        data += self._write_varint(0)  # message count = 0
        data += bytes(
            3
        )  # acknowledged = empty fixed bitset (3 bytes for up to 20 bits)
        asyncio.create_task(self._send_packet(0x06, data))

    async def activate_block(self, position: Position) -> None:
        """Activate (right-click) a block."""
        # Player Block Placement packet
        data = struct.pack(
            ">dddBB",
            position["x"],
            position["y"],
            position["z"],
            0,  # Face
            0,  # Hand
        )
        await self._send_packet(0x2E, data)
        logger.debug(f"[Connection.activate_block] Activating block at: {position}")

    def set_control_state(self, control: str, state: bool) -> None:
        """Set a movement control state."""
        self._control_states[control] = state
        self._send_player_state()

    def _send_player_state(self) -> None:
        """Send player state packet based on control states."""
        # Build flags byte
        flags = 0
        if self._control_states["forward"]:
            flags |= 0x01
        if self._control_states["back"]:
            flags |= 0x02
        if self._control_states["left"]:
            flags |= 0x04
        if self._control_states["right"]:
            flags |= 0x08
        if self._control_states["jump"]:
            flags |= 0x10
        # etc.

        # Send Player Input or Client Settings packet
        # This varies by version

    async def look(self, yaw: float, pitch: float) -> None:
        """Send look update packet."""
        # Serverbound Player Rotation packet (0x1B in 1.20.4)
        data = struct.pack(">ffB", yaw, pitch, self._bot.on_ground)
        await self._send_packet(0x1B, data)
        logger.debug(
            f"[Connection.look] Sending look update - Yaw: {yaw}, Pitch: {pitch}"
        )

    # ==================== Utility Methods ====================

    def _get_protocol_version(self, version: str) -> int:
        """Get protocol version number from version string."""
        # Map of version strings to protocol versions
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
        return versions.get(version, -1)

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

    @staticmethod
    def _varint_size(value: int) -> int:
        """Get the size of a varint in bytes."""
        size = 0
        while True:
            value >>= 7
            size += 1
            if value == 0:
                break
        return size

    @staticmethod
    def _write_string(value: str) -> bytes:
        """Write a string to bytes (varint length + UTF-8 data)."""
        encoded = value.encode("utf-8")
        return Connection._write_varint(len(encoded)) + encoded

    @staticmethod
    def _read_varint_from_bytes_with_offset(
        data: bytes, offset: int
    ) -> tuple[int, int]:
        """Read a varint from bytes with offset, return (value, new_offset)."""
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

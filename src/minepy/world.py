"""World class for minepy - equivalent to prismarine-world."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

from minepy.block import Block
from minepy.vec3 import Vec3

if TYPE_CHECKING:
    pass


class Section:
    """A 16x16x16 section of blocks in a chunk."""

    __slots__ = ("y", "blocks", "block_light", "sky_light", "palette", "data")

    def __init__(self, y: int = 0) -> None:
        self.y = y
        # Store blocks as flat array (4096 = 16*16*16)
        # Index = x + (z * 16) + (y * 256) in section coords
        self.blocks: list[int] = [0] * 4096  # Block IDs or state IDs
        self.block_light: bytes = bytes(2048)  # 4 bits per block
        self.sky_light: bytes = bytes(2048)  # 4 bits per block
        self.palette: list[int] | None = None  # For palette-based storage
        self.data: list[int] | None = None  # Raw data for palette mode

    def get_index(self, x: int, y: int, z: int) -> int:
        """Get flat array index from section coordinates."""
        return x + (z * 16) + (y * 256)

    def get_block(self, x: int, y: int, z: int) -> int:
        """Get block ID at section coordinates."""
        if not (0 <= x < 16 and 0 <= y < 16 and 0 <= z < 16):
            return 0  # Air
        return self.blocks[self.get_index(x, y, z)]

    def set_block(self, x: int, y: int, z: int, block_id: int) -> None:
        """Set block ID at section coordinates."""
        if 0 <= x < 16 and 0 <= y < 16 and 0 <= z < 16:
            self.blocks[self.get_index(x, y, z)] = block_id


class Chunk:
    """A 16xWORLD_HEIGHTx16 chunk column."""

    __slots__ = ("x", "z", "sections", "biomes", "block_entities", "min_y", "max_y", "world_height")

    def __init__(self, x: int, z: int, min_y: int = -64, world_height: int = 384) -> None:
        self.x = x
        self.z = z
        self.min_y = min_y
        self.max_y = min_y + world_height
        self.world_height = world_height

        # Calculate number of sections (world_height / 16)
        num_sections = world_height // 16
        self.sections: list[Section | None] = [None] * num_sections

        # Biomes (4x4x4 per section, but stored per column for simplicity)
        self.biomes: list[int] = [0] * 256  # Simplified

        # Block entities (tile entities) in this chunk
        self.block_entities: dict[tuple[int, int, int], dict] = {}

    def get_section_index(self, y: int) -> int:
        """Get section index from world Y coordinate."""
        return (y - self.min_y) // 16

    def get_section(self, y: int) -> Section | None:
        """Get section at world Y coordinate."""
        section_idx = self.get_section_index(y)
        if 0 <= section_idx < len(self.sections):
            return self.sections[section_idx]
        return None

    def get_or_create_section(self, y: int) -> Section:
        """Get or create section at world Y coordinate."""
        section_idx = self.get_section_index(y)
        if 0 <= section_idx < len(self.sections):
            if self.sections[section_idx] is None:
                self.sections[section_idx] = Section(section_idx)
            return self.sections[section_idx]  # type: ignore
        raise IndexError(f"Y coordinate {y} out of range")

    def get_block(self, x: int, y: int, z: int) -> int:
        """Get block ID at chunk coordinates (x: 0-15, y: any, z: 0-15)."""
        section = self.get_section(y)
        if section is None:
            return 0  # Air
        return section.get_block(x & 15, y & 15, z & 15)

    def set_block(self, x: int, y: int, z: int, block_id: int) -> None:
        """Set block ID at chunk coordinates."""
        section = self.get_or_create_section(y)
        section.set_block(x & 15, y & 15, z & 15, block_id)

    def get_block_entity(self, x: int, y: int, z: int) -> dict | None:
        """Get block entity at chunk coordinates."""
        return self.block_entities.get((x, y, z))

    def set_block_entity(self, x: int, y: int, z: int, entity: dict) -> None:
        """Set block entity at chunk coordinates."""
        self.block_entities[(x, y, z)] = entity

    def remove_block_entity(self, x: int, y: int, z: int) -> dict | None:
        """Remove and return block entity at chunk coordinates."""
        return self.block_entities.pop((x, y, z), None)

    def get_biome(self, x: int, y: int, z: int) -> int:
        """Get biome ID at chunk coordinates."""
        # Simplified - real implementation uses 4x4x4 volumes
        idx = (x // 4) + ((z // 4) * 4) + ((y // 4) * 16)
        if 0 <= idx < len(self.biomes):
            return self.biomes[idx]
        return 0

    def set_biome(self, x: int, y: int, z: int, biome_id: int) -> None:
        """Set biome ID at chunk coordinates."""
        idx = (x // 4) + ((z // 4) * 4) + ((y // 4) * 16)
        if 0 <= idx < len(self.biomes):
            self.biomes[idx] = biome_id


class World:
    """
    Represents the Minecraft world with all blocks and entities.

    This class stores chunks and provides methods to access blocks,
    biomes, and entities in the world.
    """

    def __init__(
        self,
        min_y: int = -64,
        world_height: int = 384,
        chunk_radius: int = 8,
    ) -> None:
        self.min_y = min_y
        self.max_y = min_y + world_height
        self.world_height = world_height
        self.chunk_radius = chunk_radius

        # Chunk storage: (chunk_x, chunk_z) -> Chunk
        self._chunks: dict[tuple[int, int], Chunk] = {}

        # Block update listeners
        self._block_update_handlers: list[Callable] = []

    # ==================== Chunk Management ====================

    def get_chunk(self, chunk_x: int, chunk_z: int) -> Chunk | None:
        """Get chunk at chunk coordinates."""
        return self._chunks.get((chunk_x, chunk_z))

    def get_or_create_chunk(self, chunk_x: int, chunk_z: int) -> Chunk:
        """Get or create chunk at chunk coordinates."""
        chunk = self._chunks.get((chunk_x, chunk_z))
        if chunk is None:
            chunk = Chunk(chunk_x, chunk_z, self.min_y, self.world_height)
            self._chunks[(chunk_x, chunk_z)] = chunk
        return chunk

    def load_chunk(self, chunk: Chunk) -> None:
        """Load a chunk into the world."""
        self._chunks[(chunk.x, chunk.z)] = chunk

    def unload_chunk(self, chunk_x: int, chunk_z: int) -> Chunk | None:
        """Unload and return a chunk."""
        return self._chunks.pop((chunk_x, chunk_z), None)

    def has_chunk(self, chunk_x: int, chunk_z: int) -> bool:
        """Check if a chunk is loaded."""
        return (chunk_x, chunk_z) in self._chunks

    def get_chunks(self) -> Iterator[Chunk]:
        """Iterate over all loaded chunks."""
        return iter(self._chunks.values())

    def get_chunk_count(self) -> int:
        """Get the number of loaded chunks."""
        return len(self._chunks)

    # ==================== Block Access ====================

    def block_at(self, x: int, y: int, z: int) -> Block:
        """Get block at world coordinates."""
        if y < self.min_y or y >= self.max_y:
            return Block.create_air(Vec3(x, y, z))

        chunk_x = x >> 4
        chunk_z = z >> 4
        chunk = self.get_chunk(chunk_x, chunk_z)

        if chunk is None:
            return Block.create_air(Vec3(x, y, z))

        block_id = chunk.get_block(x & 15, y, z & 15)
        position = Vec3(x, y, z)

        block = Block(id=block_id, position=position)

        # Attach block entity if present
        block_entity = chunk.get_block_entity(x & 15, y, z & 15)
        if block_entity:
            block.block_entity = block_entity

        return block

    def set_block(self, x: int, y: int, z: int, block_id: int) -> None:
        """Set block at world coordinates."""
        if y < self.min_y or y >= self.max_y:
            return

        chunk = self.get_or_create_chunk(x >> 4, z >> 4)
        old_block_id = chunk.get_block(x & 15, y, z & 15)
        chunk.set_block(x & 15, y, z & 15, block_id)

        # Notify listeners
        old_block = Block(id=old_block_id, position=Vec3(x, y, z))
        new_block = Block(id=block_id, position=Vec3(x, y, z))
        self._emit_block_update(old_block, new_block)

    def set_block_state(self, x: int, y: int, z: int, state_id: int) -> None:
        """Set block state at world coordinates (for 1.13+)."""
        # In 1.13+, we store state IDs directly
        self.set_block(x, y, z, state_id)

    def set_block_entity(self, x: int, y: int, z: int, entity: dict) -> None:
        """Set block entity (tile entity) at world coordinates."""
        chunk = self.get_or_create_chunk(x >> 4, z >> 4)
        chunk.set_block_entity(x & 15, y, z & 15, entity)

    def remove_block_entity(self, x: int, y: int, z: int) -> dict | None:
        """Remove block entity at world coordinates."""
        chunk = self.get_chunk(x >> 4, z >> 4)
        if chunk:
            return chunk.remove_block_entity(x & 15, y, z & 15)
        return None

    # ==================== Biome Access ====================

    def get_biome(self, x: int, y: int, z: int) -> int:
        """Get biome ID at world coordinates."""
        chunk = self.get_chunk(x >> 4, z >> 4)
        if chunk:
            return chunk.get_biome(x & 15, y, z & 15)
        return 0  # Default biome (plains in most versions)

    def set_biome(self, x: int, y: int, z: int, biome_id: int) -> None:
        """Set biome ID at world coordinates."""
        chunk = self.get_or_create_chunk(x >> 4, z >> 4)
        if chunk:
            chunk.set_biome(x & 15, y, z & 15, biome_id)

    # ==================== Block Finding ====================

    def find_blocks(
        self,
        matching: Callable[[Block], bool] | set[int] | int,
        point: Vec3,
        radius: int = 16,
        count: int = -1,
        extra_info: bool = False,
    ) -> list[Vec3]:
        """
        Find blocks matching criteria within radius of point.

        Args:
            matching: Block ID(s) or predicate function
            point: Center point to search around
            radius: Search radius in blocks
            count: Maximum results (-1 for all)
            extra_info: Include additional info (not implemented)

        Returns:
            List of positions where matching blocks were found
        """
        results = []

        # Determine predicate
        if isinstance(matching, int):
            block_ids = {matching}
            predicate = lambda b: b.id in block_ids
        elif isinstance(matching, set):
            predicate = lambda b: b.id in matching
        else:
            predicate = matching

        # Search in chunks within radius
        min_x = int(point.x) - radius
        max_x = int(point.x) + radius
        min_y = max(self.min_y, int(point.y) - radius)
        max_y = min(self.max_y - 1, int(point.y) + radius)
        min_z = int(point.z) - radius
        max_z = int(point.z) + radius

        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                for z in range(min_z, max_z + 1):
                    if count > 0 and len(results) >= count:
                        return results

                    block = self.block_at(x, y, z)
                    if predicate(block):
                        results.append(Vec3(x, y, z))

        return results

    def find_block(
        self,
        matching: Callable[[Block], bool] | set[int] | int,
        point: Vec3,
        radius: int = 16,
    ) -> Vec3 | None:
        """Find the nearest matching block."""
        results = self.find_blocks(matching, point, radius, count=1)
        return results[0] if results else None

    # ==================== Visibility ====================

    def can_see_block(self, block: Block) -> bool:
        """Check if a block is visible (not surrounded by solid blocks)."""
        x, y, z = int(block.position.x), int(block.position.y), int(block.position.z)

        # Check all 6 adjacent blocks
        for dx, dy, dz in [(0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)]:
            adjacent = self.block_at(x + dx, y + dy, z + dz)
            if not adjacent.is_solid or adjacent.is_transparent:
                return True
        return False

    def is_block_loaded(self, x: int, y: int, z: int) -> bool:
        """Check if the chunk containing this block is loaded."""
        return self.has_chunk(x >> 4, z >> 4)

    # ==================== Block Updates ====================

    def on_block_update(self, handler: Callable) -> None:
        """Register a block update handler."""
        self._block_update_handlers.append(handler)

    def remove_block_update_handler(self, handler: Callable) -> None:
        """Remove a block update handler."""
        if handler in self._block_update_handlers:
            self._block_update_handlers.remove(handler)

    def _emit_block_update(self, old_block: Block, new_block: Block) -> None:
        """Emit block update event to all handlers."""
        for handler in self._block_update_handlers:
            try:
                result = handler(old_block, new_block)
                # Handle async handlers
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)  # type: ignore
            except Exception:
                pass  # Don't let handler errors propagate

    # ==================== Utility ====================

    def clear(self) -> None:
        """Clear all chunks from the world."""
        self._chunks.clear()

    def get_spawn_height(self, x: int, z: int) -> int:
        """Get the spawn height at the given x, z coordinates."""
        # Simple implementation: find highest non-air block
        for y in range(self.max_y - 1, self.min_y, -1):
            block = self.block_at(x, y, z)
            if block.id != 0:  # Not air
                return y + 1
        return self.min_y + 1

    def __repr__(self) -> str:
        return f"World(chunks={len(self._chunks)}, y_range=({self.min_y}, {self.max_y}))"


# Alias for compatibility
WorldColumn = Chunk

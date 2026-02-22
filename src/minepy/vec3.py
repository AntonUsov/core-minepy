"""3D Vector class for minepy - equivalent to prismarine-vec3."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, SupportsFloat, SupportsIndex, overload

if TYPE_CHECKING:
    from collections.abc import Iterator


class Vec3:
    """
    A 3D vector class for positions and directions in Minecraft.

    Coordinates:
    - x: east/west (positive = east)
    - y: up/down (positive = up)
    - z: south/north (positive = south)
    """

    __slots__ = ("x", "y", "z")

    def __init__(
        self,
        x: SupportsFloat | SupportsIndex = 0,
        y: SupportsFloat | SupportsIndex = 0,
        z: SupportsFloat | SupportsIndex = 0,
    ) -> None:
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    @classmethod
    def from_dict(cls, d: dict) -> Vec3:
        """Create Vec3 from dictionary with x, y, z keys."""
        return cls(d.get("x", 0), d.get("y", 0), d.get("z", 0))

    @classmethod
    def from_tuple(cls, t: tuple) -> Vec3:
        """Create Vec3 from tuple (x, y, z)."""
        return cls(t[0] if len(t) > 0 else 0, t[1] if len(t) > 1 else 0, t[2] if len(t) > 2 else 0)

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {"x": self.x, "y": self.y, "z": self.z}

    def to_tuple(self) -> tuple[float, float, float]:
        """Convert to tuple."""
        return (self.x, self.y, self.z)

    def to_block_pos(self) -> Vec3:
        """Get block position (floored coordinates)."""
        return Vec3(math.floor(self.x), math.floor(self.y), math.floor(self.z))

    def to_chunk_pos(self) -> tuple[int, int]:
        """Get chunk position (chunk x, chunk z)."""
        return (math.floor(self.x) >> 4, math.floor(self.z) >> 4)

    def to_section_pos(self) -> tuple[int, int, int]:
        """Get section position within chunk."""
        return (
            math.floor(self.x) & 15,
            math.floor(self.y) & 15,
            math.floor(self.z) & 15,
        )

    # ==================== Arithmetic Operations ====================

    def __add__(self, other: Vec3 | tuple) -> Vec3:
        if isinstance(other, Vec3):
            return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)
        return Vec3(self.x + other[0], self.y + other[1], self.z + other[2])

    def __radd__(self, other: Vec3 | tuple) -> Vec3:
        return self.__add__(other)

    def __sub__(self, other: Vec3 | tuple) -> Vec3:
        if isinstance(other, Vec3):
            return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)
        return Vec3(self.x - other[0], self.y - other[1], self.z - other[2])

    def __rsub__(self, other: Vec3 | tuple) -> Vec3:
        if isinstance(other, Vec3):
            return Vec3(other.x - self.x, other.y - self.y, other.z - self.z)
        return Vec3(other[0] - self.x, other[1] - self.y, other[2] - self.z)

    @overload
    def __mul__(self, other: float) -> Vec3: ...
    @overload
    def __mul__(self, other: Vec3) -> Vec3: ...

    def __mul__(self, other: float | Vec3) -> Vec3:
        if isinstance(other, Vec3):
            return Vec3(self.x * other.x, self.y * other.y, self.z * other.z)
        return Vec3(self.x * other, self.y * other, self.z * other)

    @overload
    def __rmul__(self, other: float) -> Vec3: ...
    @overload
    def __rmul__(self, other: Vec3) -> Vec3: ...

    def __rmul__(self, other: float | Vec3) -> Vec3:
        return self.__mul__(other)

    @overload
    def __truediv__(self, other: float) -> Vec3: ...
    @overload
    def __truediv__(self, other: Vec3) -> Vec3: ...

    def __truediv__(self, other: float | Vec3) -> Vec3:
        if isinstance(other, Vec3):
            return Vec3(self.x / other.x, self.y / other.y, self.z / other.z)
        return Vec3(self.x / other, self.y / other, self.z / other)

    @overload
    def __floordiv__(self, other: float) -> Vec3: ...
    @overload
    def __floordiv__(self, other: Vec3) -> Vec3: ...

    def __floordiv__(self, other: float | Vec3) -> Vec3:
        if isinstance(other, Vec3):
            return Vec3(self.x // other.x, self.y // other.y, self.z // other.z)
        return Vec3(self.x // other, self.y // other, self.z // other)

    def __mod__(self, other: float) -> Vec3:
        return Vec3(self.x % other, self.y % other, self.z % other)

    def __neg__(self) -> Vec3:
        return Vec3(-self.x, -self.y, -self.z)

    def __abs__(self) -> Vec3:
        return Vec3(abs(self.x), abs(self.y), abs(self.z))

    # ==================== Comparison Operations ====================

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Vec3):
            return self.x == other.x and self.y == other.y and self.z == other.z
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: Vec3) -> bool:
        return (self.x, self.y, self.z) < (other.x, other.y, other.z)

    def __le__(self, other: Vec3) -> bool:
        return (self.x, self.y, self.z) <= (other.x, other.y, other.z)

    def __gt__(self, other: Vec3) -> bool:
        return (self.x, self.y, self.z) > (other.x, other.y, other.z)

    def __ge__(self, other: Vec3) -> bool:
        return (self.x, self.y, self.z) >= (other.x, other.y, other.z)

    # ==================== Vector Operations ====================

    def dot(self, other: Vec3) -> float:
        """Dot product of two vectors."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vec3) -> Vec3:
        """Cross product of two vectors."""
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length(self) -> float:
        """Get the length (magnitude) of the vector."""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def length_squared(self) -> float:
        """Get the squared length of the vector (faster than length())."""
        return self.x**2 + self.y**2 + self.z**2

    def distance_to(self, other: Vec3) -> float:
        """Get the Euclidean distance to another vector."""
        return (self - other).length()

    def distance_to_squared(self, other: Vec3) -> float:
        """Get the squared distance to another vector (faster than distance_to())."""
        return (self - other).length_squared()

    def manhattan_distance_to(self, other: Vec3) -> float:
        """Get the Manhattan distance to another vector."""
        return abs(self.x - other.x) + abs(self.y - other.y) + abs(self.z - other.z)

    def horizontal_distance_to(self, other: Vec3) -> float:
        """Get the horizontal distance (ignoring Y) to another vector."""
        dx = self.x - other.x
        dz = self.z - other.z
        return math.sqrt(dx * dx + dz * dz)

    def normalize(self) -> Vec3:
        """Return a unit vector in the same direction."""
        length = self.length()
        if length == 0:
            return Vec3(0, 0, 0)
        return Vec3(self.x / length, self.y / length, self.z / length)

    def scale(self, factor: float) -> Vec3:
        """Scale the vector by a factor."""
        return Vec3(self.x * factor, self.y * factor, self.z * factor)

    def floor(self) -> Vec3:
        """Return a vector with floored components."""
        return Vec3(math.floor(self.x), math.floor(self.y), math.floor(self.z))

    def ceil(self) -> Vec3:
        """Return a vector with ceiled components."""
        return Vec3(math.ceil(self.x), math.ceil(self.y), math.ceil(self.z))

    def round(self, ndigits: int | None = None) -> Vec3:
        """Return a vector with rounded components."""
        return Vec3(
            round(self.x, ndigits) if ndigits else round(self.x),
            round(self.y, ndigits) if ndigits else round(self.y),
            round(self.z, ndigits) if ndigits else round(self.z),
        )

    def offset(self, dx: float, dy: float, dz: float) -> Vec3:
        """Return a new vector offset by the given values."""
        return Vec3(self.x + dx, self.y + dy, self.z + dz)

    # ==================== Utility Methods ====================

    def clone(self) -> Vec3:
        """Return a copy of this vector."""
        return Vec3(self.x, self.y, self.z)

    def set(self, x: float, y: float, z: float) -> Vec3:
        """Set the components of this vector (mutating)."""
        self.x = x
        self.y = y
        self.z = z
        return self

    def update(self, other: Vec3) -> Vec3:
        """Update this vector from another vector (mutating)."""
        self.x = other.x
        self.y = other.y
        self.z = other.z
        return self

    def __repr__(self) -> str:
        return f"Vec3({self.x}, {self.y}, {self.z})"

    def __str__(self) -> str:
        return f"({self.x}, {self.y}, {self.z})"

    def __hash__(self) -> int:
        return hash((self.x, self.y, self.z))

    def __iter__(self) -> Iterator[float]:
        yield self.x
        yield self.y
        yield self.z

    def __getitem__(self, index: int) -> float:
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        elif index == 2:
            return self.z
        raise IndexError("Vec3 index out of range")

    def __len__(self) -> int:
        return 3

    # ==================== Direction Vectors ====================

    @classmethod
    @property
    def ZERO(cls) -> Vec3:
        return Vec3(0, 0, 0)

    @classmethod
    @property
    def UP(cls) -> Vec3:
        return Vec3(0, 1, 0)

    @classmethod
    @property
    def DOWN(cls) -> Vec3:
        return Vec3(0, -1, 0)

    @classmethod
    @property
    def NORTH(cls) -> Vec3:
        return Vec3(0, 0, -1)

    @classmethod
    @property
    def SOUTH(cls) -> Vec3:
        return Vec3(0, 0, 1)

    @classmethod
    @property
    def EAST(cls) -> Vec3:
        return Vec3(1, 0, 0)

    @classmethod
    @property
    def WEST(cls) -> Vec3:
        return Vec3(-1, 0, 0)


# Direction constants for face vectors
FACES: list[Vec3] = [
    Vec3(0, 1, 0),  # Top
    Vec3(0, -1, 0),  # Bottom
    Vec3(0, 0, 1),  # Front/South
    Vec3(0, 0, -1),  # Back/North
    Vec3(1, 0, 0),  # Right/East
    Vec3(-1, 0, 0),  # Left/West
]

# Named directions
UP = Vec3(0, 1, 0)
DOWN = Vec3(0, -1, 0)
NORTH = Vec3(0, 0, -1)
SOUTH = Vec3(0, 0, 1)
EAST = Vec3(1, 0, 0)
WEST = Vec3(-1, 0, 0)

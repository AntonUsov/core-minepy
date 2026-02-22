"""Physics engine for Minecraft movement."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from minepy.vec3 import Vec3

if TYPE_CHECKING:
    from minepy.bot import Bot


class Physics:
    """
    Physics engine for Minecraft movement.

    Handles gravity, collision detection, and movement simulation.
    """

    # Physics constants
    GRAVITY = 0.08
    TERMINAL_VELOCITY = 3.92
    JUMP_VELOCITY = 0.42
    MOVE_SPEED = 0.1
    SPRINT_MULTIPLIER = 1.3
    SNEAK_MULTIPLIER = 0.3
    FALL_DISTANCE = 3.0

    def __init__(self, bot: Bot) -> None:
        """Initialize physics engine."""
        self._bot = bot
        self._velocity: Vec3 = Vec3(0, 0, 0)
        self._on_ground = False
        self._last_position: Vec3 | None = None

    @property
    def velocity(self) -> Vec3:
        """Get current velocity."""
        return self._velocity

    @property
    def on_ground(self) -> bool:
        """Check if player is on ground."""
        return self._on_ground

    def update(self) -> None:
        """Update physics simulation."""
        # Apply gravity
        if not self._on_ground:
            self._velocity.y -= self.GRAVITY
            if self._velocity.y < -self.TERMINAL_VELOCITY:
                self._velocity.y = -self.TERMINAL_VELOCITY

        # Update position based on velocity
        new_position = self._calculate_next_position()

        # Check collision and resolve
        resolved_position = self._resolve_collision(new_position)

        # Update actual position
        dx = resolved_position.x - self._bot.position["x"]
        dy = resolved_position.y - self._bot.position["y"]
        dz = resolved_position.z - self._bot.position["z"]

        self._bot.position["x"] += dx
        self._bot.position["y"] += dy
        self._bot.position["z"] += dz

        # Update on_ground status
        self._on_ground = dy >= 0 or resolved_position.y == self._bot.position["y"]

        self._last_position = Vec3(
            self._bot.position["x"], self._bot.position["y"], self._bot.position["z"]
        )

    def _calculate_next_position(self) -> Vec3:
        """Calculate next position based on velocity."""
        # Get movement input
        speed = self.MOVE_SPEED
        if self._bot._connection:
            # Check sprint
            if self._bot._connection.get_control_state("sprint"):
                speed *= self.SPRINT_MULTIPLIER
            # Check sneak
            elif self._bot._connection.get_control_state("sneak"):
                speed *= self.SNEAK_MULTIPLIER

        # Calculate horizontal velocity
        forward = 0
        right = 0
        if self._bot._connection:
            forward = 1 if self._bot._connection.get_control_state("forward") else 0
            forward -= 1 if self._bot._connection.get_control_state("back") else 0
            right = 1 if self._bot._connection.get_control_state("right") else 0
            right -= 1 if self._bot._connection.get_control_state("left") else 0

        # Calculate velocity vector
        vx = forward * speed
        vz = right * speed

        # Convert yaw to direction
        if self._bot.yaw != 0:
            rad_yaw = math.radians(self._bot.yaw)
            vx = (math.sin(rad_yaw) * forward) + (math.cos(rad_yaw) * right)
            vz = (math.cos(rad_yaw) * forward) - (math.sin(rad_yaw) * right)

        # Apply horizontal velocity
        self._velocity.x = vx
        self._velocity.z = vz

        # Apply vertical velocity (including jump)
        if self._bot._connection:
            if self._bot._connection.get_control_state("jump") and self._on_ground:
                self._velocity.y = self.JUMP_VELOCITY

        return Vec3(self._velocity.x, self._velocity.y, self._velocity.z)

    def _resolve_collision(self, new_position: Vec3) -> Vec3:
        """Resolve collisions with solid blocks."""
        # Simple AABB collision detection
        x = self._bot.position["x"]
        y = self._bot.position["y"]
        z = self._bot.position["z"]
        width = 0.6  # Player width
        height = 1.8  # Player height
        eye_height = 1.62  # Eye level

        # Check horizontal collisions
        left = Vec3(new_position.x - width, y, new_position.z)
        right = Vec3(new_position.x + width, y, new_position.z)
        forward = Vec3(new_position.x, y, new_position.z + width)
        back = Vec3(new_position.x, y, new_position.z - width)

        if self._is_solid_block(left) or self._is_solid_block(right):
            self._velocity.x = 0
            new_position.x = self._bot.position["x"]
        if self._is_solid_block(forward) or self._is_solid_block(back):
            self._velocity.z = 0
            new_position.z = self._bot.position["z"]

        # Check vertical collisions
        head = Vec3(new_position.x, y + eye_height, new_position.z)
        feet = Vec3(new_position.x, y, new_position.z)
        ground = Vec3(new_position.x, y - height, new_position.z)

        if self._is_solid_block(head):
            self._velocity.y = 0
            new_position.y = self._bot.position["y"] + eye_height

        if self._is_solid_block(ground):
            if self._velocity.y < 0:
                self._on_ground = True
            self._velocity.y = 0
            new_position.y = max(ground.y, self._bot.position["y"])
        elif self._is_solid_block(feet) and self._velocity.y > 0:
            # Hit ceiling
            self._velocity.y = 0
            new_position.y = self._bot.position["y"] - height

        return new_position

    def _is_solid_block(self, position: Vec3) -> bool:
        """Check if a position intersects with a solid block."""
        # Convert to block coordinates
        x, y, z = int(position.x), int(position.y), int(position.z)

        try:
            block = self._bot.world.get_block(x, y, z)
            return block.is_solid if block else False
        except Exception:
            # If block lookup fails, assume solid (safety)
            return True

    def set_velocity(self, x: float, y: float, z: float) -> None:
        """Set velocity directly."""
        self._velocity = Vec3(x, y, z)

    def get_next_position(self) -> Vec3:
        """Get next position without applying changes."""
        return self._calculate_next_position()

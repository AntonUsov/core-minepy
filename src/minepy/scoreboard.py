"""Scoreboard and teams system for Minecraft."""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ScoreboardObjectiveType(str, Enum):
    """Objective display types."""

    INTEGER = "integer"
    BEHEMOTH = "behemoth"
    HEARTS = "hearts"
    SLIDER = "slider"
    EQUATION = "equation"
    QUESTION = "question"


class TeamColor(str, Enum):
    """Team colors."""

    WHITE = "white"
    ORANGE = "orange"
    MAGENTA = "magenta"
    LIGHT_BLUE = "light_blue"
    YELLOW = "yellow"
    LIME = "lime"
    PINK = "pink"
    GRAY = "gray"
    LIGHT_GRAY = "light_gray"
    CYAN = "cyan"
    PURPLE = "purple"
    BLUE = "blue"
    BROWN = "brown"
    GREEN = "green"
    RED = "red"
    BLACK = "black"


class CollisionRule(str, Enum):
    """Collision rules."""

    ALWAYS = "always"
    NEVER = "never"
    PUSH_OTHERS = "push_others"
    PUSH_TEAMS = "push_teams"


class Scoreboard:
    """
    Manages scoreboard objectives and scores.

    Provides methods to track and display scores for players.
    """

    def __init__(self, bot) -> None:
        """Initialize scoreboard system."""
        self._bot = bot
        self._objectives: dict[str, dict] = {}
        self._scores: dict[str, dict[str, int]] = {}  # player -> score

    def get_objectives(self) -> list[dict]:
        """Get all scoreboard objectives."""
        return list(self._objectives.values())

    def get_scores(self, player: str) -> list[dict]:
        """Get all scores for a player."""
        if player not in self._scores:
            return []
        return [{"objective": name, "score": score} for name, score in self._scores[player].items()]

    def get_score(self, player: str, objective: str) -> int:
        """Get score for a player on a specific objective."""
        if player not in self._scores or objective not in self._scores[player]:
            return 0
        return self._scores[player][objective]

    def create_objective(
        self,
        name: str,
        display_name: str,
        objective_type: ScoreboardObjectiveType = ScoreboardObjectiveType.INTEGER,
    ) -> None:
        """
        Create a new scoreboard objective.

        Args:
            name: Objective name (must be alphanumeric and 16 chars max)
            display_name: Display name (can be JSON text component)
            objective_type: Type of objective
        """
        if name in self._objectives:
            raise ValueError(f"Objective {name} already exists")

        self._objectives[name] = {
            "name": name,
            "display_name": display_name,
            "type": objective_type,
        }

        logger.debug(f"Created objective {name}")

    def remove_objective(self, name: str) -> None:
        """Remove a scoreboard objective."""
        if name not in self._objectives:
            raise ValueError(f"Objective {name} does not exist")

        # Remove scores associated with this objective
        if name in self._scores:
            for player in list(self._scores.keys()):
                if name in self._scores[player]:
                    del self._scores[player][name]

        del self._objectives[name]
        logger.debug(f"Removed objective {name}")

    def set_score(self, player: str, objective: str, score: int) -> None:
        """Set a player's score on an objective."""
        if objective not in self._objectives:
            raise ValueError(f"Objective {objective} does not exist")

        if player not in self._scores:
            self._scores[player] = {}

        self._scores[player][objective] = score
        logger.debug(f"Set score for {player} on {objective}: {score}")

    def reset_score(self, player: str, objective: str) -> None:
        """Reset a player's score to 0."""
        if player in self._scores and objective in self._scores[player]:
            del self._scores[player][objective]

    def reset_scores(self, player: str) -> None:
        """Reset all scores for a player."""
        if player in self._scores:
            del self._scores[player]

    def get_objective_display_name(self, objective: str) -> str:
        """Get display name of an objective."""
        return self._objectives.get(objective, {}).get("display_name", objective)

    def get_objective_type(self, objective: str) -> ScoreboardObjectiveType:
        """Get type of an objective."""
        return self._objectives.get(objective, {}).get("type", ScoreboardObjectiveType.INTEGER)


class Team:
    """
    Manages Minecraft teams.

    Teams provide grouping, collision rules, prefix/suffix, and display colors.
    """

    def __init__(self, bot) -> None:
        """Initialize team system."""
        self._bot = bot
        self._teams: dict[str, dict] = {}

    def create_team(
        self,
        name: str,
        display_name: str = "",
        color: TeamColor = TeamColor.WHITE,
        collision_rule: CollisionRule = CollisionRule.PUSH_OTHERS,
    ) -> None:
        """
        Create a new team.

        Args:
            name: Team name (must be alphanumeric and 16 chars max)
            display_name: Display name
            color: Team color
            collision_rule: Collision rule for this team
        """
        if name in self._teams:
            raise ValueError(f"Team {name} already exists")

        self._teams[name] = {
            "name": name,
            "display_name": display_name,
            "color": color,
            "collision_rule": collision_rule,
            "members": set(),
            "prefix": "",
            "suffix": "",
        }

        logger.debug(f"Created team {name}")

    def remove_team(self, name: str) -> None:
        """Remove a team."""
        if name not in self._teams:
            raise ValueError(f"Team {name} does not exist")

        # Remove team from all players
        for player in list(self._teams[name]["members"]):
            self._teams[name]["members"].discard(player)

        del self._teams[name]
        logger.debug(f"Removed team {name}")

    def add_member(self, name: str) -> None:
        """Add a member to a team."""
        if name not in self._teams:
            raise ValueError("Team does not exist")

        self._teams[name]["members"].add(name)
        logger.debug(f"Added {name} to team {name}")

    def remove_member(self, name: str) -> None:
        """Remove a member from a team."""
        for team in self._teams.values():
            if name in team["members"]:
                team["members"].discard(name)
                break

    def set_prefix(self, name: str, prefix: str) -> None:
        """Set team prefix."""
        if name not in self._teams:
            raise ValueError(f"Team {name} does not exist")

        self._teams[name]["prefix"] = prefix
        logger.debug(f"Set prefix for team {name}")

    def set_suffix(self, name: str, suffix: str) -> None:
        """Set team suffix."""
        if name not in self._teams:
            raise ValueError(f"Team {name} does not exist")

        self._teams[name]["suffix"] = suffix
        logger.debug(f"Set suffix for team {name}")

    def set_color(self, name: str, color: TeamColor) -> None:
        """Set team color."""
        if name not in self._teams:
            raise ValueError(f"Team {name} does not exist")

        self._teams[name]["color"] = color
        logger.debug(f"Set color for team {name}")

    def set_collision_rule(self, name: str, rule: CollisionRule) -> None:
        """Set collision rule."""
        if name not in self._teams:
            raise ValueError(f"Team {name} does not exist")

        self._teams[name]["collision_rule"] = rule
        logger.debug(f"Set collision rule for team {name}")

    def get_members(self, name: str) -> list[str]:
        """Get team members."""
        if name not in self._teams:
            raise ValueError(f"Team {name} does not exist")
        return list(self._teams[name]["members"])

    def get_all_teams(self) -> list[dict]:
        """Get all teams."""
        return list(self._teams.values())

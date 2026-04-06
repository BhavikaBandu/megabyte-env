"""
Data models for the Megabyte Environment.

Megabyte is a specialized OpenEnv environment designed for Agentic Reinforcement Learning.
It simulates a complex software supply chain, challenging agents to resolve security
vulnerabilities while navigating dependency graphs.
"""

from typing import Any, Dict, List, Literal, Optional

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


class MegabyteAction(Action):
    """Action for the Megabyte environment."""

    command: Literal["UPGRADE", "DOWNGRADE", "REVERT", "RESET"] = Field(
        ...,
        description="Operation to be performed by the agent.",
    )
    package_id: Optional[str] = Field(
        None,
        description="The package to target. Required for upgrade and downgrade actions.",
    )
    target_version: Optional[str] = Field(
        None,
        description="The version to move to. Only used for upgrade/downgrade.",
    )


class MegabyteObservation(Observation):
    """Observation returned to the agent after each step."""

    status: Literal["SUCCESS", "FAILURE"] = Field(
        ...,
        description="Build status.",
    )
    log: str = Field(
        default="",
        description="Logs related to the build or dependency conflicts.",
    )
    current_manifest: Dict[str, str] = Field(
        ...,
        description="The current version of all packages.",
    )
    attempts_remaining: int = Field(
        ...,
        description="Steps left before the episode ends.",
    )


class MegabyteState(State):
    """Internal state of the Megabyte environment."""

    episode_id: str = Field(
        ...,
        description="Unique identifier for the current episode.",
    )
    step_count: int = Field(
        ...,
        description="Number of steps taken in the current episode.",
    )
    initial_manifest: Dict[str, str] = Field(
        ...,
        description="Original snapshot used for reset/revert behavior.",
    )
    current_manifest: Dict[str, str] = Field(
        ...,
        description="Current active environment state.",
    )
    available_versions: Dict[str, List[str]] = Field(
        ...,
        description="All possible versions for each package.",
    )
    dependency_rules: Dict[str, Any] = Field(
        ...,
        description="Dependency constraint graph.",
    )
    vulnerabilities: List[Dict[str, Any]] = Field(
        ...,
        description="Known vulnerabilities grouped by package.",
    )
    max_attempts: int = Field(
        default=25,
        description="Maximum number of steps allowed per episode.",
    )
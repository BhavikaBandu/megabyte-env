"""
Data models for the Megabyte Environment.

Megabyte is an OpenEnv environment for dependency management and security repair.
It simulates a software supply chain where agents must diagnose dependency issues,
repair broken manifests, and remove vulnerabilities.
"""

from typing import Any, Dict, List, Literal, Optional

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


class MegabyteAction(Action):
    """Action for the Megabyte environment."""

    command: Literal["CLASSIFY", "UPGRADE", "DOWNGRADE", "REVERT", "RESET"] = Field(
        ...,
        description=(
            "Operation to perform. "
            "CLASSIFY is used for the easy task. "
            "UPGRADE/DOWNGRADE/REVERT/RESET are used for repair tasks."
        ),
    )

    package_id: Optional[str] = Field(
        None,
        description=(
            "Target package name. Used by UPGRADE, DOWNGRADE, and REVERT. "
            "Not used for CLASSIFY or RESET."
        ),
    )

    target_version: Optional[str] = Field(
        None,
        description=(
            "Target version for UPGRADE or DOWNGRADE. "
            "Not used for CLASSIFY, REVERT, or RESET."
        ),
    )

    label: Optional[Literal[
        "safe_and_stable",
        "stable_but_insecure",
        "broken_but_secure",
        "broken_and_insecure",
    ]] = Field(
        None,
        description=(
            "Classification label for the CLASSIFY action in the easy task."
        ),
    )


class MegabyteObservation(Observation):
    """Observation returned to the agent after each step."""

    status: Literal["SUCCESS", "FAILURE"] = Field(
        ...,
        description="Build status after evaluating the current manifest.",
    )

    log: str = Field(
        default="",
        description="Logs related to dependency conflicts or environment feedback.",
    )

    current_manifest: Dict[str, str] = Field(
        ...,
        description="Current installed version of each package.",
    )

    attempts_remaining: int = Field(
        ...,
        description="Number of steps remaining before the episode ends.",
    )

    task_id: Optional[str] = Field(
        default=None,
        description="Identifier of the currently active task.",
    )

    last_action_error: Optional[str] = Field(
        default=None,
        description="Error message for the last invalid action, if any.",
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

    task_id: Optional[str] = Field(
        default=None,
        description="Identifier of the currently active task.",
    )

    initial_manifest: Dict[str, str] = Field(
        ...,
        description="Initial manifest snapshot used for RESET/REVERT behavior.",
    )

    current_manifest: Dict[str, str] = Field(
        ...,
        description="Current active manifest state.",
    )

    available_versions: Dict[str, List[str]] = Field(
        ...,
        description="All allowed versions for each package.",
    )

    dependency_rules: Dict[str, Any] = Field(
        ...,
        description="Dependency constraint graph for the current environment.",
    )

    vulnerabilities: List[Dict[str, Any]] = Field(
        ...,
        description="Known vulnerabilities grouped by package.",
    )

    max_attempts: int = Field(
        default=25,
        description="Maximum number of steps allowed in the current task.",
    )
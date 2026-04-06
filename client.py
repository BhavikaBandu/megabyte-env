"""Megabyte Environment Client."""

from typing import Dict, Any

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from .models import MegabyteAction, MegabyteObservation, MegabyteState


class MegabyteEnv(
    EnvClient[MegabyteAction, MegabyteObservation, MegabyteState]
):
    """
    Client for the Megabyte Environment.

    This client manages the connection to the Megabyte server, handling the 
    serialization of dependency-related actions and the parsing of deployment 
    observations and environment states.
    """

    def _step_payload(self, action: MegabyteAction) -> Dict[str, Any]:
        """
        Convert MegabyteAction to a JSON-serializable dictionary.

        Args:
            action: The MegabyteAction instance containing the command, 
                package_id, and optional version.

        Returns:
            A dictionary representation of the action for transmission.
        """
        return action.model_dump()

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[MegabyteObservation]:
        """
        Parse the server's execution response into a structured StepResult.

        Args:
            payload: The raw JSON response from the server containing 
                observation data, reward, and done status.

        Returns:
            A StepResult object wrapping a validated MegabyteObservation.
        """
        obs_data = payload.get("observation", {})
        observation = MegabyteObservation.model_validate(obs_data)

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> MegabyteState:
        """
        Parse the environment state response into a MegabyteState object.

        Args:
            payload: The raw JSON state data including manifests, 
                version tables, and vulnerability data.

        Returns:
            A fully validated MegabyteState instance.
        """
        return MegabyteState.model_validate(payload)

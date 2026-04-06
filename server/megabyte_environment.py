"""Megabyte Environment Implementation."""

import os
import json
import secrets
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from .utils import generate_state, evaluate_manifest

try:
    from ..models import MegabyteAction, MegabyteObservation, MegabyteState
except ImportError:
    from models import MegabyteAction, MegabyteObservation, MegabyteState


class MegabyteEnvironment(Environment):
    """
    A software supply chain environment where the agent manages manifest health.

    Args:
        data_dir: Directory containing dependency JSON files.

    Returns:
        MegabyteEnvironment instance.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self, data_dir="deps_data"):
        """
        Picks a random dependency file and caches the lookup tables as attributes.

        Args:
            data_dir: The subdirectory for JSON data files.
        """
        base_path = os.path.join(os.path.dirname(__file__), data_dir)
        available_files = [f for f in os.listdir(base_path) if f.endswith('.json')]
        selected_file = secrets.SystemRandom().choice(available_files)
        
        with open(os.path.join(base_path, selected_file), 'r') as f:
            raw_json = json.load(f)

        # Cache lookup tables as self-attributes for easier evaluation
        (self.version_table, 
         self.vulnerability_table, 
         self.dependency_table, 
         self.initial_manifest) = generate_state(raw_json)

        self.max_attempts = 25
        self._current_manifest = self.initial_manifest.copy()
        self._episode_id = str(uuid4())
        self._step_count = 0

    def reset(self) -> MegabyteObservation:
        """
        Resets the manifest to the initial chaotic state.

        Returns:
            MegabyteObservation with the initial state.
        """
        self._current_manifest = self.initial_manifest.copy()
        self._step_count = 0
        self._episode_id = str(uuid4())

        return self._create_observation(reward=0.0, done=False)

    def step(self, action: MegabyteAction) -> MegabyteObservation:
        """
        Executes a command and updates the manifest.

        Args:
            action: MegabyteAction (UPGRADE, DOWNGRADE, REVERT, RESET).

        Returns:
            MegabyteObservation containing status, log, manifest, and meta.
        """
        self._step_count += 1
        
        if action.command == "RESET":
            self._current_manifest = self.initial_manifest.copy()
        elif action.command == "REVERT":
            self._current_manifest = self.initial_manifest.copy()
        elif action.command in ["UPGRADE", "DOWNGRADE"]:
            pkg = action.package_id
            ver = action.target_version
            if pkg in self._current_manifest and ver in self.version_table.get(pkg, []):
                self._current_manifest[pkg] = ver

        report = evaluate_manifest(
            self._current_manifest, 
            self.dependency_table, 
            self.vulnerability_table
        )

        # Reward Logic
        reward = 0.0
        num_vulns = len(report["vulnerabilities"])
        total_severity = sum(v["severity"] for v in report["vulnerabilities"].values())

        if report["build"] == "SUCCESS":
            reward -= 20.0 if num_vulns > 0 else -100.0
        else:
            reward -= 10.0

        reward -= total_severity
        done = (num_vulns == 0 and report["build"] == "SUCCESS") or (self._step_count >= self.max_attempts)

        return self._create_observation(reward=reward, done=done, report=report)

    def _create_observation(self, reward, done, report=None) -> MegabyteObservation:
        """
        Creates an observation containing only the fields the agent is allowed to see.

        Args:
            reward: Calculated step reward.
            done: Termination flag.
            report: Pre-calculated manifest health report.

        Returns:
            MegabyteObservation with strictly required fields.
        """
        if report is None:
            report = evaluate_manifest(self._current_manifest, self.dependency_table, self.vulnerability_table)

        return MegabyteObservation(
            status=report["build"],
            log=json.dumps(report["dependency_conflicts"]),
            current_manifest=self._current_manifest,
            attempts_remaining=self.max_attempts - self._step_count,
            done=done,
            reward=reward
        )

    @property
    def state(self) -> MegabyteState:
        """
        Returns the internal state object including lookup tables for the agent.

        Returns:
            MegabyteState object for agent cross-referencing.
        """
        return MegabyteState(
            episode_id=self._episode_id,
            step_count=self._step_count,
            initial_manifest=self.initial_manifest,
            current_manifest=self._current_manifest,
            available_versions=self.version_table,
            dependency_rules=self.dependency_table,
            vulnerabilities=[{"package": k, "details": v} for k, v in self.vulnerability_table.items()],
            max_attempts=self.max_attempts
        )


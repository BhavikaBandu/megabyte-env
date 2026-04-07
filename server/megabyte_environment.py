"""Megabyte Environment Implementation."""

import json
import os
import secrets
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment

from .utils import evaluate_manifest, generate_state

try:
    from ..models import MegabyteAction, MegabyteObservation, MegabyteState
    from ..tasks.easy_task import (
        MAX_STEPS as EASY_MAX_STEPS,
        REWARD_WEIGHTS as EASY_REWARD_WEIGHTS,
        TASK_ID as EASY_TASK_ID,
    )
    from ..tasks.medium_task import (
        MAX_STEPS as MEDIUM_MAX_STEPS,
        REWARD_WEIGHTS as MEDIUM_REWARD_WEIGHTS,
        TASK_ID as MEDIUM_TASK_ID,
    )
    from ..tasks.hard_task import (
        MAX_STEPS as HARD_MAX_STEPS,
        REWARD_WEIGHTS as HARD_REWARD_WEIGHTS,
        TASK_ID as HARD_TASK_ID,
    )
except ImportError:
    from models import MegabyteAction, MegabyteObservation, MegabyteState
    from tasks.easy_task import (
        MAX_STEPS as EASY_MAX_STEPS,
        REWARD_WEIGHTS as EASY_REWARD_WEIGHTS,
        TASK_ID as EASY_TASK_ID,
    )
    from tasks.medium_task import (
        MAX_STEPS as MEDIUM_MAX_STEPS,
        REWARD_WEIGHTS as MEDIUM_REWARD_WEIGHTS,
        TASK_ID as MEDIUM_TASK_ID,
    )
    from tasks.hard_task import (
        MAX_STEPS as HARD_MAX_STEPS,
        REWARD_WEIGHTS as HARD_REWARD_WEIGHTS,
        TASK_ID as HARD_TASK_ID,
    )


class MegabyteEnvironment(Environment):
    """
    A software supply chain environment where the agent diagnoses and repairs
    dependency and vulnerability issues in a package manifest.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    TASK_CONFIGS = {
        EASY_TASK_ID: {
            "max_steps": EASY_MAX_STEPS,
            "reward_weights": EASY_REWARD_WEIGHTS,
        },
        MEDIUM_TASK_ID: {
            "max_steps": MEDIUM_MAX_STEPS,
            "reward_weights": MEDIUM_REWARD_WEIGHTS,
        },
        HARD_TASK_ID: {
            "max_steps": HARD_MAX_STEPS,
            "reward_weights": HARD_REWARD_WEIGHTS,
        },
    }

    def __init__(self, data_dir: str = "deps_data"):
        """
        Load one dependency dataset and initialize the environment state.

        Task selection is controlled by the environment variable:
            MEGABYTE_TASK

        Allowed values:
            - easy_system_triage
            - medium_dependency_repair
            - hard_secure_dependency_repair
        """
        base_path = os.path.join(os.path.dirname(__file__), data_dir)
        available_files = [f for f in os.listdir(base_path) if f.endswith(".json")]
        selected_file = secrets.SystemRandom().choice(available_files)

        with open(os.path.join(base_path, selected_file), "r", encoding="utf-8") as f:
            raw_json = json.load(f)

        (
            self.version_table,
            self.vulnerability_table,
            self.dependency_table,
            self.initial_manifest,
        ) = generate_state(raw_json)

        self.task_id = os.getenv("MEGABYTE_TASK", HARD_TASK_ID)
        if self.task_id not in self.TASK_CONFIGS:
            self.task_id = HARD_TASK_ID

        self.max_attempts = self.TASK_CONFIGS[self.task_id]["max_steps"]
        self.reward_weights = self.TASK_CONFIGS[self.task_id]["reward_weights"]

        self._current_manifest = self.initial_manifest.copy()
        self._episode_id = str(uuid4())
        self._step_count = 0
        self._last_action_error = None

        self._initial_report = evaluate_manifest(
            self._current_manifest,
            self.dependency_table,
            self.vulnerability_table,
        )

    def reset(self) -> MegabyteObservation:
        """
        Reset the environment to the initial manifest for the current task.
        """
        self._current_manifest = self.initial_manifest.copy()
        self._episode_id = str(uuid4())
        self._step_count = 0
        self._last_action_error = None

        self.max_attempts = self.TASK_CONFIGS[self.task_id]["max_steps"]
        self.reward_weights = self.TASK_CONFIGS[self.task_id]["reward_weights"]

        self._initial_report = evaluate_manifest(
            self._current_manifest,
            self.dependency_table,
            self.vulnerability_table,
        )

        done = self.task_id == EASY_TASK_ID and False
        return self._create_observation(reward=0.0, done=done, report=self._initial_report)

    def step(self, action: MegabyteAction) -> MegabyteObservation:
        """
        Execute one action and return the new observation.

        Easy task:
            - only CLASSIFY is valid

        Medium task:
            - focuses on dependency repair

        Hard task:
            - focuses on dependency + vulnerability repair
        """
        self._step_count += 1
        self._last_action_error = None

        previous_report = evaluate_manifest(
            self._current_manifest,
            self.dependency_table,
            self.vulnerability_table,
        )

        if self.task_id == EASY_TASK_ID:
            reward, done = self._handle_easy_task(action, previous_report)
            final_report = previous_report
            return self._create_observation(reward=reward, done=done, report=final_report)

        self._apply_repair_action(action)

        final_report = evaluate_manifest(
            self._current_manifest,
            self.dependency_table,
            self.vulnerability_table,
        )

        if self.task_id == MEDIUM_TASK_ID:
            reward = self._compute_medium_reward(previous_report, final_report)
            done = self._is_medium_done(final_report)
        else:
            reward = self._compute_hard_reward(previous_report, final_report)
            done = self._is_hard_done(final_report)

        if self._step_count >= self.max_attempts:
            done = True

        return self._create_observation(reward=reward, done=done, report=final_report)

    def _handle_easy_task(self, action: MegabyteAction, report: dict) -> tuple[float, bool]:
        """
        Handle one-step classification for the easy task.
        """
        if action.command != "CLASSIFY":
            self._last_action_error = "Easy task only accepts CLASSIFY action."
            reward = self.reward_weights.get("incorrect_classification", 0.0)
            return reward, True

        predicted_label = (action.label or "").strip().lower()
        true_label = self._infer_system_state(report)

        if predicted_label == true_label:
            reward = self.reward_weights.get("correct_classification", 1.0)
        else:
            self._last_action_error = f"Incorrect classification: expected {true_label}, got {predicted_label or 'null'}."
            reward = self.reward_weights.get("incorrect_classification", 0.0)

        return reward, True

    def _apply_repair_action(self, action: MegabyteAction) -> None:
        """
        Apply repair action for medium/hard tasks.
        """
        if action.command == "RESET":
            self._current_manifest = self.initial_manifest.copy()
            return

        if action.command == "REVERT":
            pkg = action.package_id
            if not pkg or pkg not in self.initial_manifest:
                self._last_action_error = "REVERT requires a valid package_id."
                return
            self._current_manifest[pkg] = self.initial_manifest[pkg]
            return

        if action.command in {"UPGRADE", "DOWNGRADE"}:
            pkg = action.package_id
            ver = action.target_version

            if not pkg or pkg not in self._current_manifest:
                self._last_action_error = "Action requires a valid package_id."
                return

            if not ver:
                self._last_action_error = "UPGRADE/DOWNGRADE requires a target_version."
                return

            allowed_versions = self.version_table.get(pkg, [])
            if ver not in allowed_versions:
                self._last_action_error = f"Version {ver} is not valid for package {pkg}."
                return

            current_version = self._current_manifest[pkg]
            if current_version == ver:
                self._last_action_error = "Requested version is already installed."
                return

            self._current_manifest[pkg] = ver
            return

        self._last_action_error = f"Unsupported action {action.command} for repair task."

    def _compute_medium_reward(self, previous_report: dict, final_report: dict) -> float:
        """
        Reward for dependency repair only.
        """
        reward = 0.0

        prev_conflicts = len(previous_report.get("dependency_conflicts", {}))
        new_conflicts = len(final_report.get("dependency_conflicts", {}))
        conflict_delta = prev_conflicts - new_conflicts

        reward += self.reward_weights.get("conflict_reduction", 0.0) * conflict_delta
        reward += self.reward_weights.get("step_penalty", 0.0)

        if final_report.get("build") == "SUCCESS":
            reward += self.reward_weights.get("build_success_bonus", 0.0)

        if self._last_action_error:
            reward += self.reward_weights.get("invalid_action_penalty", 0.0)

        return float(reward)

    def _compute_hard_reward(self, previous_report: dict, final_report: dict) -> float:
        """
        Reward for full secure repair.
        """
        reward = 0.0

        prev_conflicts = len(previous_report.get("dependency_conflicts", {}))
        new_conflicts = len(final_report.get("dependency_conflicts", {}))
        conflict_delta = prev_conflicts - new_conflicts

        prev_vulns = len(previous_report.get("vulnerabilities", {}))
        new_vulns = len(final_report.get("vulnerabilities", {}))
        vuln_delta = prev_vulns - new_vulns

        reward += self.reward_weights.get("conflict_reduction", 0.0) * conflict_delta
        reward += self.reward_weights.get("vulnerability_reduction", 0.0) * vuln_delta
        reward += self.reward_weights.get("step_penalty", 0.0)

        if (
            final_report.get("build") == "SUCCESS"
            and len(final_report.get("vulnerabilities", {})) == 0
        ):
            reward += self.reward_weights.get("build_success_bonus", 0.0)

        if self._last_action_error:
            reward += self.reward_weights.get("invalid_action_penalty", 0.0)

        return float(reward)

    def _is_medium_done(self, report: dict) -> bool:
        """
        Medium task ends when dependency conflicts are resolved and build succeeds,
        or when attempts are exhausted.
        """
        no_conflicts = len(report.get("dependency_conflicts", {})) == 0
        return no_conflicts and report.get("build") == "SUCCESS"

    def _is_hard_done(self, report: dict) -> bool:
        """
        Hard task ends when build succeeds and vulnerabilities are removed,
        or when attempts are exhausted.
        """
        no_conflicts = len(report.get("dependency_conflicts", {})) == 0
        no_vulns = len(report.get("vulnerabilities", {})) == 0
        return report.get("build") == "SUCCESS" and no_conflicts and no_vulns

    def _infer_system_state(self, report: dict) -> str:
        """
        Infer the true easy-task label from the current report.
        """
        has_conflicts = len(report.get("dependency_conflicts", {})) > 0
        has_vulnerabilities = len(report.get("vulnerabilities", {})) > 0

        if not has_conflicts and not has_vulnerabilities:
            return "safe_and_stable"
        if not has_conflicts and has_vulnerabilities:
            return "stable_but_insecure"
        if has_conflicts and not has_vulnerabilities:
            return "broken_but_secure"
        return "broken_and_insecure"

    def _create_observation(
        self,
        reward: float,
        done: bool,
        report: dict | None = None,
    ) -> MegabyteObservation:
        """
        Create the observation visible to the agent.
        """
        if report is None:
            report = evaluate_manifest(
                self._current_manifest,
                self.dependency_table,
                self.vulnerability_table,
            )

        return MegabyteObservation(
            status=report["build"],
            log=json.dumps(report["dependency_conflicts"]),
            current_manifest=self._current_manifest.copy(),
            attempts_remaining=max(0, self.max_attempts - self._step_count),
            task_id=self.task_id,
            last_action_error=self._last_action_error,
            done=done,
            reward=reward,
        )

    @property
    def state(self) -> MegabyteState:
        """
        Return the full internal state for the client/agent.
        """
        return MegabyteState(
            episode_id=self._episode_id,
            step_count=self._step_count,
            task_id=self.task_id,
            initial_manifest=self.initial_manifest.copy(),
            current_manifest=self._current_manifest.copy(),
            available_versions=self.version_table,
            dependency_rules=self.dependency_table,
            vulnerabilities=[
                {"package": pkg, "details": vuln_list}
                for pkg, vuln_list in self.vulnerability_table.items()
            ],
            max_attempts=self.max_attempts,
        )
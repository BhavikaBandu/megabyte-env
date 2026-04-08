"""
Inference Script for Megabyte Environment
========================================

MANDATORY ENV VARIABLES
- API_BASE_URL     : OpenAI-compatible API endpoint
- MODEL_NAME       : Model identifier used for inference
- HF_TOKEN         : API key / Hugging Face token for the LLM endpoint
- LOCAL_IMAGE_NAME : Local Docker image name for the environment (recommended for running all 3 tasks)

OPTIONAL ENV VARIABLES
- ENV_BASE_URL               : Use an already running Megabyte server instead of Docker
- MEGABYTE_TASKS             : Comma-separated task ids to run
                               default: easy_system_triage,medium_dependency_repair,hard_secure_dependency_repair
- MEGABYTE_BENCHMARK         : Benchmark name for logging
- SUCCESS_SCORE_THRESHOLD    : Score threshold for success
- TEMPERATURE                : Model temperature
- MAX_TOKENS                 : Max tokens for model response

NOTES
- If you want to run all 3 tasks in one script execution, use LOCAL_IMAGE_NAME so a fresh env
  can be launched per task with the correct task configuration.
- If ENV_BASE_URL is used, that server is already locked to one MEGABYTE_TASK value, so only one
  task should be run per execution.

STDOUT FORMAT
[START] task=<task_name> env=<benchmark> model=<model_name>
[STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
[END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import textwrap
from typing import Any, Dict, List, Optional

from openai import OpenAI

from client import MegabyteEnv
from graders import grade_easy_task, grade_hard_task, grade_medium_task
from models import MegabyteAction
from server.utils import evaluate_manifest
from tasks.easy_task import (
    MAX_STEPS as EASY_MAX_STEPS,
    SYSTEM_PROMPT as EASY_SYSTEM_PROMPT,
    TASK_ID as EASY_TASK_ID,
    TASK_NAME as EASY_TASK_NAME,
)
from tasks.medium_task import (
    MAX_STEPS as MEDIUM_MAX_STEPS,
    SYSTEM_PROMPT as MEDIUM_SYSTEM_PROMPT,
    TASK_ID as MEDIUM_TASK_ID,
    TASK_NAME as MEDIUM_TASK_NAME,
)
from tasks.hard_task import (
    MAX_STEPS as HARD_MAX_STEPS,
    SYSTEM_PROMPT as HARD_SYSTEM_PROMPT,
    TASK_ID as HARD_TASK_ID,
    TASK_NAME as HARD_TASK_NAME,
)

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME") or os.getenv("IMAGE_NAME")
ENV_BASE_URL = os.getenv("ENV_BASE_URL")

BENCHMARK = os.getenv("MEGABYTE_BENCHMARK") or "megabyte"
SUCCESS_SCORE_THRESHOLD = float(os.getenv("SUCCESS_SCORE_THRESHOLD", "0.8"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "256"))

TASK_SEQUENCE = [
    task.strip()
    for task in os.getenv(
        "MEGABYTE_TASKS",
        f"{EASY_TASK_ID},{MEDIUM_TASK_ID},{HARD_TASK_ID}",
    ).split(",")
    if task.strip()
]

TASK_CONFIGS: Dict[str, Dict[str, Any]] = {
    EASY_TASK_ID: {
        "task_name": EASY_TASK_NAME,
        "system_prompt": EASY_SYSTEM_PROMPT,
        "max_steps": EASY_MAX_STEPS,
    },
    MEDIUM_TASK_ID: {
        "task_name": MEDIUM_TASK_NAME,
        "system_prompt": MEDIUM_SYSTEM_PROMPT,
        "max_steps": MEDIUM_MAX_STEPS,
    },
    HARD_TASK_ID: {
        "task_name": HARD_TASK_NAME,
        "system_prompt": HARD_SYSTEM_PROMPT,
        "max_steps": HARD_MAX_STEPS,
    },
}


# ---------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------

def _one_line(text: Any) -> str:
    """Convert any text into a single-line string for strict log format."""
    if text is None:
        return "null"
    return str(text).replace("\n", " ").replace("\r", " ").strip()


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    print(
        f"[STEP] step={step} action={_one_line(action)} reward={reward:.2f} "
        f"done={str(done).lower()} error={_one_line(error)}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ---------------------------------------------------------------------
# Async compatibility helpers
# ---------------------------------------------------------------------

async def maybe_await(value: Any) -> Any:
    """Await the value if it is awaitable, otherwise return it directly."""
    if inspect.isawaitable(value):
        return await value
    return value


# ---------------------------------------------------------------------
# Report reconstruction helpers
# ---------------------------------------------------------------------

def _vulnerability_table_from_state(state: Any) -> Dict[str, Any]:
    """
    Convert state.vulnerabilities list back into the vulnerability table format
    expected by evaluate_manifest().
    """
    table: Dict[str, Any] = {}
    for item in getattr(state, "vulnerabilities", []):
        pkg = item.get("package")
        details = item.get("details")
        if pkg is not None:
            table[pkg] = details
    return table


def _manifest_report(current_manifest: Dict[str, str], state: Any) -> Dict[str, Any]:
    """Recompute the true report from manifest + state tables."""
    return evaluate_manifest(
        current_manifest,
        getattr(state, "dependency_rules", {}),
        _vulnerability_table_from_state(state),
    )


def _safe_json_loads(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# ---------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------

def _current_relevant_view(obs: Any, state: Any) -> Dict[str, Any]:
    """
    Build a compact, relevant view of the current state for the model.
    Uses only currently installed packages to avoid huge prompts.
    """
    manifest = getattr(obs, "current_manifest", {}) or {}
    dependency_rules = getattr(state, "dependency_rules", {}) or {}
    available_versions = getattr(state, "available_versions", {}) or {}

    installed_rules = {pkg: dependency_rules.get(pkg, {}) for pkg in manifest.keys()}
    installed_versions = {pkg: available_versions.get(pkg, []) for pkg in manifest.keys()}

    report = _manifest_report(manifest, state)
    active_vulns = report.get("vulnerabilities", {})
    dependency_conflicts = report.get("dependency_conflicts", {})

    return {
        "build_status": getattr(obs, "status", "UNKNOWN"),
        "dependency_conflicts": dependency_conflicts,
        "active_vulnerabilities": active_vulns,
        "current_manifest": manifest,
        "dependency_rules": installed_rules,
        "available_versions": installed_versions,
        "attempts_remaining": getattr(obs, "attempts_remaining", None),
        "last_action_error": getattr(obs, "last_action_error", None),
    }


def build_user_prompt(task_id: str, step: int, obs: Any, state: Any, history: List[str]) -> str:
    """
    Build the user prompt by combining task instructions with the current state view.
    """
    state_view = _current_relevant_view(obs, state)
    history_block = "\n".join(history[-5:]) if history else "None"

    if task_id == EASY_TASK_ID:
        guidance = (
            "This is a single-step diagnosis task. "
            "Use the dependency conflicts and active vulnerabilities to classify the system."
        )
    elif task_id == MEDIUM_TASK_ID:
        guidance = (
            "This task focuses only on dependency repair. "
            "Ignore vulnerabilities in your decision-making."
        )
    else:
        guidance = (
            "This task requires both dependency repair and vulnerability removal. "
            "Prioritize actions that move the system toward a secure successful build."
        )

    return textwrap.dedent(
        f"""
        Step: {step}
        Guidance: {guidance}

        Current environment state:
        {json.dumps(state_view, indent=2, sort_keys=True)}

        Previous steps:
        {history_block}

        Return exactly one valid JSON action.
        """
    ).strip()


# ---------------------------------------------------------------------
# Model call + action parsing
# ---------------------------------------------------------------------

def _extract_first_json_object(text: str) -> Dict[str, Any]:
    """
    Extract the first JSON object from a possibly noisy model response.
    """
    if not text:
        return {}

    # First try direct parse
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        pass

    # Then try balanced brace extraction
    start = text.find("{")
    if start == -1:
        return {}

    depth = 0
    for idx in range(start, len(text)):
        ch = text[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : idx + 1]
                try:
                    data = json.loads(candidate)
                    return data if isinstance(data, dict) else {}
                except Exception:
                    return {}
    return {}


def _fallback_action(task_id: str) -> Dict[str, Any]:
    """
    Safe fallback action if parsing/model output fails.
    """
    if task_id == EASY_TASK_ID:
        return {"command": "CLASSIFY", "label": "broken_and_insecure"}
    return {"command": "RESET"}


def _normalize_action_dict(task_id: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize model output into a MegabyteAction-compatible dictionary.
    """
    if not isinstance(raw, dict):
        return _fallback_action(task_id)

    command = str(raw.get("command", "")).strip().upper()

    if task_id == EASY_TASK_ID:
        label = str(raw.get("label", "")).strip().lower()
        if command != "CLASSIFY" or not label:
            return _fallback_action(task_id)
        return {"command": "CLASSIFY", "label": label}

    if command in {"UPGRADE", "DOWNGRADE"}:
        package_id = raw.get("package_id")
        target_version = raw.get("target_version")
        if package_id and target_version:
            return {
                "command": command,
                "package_id": str(package_id),
                "target_version": str(target_version),
            }
        return _fallback_action(task_id)

    if command == "REVERT":
        package_id = raw.get("package_id")
        if package_id:
            return {"command": "REVERT", "package_id": str(package_id)}
        return _fallback_action(task_id)

    if command == "RESET":
        return {"command": "RESET"}

    return _fallback_action(task_id)


def get_model_action(
    client: OpenAI,
    task_id: str,
    system_prompt: str,
    user_prompt: str,
) -> MegabyteAction:
    """
    Query the model and parse the response into a MegabyteAction.
    """
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        raw_action = _extract_first_json_object(text)
    except Exception:
        raw_action = _fallback_action(task_id)

    normalized = _normalize_action_dict(task_id, raw_action)
    return MegabyteAction(**normalized)


def action_to_log_string(action: MegabyteAction) -> str:
    """
    Convert action to a compact one-line JSON string for [STEP] logging.
    """
    return json.dumps(action.model_dump(exclude_none=True), separators=(",", ":"))


# ---------------------------------------------------------------------
# Environment creation
# ---------------------------------------------------------------------

async def create_env_for_task(task_id: str) -> Any:
    """
    Create an environment instance for one task.

    Preferred:
    - LOCAL_IMAGE_NAME: launches a fresh Docker environment for each task

    Alternative:
    - ENV_BASE_URL: connects to an already running server, but that server can
      only support one task mode per launch.
    """
    if LOCAL_IMAGE_NAME:
        previous = os.environ.get("MEGABYTE_TASK")
        os.environ["MEGABYTE_TASK"] = task_id
        try:
            env = await maybe_await(MegabyteEnv.from_docker_image(LOCAL_IMAGE_NAME))
        finally:
            if previous is None:
                os.environ.pop("MEGABYTE_TASK", None)
            else:
                os.environ["MEGABYTE_TASK"] = previous
        return env

    if ENV_BASE_URL:
        if len(TASK_SEQUENCE) > 1:
            raise RuntimeError(
                "ENV_BASE_URL points to a single running server task. "
                "To run all 3 tasks in one script, use LOCAL_IMAGE_NAME instead."
            )
        return MegabyteEnv(base_url=ENV_BASE_URL)

    raise RuntimeError(
        "No environment source configured. Set LOCAL_IMAGE_NAME or ENV_BASE_URL."
    )


# ---------------------------------------------------------------------
# Task runner
# ---------------------------------------------------------------------

async def run_one_task(client: OpenAI, task_id: str) -> None:
    """
    Run one complete task episode and emit strict benchmark logs.
    """
    if task_id not in TASK_CONFIGS:
        raise ValueError(f"Unsupported task_id: {task_id}")

    task_name = TASK_CONFIGS[task_id]["task_name"]
    system_prompt = TASK_CONFIGS[task_id]["system_prompt"]
    max_steps = TASK_CONFIGS[task_id]["max_steps"]

    env = await create_env_for_task(task_id)

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    initial_report: Dict[str, Any] = {}
    predicted_label = ""

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        reset_result = await maybe_await(env.reset())
        obs = reset_result.observation
        state = env.state

        initial_report = _manifest_report(
            getattr(state, "initial_manifest", {}),
            state,
        )

        done = bool(getattr(reset_result, "done", False))

        for step in range(1, max_steps + 1):
            if done:
                break

            user_prompt = build_user_prompt(task_id, step, obs, state, history)
            action = get_model_action(client, task_id, system_prompt, user_prompt)

            if task_id == EASY_TASK_ID:
                predicted_label = action.label or ""

            result = await maybe_await(env.step(action))
            obs = result.observation
            state = env.state

            reward = float(result.reward or 0.0)
            done = bool(result.done)
            error = getattr(obs, "last_action_error", None)

            rewards.append(reward)
            steps_taken = step

            action_str = action_to_log_string(action)
            log_step(step=step, action=action_str, reward=reward, done=done, error=error)

            history.append(f"step={step} action={action_str} reward={reward:.2f} done={str(done).lower()}")

            if done:
                break

        final_report = _manifest_report(
            getattr(obs, "current_manifest", {}),
            state,
        )

        if task_id == EASY_TASK_ID:
            score = grade_easy_task(predicted_label, final_report)
        elif task_id == MEDIUM_TASK_ID:
            score = grade_medium_task(final_report, steps_taken, max_steps)
        else:
            score = grade_hard_task(initial_report, final_report, steps_taken, max_steps)

        score = max(0.0, min(1.0, float(score)))
        success = score >= SUCCESS_SCORE_THRESHOLD

    finally:
        try:
            await maybe_await(env.close())
        except Exception:
            pass

        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

async def main() -> None:
    if not API_KEY:
        raise RuntimeError("Missing API key. Set HF_TOKEN, OPENAI_API_KEY, or API_KEY.")

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    for task_id in TASK_SEQUENCE:
        await run_one_task(client, task_id)


if __name__ == "__main__":
    asyncio.run(main())
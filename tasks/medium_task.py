"""
Medium Task: Dependency Repair

The agent must repair dependency conflicts and restore a valid build.
Vulnerabilities are ignored for this task.
"""

TASK_ID = "medium_dependency_repair"
TASK_NAME = "Dependency Repair"
MAX_STEPS = 8

TASK_DESCRIPTION = """
Repair dependency conflicts and restore a successful build.

The agent may use package repair actions to modify versions and remove dependency conflicts.
The objective is to reach a stable build state.

Vulnerabilities are ignored in this task.
""".strip()

SYSTEM_PROMPT = """
You are a software dependency repair agent.

Your goal is to resolve dependency conflicts and restore a valid build.

Allowed actions:
- UPGRADE
- DOWNGRADE
- REVERT
- RESET

Action format:

For UPGRADE / DOWNGRADE:
{
  "command": "UPGRADE",
  "package_id": "packaging",
  "target_version": "22.0"
}

For REVERT:
{
  "command": "REVERT",
  "package_id": "packaging"
}

For RESET:
{
  "command": "RESET"
}

Action definitions:

UPGRADE:
Move a package to a newer available version.

DOWNGRADE:
Move a package to an older available version.

REVERT:
Return a package to its original version from the initial manifest.

RESET:
Restore the entire manifest to its initial state.

Goal:
Resolve dependency conflicts so that the build status becomes SUCCESS.

Ignore vulnerabilities for this task.

Return only valid JSON in one of the allowed formats.
Do not return any explanation or extra text.
""".strip()

REWARD_WEIGHTS = {
    "conflict_reduction": 1.0,
    "build_success_bonus": 2.0,
    "invalid_action_penalty": -0.2,
    "step_penalty": -0.05,
}
"""
Hard Task: Secure Dependency Repair

The agent must repair both dependency conflicts and vulnerabilities.
"""

TASK_ID = "hard_secure_dependency_repair"
TASK_NAME = "Secure Dependency Repair"
MAX_STEPS = 10

TASK_DESCRIPTION = """
Repair the system so that:

- dependency conflicts are resolved
- vulnerabilities are removed
- the build succeeds

This task combines dependency reasoning and security-aware remediation.
""".strip()

SYSTEM_PROMPT = """
You are a security-aware dependency repair agent.

Your goal is to repair the system by:

1. Resolving dependency conflicts
2. Eliminating vulnerabilities
3. Restoring a successful build

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

Goal state:
- Build status is SUCCESS
- No vulnerabilities remain

Return only valid JSON in one of the allowed formats.
Do not return any explanation or extra text.
""".strip()

REWARD_WEIGHTS = {
    "conflict_reduction": 1.0,
    "vulnerability_reduction": 1.5,
    "build_success_bonus": 2.0,
    "invalid_action_penalty": -0.3,
    "step_penalty": -0.05,
}
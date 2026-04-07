"""
Easy Task: System Triage

The agent inspects the current environment and classifies the overall system state.
This is a one-step task.
"""

TASK_ID = "easy_system_triage"
TASK_NAME = "System Triage"
MAX_STEPS = 1

VALID_LABELS = [
    "safe_and_stable",
    "stable_but_insecure",
    "broken_but_secure",
    "broken_and_insecure",
]

TASK_DESCRIPTION = """
Classify the system into one of four states:

- safe_and_stable:
  No dependency conflicts and no vulnerabilities.

- stable_but_insecure:
  Build succeeds, but vulnerabilities exist.

- broken_but_secure:
  Dependency conflicts exist, but no vulnerabilities exist.

- broken_and_insecure:
  Both dependency conflicts and vulnerabilities exist.
""".strip()

SYSTEM_PROMPT = """
You are a software dependency triage agent.

Your task is to inspect the current dependency environment and classify the overall system state.

You must choose exactly one of the following labels:

- safe_and_stable
- stable_but_insecure
- broken_but_secure
- broken_and_insecure

Definitions:

safe_and_stable:
No dependency conflicts and no vulnerabilities.

stable_but_insecure:
The build succeeds, but vulnerabilities exist.

broken_but_secure:
Dependency conflicts exist, but no vulnerabilities exist.

broken_and_insecure:
Both dependency conflicts and vulnerabilities exist.

Return only valid JSON in this exact format:

{
  "command": "CLASSIFY",
  "label": "broken_and_insecure"
}

Do not return any explanation or extra text.
""".strip()

REWARD_WEIGHTS = {
    "correct_classification": 1.0,
    "incorrect_classification": 0.0,
}
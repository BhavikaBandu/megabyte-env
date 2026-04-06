"""
Medium Task: Dependency Management Agent.
This script focuses on resolving version conflicts and build failures 
to reach a SUCCESS status using iterative OpenAI-driven actions.
"""

import os
import json
import textwrap
from openai import OpenAI
from client import MegabyteEnv
from models import MegabyteAction

# Setup OpenAI from Environment Variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
URL = "https://bhavikabandu-megabyte-env.hf.space"

SYSTEM_PROMPT = textwrap.dedent("""
    You are a Dependency Management Agent. Your ONLY goal is to fix the build.

    ## PRIMARY OBJECTIVE
    - Resolve version conflicts and build failures.
    - A build is valid once status is SUCCESS.

    ## ENVIRONMENT INPUTS
    - current_manifest: Current package versions
    - available_versions: Allowed versions per package
    - log: Error/debug output (only relevant on FAILURE)
    - attempts_remaining: Remaining steps

    ## ACTION SPACE
    Valid commands: UPGRADE, DOWNGRADE, REVERT, RESET

    ## RESPONSE FORMAT (STRICT)
    Output ONLY valid JSON.
    {
        "command": "UPGRADE" | "DOWNGRADE" | "REVERT" | "RESET",
        "package_id": "string or null",
        "target_version": "string or null"
    }

    ## DECISION POLICY
    1. If status == FAILURE: Analyze 'log' to find the conflict.
    2. Use UPGRADE/DOWNGRADE to find a compatible version.
    3. Use RESET if you are stuck in a loop.

    ## SUCCESS CONDITION
    - Build status is SUCCESS.
    """).strip()

def run_medium_task():
    env = MegabyteEnv(base_url=URL)
    sync_env = env.sync()
    try:
        sync_env.connect()
        obs_step = sync_env.reset()
        while obs_step.observation.attempts_remaining > 0:
            if obs_step.observation.status == "SUCCESS":
                print("MEDIUM TASK COMPLETE: Build is stable.")
                break

            state = sync_env.state()
            prompt_input = {
                "status": obs_step.observation.status,
                "log": obs_step.observation.log,
                "current_manifest": obs_step.observation.current_manifest,
                "available_versions": state.available_versions
            }

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"INPUT:\n{json.dumps(prompt_input)}"}
                ],
                response_format={"type": "json_object"}
            )

            action = MegabyteAction(**json.loads(response.choices[0].message.content))
            print(f"Action: {action.command} {action.package_id}")
            obs_step = sync_env.step(action)
    finally:
        sync_env.close()

if __name__ == "__main__":
    run_medium_task()

"""
Hard Task: Senior Security Engineer.
This script manages complex dependency resolution with the dual goal 
of fixing build failures and eliminating all CVEs from the environment.
"""

import os
import json
import textwrap
from openai import OpenAI
from client import MegabyteEnv
from models import MegabyteAction

# Setup OpenAI from Environment Variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
megabyte_url = "https://bhavikabandu-megabyte-env.hf.space"

SYSTEM_PROMPT = textwrap.dedent("""
    You are a Senior Security Engineer and Dependency Management Agent specializing in software supply chain security and dependency resolution.

    ## PRIMARY OBJECTIVE
    Achieve a fully secure environment:
    - Eliminate ALL known CVEs.
    - A build is valid ONLY if it is both SUCCESS and has zero vulnerabilities.

    ## SECONDARY OBJECTIVE
    Maintain dependency correctness:
    - Resolve version conflicts and build failures.
    - Never accept a stable build that contains vulnerabilities.

    ## ENVIRONMENT INPUTS
    - vulnerabilities: List of packages with CVEs
    - current_manifest: Current package versions
    - available_versions: Allowed versions per package
    - log: Error/debug output (only relevant on FAILURE)
    - attempts_remaining: Remaining steps

    ## ACTION SPACE
    Valid commands:
    - UPGRADE
    - DOWNGRADE
    - REVERT
    - RESET

    ## ACTION RULES
    - UPGRADE/DOWNGRADE require: package_id + target_version
    - REVERT requires: package_id only
    - RESET requires: no parameters

    ## RESPONSE FORMAT (STRICT)
    Output ONLY valid JSON. No explanations. No extra text.

    {
        "command": "UPGRADE" | "DOWNGRADE" | "REVERT" | "RESET",
        "package_id": "string or null",
        "target_version": "string or null"
    }

    ## DECISION POLICY

    1. SECURITY FIRST
        - Identify vulnerable packages.
        - Move to nearest non-vulnerable version.
        - Prioritize highest severity CVEs.

    2. HANDLE FAILURES
        - If status == FAILURE:
        - Analyze 'log'
        - REVERT the last risky package OR RESET if state is unclear

    3. STABILITY CONSTRAINT
        - Ensure dependency compatibility.
        - Avoid invalid version combinations.

    4. EFFICIENCY
        - Avoid repeating the same action.
        - Avoid oscillations (upgrade ↔ downgrade loops).
        - Minimize number of steps.

    ## SUCCESS CONDITION
        - No CVEs remain
        - Build status is SUCCESS

    Any state with remaining vulnerabilities is considered FAILURE.
    """).strip()

def run_hard_task():
    env = MegabyteEnv(base_url=megabyte_url)
    sync_env = env.sync()
    
    try:
        sync_env.connect()
        obs_step = sync_env.reset()
        
        while obs_step.observation.attempts_remaining > 0:
            state = sync_env.state()
            current_manifest = obs_step.observation.current_manifest
            active_vulns = [v for v in state.vulnerabilities if v['package'] in current_manifest]
            
            print(f"\n[HARD TASK] Build: {obs_step.observation.status} | Active CVEs: {len(active_vulns)} | Remaining: {obs_step.observation.attempts_remaining}")
            
            if obs_step.observation.status == "SUCCESS" and len(active_vulns) == 0:
                print("HARD TASK COMPLETE: Environment is SECURE and FUNCTIONAL.")
                break

            prompt_input = {
                "vulnerabilities": state.vulnerabilities,
                "current_manifest": current_manifest,
                "available_versions": state.available_versions,
                "log": obs_step.observation.log,
                "attempts_remaining": obs_step.observation.attempts_remaining
            }

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"INPUT DATA:\n{json.dumps(prompt_input)}"}
                ],
                response_format={"type": "json_object"}
            )

            action_data = json.loads(response.choices[0].message.content)
            action = MegabyteAction(**action_data)
            
            print(f"Action: {action.command} | Pkg: {action.package_id} | To: {action.target_version}")
            obs_step = sync_env.step(action)

        if obs_step.observation.attempts_remaining == 0:
            print("Hard Task Failed: Out of attempts.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        sync_env.close()

if __name__ == "__main__":
    run_hard_task()

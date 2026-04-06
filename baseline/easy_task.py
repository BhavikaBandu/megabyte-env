"""
Easy Task: Software Supply Chain Auditor.
This script connects to the Megabyte environment and performs a single-step audit 
of dependency issues and vulnerabilities using OpenAI inference.
"""

import os
import json
import textwrap
from openai import OpenAI
from client import MegabyteEnv

# Setup OpenAI from Environment Variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

megabyte_url = "https://bhavikabandu-megabyte-env.hf.space"

SYSTEM_PROMPT = textwrap.dedent("""
    You are a Software Supply Chain Auditor. Your mission is to IDENTIFY issues within the provided environment data.
    
    ## TASK
    Count and report two specific metrics:
    1. DEPENDENCY ISSUES: Any package involved in a version conflict or build failure (status == FAILURE).
    2. VULNERABILITIES: Any package present in the 'current_manifest' that is also listed in the 'vulnerability_database'.

    ## OUTPUT RULES
    - Respond ONLY in valid JSON.
    - Do NOT suggest fixes or take actions.
    - If status is "SUCCESS", dependency_issue_count is 0.
    - If status is "FAILURE", analyze the log to determine the count of affected packages.

    ## JSON STRUCTURE
    {
        "dependency_issue_count": integer,
        "vulnerability_count": integer,
        "affected_packages": ["list", "of", "package_names"],
        "status_summary": "string"
    }
    """).strip()

def run_easy_task():
    env = MegabyteEnv(base_url=megabyte_url)
    sync_env = env.sync()
    
    try:
        sync_env.connect()
        result = sync_env.reset()
        state = sync_env.state()

        prompt_input = {
            "status": result.observation.status,
            "log": result.observation.log,
            "current_manifest": result.observation.current_manifest,
            "vulnerability_database": state.vulnerabilities
        }

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Input Data: {json.dumps(prompt_input)}"}
            ],
            response_format={"type": "json_object"}
        )

        report = json.loads(response.choices[0].message.content)
        print(f"\n=== AUDIT REPORT ===\n{json.dumps(report, indent=2)}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        sync_env.close()

if __name__ == "__main__":
    run_easy_task()

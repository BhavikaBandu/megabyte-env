
# Megabyte Environment

Megabyte is a Reinforcement Learning (RL) environment built on top of the OpenEnv framework.  
It simulates a realistic software dependency ecosystem where intelligent agents must diagnose, repair, and secure package manifests.  

The environment models the real-world challenge commonly known as Dependency Hell, where version conflicts and security vulnerabilities propagate through complex dependency graphs.  

---

## Megabyte trains agents to:

- Diagnose broken dependency systems  
- Resolve version conflicts  
- Remove vulnerable packages  
- Restore stable builds under constrained actions  

---

## Overview

Modern software systems rely on deeply interconnected dependency graphs.  
A small version mismatch or vulnerable package can cascade into widespread failures.  

Megabyte recreates this challenge in a structured RL environment where agents must reason about:  

- package compatibility  
- version constraints  
- security vulnerabilities  
- limited action budgets  

Agents must balance system correctness (build success) with security (zero vulnerabilities).  

---

## Core Concepts

### Observation (MegabyteObservation)

Observations are the only information visible to the agent during interaction.  

**Fields:**  

- status — Build state (SUCCESS or FAILURE)  
- log — Dependency conflict report  
- current_manifest — Dictionary mapping packages → installed versions  
- attempts_remaining — Remaining actions before termination  
- task_id — Current task identifier  
- last_action_error — Error message if the previous action was invalid  

**Purpose:**  

Observations provide structured feedback for decision-making without exposing full system knowledge.  

---

### State (MegabyteState)

The state represents the complete internal environment configuration.  

**Fields:**  

- initial_manifest — Original package configuration  
- current_manifest — Current package configuration  
- dependency_rules — Package compatibility constraints  
- vulnerabilities — Known vulnerabilities affecting package versions  
- available_versions — Allowed versions for each package  
- max_attempts — Maximum steps allowed in the current task  

**Purpose:**  

This defines the full dependency ecosystem used to evaluate actions.  

---

## Actions (MegabyteAction)

Agents interact with the environment through a constrained action space.  

### 🔹 Classification Action

CLASSIFY(label)  

Used only in the Easy task.  

**Example:**  
```json
{
  "command": "CLASSIFY",
  "label": "broken_and_insecure"
}
```

---

### 🔹 Repair Actions

```text
UPGRADE(package_id, version)
DOWNGRADE(package_id, version)
REVERT(package_id)
RESET()
```

**Examples:**  
```json
{
  "command": "UPGRADE",
  "package_id": "typing-extensions",
  "target_version": "4.6.0"
}
```

**Design notes:**  

- Actions mutate the dependency manifest  
- Version changes must exist in available_versions  
- Invalid actions produce structured errors  

---

## Task Levels

Megabyte contains three difficulty levels, each testing different reasoning abilities.  

---

### 🟢 Easy Task — System Triage

**Role:** System Monitor  

**Objective:**  

Classify the system state into one of four categories:  

- safe_and_stable  
- stable_but_insecure  
- broken_but_secure  
- broken_and_insecure  

**Definitions:**  

| Condition | Result |
|----------|--------|
| No conflicts + no vulnerabilities | safe_and_stable |
| No conflicts + vulnerabilities | stable_but_insecure |
| Conflicts + no vulnerabilities | broken_but_secure |
| Conflicts + vulnerabilities | broken_and_insecure |

**Characteristics:**  

- Single step task  
- No system modification allowed  

**Success Criteria:**  

Correct classification.  

---

### 🟡 Medium Task — Dependency Repair

**Role:** Package Manager  

**Objective:**  

Resolve dependency conflicts and restore a valid build.  

**Agent must:**  

- inspect dependency rules  
- detect incompatible versions  
- apply upgrades or downgrades  

**Constraints:**  

- limited number of actions  
- vulnerabilities are ignored  

**Success Criteria:**  
```text
build == SUCCESS
dependency_conflicts == 0
```

---

### 🔴 Hard Task — Secure Dependency Repair

**Role:** Security Engineer  

**Objective:**  

Repair the system while also eliminating vulnerabilities.  

**Agent must:**  

- resolve dependency conflicts  
- upgrade or downgrade vulnerable packages  
- maintain compatibility across the dependency graph  

**Key challenge:**  

Fixing vulnerabilities may introduce dependency conflicts.  

**Success Criteria:**  
```text
build == SUCCESS
dependency_conflicts == 0
vulnerabilities == 0
```

---

## Environment Mechanics

### Dependency System

Example rule:  
```
aiohttp requires aiosignal >=1.4.0
```

Dependency conflicts occur when version constraints are violated.  

---

### Version System

```
available_versions["aiohttp"] → ["3.8.0", "3.9.0", ...]
```

Agents must choose versions from this set.  

---

### Vulnerability Model

Example:  
```
aiohttp versions <3.10.11 are vulnerable
```

Each vulnerability contains:  

- introduced version  
- fixed version  
- severity score  

---

## Reinforcement Learning Loop

Typical interaction cycle:  

```python
obs = env.reset()

done = False

while not done:
    action = agent.act(obs)
    result = env.step(action)
    obs = result.observation
    reward = result.reward
    done = result.done
```

---

## Scoring

Megabyte provides two evaluation layers.  

### Step Rewards

The environment returns rewards based on:  

- dependency conflict reduction  
- vulnerability reduction  
- build success  
- invalid actions  

These guide agent behavior during training.  

---

### Final Task Score

Benchmark graders compute final scores between 0 and 1.  

**Easy Task**  
```
correct classification → 1.0
incorrect → 0.0
```

**Medium Task**  

Score based on:  

- dependency repair success  
- efficiency  

**Hard Task**  

Score based on:  

- vulnerability removal  
- dependency repair  
- final secure build  
- efficiency  

---

## Example Scenario

**Initial manifest:**  
```json
{
  "aiohttp": "3.8.0",
  "typing-extensions": "3.6.6"
}
```

**Problems:**  

- dependency conflicts  
- vulnerable versions  

**Possible repair sequence:**  
```
Upgrade typing-extensions to 4.6.0
Upgrade aiohttp to 3.10.11
Verify dependency compatibility
```

---

## Running Locally

**Install dependencies:**  
```bash
pip install openenv-core uvicorn fastapi pydantic
```

**Run the environment server:**  
```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

---

## Hugging Face Deployment

Megabyte is deployed on Hugging Face Spaces.  

**Environment endpoint:**  
https://huggingface.co/spaces/BhavikaBandu/megabyte-env  

The deployment exposes:  

- Web interface  
- REST API  
- WebSocket interaction  

---

## Research Applications

Megabyte enables research in:  

- autonomous dependency management  
- secure software supply chains  
- reinforcement learning for DevOps  
- program repair systems  
- constraint reasoning over dependency graphs  

---

## Summary

Megabyte provides a realistic simulation of modern dependency management challenges.  

Agents must reason about version constraints, security vulnerabilities, and limited action budgets to maintain stable and secure software systems.

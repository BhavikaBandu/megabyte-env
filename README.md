# Megabyte Environment

Megabyte Environment is a Reinforcement Learning (RL) simulation built on top of the OpenEnv framework. It is designed to train intelligent agents to manage, repair, and secure complex software dependency graphs—replicating the real-world challenge commonly known as "Dependency Hell."

The environment focuses on teaching agents how to:

* Detect broken builds
* Resolve dependency conflicts
* Mitigate security vulnerabilities
* Maintain system stability under constraints

---

## Overview

Modern software systems rely on deeply interconnected dependency graphs. Version incompatibilities and security vulnerabilities frequently create cascading failures.

Megabyte simulates this ecosystem by exposing an RL agent to a controlled but highly realistic environment where it must reason about:

* Package compatibility
* Version constraints
* Security risks (CVEs)
* Limited action budgets

The agent must balance correctness (build success) with security (zero vulnerabilities).

---

## Core Concepts

### 1. Observation (MegabyteObservation)

This is the only information visible to the agent at each step.

Fields:

* status: Build state ("SUCCESS" or "FAILURE")
* build_log: Detailed log explaining failures or warnings
* current_manifest: Dictionary mapping packages to versions
* attempts_remaining: Remaining steps before termination

Purpose:
Provides structured feedback for decision-making without exposing ground truth.

---

### 2. State (MegabyteState)

This is the hidden ground truth, used internally for environment validation and training.

Fields:

* initial_manifest: Starting package configuration
* dependency_rules: Constraints governing compatibility
* vulnerabilities: List of known CVEs affecting packages
* available_versions: All valid versions per package

Purpose:
Defines the full problem space and evaluation criteria.

---

### 3. Actions (MegabyteAction)

The agent interacts with the environment through a constrained action space:

* UPGRADE(package, version)
* DOWNGRADE(package, version)
* REVERT()
* RESET()

Design Notes:

* Actions are discrete and deterministic
* No partial updates: every action fully mutates the manifest
* Encourages planning rather than brute force

---

## Task Levels

The environment is structured into three progressive difficulty levels, each requiring increasingly sophisticated reasoning.

---

### Easy: Identification

Role: Monitor

Objective:
Determine whether the current manifest is valid.

Agent Behavior:

* Inspect status
* Parse build_log if needed
* No modifications allowed

Success Criteria:

* Correctly classify system health (SUCCESS vs FAILURE)

---

### Medium: Dependency Resolution

Role: Package Manager

Objective:
Fix version conflicts and achieve a successful build.

Agent Behavior:

* Detect failing packages
* Consult dependency_rules
* Search available_versions
* Apply UPGRADE or DOWNGRADE

Constraints:

* Limited number of attempts

Success Criteria:

* Transition from FAILURE to SUCCESS

---

### Hard: Secure Dependency Resolution

Role: Security Engineer

Objective:
Achieve a working build with zero vulnerabilities.

Agent Behavior:

* Identify vulnerable packages from vulnerabilities
* Find secure versions
* Ensure compatibility with all dependencies
* Perform multi-step fixes when required

Key Challenge:
Fixing one vulnerability may break dependencies elsewhere, requiring cascade updates.

Success Criteria:

* status == "SUCCESS"
* len(vulnerabilities) == 0

---

## Environment Mechanics

### Dependency System

* Graph-based dependency relationships
* Version constraints (e.g., semantic compatibility)
* Conflict detection during validation

### Build System Simulation

* Deterministic evaluation
* Structured logs for debugging
* Failure propagation across dependency chains

### Vulnerability Modeling

* CVE-style tagging
* Version-specific exposure
* Security-aware scoring

---

## Technical Infrastructure

Megabyte is deployed via Hugging Face Spaces and communicates using a persistent WebSocket connection.

Key Components:

1. Client (MegabyteEnv)

* Handles communication with the backend
* Serializes actions
* Receives observations
* Validates responses using Pydantic models

2. Backend Environment

* Maintains state
* Applies actions
* Computes build results
* Injects dependency and vulnerability logic

3. Communication Layer

* WebSocket-based
* Low-latency interaction loop
* Supports real-time RL training

---

## RL Loop

Typical interaction cycle:

```python
obs = env.reset()

done = False
while not done:
    action = agent.act(obs)
    obs, reward, done, info = env.step(action)
```

---

## Learning Objectives

Agents trained in Megabyte learn to:

* Perform constraint reasoning over graphs
* Interpret unstructured logs
* Optimize under limited action budgets
* Balance correctness vs security
* Execute multi-step planning strategies

---

## Potential Research Applications

* Automated dependency management
* Secure software supply chain optimization
* Program synthesis under constraints
* Multi-objective reinforcement learning
* Autonomous DevOps agents

---

## Example Scenario

Initial State:

```json
{
  "packageA": "1.0",
  "packageB": "2.0"
}
```

Problem:

* packageA@1.0 incompatible with packageB@2.0
* packageB@2.0 has a vulnerability

Solution Path:

1. Downgrade packageB to 1.5
2. Verify compatibility
3. Confirm vulnerability removed

---

## Key Challenges

* Combinatorial explosion of version choices
* Hidden dependency constraints
* Trade-offs between stability and security
* Limited observation vs full state

---

## Future Extensions

* Probabilistic failures
* Partial observability (noisy logs)
* Multi-agent collaboration
* Real-world package registry integration
* Learning-based dependency rule inference

---

## Contribution Guidelines

* Follow modular design principles
* Add new dependency rules as composable units
* Ensure deterministic behavior for reproducibility
* Include tests for new environment features

---

## License

Specify license here (e.g., MIT, Apache 2.0).

---

## Resources

* Hugging Face Space: [https://huggingface.co/spaces/BhavikaBandu/megabyte-env](https://huggingface.co/spaces/BhavikaBandu/megabyte-env)

---

## Summary

Megabyte Environment transforms the problem of dependency management into a structured RL challenge. By combining build systems, dependency graphs, and security constraints, it creates a testbed for training autonomous software engineering agents.python
obs = env.reset()

done = False
while not done:
action = agent.act(obs)
obs, reward, done, info = env.step(action)

````

---

##  Learning Objectives

Agents trained in Megabyte learn to:

- Perform **constraint reasoning** over graphs
- Interpret **unstructured logs**
- Optimize under **limited action budgets**
- Balance **correctness vs security**
- Execute **multi-step planning strategies**

---

##  Potential Research Applications

- Automated dependency management
- Secure software supply chain optimization
- Program synthesis under constraints
- Multi-objective reinforcement learning
- Autonomous DevOps agents

---

##  Example Scenario

### Initial State:
```json
{
  "packageA": "1.0",
  "packageB": "2.0"
}
````

### Problem:

* `packageA@1.0` incompatible with `packageB@2.0`
* `packageB@2.0` has a vulnerability

### Solution Path:

1. Downgrade `packageB` → `1.5`
2. Verify compatibility
3. Confirm vulnerability removed

---

## Key Challenges

* Combinatorial explosion of version choices
* Hidden dependency constraints
* Trade-offs between stability and security
* Limited observation vs full state

---

## Future Extensions

* Probabilistic failures
* Partial observability (noisy logs)
* Multi-agent collaboration
* Real-world package registry integration
* Learning-based dependency rule inference

---

## Contribution Guidelines

* Follow modular design principles
* Add new dependency rules as composable units
* Ensure deterministic behavior for reproducibility
* Include tests for new environment features

---

## License

Specify license here (e.g., MIT, Apache 2.0).

---

## Resources

* Hugging Face Space: [https://huggingface.co/spaces/BhavikaBandu/megabyte-env](https://huggingface.co/spaces/BhavikaBandu/megabyte-env)

---

## Summary

Megabyte Environment transforms the chaotic problem of dependency management into a structured RL challenge. By combining build systems, dependency graphs, and security constraints, it creates a powerful testbed for training next-generation autonomous software engineering agents.

```
```


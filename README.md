---
title: Megabyte Environment Server
emoji: 🎮
colorFrom: green
colorTo: green
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
---

# Megabyte Environment

Megabyte is an OpenEnv environment for dependency and vulnerability remediation.  
It simulates a software package ecosystem where an agent must inspect package versions, resolve dependency conflicts, and reduce known vulnerabilities through actions such as upgrade, downgrade, reset, and revert.

## Running Locally

```bash
docker build -t megabyte-env .
docker run -p 8000:8000 megabyte-env
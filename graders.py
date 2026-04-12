"""
Graders for the Megabyte environment tasks.

This file contains final scoring functions for the three benchmark tasks.

Tasks:
1. Easy   - System Triage
2. Medium - Dependency Repair
3. Hard   - Secure Dependency Repair
"""

from __future__ import annotations

from typing import Any, Dict


# ============================================================
# Helper functions
# ============================================================

EPS = 1e-4


def _clamp_score(score: float) -> float:
    """
    Clamp any score into the strict benchmark range (0.0, 1.0).

    The validator rejects exact boundary values 0.0 and 1.0,
    so all returned scores must satisfy:
        0.0 < score < 1.0
    """
    return max(EPS, min(1.0 - EPS, round(float(score), 4)))


def _safe_len(value: Any) -> int:
    """
    Safely get the length of a dict/list-like object.
    Returns 0 if the value is None or invalid.
    """
    try:
        return len(value)
    except Exception:
        return 0


def infer_true_system_state(report: Dict[str, Any]) -> str:
    """
    Infer the true easy-task system state from the final environment report.

    Possible outputs:
    - safe_and_stable
    - stable_but_insecure
    - broken_but_secure
    - broken_and_insecure
    """
    has_conflicts = _safe_len(report.get("dependency_conflicts", {})) > 0
    has_vulnerabilities = _safe_len(report.get("vulnerabilities", {})) > 0

    if not has_conflicts and not has_vulnerabilities:
        return "safe_and_stable"
    if not has_conflicts and has_vulnerabilities:
        return "stable_but_insecure"
    if has_conflicts and not has_vulnerabilities:
        return "broken_but_secure"
    return "broken_and_insecure"


# ============================================================
# Easy Task Grader
# ============================================================

def grade_easy_task(predicted_label: str, final_report: Dict[str, Any]) -> float:
    """
    Easy Task: System Triage

    The agent classifies the system into one of four states:
    - safe_and_stable
    - stable_but_insecure
    - broken_but_secure
    - broken_and_insecure

    Returns a score strictly between 0 and 1.
    """
    true_label = infer_true_system_state(final_report)
    predicted_label = (predicted_label or "").strip().lower()

    score = 1.0 if predicted_label == true_label else 0.0
    return _clamp_score(score)


# ============================================================
# Medium Task Grader
# ============================================================

def grade_medium_task(final_report: Dict[str, Any], steps_used: int, max_steps: int) -> float:
    """
    Medium Task: Dependency Repair

    The agent must resolve dependency conflicts and restore a valid build.
    Vulnerabilities are ignored for this task.

    Returns a score strictly between 0 and 1.
    """
    build_success = final_report.get("build") == "SUCCESS"
    num_conflicts = _safe_len(final_report.get("dependency_conflicts", {}))

    repair_success = 1.0 if (build_success and num_conflicts == 0) else 0.0

    if max_steps <= 0:
        efficiency = 0.0
    else:
        efficiency = max(0.0, 1.0 - (steps_used / max_steps))

    score = (0.85 * repair_success) + (0.15 * efficiency)
    return _clamp_score(score)


# ============================================================
# Hard Task Grader
# ============================================================

def grade_hard_task(
    initial_report: Dict[str, Any],
    final_report: Dict[str, Any],
    steps_used: int,
    max_steps: int,
) -> float:
    """
    Hard Task: Secure Dependency Repair

    The agent must:
    - resolve dependency conflicts
    - remove vulnerabilities
    - restore a valid build

    Returns a score strictly between 0 and 1.
    """
    initial_vulns = _safe_len(initial_report.get("vulnerabilities", {}))
    final_vulns = _safe_len(final_report.get("vulnerabilities", {}))

    initial_conflicts = _safe_len(initial_report.get("dependency_conflicts", {}))
    final_conflicts = _safe_len(final_report.get("dependency_conflicts", {}))

    build_success = final_report.get("build") == "SUCCESS"

    full_success = 1.0 if (
        build_success and final_vulns == 0 and final_conflicts == 0
    ) else 0.0

    if initial_vulns == 0:
        vuln_reduction_score = 1.0 if final_vulns == 0 else 0.0
    else:
        vuln_reduction_score = (initial_vulns - final_vulns) / initial_vulns
        vuln_reduction_score = max(0.0, min(1.0, vuln_reduction_score))

    if initial_conflicts == 0:
        conflict_reduction_score = 1.0 if final_conflicts == 0 else 0.0
    else:
        conflict_reduction_score = (initial_conflicts - final_conflicts) / initial_conflicts
        conflict_reduction_score = max(0.0, min(1.0, conflict_reduction_score))

    if max_steps <= 0:
        efficiency = 0.0
    else:
        efficiency = max(0.0, 1.0 - (steps_used / max_steps))

    score = (
        0.50 * full_success
        + 0.25 * vuln_reduction_score
        + 0.15 * conflict_reduction_score
        + 0.10 * efficiency
    )

    return _clamp_score(score)
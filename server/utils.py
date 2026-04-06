"""Megabyte Helper Script"""

import json
import secrets
from packaging.version import parse as parse_version, InvalidVersion
from packaging.specifiers import SpecifierSet


def _safe_parse(v_string):
    """
    Attempts to safely parse version strings.

    Args:
        v_string: The version string to be parsed.

    Returns:
        A parsed Version object, defaulting to 0.0.0 on failure.
    """
    try:
        return parse_version(v_string)
    except (InvalidVersion, TypeError):
        return parse_version("0.0.0")


def generate_state(data):
    """
    Processes raw environment data to produce lookup tables and a randomized initial manifest.

    Args:
        data: The raw JSON dictionary containing manifest and dependencies.

    Returns:
        tuple: (version_table, vulnerability_table, dependency_table, current_manifest).
    """
    manifest_data = data.get("manifest", {})
    visible_deps = data.get("visible_dependencies", {})

    # VERSION TABLE
    version_table = {
        pkg: sorted(info["all_versions"], key=_safe_parse) 
        for pkg, info in manifest_data.items()
    }

    # VULNERABILITY TABLE
    vulnerability_table = {}
    for pkg, info in manifest_data.items():
        vulns = info.get("vulnerabilities", [])
        if vulns:
            vulnerability_table[pkg] = [
                {
                    "introduced": v["ranges"][0].get("introduced"), 
                    "fixed": v["ranges"][0].get("fixed"), 
                    "severity": v.get("severity")
                }
                for v in vulns
            ]

    # DEPENDENCY TABLE
    dependency_table = {
        parent: {d[0]: d[1] for d in deps} 
        for parent, deps in visible_deps.items()
    }

    # CURRENT MANIFEST
    entropy = secrets.randbits(32)
    difficulty_roll = entropy % 3

    current_manifest = {pkg: info["installed"] for pkg, info in manifest_data.items()}
    all_packages = list(current_manifest.keys())

    scramble_factor = (difficulty_roll + 1) / 3
    num_to_scramble = int(len(all_packages) * scramble_factor)

    scramble_targets = secrets.SystemRandom().sample(all_packages, num_to_scramble)

    for pkg in scramble_targets:
        random_version = secrets.SystemRandom().choice(version_table[pkg])
        current_manifest[pkg] = random_version

    return (
        version_table, 
        vulnerability_table, 
        dependency_table, 
        current_manifest
    )


def evaluate_manifest(current_manifest, dependency_table, vulnerability_table):
    """
    Evaluates the manifest to check for dependency rule violations and active security vulnerabilities.

    Args:
        current_manifest: Dict of {package_name: installed_version_string}.
        dependency_table: Dict of {parent: {child: constraint_string}}.
        vulnerability_table: Dict of {package_name: list_of_vulnerability_dicts}.

    Returns:
        list: A list of strings describing found issues (conflicts or vulnerabilities).
    """
    dependency_conflicts = {}
    vulnerabilities = {}

    # DEPENDENCY CHECK
    for parent, requirements in dependency_table.items():
        if parent not in current_manifest:
            continue
        for child, constraint in requirements.items():
            if child not in current_manifest:
                dependency_conflicts[child] = f"Missing; required by {parent}"
                continue

            if not constraint or constraint.lower() == "any":
                continue

            installed_v = current_manifest[child]
            try:
                spec = SpecifierSet(constraint)
                if _safe_parse(installed_v) not in spec:
                    dependency_conflicts[child] = f"Requires {constraint} (from {parent}), but {installed_v} installed"
            except Exception:
                continue

    # VULNERABILITY CHECK
    for pkg, installed_v in current_manifest.items():
        if pkg in vulnerability_table:
            v_parsed = _safe_parse(installed_v)
            pkg_severities = []

            for vuln in vulnerability_table[pkg]:
                intro_v = _safe_parse(vuln["introduced"])
                fixed_v = _safe_parse(vuln["fixed"]) if vuln["fixed"] else None

                is_vulnerable = v_parsed >= intro_v
                if fixed_v and v_parsed >= fixed_v:
                    is_vulnerable = False

                if is_vulnerable:
                    pkg_severities.append(vuln.get("severity", 0.0))

            if pkg_severities:
                avg_severity = sum(pkg_severities) / len(pkg_severities)
                vulnerabilities[pkg] = {
                    "installed_version": installed_v,
                    "count": len(pkg_severities),
                    "severity": round(avg_severity, 2)
                }

    build_status = "FAILURE" if dependency_conflicts else "SUCCESS"

    return {
        "build": build_status,
        "dependency_conflicts": dependency_conflicts,
        "vulnerabilities": vulnerabilities
    }


#!/usr/bin/env python3
"""Adaptive-native CG-MPD V6 profile, path, gate, and risk helpers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

RISK_LEVELS = ("FAST", "STANDARD", "CRITICAL")
RISK_RANK = {name: index for index, name in enumerate(RISK_LEVELS)}
AUTH_VALUES = {"unknown", "granted", "denied"}
TRANSPORTS = {"native-dispatch", "prompt-handoff"}


class PolicyError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_path_rule(rule: object) -> str:
    if not isinstance(rule, str) or not rule.strip():
        raise PolicyError("path rule must be a non-empty string")
    rule = rule.strip()
    if rule.startswith("/") or "\\" in rule or any(part == ".." for part in rule.split("/")):
        raise PolicyError(f"invalid path rule {rule!r}: use repository-relative paths")
    wildcard_chars = set("*?[")
    if rule.endswith("/**"):
        prefix = rule[:-3].rstrip("/")
        if not prefix or any(ch in prefix for ch in wildcard_chars):
            raise PolicyError(f"invalid subtree rule {rule!r}")
        return rule
    if any(ch in rule for ch in wildcard_chars):
        raise PolicyError(
            f"invalid path rule {rule!r}: V6 accepts exact files or a final '/**' subtree only"
        )
    return rule


def _kind(rule: str) -> tuple[str, str]:
    rule = validate_path_rule(rule)
    if rule.endswith("/**"):
        return "subtree", rule[:-3].rstrip("/")
    return "exact", rule


def path_matches(path: str, rule: str) -> bool:
    kind, value = _kind(rule)
    if kind == "exact":
        return path == value
    return path == value or path.startswith(value + "/")


def rules_overlap(left: str, right: str) -> bool:
    lk, lv = _kind(left)
    rk, rv = _kind(right)
    if lk == "exact" and rk == "exact":
        return lv == rv
    if lk == "exact":
        return path_matches(lv, right)
    if rk == "exact":
        return path_matches(rv, left)
    return lv == rv or lv.startswith(rv + "/") or rv.startswith(lv + "/")


def _risk(value: object, *, field: str) -> str:
    if value not in RISK_RANK:
        raise PolicyError(f"{field} must be FAST, STANDARD, or CRITICAL")
    return str(value)


def _normalize_gate(gate: object) -> dict[str, str]:
    if not isinstance(gate, dict):
        raise PolicyError("verification.gate_catalog entries must be objects")
    normalized: dict[str, str] = {}
    for key in ("id", "job"):
        value = gate.get(key)
        if not isinstance(value, str) or not value.strip():
            raise PolicyError(f"metadata gate {key} must be a non-empty string")
        normalized[key] = value.strip()
    step = gate.get("step")
    if step is not None:
        if not isinstance(step, str) or not step.strip():
            raise PolicyError("metadata gate step must be a non-empty string when present")
        normalized["step"] = step.strip()
    return normalized


def gate_catalog(profile: dict) -> dict[str, dict[str, str]]:
    values = (profile.get("verification") or {}).get("gate_catalog")
    if not isinstance(values, list) or not values:
        raise PolicyError("verification.gate_catalog must contain at least one metadata gate")
    gates = [_normalize_gate(gate) for gate in values]
    catalog = {gate["id"]: gate for gate in gates}
    if len(catalog) != len(gates):
        raise PolicyError("gate catalog ids must be unique")
    return catalog


def risk_gate_ids(profile: dict, level: str) -> list[str]:
    _risk(level, field="risk level")
    levels = ((profile.get("risk_policy") or {}).get("levels") or {})
    config = levels.get(level) or {}
    gates = config.get("gates")
    if not isinstance(gates, list) or not gates or not all(isinstance(x, str) and x.strip() for x in gates):
        raise PolicyError(f"risk level {level!r} must define a non-empty gate id list")
    return [x.strip() for x in gates]


def gates_for_level(profile: dict, level: str) -> list[dict[str, str]]:
    catalog = gate_catalog(profile)
    ids = risk_gate_ids(profile, level)
    missing = [gate_id for gate_id in ids if gate_id not in catalog]
    if missing:
        raise PolicyError(f"risk level {level!r} references unknown gates: {', '.join(missing)}")
    return [catalog[gate_id] for gate_id in ids]


def find_lane(profile: dict, lane_id: str) -> dict:
    for lane in profile.get("lanes", []):
        if lane.get("id") == lane_id:
            return lane
    raise PolicyError(f"unknown lane {lane_id!r}")


def validate_profile(data: dict) -> dict:
    errors: list[str] = []
    if not isinstance(data, dict):
        raise PolicyError("profile must be a JSON object")
    if data.get("schema_version") != 4:
        errors.append("schema_version must be 4")
    if data.get("protocol_version") != 6:
        errors.append("protocol_version must be 6")
    if not isinstance(data.get("wave"), str) or not data["wave"].strip():
        errors.append("wave must be a non-empty string")

    repo = data.get("repository") or {}
    for key in ("repo", "trunk", "frozen_base_sha"):
        if not isinstance(repo.get(key), str) or not repo[key].strip():
            errors.append(f"repository.{key} must be a non-empty string")
    sha = repo.get("frozen_base_sha")
    if isinstance(sha, str) and (len(sha) != 40 or any(ch not in "0123456789abcdefABCDEF" for ch in sha)):
        errors.append("repository.frozen_base_sha must be a full 40-character hexadecimal SHA")

    adaptive = data.get("adaptive") or {}
    try:
        floor = _risk(adaptive.get("risk_floor"), field="adaptive.risk_floor")
        if RISK_RANK[floor] < RISK_RANK["STANDARD"]:
            errors.append("adaptive.risk_floor must be STANDARD or CRITICAL for an MPD wave")
    except PolicyError as exc:
        errors.append(str(exc))
    if adaptive.get("transport") not in TRANSPORTS:
        errors.append("adaptive.transport must be native-dispatch or prompt-handoff")
    authorization = adaptive.get("authorization")
    if not isinstance(authorization, dict):
        errors.append("adaptive.authorization must be an object")
        authorization = {}
    for key in ("push", "merge", "deploy", "production_write", "destructive_action"):
        if authorization.get(key) not in AUTH_VALUES:
            errors.append(f"adaptive.authorization.{key} must be unknown, granted, or denied")

    verification = data.get("verification") or {}
    workflow = verification.get("workflow") or {}
    for key in ("name", "path", "head_event", "trunk_event"):
        if not isinstance(workflow.get(key), str) or not workflow[key].strip():
            errors.append(f"verification.workflow.{key} must be a non-empty string")
    try:
        catalog = gate_catalog(data)
    except PolicyError as exc:
        errors.append(str(exc))
        catalog = {}

    risk = data.get("risk_policy") or {}
    try:
        _risk(risk.get("default_level"), field="risk_policy.default_level")
    except PolicyError as exc:
        errors.append(str(exc))
    level_sets: dict[str, set[str]] = {}
    for level in RISK_LEVELS:
        try:
            ids = risk_gate_ids(data, level)
            unknown = [gate_id for gate_id in ids if gate_id not in catalog]
            if unknown:
                errors.append(f"risk level {level}: unknown gate ids {unknown}")
            level_sets[level] = set(ids)
        except PolicyError as exc:
            errors.append(str(exc))
            level_sets[level] = set()
    if level_sets["FAST"] and not level_sets["FAST"].issubset(level_sets["STANDARD"]):
        errors.append("risk gates must be monotonic: FAST gates must be a subset of STANDARD")
    if level_sets["STANDARD"] and not level_sets["STANDARD"].issubset(level_sets["CRITICAL"]):
        errors.append("risk gates must be monotonic: STANDARD gates must be a subset of CRITICAL")

    for index, floor_rule in enumerate(risk.get("path_floors") or []):
        if not isinstance(floor_rule, dict):
            errors.append(f"risk_policy.path_floors[{index}] must be an object")
            continue
        try:
            _risk(floor_rule.get("level"), field=f"risk_policy.path_floors[{index}].level")
        except PolicyError as exc:
            errors.append(str(exc))
        paths = floor_rule.get("paths")
        if not isinstance(paths, list) or not paths:
            errors.append(f"risk_policy.path_floors[{index}].paths must be non-empty")
            continue
        for rule in paths:
            try:
                validate_path_rule(rule)
            except PolicyError as exc:
                errors.append(f"risk floor path invalid: {exc}")

    hot_zones = data.get("hot_zones", [])
    if not isinstance(hot_zones, list):
        errors.append("hot_zones must be a list")
        hot_zones = []
    valid_hot: list[str] = []
    for rule in hot_zones:
        try:
            valid_hot.append(validate_path_rule(rule))
        except PolicyError as exc:
            errors.append(f"hot-zone path invalid: {exc}")

    lanes = data.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        errors.append("lanes must be a non-empty list")
        lanes = []
    ids: list[str] = []
    branches: list[str] = []
    deps: dict[str, list[str]] = {}
    downstream: dict[str, list[str]] = {}
    owned_entries: list[tuple[str, str, bool]] = []

    default_level = risk.get("default_level")
    for lane in lanes:
        if not isinstance(lane, dict):
            errors.append("each lane must be an object")
            continue
        lane_id = lane.get("id")
        branch = lane.get("branch")
        if not isinstance(lane_id, str) or not lane_id.strip():
            errors.append("lane.id must be a non-empty string")
            continue
        ids.append(lane_id)
        if not isinstance(branch, str) or not branch.strip():
            errors.append(f"lane {lane_id}: branch must be a non-empty string")
        else:
            branches.append(branch)
        try:
            _risk(lane.get("risk", default_level), field=f"lane {lane_id}.risk")
        except PolicyError as exc:
            errors.append(str(exc))
        integration = lane.get("integration", False)
        if not isinstance(integration, bool):
            errors.append(f"lane {lane_id}: integration must be boolean when present")
            integration = False

        owned = lane.get("owned")
        if not isinstance(owned, list) or not owned:
            errors.append(f"lane {lane_id}: owned must be a non-empty list of path rules")
            owned = []
        valid_owned: list[str] = []
        for rule in owned:
            try:
                normalized = validate_path_rule(rule)
                valid_owned.append(normalized)
                owned_entries.append((lane_id, normalized, integration))
            except PolicyError as exc:
                errors.append(f"lane {lane_id}: owned path invalid: {exc}")

        forbidden = lane.get("forbidden", [])
        if not isinstance(forbidden, list):
            errors.append(f"lane {lane_id}: forbidden must be a list of path rules")
            forbidden = []
        valid_forbidden: list[str] = []
        for rule in forbidden:
            try:
                valid_forbidden.append(validate_path_rule(rule))
            except PolicyError as exc:
                errors.append(f"lane {lane_id}: forbidden path invalid: {exc}")
        for left in valid_owned:
            for right in valid_forbidden:
                if rules_overlap(left, right):
                    errors.append(f"lane {lane_id}: owned path {left!r} overlaps forbidden path {right!r}")
            for hot in valid_hot:
                if rules_overlap(left, hot) and not integration:
                    errors.append(f"lane {lane_id}: owned path {left!r} overlaps hot zone {hot!r}; use an integration lane")

        prereqs = lane.get("prerequisites", [])
        if not isinstance(prereqs, list) or not all(isinstance(x, str) for x in prereqs):
            errors.append(f"lane {lane_id}: prerequisites must be a list of lane ids")
            prereqs = []
        deps[lane_id] = prereqs
        children = lane.get("downstream", [])
        if not isinstance(children, list) or not all(isinstance(x, str) for x in children):
            errors.append(f"lane {lane_id}: downstream must be a list of lane ids")
            children = []
        downstream[lane_id] = children

    if len(ids) != len(set(ids)):
        errors.append("lane ids must be unique")
    if len(branches) != len(set(branches)):
        errors.append("lane branches must be unique")
    for i, (lane_a, rule_a, _) in enumerate(owned_entries):
        for lane_b, rule_b, _ in owned_entries[i + 1:]:
            if lane_a != lane_b and rules_overlap(rule_a, rule_b):
                errors.append(f"owned scope overlap: {lane_a}:{rule_a!r} overlaps {lane_b}:{rule_b!r}")

    id_set = set(ids)
    for lane_id, prereqs in deps.items():
        for dep in prereqs:
            if dep not in id_set:
                errors.append(f"lane {lane_id}: unknown prerequisite {dep}")
            elif dep == lane_id:
                errors.append(f"lane {lane_id}: cannot depend on itself")
    for lane_id, children in downstream.items():
        for child in children:
            if child not in id_set:
                errors.append(f"lane {lane_id}: unknown downstream lane {child}")
            elif lane_id not in deps.get(child, []):
                errors.append(f"lane {lane_id}: downstream {child} must list {lane_id} as a prerequisite")

    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            errors.append(f"dependency cycle detected at lane {node}")
            return
        visiting.add(node)
        for dep in deps.get(node, []):
            if dep in id_set:
                visit(dep)
        visiting.remove(node)
        visited.add(node)
    for lane_id in ids:
        visit(lane_id)

    merge = data.get("merge") or {}
    if merge.get("method") not in {"squash", "merge", "rebase"}:
        errors.append("merge.method must be squash, merge, or rebase")
    if not isinstance(merge.get("approvals_dir"), str) or not merge["approvals_dir"].strip():
        errors.append("merge.approvals_dir must be a non-empty path")
    if merge.get("trunk_green_after_each") is not True:
        errors.append("merge.trunk_green_after_each must be true")

    if errors:
        raise PolicyError("; ".join(errors))
    return data


def load_profile(path: str | Path) -> tuple[Path, dict]:
    p = Path(path).resolve()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"profile unreadable: {exc}") from exc
    return p, validate_profile(data)


def resolve_effective_risk(
    profile: dict,
    lane_id: str,
    changed_files: Iterable[str],
    *,
    runtime_risk: str | None = None,
) -> dict:
    validate_profile(profile)
    lane = find_lane(profile, lane_id)
    floor = _risk((profile.get("adaptive") or {}).get("risk_floor"), field="adaptive.risk_floor")
    default = _risk((profile.get("risk_policy") or {}).get("default_level"), field="risk_policy.default_level")
    declared = _risk(lane.get("risk", default), field=f"lane {lane_id}.risk")
    effective = max((floor, declared), key=RISK_RANK.__getitem__)
    escalations: list[dict[str, str]] = []
    if RISK_RANK[floor] > RISK_RANK[declared]:
        escalations.append({"reason": "inherited-risk-floor", "from": declared, "to": floor})

    for path in changed_files:
        for floor_rule in ((profile.get("risk_policy") or {}).get("path_floors") or []):
            level = _risk(floor_rule.get("level"), field="path floor level")
            for rule in floor_rule.get("paths") or []:
                normalized = validate_path_rule(rule)
                if path_matches(path, normalized) and RISK_RANK[level] > RISK_RANK[effective]:
                    escalations.append({"reason": "path-floor", "path": path, "rule": normalized, "from": effective, "to": level})
                    effective = level

    if runtime_risk is not None:
        runtime = _risk(runtime_risk, field="runtime_risk")
        if RISK_RANK[runtime] > RISK_RANK[effective]:
            escalations.append({"reason": "runtime-escalation", "from": effective, "to": runtime})
            effective = runtime

    return {"declared": declared, "floor": floor, "effective": effective, "escalations": escalations}

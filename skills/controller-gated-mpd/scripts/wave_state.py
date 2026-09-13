#!/usr/bin/env python3
"""Read-only Controller-Gated MPD V6 dependency/recovery state helper.

The helper intentionally does not query or mutate GitHub. A coordinator must first
reconcile current Git/PR/Actions facts into integration.json. Dependency release
then consumes only those independently verified fields; worker reports remain hints.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

V6_PROTOCOL = 6
V6_WAVE_SCHEMA = 4
VALID_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
DEPENDENCY_SATISFIED = "satisfied"
VERIFIED_SOURCES = {"git-pr-actions", "controller-reconciled"}
REQUIRED_DIRS = ("handoffs", "evidence", "approvals")


class WaveStateError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WaveStateError(f"missing canonical ledger file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WaveStateError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WaveStateError(f"expected JSON object in {path}")
    return value


def load_ledger(wave_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    wave_dir = wave_dir.resolve()
    if not wave_dir.is_dir():
        raise WaveStateError(f"wave directory does not exist: {wave_dir}")
    for dirname in REQUIRED_DIRS:
        path = wave_dir / dirname
        if not path.is_dir():
            raise WaveStateError(f"missing canonical ledger directory: {path}")

    wave = _read_json(wave_dir / "wave.json")
    integration = _read_json(wave_dir / "integration.json")

    if wave.get("schema_version") != V6_WAVE_SCHEMA or wave.get("protocol_version") != V6_PROTOCOL:
        raise WaveStateError("wave.json is not a V6 schema_version=4/protocol_version=6 wave")
    if integration.get("protocol_version") != V6_PROTOCOL:
        raise WaveStateError("integration.json must declare protocol_version=6")
    if not isinstance(wave.get("wave"), str) or not wave["wave"]:
        raise WaveStateError("wave.json missing non-empty wave id")
    if integration.get("wave") != wave["wave"]:
        raise WaveStateError("integration.json wave id does not match wave.json")
    if not isinstance(wave.get("lanes"), list):
        raise WaveStateError("wave.json lanes must be a list")
    if not isinstance(integration.get("lanes", {}), dict):
        raise WaveStateError("integration.json lanes must be an object")
    return wave, integration


def _lane_map(wave: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for lane in wave["lanes"]:
        if not isinstance(lane, dict) or not isinstance(lane.get("id"), str) or not lane["id"]:
            raise WaveStateError("each lane must have a non-empty string id")
        lane_id = lane["id"]
        if lane_id in result:
            raise WaveStateError(f"duplicate lane id: {lane_id}")
        prereqs = lane.get("prerequisites", [])
        if not isinstance(prereqs, list) or not all(isinstance(item, str) and item for item in prereqs):
            raise WaveStateError(f"lane {lane_id} prerequisites must be a list of lane ids")
        result[lane_id] = lane
    for lane_id, lane in result.items():
        for prereq in lane.get("prerequisites", []):
            if prereq not in result:
                raise WaveStateError(f"lane {lane_id} references unknown prerequisite {prereq}")
    return result


def _valid_head(value: Any) -> bool:
    return isinstance(value, str) and bool(VALID_SHA.fullmatch(value))


def _head_facts(integration: dict[str, Any], lane_id: str) -> dict[str, Any]:
    lane_state = integration.get("lanes", {}).get(lane_id, {})
    if not isinstance(lane_state, dict):
        lane_state = {}
    worker_report = lane_state.get("worker_report", {})
    verified_pr = lane_state.get("verified_pr", {})
    if not isinstance(worker_report, dict):
        worker_report = {}
    if not isinstance(verified_pr, dict):
        verified_pr = {}

    worker_head = worker_report.get("reported_head_sha")
    verified_head = verified_pr.get("head_sha")
    return {
        "worker_reported_head_sha": worker_head if _valid_head(worker_head) else None,
        "verified_pr_head_sha": verified_head if _valid_head(verified_head) else None,
        "verified_pr_number": verified_pr.get("number") if isinstance(verified_pr.get("number"), int) and verified_pr.get("number") > 0 else None,
        # Worker reports are deliberately never promoted to authority.
        "authoritative_head_sha": verified_head if _valid_head(verified_head) else None,
        "heads_match": bool(_valid_head(worker_head) and _valid_head(verified_head) and worker_head == verified_head),
        "verified_dependency_state": verified_pr.get("dependency_state"),
        "verified_source": verified_pr.get("source"),
    }


def lane_status(wave: dict[str, Any], integration: dict[str, Any], lane_id: str) -> dict[str, Any]:
    lanes = _lane_map(wave)
    if lane_id not in lanes:
        raise WaveStateError(f"unknown lane: {lane_id}")

    blockers: list[dict[str, str]] = []
    prerequisite_facts: dict[str, dict[str, Any]] = {}
    for prereq in lanes[lane_id].get("prerequisites", []):
        facts = _head_facts(integration, prereq)
        prerequisite_facts[prereq] = facts
        if not facts["verified_pr_head_sha"]:
            blockers.append({"lane": prereq, "reason": "missing independently verified PR head"})
            continue
        if not facts["verified_pr_number"]:
            blockers.append({"lane": prereq, "reason": "missing independently verified PR number"})
            continue
        if facts["verified_source"] not in VERIFIED_SOURCES:
            blockers.append({"lane": prereq, "reason": "verified PR state lacks an accepted independent reconciliation source"})
            continue
        if facts["verified_dependency_state"] != DEPENDENCY_SATISFIED:
            blockers.append({"lane": prereq, "reason": "verified dependency state is not satisfied"})

    return {
        "wave": wave["wave"],
        "lane": lane_id,
        "prerequisites": list(lanes[lane_id].get("prerequisites", [])),
        "dispatchable": not blockers,
        "blockers": blockers,
        "heads": _head_facts(integration, lane_id),
        "prerequisite_facts": prerequisite_facts,
    }


def recovery_status(wave: dict[str, Any], integration: dict[str, Any]) -> dict[str, Any]:
    lanes = _lane_map(wave)
    return {
        "wave": wave["wave"],
        "conversation_memory_required": False,
        "recovery_sources": ["git", "pull-requests", "actions", "mpd-ledger"],
        "lanes": {lane_id: lane_status(wave, integration, lane_id) for lane_id in lanes},
        "instruction": "Reconcile current Git/PR/Actions facts into verified_pr fields before releasing blocked downstream lanes.",
    }


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-layout", help="validate the canonical V6 ledger layout")
    validate.add_argument("wave_dir", type=Path)

    check = sub.add_parser("check-deps", help="fail closed unless a lane's verified prerequisites are satisfied")
    check.add_argument("wave_dir", type=Path)
    check.add_argument("lane")

    status = sub.add_parser("status", help="show one lane's dependency/head state")
    status.add_argument("wave_dir", type=Path)
    status.add_argument("lane")

    recover = sub.add_parser("recover", help="show recovery state derivable without conversation memory")
    recover.add_argument("wave_dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        wave, integration = load_ledger(args.wave_dir)
        _lane_map(wave)
        if args.command == "validate-layout":
            _emit({"wave": wave["wave"], "valid": True, "canonical_ledger": str(args.wave_dir.resolve())})
            return 0
        if args.command in {"check-deps", "status"}:
            state = lane_status(wave, integration, args.lane)
            _emit(state)
            if args.command == "check-deps" and not state["dispatchable"]:
                return 3
            return 0
        if args.command == "recover":
            _emit(recovery_status(wave, integration))
            return 0
        raise WaveStateError(f"unknown command: {args.command}")
    except WaveStateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Controller-only CG-MPD V6 READY@SHA materializer for authoritative Actions evidence."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

from actions_metadata import (
    MetadataError,
    get_pull_request,
    get_pull_request_files,
    read_json,
    require_full_sha,
    require_v6_evidence,
    validate_selected_attempt,
    write_json,
)
from policy import (
    PolicyError,
    gates_for_level,
    load_profile,
    resolve_effective_risk,
    risk_gate_ids,
    sha256_file,
)


def _mapping(value: object, *, field: str) -> dict:
    if not isinstance(value, dict):
        raise MetadataError(f"{field} must be an object")
    return value


def _string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise MetadataError(f"{field} must be a non-empty string")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise MetadataError(f"{field} must be a positive integer")
    return value


def validate_evidence_state(
    *,
    profile_path: Path,
    profile: dict,
    evidence: dict,
    lane: str,
    pr_number: int,
    gh: str,
    runtime_risk: str | None = None,
) -> dict:
    """Re-read live PR/files/Actions metadata and prove the evidence still names that exact state."""
    require_v6_evidence(evidence)
    repo = profile["repository"]["repo"]
    trunk = profile["repository"]["trunk"]
    if evidence.get("profile_digest") != sha256_file(profile_path):
        raise MetadataError("evidence profile digest does not match the current V6 wave profile")

    source = _mapping(evidence.get("source"), field="evidence source")
    if source.get("kind") != "pull_request" or source.get("pr") != pr_number or source.get("lane") != lane:
        raise MetadataError("evidence source does not match the requested V6 lane/PR")

    evidence_repo = _mapping(evidence.get("repository"), field="evidence repository")
    if evidence_repo.get("repo") != repo:
        raise MetadataError("evidence repository does not match the current V6 profile")
    evidence_head = require_full_sha(evidence_repo.get("head_sha"), field="evidence head")
    evidence_base = _string(evidence_repo.get("base_ref"), field="evidence base")

    live_pr = get_pull_request(gh, repo, pr_number)
    live_head = require_full_sha(live_pr["head"]["sha"], field="live PR head")
    live_base = _string(live_pr["base"]["ref"], field="live PR base")
    if live_head != evidence_head:
        raise MetadataError(f"live PR head {live_head} wins and does not match evidence head {evidence_head}")
    if live_base != evidence_base:
        raise MetadataError("live PR base does not match evidence base")
    if live_base != trunk:
        raise MetadataError(f"live PR base {live_base!r} does not match configured trunk {trunk!r}")

    changed_files = get_pull_request_files(gh, repo, pr_number)
    if evidence.get("changed_files") != changed_files:
        raise MetadataError("evidence changed-files metadata is stale or incomplete")

    risk_doc = _mapping(evidence.get("risk"), field="evidence risk")
    evidence_runtime = risk_doc.get("runtime_input")
    if runtime_risk is not None and runtime_risk != evidence_runtime:
        raise MetadataError("current runtime risk input does not match evidence runtime risk input")
    current_runtime = evidence_runtime if runtime_risk is None else runtime_risk
    risk = resolve_effective_risk(profile, lane, changed_files, runtime_risk=current_runtime)
    if risk_doc.get("declared") != risk["declared"] or risk_doc.get("floor") != risk["floor"]:
        raise MetadataError("evidence Adaptive risk inputs are stale")
    if risk_doc.get("effective") != risk["effective"]:
        raise MetadataError(
            f"effective Adaptive risk changed: evidence={risk_doc.get('effective')!r} current={risk['effective']!r}"
        )
    if risk_doc.get("escalation_reasons") != risk["escalations"]:
        raise MetadataError("evidence risk escalation reasons are stale")

    effective = risk["effective"]
    gates = gates_for_level(profile, effective)
    gate_ids = risk_gate_ids(profile, effective)
    if not gate_ids:
        raise MetadataError("required gate set is empty; zero-gate authority is forbidden")
    if evidence.get("required_gate_ids") != gate_ids or evidence.get("satisfied_gate_ids") != gate_ids:
        raise MetadataError("evidence gate binding does not match effective Adaptive risk")

    workflow_cfg = profile["verification"]["workflow"]
    expected_workflow = {
        "name": workflow_cfg["name"],
        "path": workflow_cfg["path"],
        "event": workflow_cfg["head_event"],
    }
    if evidence.get("workflow") != expected_workflow:
        raise MetadataError("evidence workflow name/path/event identity is stale or non-canonical")

    selected = _mapping(evidence.get("selected_run"), field="evidence selected_run")
    run_id = _positive_int(selected.get("id"), field="evidence run id")
    attempt = _positive_int(selected.get("attempt"), field="evidence run attempt")
    validate_selected_attempt(
        gh,
        repo,
        workflow_cfg,
        head_sha=live_head,
        event=workflow_cfg["head_event"],
        run_id=run_id,
        attempt=attempt,
        gates=gates,
    )
    return {
        "repo": repo,
        "pr": pr_number,
        "lane": lane,
        "head_sha": live_head,
        "base_ref": live_base,
        "risk": risk,
        "runtime_risk": current_runtime,
        "required_gate_ids": gate_ids,
        "selected_run": {"id": run_id, "attempt": attempt},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--controller-id", default="controller")
    parser.add_argument("--runtime-risk", choices=("FAST", "STANDARD", "CRITICAL"))
    parser.add_argument("--gh", default="gh")
    args = parser.parse_args()
    try:
        profile_path, profile = load_profile(args.profile)
        evidence_path = Path(args.evidence).resolve()
        evidence = read_json(evidence_path, context="V6 Actions evidence")
        state = validate_evidence_state(
            profile_path=profile_path,
            profile=profile,
            evidence=evidence,
            lane=args.lane,
            pr_number=args.pr,
            gh=args.gh,
            runtime_risk=args.runtime_risk,
        )
        receipt = {
            "schema_version": 4,
            "protocol_version": 6,
            "receipt_type": "READY@SHA",
            "authority_role": "controller",
            "controller": {
                "id": _string(args.controller_id, field="controller id"),
                "materialized_at": datetime.now(timezone.utc).isoformat(),
            },
            "repository": {
                "repo": state["repo"],
                "pr": state["pr"],
                "head_sha": state["head_sha"],
                "base_ref": state["base_ref"],
            },
            "lane": state["lane"],
            "profile_digest": sha256_file(profile_path),
            "risk": {
                "effective": state["risk"]["effective"],
                "runtime_input": state["runtime_risk"],
                "escalation_reasons": state["risk"]["escalations"],
            },
            "required_gate_ids": state["required_gate_ids"],
            "selected_run": state["selected_run"],
            "evidence_digest": sha256_file(evidence_path),
        }
        write_json(args.output, receipt)
    except (PolicyError, MetadataError, KeyError, TypeError) as exc:
        print(f"READY NOT ISSUED: {exc}", file=sys.stderr)
        return 2
    print(
        f"READY@SHA ISSUED: PR #{state['pr']} {state['head_sha']} "
        f"run {state['selected_run']['id']}@{state['selected_run']['attempt']} risk {state['risk']['effective']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

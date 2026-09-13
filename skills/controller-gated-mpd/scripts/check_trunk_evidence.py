#!/usr/bin/env python3
"""Create fail-closed CG-MPD V6 Actions evidence for an exact live trunk head."""
from __future__ import annotations

import argparse
import sys

from actions_metadata import MetadataError, get_branch_head, require_full_sha, select_complete_attempt, write_json
from policy import PolicyError, RISK_RANK, gates_for_level, load_profile, risk_gate_ids, sha256_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--effective-risk", required=True, choices=("FAST", "STANDARD", "CRITICAL"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--gh", default="gh")
    args = parser.parse_args()
    try:
        profile_path, profile = load_profile(args.profile)
        repo = profile["repository"]["repo"]
        trunk = profile["repository"]["trunk"]
        expected_head = require_full_sha(args.head, field="requested trunk head")
        live_head = get_branch_head(args.gh, repo, trunk)
        if live_head != expected_head:
            raise MetadataError(f"live trunk head {live_head} does not match requested exact head {expected_head}")
        floor = profile["adaptive"]["risk_floor"]
        if RISK_RANK[args.effective_risk] < RISK_RANK[floor]:
            raise MetadataError(
                f"trunk evidence risk {args.effective_risk} cannot be below inherited wave floor {floor}"
            )
        gates = gates_for_level(profile, args.effective_risk)
        gate_ids = risk_gate_ids(profile, args.effective_risk)
        if not gate_ids:
            raise MetadataError("required gate set is empty; zero-gate authority is forbidden")
        workflow_cfg = profile["verification"]["workflow"]
        event = workflow_cfg["trunk_event"]
        run, satisfied = select_complete_attempt(
            args.gh,
            repo,
            workflow_cfg,
            head_sha=expected_head,
            event=event,
            gates=gates,
        )
        evidence = {
            "schema_version": 4,
            "protocol_version": 6,
            "evidence_type": "actions-metadata",
            "metadata_authority": "github-actions-jobs-steps",
            "source": {"kind": "trunk", "branch": trunk},
            "repository": {"repo": repo, "head_sha": expected_head, "base_ref": trunk},
            "profile_digest": sha256_file(profile_path),
            "workflow": {"name": workflow_cfg["name"], "path": workflow_cfg["path"], "event": event},
            "selected_run": {"id": run["id"], "attempt": run["run_attempt"]},
            "required_gate_ids": gate_ids,
            "satisfied_gate_ids": satisfied,
            "changed_files": [],
            "risk": {
                "declared": None,
                "floor": profile["adaptive"]["risk_floor"],
                "effective": args.effective_risk,
                "runtime_input": None,
                "escalation_reasons": [],
            },
        }
        write_json(args.output, evidence)
    except (PolicyError, MetadataError, KeyError, TypeError) as exc:
        print(f"TRUNK EVIDENCE INVALID: {exc}", file=sys.stderr)
        return 2
    print(f"TRUNK EVIDENCE OK: {trunk}@{expected_head} run {run['id']}@{run['run_attempt']} risk {args.effective_risk}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

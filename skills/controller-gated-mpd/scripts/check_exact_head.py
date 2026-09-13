#!/usr/bin/env python3
"""Create fail-closed CG-MPD V6 Actions evidence for the live pull-request head."""
from __future__ import annotations

import argparse
import sys

from actions_metadata import (
    MetadataError,
    get_pull_request,
    get_pull_request_files,
    require_full_sha,
    select_complete_attempt,
    write_json,
)
from policy import PolicyError, gates_for_level, load_profile, resolve_effective_risk, risk_gate_ids, sha256_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--output", required=True)
    parser.add_argument("--runtime-risk", choices=("FAST", "STANDARD", "CRITICAL"))
    parser.add_argument("--gh", default="gh")
    args = parser.parse_args()
    try:
        profile_path, profile = load_profile(args.profile)
        repo = profile["repository"]["repo"]
        trunk = profile["repository"]["trunk"]
        pr = get_pull_request(args.gh, repo, args.pr)
        head_sha = require_full_sha(pr["head"]["sha"], field="live PR head")
        base_ref = pr["base"]["ref"]
        if base_ref != trunk:
            raise MetadataError(f"live PR base {base_ref!r} does not match configured trunk {trunk!r}")
        changed_files = get_pull_request_files(args.gh, repo, args.pr)
        risk = resolve_effective_risk(profile, args.lane, changed_files, runtime_risk=args.runtime_risk)
        effective = risk["effective"]
        gates = gates_for_level(profile, effective)
        gate_ids = risk_gate_ids(profile, effective)
        if not gate_ids:
            raise MetadataError("required gate set is empty; zero-gate authority is forbidden")
        workflow_cfg = profile["verification"]["workflow"]
        event = workflow_cfg["head_event"]
        run, satisfied = select_complete_attempt(
            args.gh,
            repo,
            workflow_cfg,
            head_sha=head_sha,
            event=event,
            gates=gates,
        )
        evidence = {
            "schema_version": 4,
            "protocol_version": 6,
            "evidence_type": "actions-metadata",
            "metadata_authority": "github-actions-jobs-steps",
            "source": {"kind": "pull_request", "pr": args.pr, "lane": args.lane},
            "repository": {"repo": repo, "head_sha": head_sha, "base_ref": base_ref},
            "profile_digest": sha256_file(profile_path),
            "workflow": {"name": workflow_cfg["name"], "path": workflow_cfg["path"], "event": event},
            "selected_run": {"id": run["id"], "attempt": run["run_attempt"]},
            "required_gate_ids": gate_ids,
            "satisfied_gate_ids": satisfied,
            "changed_files": changed_files,
            "risk": {
                "declared": risk["declared"],
                "floor": risk["floor"],
                "effective": effective,
                "runtime_input": args.runtime_risk,
                "escalation_reasons": risk["escalations"],
            },
        }
        write_json(args.output, evidence)
    except (PolicyError, MetadataError, KeyError, TypeError) as exc:
        print(f"EVIDENCE INVALID: {exc}", file=sys.stderr)
        return 2
    print(f"EVIDENCE OK: PR #{args.pr} {head_sha} run {run['id']}@{run['run_attempt']} risk {effective}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

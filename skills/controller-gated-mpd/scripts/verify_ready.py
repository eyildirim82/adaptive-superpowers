#!/usr/bin/env python3
"""Verify a controller-materialized CG-MPD V6 READY@SHA against current live authority."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from actions_metadata import MetadataError, read_json, require_v6_evidence
from approve_ready import validate_evidence_state
from policy import PolicyError, load_profile, sha256_file


def _mapping(value: object, *, field: str) -> dict:
    if not isinstance(value, dict):
        raise MetadataError(f"{field} must be an object")
    return value


def _require_v6_receipt(receipt: dict) -> None:
    if receipt.get("schema_version") != 4 or receipt.get("protocol_version") != 6:
        raise MetadataError("V6 READY requires schema_version=4 and protocol_version=6; legacy authority is non-upgradable")
    if receipt.get("receipt_type") != "READY@SHA":
        raise MetadataError("V6 READY receipt_type must be READY@SHA")
    if receipt.get("authority_role") != "controller":
        raise MetadataError("only controller authority may materialize V6 READY")
    required = receipt.get("required_gate_ids")
    if not isinstance(required, list) or not required:
        raise MetadataError("READY required gate set is empty; zero-gate authority is forbidden")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--runtime-risk", choices=("FAST", "STANDARD", "CRITICAL"))
    parser.add_argument("--gh", default="gh")
    args = parser.parse_args()
    try:
        profile_path, profile = load_profile(args.profile)
        receipt = read_json(args.receipt, context="READY receipt")
        _require_v6_receipt(receipt)
        evidence_path = Path(args.evidence).resolve()
        evidence = read_json(evidence_path, context="V6 Actions evidence")
        require_v6_evidence(evidence)

        current_profile_digest = sha256_file(profile_path)
        if receipt.get("profile_digest") != current_profile_digest:
            raise MetadataError("READY profile digest no longer matches the current V6 wave profile")
        current_evidence_digest = sha256_file(evidence_path)
        if receipt.get("evidence_digest") != current_evidence_digest:
            raise MetadataError("READY evidence digest no longer matches the exact evidence file")

        repo_doc = _mapping(receipt.get("repository"), field="READY repository")
        repo = profile["repository"]["repo"]
        if repo_doc.get("repo") != repo:
            raise MetadataError("READY repository no longer matches the current V6 profile")
        pr_number = repo_doc.get("pr")
        if not isinstance(pr_number, int) or isinstance(pr_number, bool) or pr_number <= 0:
            raise MetadataError("READY PR number is invalid")
        lane = receipt.get("lane")
        if not isinstance(lane, str) or not lane:
            raise MetadataError("READY lane is invalid")

        risk_doc = _mapping(receipt.get("risk"), field="READY risk")
        bound_runtime = risk_doc.get("runtime_input")
        if args.runtime_risk is not None and args.runtime_risk != bound_runtime:
            raise MetadataError("current runtime risk input differs from READY-bound runtime risk")
        current_runtime = bound_runtime if args.runtime_risk is None else args.runtime_risk

        state = validate_evidence_state(
            profile_path=profile_path,
            profile=profile,
            evidence=evidence,
            lane=lane,
            pr_number=pr_number,
            gh=args.gh,
            runtime_risk=current_runtime,
        )

        if repo_doc.get("head_sha") != state["head_sha"]:
            raise MetadataError("READY head is stale")
        if repo_doc.get("base_ref") != state["base_ref"]:
            raise MetadataError("READY base is stale")
        if risk_doc.get("effective") != state["risk"]["effective"]:
            raise MetadataError("READY effective Adaptive risk is stale")
        if risk_doc.get("escalation_reasons") != state["risk"]["escalations"]:
            raise MetadataError("READY risk escalation reasons are stale")
        if receipt.get("required_gate_ids") != state["required_gate_ids"]:
            raise MetadataError("READY gate set is stale")
        if receipt.get("selected_run") != state["selected_run"]:
            raise MetadataError("READY selected workflow run/attempt is stale")
    except (PolicyError, MetadataError, KeyError, TypeError) as exc:
        print(f"READY INVALID: {exc}", file=sys.stderr)
        return 2
    print(
        f"READY VERIFIED: PR #{state['pr']} {state['head_sha']} "
        f"run {state['selected_run']['id']}@{state['selected_run']['attempt']} risk {state['risk']['effective']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

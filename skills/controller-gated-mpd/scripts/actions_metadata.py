#!/usr/bin/env python3
"""GitHub Actions metadata authority for CG-MPD V6 evidence and READY checks."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable
from urllib.parse import quote, urlencode


class MetadataError(RuntimeError):
    """Raised when authoritative GitHub metadata is absent, ambiguous, or incomplete."""


_FULL_SHA = re.compile(r"^[0-9a-fA-F]{40}$")


def require_full_sha(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not _FULL_SHA.fullmatch(value):
        raise MetadataError(f"{field} must be a full 40-character hexadecimal SHA")
    return value.lower()


def _parse_include_output(text: str) -> tuple[dict[str, str], Any]:
    normalized = text.replace("\r\n", "\n")
    split_at = normalized.find("\n\n")
    if split_at < 0:
        raise MetadataError("GitHub metadata response did not include HTTP headers")
    header_text = normalized[:split_at]
    body_text = normalized[split_at + 2 :].strip()
    if not header_text.startswith("HTTP/"):
        raise MetadataError("GitHub metadata response did not include an HTTP status line")
    headers: dict[str, str] = {}
    for line in header_text.splitlines()[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    try:
        body = json.loads(body_text)
    except json.JSONDecodeError as exc:
        raise MetadataError(f"GitHub metadata response was not JSON: {exc}") from exc
    return headers, body


def gh_api(gh: str, endpoint: str) -> tuple[dict[str, str], Any]:
    try:
        proc = subprocess.run(
            [gh, "api", "-i", endpoint],
            text=True,
            capture_output=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MetadataError(f"GitHub metadata request failed: {exc}") from exc
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
        raise MetadataError(f"GitHub metadata request failed for {endpoint}: {detail}")
    return _parse_include_output(proc.stdout)


def _reject_pagination(headers: dict[str, str], *, context: str) -> None:
    link = headers.get("link", "")
    if 'rel="next"' in link or "rel=next" in link:
        raise MetadataError(f"{context} metadata requires pagination; failing closed")


def _require_dict(value: Any, *, context: str) -> dict:
    if not isinstance(value, dict):
        raise MetadataError(f"{context} metadata must be an object")
    return value


def _require_list(value: Any, *, context: str) -> list:
    if not isinstance(value, list):
        raise MetadataError(f"{context} metadata must be a list")
    return value


def get_pull_request(gh: str, repo: str, pr_number: int) -> dict:
    _, body = gh_api(gh, f"/repos/{repo}/pulls/{pr_number}")
    pr = _require_dict(body, context="pull request")
    head = _require_dict(pr.get("head"), context="pull request head")
    base = _require_dict(pr.get("base"), context="pull request base")
    require_full_sha(head.get("sha"), field="live PR head")
    if not isinstance(base.get("ref"), str) or not base["ref"].strip():
        raise MetadataError("live PR base ref is missing")
    return pr


def get_pull_request_files(gh: str, repo: str, pr_number: int) -> list[str]:
    endpoint = f"/repos/{repo}/pulls/{pr_number}/files?per_page=100&page=1"
    headers, body = gh_api(gh, endpoint)
    _reject_pagination(headers, context="pull request files")
    rows = _require_list(body, context="pull request files")
    files: list[str] = []
    for row in rows:
        item = _require_dict(row, context="pull request file")
        filename = item.get("filename")
        if not isinstance(filename, str) or not filename.strip():
            raise MetadataError("pull request file metadata is missing filename")
        files.append(filename)
    return files


def get_branch_head(gh: str, repo: str, branch: str) -> str:
    _, body = gh_api(gh, f"/repos/{repo}/branches/{quote(branch, safe='')}")
    data = _require_dict(body, context="branch")
    commit = _require_dict(data.get("commit"), context="branch commit")
    return require_full_sha(commit.get("sha"), field="live trunk head")


def list_workflow_runs(
    gh: str,
    repo: str,
    workflow: dict,
    *,
    head_sha: str,
    event: str,
) -> list[dict]:
    query = urlencode(
        {
            "head_sha": head_sha,
            "event": event,
            "status": "completed",
            "per_page": 100,
            "page": 1,
        }
    )
    endpoint = f"/repos/{repo}/actions/runs?{query}"
    headers, body = gh_api(gh, endpoint)
    _reject_pagination(headers, context="workflow runs")
    data = _require_dict(body, context="workflow runs")
    runs = _require_list(data.get("workflow_runs"), context="workflow runs")
    total = data.get("total_count")
    if not isinstance(total, int) or total != len(runs):
        raise MetadataError("workflow runs metadata is incomplete")
    return [_require_dict(run, context="workflow run") for run in runs]


def get_attempt_jobs(gh: str, repo: str, run_id: int, attempt: int) -> list[dict]:
    endpoint = f"/repos/{repo}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100&page=1"
    headers, body = gh_api(gh, endpoint)
    _reject_pagination(headers, context="workflow attempt jobs")
    data = _require_dict(body, context="workflow attempt jobs")
    jobs = _require_list(data.get("jobs"), context="workflow attempt jobs")
    total = data.get("total_count")
    if not isinstance(total, int) or total != len(jobs):
        raise MetadataError("workflow attempt jobs metadata is incomplete")
    return [_require_dict(job, context="workflow job") for job in jobs]


def get_run(gh: str, repo: str, run_id: int) -> dict:
    _, body = gh_api(gh, f"/repos/{repo}/actions/runs/{run_id}")
    return _require_dict(body, context="workflow run")


def _require_positive_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise MetadataError(f"{field} must be a positive integer")
    return value


def validate_run_identity(run: dict, workflow: dict, *, head_sha: str, event: str) -> tuple[int, int]:
    run_id = _require_positive_int(run.get("id"), field="workflow run id")
    attempt = _require_positive_int(run.get("run_attempt"), field="workflow run attempt")
    run_path = run.get("path")
    if not isinstance(run_path, str) or run_path.split("@", 1)[0] != workflow["path"]:
        raise MetadataError(
            f"workflow run {run_id} identity mismatch for path: expected canonical path {workflow['path']!r}"
        )
    expected = {
        "name": workflow["name"],
        "event": event,
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": "success",
    }
    for field, value in expected.items():
        if run.get(field) != value:
            raise MetadataError(f"workflow run {run_id} identity mismatch for {field}: expected {value!r}")
    return run_id, attempt


def _gate_is_satisfied(jobs: list[dict], gate: dict[str, str]) -> bool:
    matches = [job for job in jobs if job.get("name") == gate["job"]]
    if len(matches) != 1:
        return False
    job = matches[0]
    if job.get("status") != "completed" or job.get("conclusion") != "success":
        return False
    step_name = gate.get("step")
    if step_name is None:
        return True
    steps = job.get("steps")
    if not isinstance(steps, list):
        return False
    step_matches = [step for step in steps if isinstance(step, dict) and step.get("name") == step_name]
    if len(step_matches) != 1:
        return False
    step = step_matches[0]
    return step.get("status") == "completed" and step.get("conclusion") == "success"


def satisfied_gate_ids(jobs: list[dict], gates: Iterable[dict[str, str]]) -> list[str]:
    satisfied: list[str] = []
    for gate in gates:
        if _gate_is_satisfied(jobs, gate):
            satisfied.append(gate["id"])
    return satisfied


def select_complete_attempt(
    gh: str,
    repo: str,
    workflow: dict,
    *,
    head_sha: str,
    event: str,
    gates: list[dict[str, str]],
) -> tuple[dict, list[str]]:
    if not gates:
        raise MetadataError("required gate set is empty; zero-gate authority is forbidden")
    required = [gate["id"] for gate in gates]
    runs = list_workflow_runs(gh, repo, workflow, head_sha=head_sha, event=event)
    candidates: list[tuple[int, int, dict]] = []
    for run in runs:
        try:
            run_id, attempt = validate_run_identity(run, workflow, head_sha=head_sha, event=event)
        except MetadataError:
            continue
        candidates.append((run_id, attempt, run))
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    for run_id, attempt, run in candidates:
        jobs = get_attempt_jobs(gh, repo, run_id, attempt)
        satisfied = satisfied_gate_ids(jobs, gates)
        if satisfied == required:
            return run, satisfied
    raise MetadataError("no single workflow attempt satisfied the complete required gate set")


def validate_selected_attempt(
    gh: str,
    repo: str,
    workflow: dict,
    *,
    head_sha: str,
    event: str,
    run_id: int,
    attempt: int,
    gates: list[dict[str, str]],
) -> list[str]:
    if not gates:
        raise MetadataError("required gate set is empty; zero-gate authority is forbidden")
    current = get_run(gh, repo, run_id)
    current_id, current_attempt = validate_run_identity(current, workflow, head_sha=head_sha, event=event)
    if current_id != run_id or current_attempt != attempt:
        raise MetadataError(
            f"workflow run attempt changed: receipt/evidence binds {run_id}@{attempt}, current is {current_id}@{current_attempt}"
        )
    jobs = get_attempt_jobs(gh, repo, run_id, attempt)
    satisfied = satisfied_gate_ids(jobs, gates)
    required = [gate["id"] for gate in gates]
    if satisfied != required:
        raise MetadataError("selected workflow attempt no longer satisfies the complete required gate set")
    return satisfied


def read_json(path: str | Path, *, context: str) -> dict:
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MetadataError(f"{context} unreadable: {exc}") from exc
    return _require_dict(data, context=context)


def write_json(path: str | Path, data: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(p)


def require_v6_evidence(data: dict) -> None:
    if data.get("schema_version") != 4 or data.get("protocol_version") != 6:
        raise MetadataError(f"V6 evidence requires schema_version=4 and protocol_version=6; legacy authority is non-upgradable")
    if data.get("evidence_type") != "actions-metadata":
        raise MetadataError("V6 READY accepts only actions-metadata evidence")
    if data.get("metadata_authority") != "github-actions-jobs-steps":
        raise MetadataError("V6 evidence metadata authority is invalid")
    required = data.get("required_gate_ids")
    satisfied = data.get("satisfied_gate_ids")
    if not isinstance(required, list) or not required or not all(isinstance(x, str) and x for x in required):
        raise MetadataError(f"V6 evidence required gate set is empty or invalid")
    if satisfied != required:
        raise MetadataError("V6 evidence does not prove the complete required gate set")
    selected = data.get("selected_run")
    if not isinstance(selected, dict):
        raise MetadataError("V6 evidence selected_run is missing")
    _require_positive_int(selected.get("id"), field="eviddence run id")
    _require_positive_int(selected.get("attempt"), field="evidence run attempt")

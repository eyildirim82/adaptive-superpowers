from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/controller-gated-mpd/scripts"
A = "a" * 40
BASE = "b" * 40
MERGE = "c" * 40

FAKE_GH = r'''#!/usr/bin/env -S python3 -S
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlsplit

state_path = Path(os.environ["FAKE_GH_STATE"])
log_path = Path(os.environ["FAKE_GH_CALLS"])
args = sys.argv[1:]
pid = os.getpid()


def log(event, *, rc=None, state_snapshot=None, note=""):
    record = {
        "event": event,
        "pid": pid,
        "argv": args,
        "argv_text": " ".join(args),
        "state": state_snapshot,
    }
    if rc is not None:
        record["rc"] = rc
    if note:
        record["note"] = note
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


log("START", note=f"state_path={state_path}")
state = json.loads(state_path.read_text(encoding="utf-8"))
log("STATE", state_snapshot={"merged": state.get("merged"), "trunk": state.get("merge_sha") if state.get("merged") else state.get("trunk_before")})


def save():
    tmp = state_path.with_name(state_path.name + f".{pid}.tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    tmp.replace(state_path)


def trunk():
    return state["merge_sha"] if state.get("merged") else state["trunk_before"]


def emit(body, include):
    if include:
        print("HTTP/2 200")
        print()
    print(json.dumps(body, separators=(",", ":")))


def finish(code, note=""):
    try:
        try:
            final = json.loads(state_path.read_text(encoding="utf-8"))
            snapshot = {
                "merged": final.get("merged"),
                "trunk": final.get("merge_sha") if final.get("merged") else final.get("trunk_before"),
            }
        except Exception as exc:
            snapshot = {"state_read_error": repr(exc)}
        sys.stdout.flush()
        sys.stderr.flush()
        log("END", rc=code, state_snapshot=snapshot, note=note)
        sys.stdout.flush()
        sys.stderr.flush()
    finally:
        # This is a test executable, not production code. Bypass interpreter
        # finalization so each fake-gh invocation has a deterministic OS-level
        # exit after its output/state/logs are flushed.
        os._exit(code)


if not args:
    finish(9, "no argv")
if args[0] == "api":
    include = "-i" in args or "--include" in args
    endpoint = next((x for x in args[1:] if x.startswith("/") or x.startswith("repos/")), "")
    if endpoint == "repos/owner/repo/commits/main":
        print(trunk())
        finish(0, "trunk read")
    path = endpoint.lstrip("/")
    if re.fullmatch(r"repos/owner/repo/pulls/7", path):
        emit(state["pr"], include)
    elif path.startswith("repos/owner/repo/pulls/7/files?"):
        emit(state["files"], include)
    elif path.startswith("repos/owner/repo/actions/runs?"):
        query = parse_qs(urlsplit(endpoint).query)
        rows = [r for r in state["workflow_runs"]
                if r.get("head_sha") == query.get("head_sha", [None])[0]
                and r.get("event") == query.get("event", [None])[0]]
        status = query.get("status", [None])[0]
        if status:
            rows = [r for r in rows if r.get("status") == status]
        emit({"total_count": len(rows), "workflow_runs": rows}, include)
    elif re.fullmatch(r"repos/owner/repo/actions/runs/[0-9]+", path):
        run_id = path.rsplit("/", 1)[-1]
        emit(state["run_details"][run_id], include)
    elif re.fullmatch(r"repos/owner/repo/actions/runs/[0-9]+/attempts/[0-9]+/jobs\?per_page=100&page=1", path):
        match = re.search(r"runs/([0-9]+)/attempts/([0-9]+)/jobs", path)
        emit(state["jobs"][f"{match.group(1)}:{match.group(2)}"], include)
    elif re.fullmatch(r"repos/owner/repo/branches/main", path):
        emit({"commit": {"sha": trunk()}}, include)
    else:
        print(f"unsupported api endpoint: {endpoint}", file=sys.stderr)
        finish(9, f"unsupported api endpoint: {endpoint}")
    finish(0, f"api {path}")
if args[:2] == ["pr", "view"]:
    joined = " ".join(args)
    if "headRefOid" in joined:
        print("\t".join([state["pr"]["head"]["sha"], state["pr"]["base"]["ref"], "MERGEABLE", "CLEAN", "false"]))
        finish(0, "live PR metadata")
    print("\t".join(["MERGED" if state.get("merged") else "OPEN", state["merge_sha"] if state.get("merged") else ""]))
    finish(0, "PR merged confirmation")
if args[:2] == ["pr", "merge"]:
    before = state.get("merged")
    state["merged"] = True
    save()
    finish(0, f"merge state {before!r}->True")
if args[:2] == ["pr", "ready"]:
    finish(0, "mark ready")
print("unsupported gh invocation", file=sys.stderr)
finish(9, "unsupported gh invocation")
'''


def gate_job(name: str, step: str | None = None) -> dict:
    return {
        "name": name,
        "status": "completed",
        "conclusion": "success",
        "steps": [] if step is None else [{"name": step, "status": "completed", "conclusion": "success"}],
    }


def run_record(run_id: int, head: str, event: str) -> dict:
    return {
        "id": run_id,
        "run_attempt": 1,
        "name": "Full CI",
        "path": ".github/workflows/ci.yml",
        "event": event,
        "head_sha": head,
        "status": "completed",
        "conclusion": "success",
    }


def base_state() -> dict:
    pr_run = run_record(101, A, "pull_request")
    trunk_run = run_record(202, MERGE, "push")
    jobs = [gate_job("test", "unit"), gate_job("typecheck"), gate_job("build"), gate_job("security")]
    return {
        "merged": False,
        "trunk_before": BASE,
        "merge_sha": MERGE,
        "pr": {"head": {"sha": A}, "base": {"ref": "main"}},
        "files": [{"filename": "src/auth/session.py"}],
        "workflow_runs": [pr_run, trunk_run],
        "run_details": {"101": copy.deepcopy(pr_run), "202": copy.deepcopy(trunk_run)},
        "jobs": {
            "101:1": {"total_count": len(jobs), "jobs": copy.deepcopy(jobs)},
            "202:1": {"total_count": len(jobs), "jobs": copy.deepcopy(jobs)},
        },
    }


class IntegrationContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ledger = self.root / ".superpowers/mpd/integration"
        self.evidence_dir = self.ledger / "evidence"
        self.approvals_dir = self.ledger / "approvals"
        self.evidence_dir.mkdir(parents=True)
        self.approvals_dir.mkdir(parents=True)
        self.profile_path = self.ledger / "wave.json"
        self.state_path = self.root / "state.json"
        self.calls_path = self.root / "gh.log"
        self.gh = self.root / "gh"
        self.gh.write_text(FAKE_GH, encoding="utf-8")
        self.gh.chmod(0o755)
        self.calls_path.write_text("", encoding="utf-8")
        self.state_path.write_text(json.dumps(base_state()), encoding="utf-8")
        self.profile_path.write_text(json.dumps(self.profile(), sort_keys=True) + "\n", encoding="utf-8")

    def profile(self) -> dict:
        return {
            "schema_version": 4,
            "protocol_version": 6,
            "wave": "integration",
            "repository": {"repo": "owner/repo", "trunk": "main", "frozen_base_sha": BASE},
            "adaptive": {
                "risk_floor": "STANDARD",
                "transport": "prompt-handoff",
                "authorization": {
                    "push": "granted",
                    "merge": "granted",
                    "deploy": "denied",
                    "production_write": "denied",
                    "destructive_action": "denied",
                },
            },
            "verification": {
                "workflow": {
                    "name": "Full CI",
                    "path": ".github/workflows/ci.yml",
                    "head_event": "pull_request",
                    "trunk_event": "push",
                },
                "gate_catalog": [
                    {"id": "tests", "job": "test", "step": "unit"},
                    {"id": "typecheck", "job": "typecheck"},
                    {"id": "build", "job": "build"},
                    {"id": "security", "job": "security"},
                ],
            },
            "risk_policy": {
                "default_level": "STANDARD",
                "levels": {
                    "FAST": {"gates": ["tests"]},
                    "STANDARD": {"gates": ["tests", "typecheck", "build"]},
                    "CRITICAL": {"gates": ["tests", "typecheck", "build", "security"]},
                },
                "path_floors": [{"level": "CRITICAL", "paths": ["src/auth/**"]}],
            },
            "hot_zones": [],
            "lanes": [{
                "id": "lane-c",
                "branch": "agent/lane-c",
                "risk": "STANDARD",
                "prerequisites": [],
                "owned": ["src/**"],
                "forbidden": [],
                "downstream": [],
            }],
            "merge": {
                "method": "squash",
                "approvals_dir": str(self.approvals_dir),
                "trunk_green_after_each": True,
            },
        }

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PATH"] = f"{self.root}:{env['PATH']}"
        env["FAKE_GH_STATE"] = str(self.state_path)
        env["FAKE_GH_CALLS"] = str(self.calls_path)
        env["CGMPD_POLL_INTERVAL_SECONDS"] = "0"
        return env

    def run_python(self, script: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPTS / script), *args],
            cwd=ROOT,
            env=self.env(),
            text=True,
            capture_output=True,
            timeout=20,
        )

    def materialize_ready(self) -> tuple[Path, Path]:
        evidence = self.evidence_dir / "candidate-with-arbitrary-name.json"
        result = self.run_python(
            "check_exact_head.py",
            "--profile", str(self.profile_path),
            "--lane", "lane-c",
            "--pr", "7",
            "--output", str(evidence),
            "--gh", str(self.gh),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = self.approvals_dir / "pr-7.ready.json"
        result = self.run_python(
            "approve_ready.py",
            "--profile", str(self.profile_path),
            "--lane", "lane-c",
            "--pr", "7",
            "--evidence", str(evidence),
            "--output", str(receipt),
            "--controller-id", "integration-test",
            "--gh", str(self.gh),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_python(
            "verify_ready.py",
            "--profile", str(self.profile_path),
            "--receipt", str(receipt),
            "--evidence", str(evidence),
            "--gh", str(self.gh),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return evidence, receipt

    def test_real_lane_b_authority_flows_through_merge_train_and_trunk_proof(self):
        evidence, receipt = self.materialize_ready()
        ready_doc = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(ready_doc["receipt_type"], "READY@SHA")
        self.assertEqual(ready_doc["repository"]["head_sha"], A)
        self.assertTrue(ready_doc["evidence_digest"])
        self.assertNotEqual(evidence.name, "pr-7.json")

        result = subprocess.run(
            [
                "bash", str(SCRIPTS / "merge_train.sh"),
                "--profile", str(self.profile_path),
                "--repo", "owner/repo",
                "--approvals-dir", str(self.approvals_dir),
                "--timeout", "0",
                "--apply",
                "7",
            ],
            cwd=ROOT,
            env=self.env(),
            text=True,
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.calls_path.read_text(encoding="utf-8")
        self.assertIn(f"pr merge 7 --repo owner/repo --squash --match-head-commit {A}", calls)
        trunk_proof = self.evidence_dir / f"trunk-{MERGE}.actions.json"
        self.assertTrue(trunk_proof.is_file(), result.stdout + result.stderr)
        proof = json.loads(trunk_proof.read_text(encoding="utf-8"))
        self.assertEqual(proof["source"], {"kind": "trunk", "branch": "main"})
        self.assertEqual(proof["repository"]["head_sha"], MERGE)
        self.assertEqual(proof["risk"]["effective"], "CRITICAL")

    def test_digest_resolution_fails_closed_on_duplicate_candidates(self):
        evidence, _ = self.materialize_ready()
        shutil.copy2(evidence, self.evidence_dir / "duplicate.json")
        result = subprocess.run(
            [
                "bash", str(SCRIPTS / "merge_train.sh"),
                "--profile", str(self.profile_path),
                "--approvals-dir", str(self.approvals_dir),
                "7",
            ],
            cwd=ROOT,
            env=self.env(),
            text=True,
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("ambiguous", result.stderr.lower())
        self.assertNotIn("pr merge", self.calls_path.read_text(encoding="utf-8"))

    def test_trunk_checker_distinguishes_pending_from_invalid_authority(self):
        state = base_state()
        state["merged"] = True
        state["workflow_runs"] = [state["workflow_runs"][0]]
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        output = self.evidence_dir / "pending.json"
        pending = self.run_python(
            "check_trunk_evidence.py",
            "--profile", str(self.profile_path),
            "--head", MERGE,
            "--effective-risk", "CRITICAL",
            "--output", str(output),
            "--gh", str(self.gh),
        )
        self.assertEqual(pending.returncode, 4, pending.stdout + pending.stderr)

        state = base_state()
        state["merged"] = True
        bad = run_record(303, MERGE, "push")
        bad["path"] = ".github/workflows/not-authority.yml"
        state["workflow_runs"] = [bad]
        state["run_details"] = {"303": copy.deepcopy(bad)}
        state["jobs"] = {"303:1": state["jobs"]["202:1"]}
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        invalid = self.run_python(
            "check_trunk_evidence.py",
            "--profile", str(self.profile_path),
            "--head", MERGE,
            "--effective-risk", "CRITICAL",
            "--output", str(output),
            "--gh", str(self.gh),
        )
        self.assertEqual(invalid.returncode, 2, invalid.stdout + invalid.stderr)


if __name__ == "__main__":
    unittest.main()

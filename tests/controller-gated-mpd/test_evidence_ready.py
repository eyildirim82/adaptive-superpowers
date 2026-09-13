from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/controller-gated-mpd/scripts"
A, B = "a" * 40, "b" * 40


def profile() -> dict:
    return {
        "schema_version": 4, "protocol_version": 6, "wave": "evidence-ready",
        "repository": {"repo": "owner/repo", "trunk": "main", "frozen_base_sha": "f" * 40},
        "adaptive": {"risk_floor": "STANDARD", "transport": "prompt-handoff", "authorization": {
            "push": "granted", "merge": "denied", "deploy": "denied", "production_write": "denied", "destructive_action": "denied"}},
        "verification": {"workflow": {"name": "Full CI", "path": ".github/workflows/ci.yml", "head_event": "pull_request", "trunk_event": "push"},
            "gate_catalog": [{"id": "tests", "job": "test", "step": "unit"}, {"id": "typecheck", "job": "typecheck"},
                             {"id": "build", "job": "build"}, {"id": "security", "job": "security"}]},
        "risk_policy": {"default_level": "STANDARD", "levels": {
            "FAST": {"gates": ["tests"]}, "STANDARD": {"gates": ["tests", "typecheck", "build"]},
            "CRITICAL": {"gates": ["tests", "typecheck", "build", "security"]}},
            "path_floors": [{"level": "CRITICAL", "paths": ["src/auth/**", ".github/workflows/**"]},
                            {"level": "STANDARD", "paths": ["src/**"]}, {"level": "FAST", "paths": ["docs/**"]}]},
        "hot_zones": [],
        "lanes": [{"id": "lane-b", "branch": "agent/lane-b", "risk": "FAST", "prerequisites": [],
                   "owned": ["src/**", "docs/**"], "forbidden": [], "downstream": []}],
        "merge": {"method": "squash", "approvals_dir": ".superpowers/mpd/evidence-ready/approvals", "trunk_green_after_each": True},
    }


def job(name: str, step: str | None = None) -> dict:
    return {"name": name, "status": "completed", "conclusion": "success",
            "steps": [] if not step else [{"name": step, "status": "completed", "conclusion": "success"}]}


def state(head: str = A, files: list[str] | None = None, attempt: int = 2) -> dict:
    run = {"id": 101, "run_attempt": attempt, "name": "Full CI", "path": ".github/workflows/ci.yml",
           "event": "pull_request", "head_sha": head, "status": "completed", "conclusion": "success"}
    jobs = [job("test", "unit"), job("typecheck"), job("build"), job("security")]
    return {"pr": {"head": {"sha": head}, "base": {"ref": "main"}},
            "files": [{"filename": f} for f in (files or ["src/auth/session.py"])],
            "runs": {"total_count": 1, "workflow_runs": [run]},
            "jobs": {f"101:{attempt}": {"total_count": len(jobs), "jobs": jobs}},
            "run_details": {"101": copy.deepcopy(run)}, "branch": {"commit": {"sha": head}}, "headers": {}}


FAKE_GH = r'''#!/usr/bin/env bash
set -euo pipefail
s="${FAKE_GH_STATE:?}"; shift; ep=""; sec=""; key=""
for a in "$@"; do [[ "$a" != "-i" && "$a" != --include && "$a" != -* ]] && ep="$a"; done
p="${ep#/}"
if [[ "$p" =~ /pulls/[0-9]+/files\? ]]; then body=$(jq -c .files "$s"); sec=files
elif [[ "$p" =~ /pulls/[0-9]+$ ]]; then body=$(jq -c .pr "$s")
elif [[ "$p" == *"/actions/runs?"* ]]; then body=$(jq -c .runs "$s"); sec=runs
elif [[ "$p" =~ /actions/runs/([0-9]+)/attempts/([0-9]+)/jobs\? ]]; then key="${BASH_REMATCH[1]}:${BASH_REMATCH[2]}"; body=$(jq -c --arg k "$key" '.jobs[$k]' "$s"); sec=jobs
elif [[ "$p" =~ /actions/runs/([0-9]+)$ ]]; then key="${BASH_REMATCH[1]}"; body=$(jq -c --arg k "$key" '.run_details[$k]' "$s")
elif [[ "$p" == *"/branches/"* ]]; then body=$(jq -c .branch "$s")
else echo "unhandled $ep" >&2; exit 3; fi
echo 'HTTP/2 200'
if [[ "$sec" == jobs ]]; then jq -r --arg k "$key" '(.headers.jobs[$k] // {}) | to_entries[] | "\(.key): \(.value)"' "$s"
elif [[ -n "$sec" ]]; then jq -r --arg x "$sec" '(.headers[$x] // {}) | to_entries[] | "\(.key): \(.value)"' "$s"; fi
echo; printf '%s\n' "$body"
'''


class H(unittest.TestCase):
    def setup(self, td: str, st: dict, pf: dict | None = None):
        root = Path(td); p = root / "wave.json"; s = root / "state.json"; gh = root / "gh"
        p.write_text(json.dumps(pf or profile(), sort_keys=True)); s.write_text(json.dumps(st)); gh.write_text(FAKE_GH); gh.chmod(0o755)
        return p, s, gh

    def run_script(self, script: str, args: list[str], st: Path):
        env = os.environ.copy(); env["FAKE_GH_STATE"] = str(st)
        return subprocess.run(["python3", str(SCRIPTS / script), *args], cwd=ROOT, env=env, text=True, capture_output=True, timeout=20)

    def evidence(self, td: str, st: dict, pf: dict | None = None):
        p, s, gh = self.setup(td, st, pf); e = Path(td) / "evidence.json"
        r = self.run_script("check_exact_head.py", ["--profile", str(p), "--lane", "lane-b", "--pr", "7", "--output", str(e), "--gh", str(gh)], s)
        self.assertEqual(r.returncode, 0, r.stderr); return p, s, gh, e

    def approve(self, td, p, s, gh, e):
        out = Path(td) / "ready.json"
        r = self.run_script("approve_ready.py", ["--profile", str(p), "--lane", "lane-b", "--pr", "7", "--evidence", str(e), "--output", str(out), "--controller-id", "controller-test", "--gh", str(gh)], s)
        return r, out

    def verify(self, p, s, gh, e, receipt):
        return self.run_script("verify_ready.py", ["--profile", str(p), "--receipt", str(receipt), "--evidence", str(e), "--gh", str(gh)], s)


class Task5(H):
    def test_exact_head_binds_v6_identity_attempt_and_risk(self):
        with tempfile.TemporaryDirectory() as td:
            p, _, _, e = self.evidence(td, state()); d = json.loads(e.read_text())
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual((d["schema_version"], d["protocol_version"]), (4, 6)); self.assertEqual(d["selected_run"], {"id": 101, "attempt": 2})
        self.assertEqual(d["workflow"], {"name": "Full CI", "path": ".github/workflows/ci.yml", "event": "pull_request"})
        self.assertEqual(d["risk"]["effective"], "CRITICAL"); self.assertTrue(d["risk"]["escalation_reasons"]); self.assertEqual(d["profile_digest"], digest)

    def test_no_cross_run_aggregation(self):
        st = state(files=["docs/x.md"], attempt=1); r1 = st["runs"]["workflow_runs"][0]; r1["id"] = 201; r2 = copy.deepcopy(r1); r2["id"] = 202
        st["runs"] = {"total_count": 2, "workflow_runs": [r1, r2]}; st["jobs"] = {"201:1": {"total_count": 2, "jobs": [job("test", "unit"), job("typecheck")]}, "202:1": {"total_count": 1, "jobs": [job("build")]}}
        with tempfile.TemporaryDirectory() as td:
            p, s, gh = self.setup(td, st); e = Path(td) / "e.json"; out = self.run_script("check_exact_head.py", ["--profile", str(p), "--lane", "lane-b", "--pr", "7", "--output", str(e), "--gh", str(gh)], s)
        self.assertNotEqual(out.returncode, 0); self.assertIn("single workflow attempt", out.stderr)

    def test_logs_do_not_substitute_for_missing_step_and_pagination_fails_closed(self):
        for mode in ("step", "page"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as td:
                st = state()
                if mode == "step": st["jobs"]["101:2"]["jobs"][0] = {"name": "test", "status": "completed", "conclusion": "success", "steps": [], "logs": "unit success"}
                else: st["headers"] = {"runs": {"Link": '<next>; rel="next"'}}
                p, s, gh = self.setup(td, st); e = Path(td) / "e.json"; out = self.run_script("check_exact_head.py", ["--profile", str(p), "--lane", "lane-b", "--pr", "7", "--output", str(e), "--gh", str(gh)], s)
                self.assertNotEqual(out.returncode, 0)

    def test_path_ref_suffix_is_canonical_and_trunk_floor_is_enforced(self):
        st = state(); st["runs"]["workflow_runs"][0]["path"] += "@main"; st["run_details"]["101"]["path"] += "@main"
        with tempfile.TemporaryDirectory() as td:
            _, _, _, e = self.evidence(td, st); self.assertEqual(json.loads(e.read_text())["workflow"]["path"], ".github/workflows/ci.yml")
        st = state(files=["docs/x.md"]); st["runs"]["workflow_runs"][0]["event"] = "push"; st["run_details"]["101"]["event"] = "push"
        with tempfile.TemporaryDirectory() as td:
            p, s, gh = self.setup(td, st); e = Path(td) / "t.json"
            good = self.run_script("check_trunk_evidence.py", ["--profile", str(p), "--head", A, "--effective-risk", "STANDARD", "--output", str(e), "--gh", str(gh)], s)
            self.assertEqual(good.returncode, 0, good.stderr)
            proof = json.loads(e.read_text())
            self.assertEqual(proof["source"], {"kind": "trunk", "branch": "main"})
            self.assertEqual(proof["workflow"]["event"], "push")
            out = self.run_script("check_trunk_evidence.py", ["--profile", str(p), "--head", A, "--effective-risk", "FAST", "--output", str(e), "--gh", str(gh)], s)
        self.assertNotEqual(out.returncode, 0); self.assertIn("wave floor", out.stderr)


class Task6(H):
    def test_ready_controller_authority_verifies(self):
        with tempfile.TemporaryDirectory() as td:
            p, s, gh, e = self.evidence(td, state()); a, receipt = self.approve(td, p, s, gh, e); self.assertEqual(a.returncode, 0, a.stderr)
            v = self.verify(p, s, gh, e, receipt); self.assertEqual(v.returncode, 0, v.stderr); d = json.loads(receipt.read_text())
            legacy = copy.deepcopy(d); legacy.update(schema_version=3, protocol_version=5); receipt.write_text(json.dumps(legacy))
            legacy_verify = self.verify(p, s, gh, e, receipt)
            self.assertNotEqual(legacy_verify.returncode, 0); self.assertIn("V6", legacy_verify.stderr)
        self.assertEqual((d["schema_version"], d["protocol_version"]), (4, 6)); self.assertEqual(d["authority_role"], "controller"); self.assertEqual(d["receipt_type"], "READY@SHA")

    def test_live_head_wins_and_stale_state_invalidates(self):
        with tempfile.TemporaryDirectory() as td:
            p, s, gh, e = self.evidence(td, state()); moved = state(head=B); s.write_text(json.dumps(moved)); a, _ = self.approve(td, p, s, gh, e)
        self.assertNotEqual(a.returncode, 0); self.assertIn("live PR head", a.stderr)
        for mode in ("base", "profile", "evidence", "attempt", "risk"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as td:
                p, s, gh, e = self.evidence(td, state()); a, receipt = self.approve(td, p, s, gh, e); self.assertEqual(a.returncode, 0, a.stderr); st = json.loads(s.read_text())
                if mode == "base": st["pr"]["base"]["ref"] = "release"
                elif mode == "profile": x = json.loads(p.read_text()); x["adaptive"]["authorization"]["deploy"] = "unknown"; p.write_text(json.dumps(x))
                elif mode == "evidence": x = json.loads(e.read_text()); x["tampered"] = True; e.write_text(json.dumps(x))
                elif mode == "attempt": st["run_details"]["101"]["run_attempt"] = 3
                else: st["files"] = [{"filename": "docs/x.md"}]
                s.write_text(json.dumps(st)); self.assertNotEqual(self.verify(p, s, gh, e, receipt).returncode, 0)

    def test_v5_and_zero_gate_are_non_authority(self):
        with tempfile.TemporaryDirectory() as td:
            p, s, gh, e = self.evidence(td, state()); x = json.loads(e.read_text()); x.update(schema_version=3, protocol_version=5); e.write_text(json.dumps(x)); a, _ = self.approve(td, p, s, gh, e); self.assertNotEqual(a.returncode, 0); self.assertIn("V6", a.stderr)
        with tempfile.TemporaryDirectory() as td:
            p, s, gh, e = self.evidence(td, state()); x = json.loads(e.read_text()); x["required_gate_ids"] = []; x["satisfied_gate_ids"] = []; e.write_text(json.dumps(x)); a, _ = self.approve(td, p, s, gh, e); self.assertNotEqual(a.returncode, 0)


class Contract(unittest.TestCase):
    def test_worker_result_is_not_evidence_input_and_ready_scripts_exist(self):
        self.assertTrue((SCRIPTS / "approve_ready.py").exists() and (SCRIPTS / "verify_ready.py").exists())
        self.assertNotIn("worker_result", (SCRIPTS / "check_exact_head.py").read_text())


if __name__ == "__main__":
    unittest.main()

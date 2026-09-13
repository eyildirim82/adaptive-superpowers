from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "controller-gated-mpd" / "scripts"
ADAPTER = ROOT / "skills" / "using-superpowers" / "references" / "controller-gated-mpd-adapter.md"


def wave_profile() -> dict:
    return {
        "schema_version": 4,
        "protocol_version": 6,
        "wave": "routing-ledger-test",
        "repository": {
            "repo": "owner/repo",
            "trunk": "main",
            "frozen_base_sha": "a" * 40,
        },
        "adaptive": {
            "risk_floor": "CRITICAL",
            "authorization": {"merge": "denied"},
            "transport": "prompt-handoff",
        },
        "lanes": [
            {"id": "lane-a", "branch": "agent/a", "risk": "FAST", "prerequisites": [], "owned": ["docs/a.md"]},
            {"id": "lane-b", "branch": "agent/b", "risk": "CRITICAL", "prerequisites": [], "owned": ["src/b.py"]},
            {"id": "lane-c", "branch": "agent/c", "risk": "CRITICAL", "prerequisites": ["lane-a", "lane-b"], "owned": ["src/c.py"]},
        ],
    }


def integration_state() -> dict:
    return {
        "protocol_version": 6,
        "wave": "routing-ledger-test",
        "lanes": {
            "lane-a": {
                "worker_report": {"reported_head_sha": "1" * 40, "status": "complete"},
                "verified_pr": {
                    "number": 101,
                    "head_sha": "2" * 40,
                    "dependency_state": "satisfied",
                    "source": "git-pr-actions",
                },
            },
            "lane-b": {
                "worker_report": {"reported_head_sha": "3" * 40, "status": "complete"}
            },
            "lane-c": {},
        },
    }


class RoutingLedgerTests(unittest.TestCase):
    @contextmanager
    def make_ledger(self, integration: dict | None = None):
        with tempfile.TemporaryDirectory() as td:
            wave_dir = Path(td) / ".superpowers" / "mpd" / "routing-ledger-test"
            wave_dir.mkdir(parents=True)
            for name in ("handoffs", "evidence", "approvals"):
                (wave_dir / name).mkdir()
            (wave_dir / "wave.json").write_text(json.dumps(wave_profile()), encoding="utf-8")
            (wave_dir / "integration.json").write_text(json.dumps(integration or integration_state()), encoding="utf-8")
            yield wave_dir

    def run_state(self, *args: str, expected: int | None = None) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["python3", str(SCRIPTS / "wave_state.py"), *args],
            text=True,
            capture_output=True,
            timeout=20,
        )
        if expected is not None:
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_adapter_keeps_adaptive_as_single_authority_and_routes_transports_truthfully(self) -> None:
        text = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("single top-level authority", text)
        self.assertIn("one branch + two small independent edits", text)
        self.assertIn("three PRs from one frozen base", text)
        self.assertIn("prompt-handoff", text)
        self.assertIn("native-dispatch", text)
        self.assertIn("Worker prompts were generated for separate ChatGPT windows.", text)

    def test_stale_worker_report_cannot_release_downstream(self) -> None:
        with self.make_ledger() as wave_dir:
            wave_dir = str(wave_dir)
            result = self.run_state("check-deps", wave_dir, "lane-c", expected=3)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["dispatchable"])
            self.assertEqual([b["lane"] for b in payload["blockers"]], ["lane-b"])
            self.assertEqual(payload["prerequisite_facts"]["lane-b"]["worker_reported_head_sha"], "3" * 40)
            self.assertIsNone(payload["prerequisite_facts"]["lane-b"]["verified_pr_head_sha"])

    def test_worker_cannot_spoof_verified_dependency_with_untrusted_source(self) -> None:
        state = integration_state()
        state["lanes"]["lane-b"]["verified_pr"] = {
            "number": 102,
            "head_sha": "4" * 40,
            "dependency_state": "satisfied",
            "source": "worker-report",
        }
        with self.make_ledger(state) as wave_dir:
            result = self.run_state("check-deps", str(wave_dir), "lane-c", expected=3)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["dispatchable"])
            self.assertIn("independent reconciliation source", payload["blockers"][0]["reason"])

    def test_verified_pr_head_supersedes_worker_reported_head(self) -> None:
        with self.make_ledger() as wave_dir:
            wave_dir = str(wave_dir)
            result = self.run_state("status", wave_dir, "lane-a", expected=0)
            heads = json.loads(result.stdout)["heads"]
            self.assertEqual(heads["worker_reported_head_sha"], "1" * 40)
            self.assertEqual(heads["verified_pr_head_sha"], "2" * 40)
            self.assertEqual(heads["authoritative_head_sha"], "2" * 40)
            self.assertFalse(heads["heads_match"])

    def test_downstream_releases_only_after_all_verified_prerequisites_are_satisfied(self) -> None:
        state = integration_state()
        state["lanes"]["lane-b"]["verified_pr"] = {
            "number": 102,
            "head_sha": "4" * 40,
            "dependency_state": "satisfied",
            "source": "git-pr-actions",
        }
        with self.make_ledger(state) as wave_dir:
            wave_dir = str(wave_dir)
            result = subprocess.run(
                [str(SCRIPTS / "check_deps.sh"), wave_dir, "lane-c"],
                text=True,
                capture_output=True,
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["dispatchable"])

    def test_recovery_requires_no_conversation_memory_and_names_external_sources(self) -> None:
        with self.make_ledger() as wave_dir:
            wave_dir = str(wave_dir)
            result = self.run_state("recover", wave_dir, expected=0)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["conversation_memory_required"])
            self.assertEqual(payload["recovery_sources"], ["git", "pull-requests", "actions", "mpd-ledger"])
            self.assertFalse(payload["lanes"]["lane-c"]["dispatchable"])

    def test_missing_canonical_ledger_directory_fails_closed(self) -> None:
        with self.make_ledger() as wave_dir:
            (wave_dir / "evidence").rmdir()
            result = self.run_state("validate-layout", str(wave_dir), expected=2)
            self.assertIn("missing canonical ledger directory", result.stderr)

    def test_protocol_5_ledger_fails_closed(self) -> None:
        state = integration_state()
        state["protocol_version"] = 5
        with self.make_ledger(state) as wave_dir:
            result = self.run_state("validate-layout", str(wave_dir), expected=2)
            self.assertIn("protocol_version=6", result.stderr)

    def test_dependency_commands_do_not_create_competing_sdd_ledger(self) -> None:
        with self.make_ledger() as wave_dir:
            repo_root = wave_dir.parents[2]
            self.run_state("status", str(wave_dir), "lane-a", expected=0)
            self.assertFalse((repo_root / ".superpowers" / "sdd").exists())


if __name__ == "__main__":
    unittest.main()

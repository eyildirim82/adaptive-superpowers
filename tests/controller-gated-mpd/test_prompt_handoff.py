import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "skills/controller-gated-mpd/scripts/render_handoff_prompts.py"


def profile_fixture() -> dict:
    return {
        "schema_version": 4,
        "protocol_version": 6,
        "wave": "phase-3",
        "canonical": {
            "spec": "docs/superpowers/specs/canonical-design.md",
            "plan": "docs/superpowers/plans/canonical-plan.md",
        },
        "repository": {
            "repo": "owner/example",
            "trunk": "main",
            "frozen_base_sha": "a" * 40,
        },
        "adaptive": {
            "risk_floor": "STANDARD",
            "authorization": {
                "push": "granted",
                "merge": "denied",
                "deploy": "denied",
                "production_write": "denied",
                "destructive_action": "denied",
            },
            "transport": "prompt-handoff",
        },
        "verification": {
            "workflow": {
                "name": "Full CI",
                "path": ".github/workflows/ci.yml",
                "head_event": "push",
                "trunk_event": "push",
            },
            "gate_catalog": [
                {"id": "tests", "job": "test"},
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
            "path_floors": [],
        },
        "shared_read_only": ["README.md", "docs/shared/**"],
        "hot_zones": ["src/shared/**"],
        "lanes": [
            {
                "id": "lane-a",
                "task": "Implement Task A only.",
                "branch": "agent/lane-a",
                "risk": "STANDARD",
                "prerequisites": [],
                "owned": ["src/a/**"],
                "forbidden": ["src/b/**"],
                "downstream": ["lane-c"],
                "reserved_resources": ["migration-001"],
                "required_verification": ["python3 -m unittest tests.test_a"],
            },
            {
                "id": "lane-b",
                "task": "Implement Task B only.",
                "branch": "agent/lane-b",
                "risk": "STANDARD",
                "prerequisites": [],
                "owned": ["src/b/**"],
                "forbidden": ["src/a/**"],
                "downstream": ["lane-c"],
            },
            {
                "id": "lane-c",
                "task": "Integrate A and B only after prerequisites are satisfied.",
                "branch": "agent/lane-c",
                "risk": "CRITICAL",
                "prerequisites": ["lane-a", "lane-b"],
                "owned": ["src/integration/**"],
                "forbidden": [],
                "downstream": [],
                "reserved": ["integration-slot-1"],
            },
        ],
        "merge": {
            "method": "squash",
            "approvals_dir": ".superpowers/mpd/phase-3/approvals",
            "trunk_green_after_each": True,
        },
    }


def dependency_fixture(*, a=False, b=False) -> dict:
    return {
        "lanes": {
            "lane-a": {"satisfied": a, "status": "merged" if a else "pending"},
            "lane-b": {"satisfied": b, "status": "merged" if b else "pending"},
            "lane-c": {"satisfied": False, "status": "blocked"},
        }
    }


class PromptHandoffContractTests(unittest.TestCase):
    def run_renderer(self, profile: dict, dependency_state: dict, output: Path, *extra: str) -> subprocess.CompletedProcess:
        profile_path = output.parent / f"{output.name}-wave.json"
        dependency_path = output.parent / f"{output.name}-dependencies.json"
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        dependency_path.write_text(json.dumps(dependency_state), encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                str(RENDERER),
                str(profile_path),
                "--dependency-state",
                str(dependency_path),
                "--output-dir",
                str(output),
                *extra,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_default_renders_only_dispatchable_zero_context_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "handoffs"
            result = self.run_renderer(profile_fixture(), dependency_fixture(), output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                sorted(path.name for path in output.glob("*.md")),
                ["coordinator.md", "lane-a.md", "lane-b.md"],
            )
            worker = (output / "lane-a.md").read_text(encoding="utf-8")
            for required in (
                "Adaptive Superpowers + Controller-Gated MPD kullan",
                "Repository: `owner/example`",
                "Canonical spec: `docs/superpowers/specs/canonical-design.md`",
                "Canonical plan: `docs/superpowers/plans/canonical-plan.md`",
                "Assigned branch: `agent/lane-a`",
                f"Frozen base SHA: `{'a' * 40}`",
                "Inherited risk floor: **STANDARD**",
                "## Exclusive files / owned paths",
                "## Shared / read-only files",
                "## Effect authorization",
                "push/write authority applies only to `agent/lane-a`",
                "other branches/trunk: no write authority is implied",
                "## Required verification",
                "## Dependency contract",
                "Self-READY: **FORBIDDEN**",
                "Self-merge: **FORBIDDEN**",
                "not evidence",
                "READY_FOR_COORDINATOR",
            ):
                self.assertIn(required, worker)
            self.assertNotIn("DO NOT START", worker)

            coordinator = (output / "coordinator.md").read_text(encoding="utf-8")
            self.assertIn("Bu promptları ayrı ChatGPT pencerelerinde aç.", coordinator)
            self.assertIn("Dependency-blocked lanes withheld by default: `lane-c`", coordinator)
            self.assertIn("merge=denied", coordinator)
            self.assertNotIn("Worker'ları başlattım.", coordinator)
            self.assertNotIn("3 agent çalışıyor.", coordinator)

    def test_preview_blocked_marks_do_not_start_and_unmet_prerequisites(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "handoffs"
            result = self.run_renderer(
                profile_fixture(), dependency_fixture(), output, "--preview-blocked"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            blocked = (output / "lane-c.md").read_text(encoding="utf-8")
            self.assertTrue(blocked.startswith("# DO NOT START"))
            self.assertIn("## Unmet prerequisites", blocked)
            self.assertIn("lane-a — pending", blocked)
            self.assertIn("lane-b — pending", blocked)
            self.assertIn("Do not edit, commit, push", blocked)

    def test_satisfied_prerequisites_release_downstream_and_stale_preview_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "handoffs"
            first = self.run_renderer(
                profile_fixture(), dependency_fixture(), output, "--preview-blocked"
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((output / "lane-c.md").exists())

            second = self.run_renderer(profile_fixture(), dependency_fixture(), output)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertFalse((output / "lane-c.md").exists())

            third = self.run_renderer(profile_fixture(), dependency_fixture(a=True, b=True), output)
            self.assertEqual(third.returncode, 0, third.stderr)
            self.assertEqual(
                sorted(path.name for path in output.glob("*.md")),
                ["coordinator.md", "lane-c.md"],
            )
            downstream = (output / "lane-c.md").read_text(encoding="utf-8")
            self.assertNotIn("DO NOT START", downstream)
            self.assertIn("lane-a: satisfied (merged)", downstream)
            self.assertIn("lane-b: satisfied (merged)", downstream)

    def test_same_normalized_profile_and_dependency_state_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output_a = root / "one"
            output_b = root / "two"
            profile_a = profile_fixture()
            profile_b = copy.deepcopy(profile_a)
            profile_b = dict(reversed(list(profile_b.items())))
            dependency_a = dependency_fixture()
            dependency_b = {"lanes": dict(reversed(list(dependency_a["lanes"].items())))}
            first = self.run_renderer(profile_a, dependency_a, output_a)
            second = self.run_renderer(profile_b, dependency_b, output_b)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            names_a = sorted(path.name for path in output_a.glob("*.md"))
            names_b = sorted(path.name for path in output_b.glob("*.md"))
            self.assertEqual(names_a, names_b)
            hashes_a = {
                name: hashlib.sha256((output_a / name).read_bytes()).hexdigest()
                for name in names_a
            }
            hashes_b = {
                name: hashlib.sha256((output_b / name).read_bytes()).hexdigest()
                for name in names_b
            }
            self.assertEqual(hashes_a, hashes_b)

    def test_missing_canonical_pointers_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "handoffs"
            profile = profile_fixture()
            profile.pop("canonical")
            result = self.run_renderer(profile, dependency_fixture(), output)
            self.assertEqual(result.returncode, 2)
            self.assertIn("canonical spec pointer", result.stderr)
            self.assertFalse(output.exists())

    def test_worker_result_contract_cannot_self_ready(self) -> None:
        contract = ROOT / "skills/controller-gated-mpd/references/worker-result-contract.md"
        self.assertTrue(contract.exists(), "worker result contract is not implemented yet")
        text = contract.read_text(encoding="utf-8")
        self.assertIn("not evidence", text.lower())
        self.assertIn("must not create ready", text.lower())
        self.assertIn("ready_for_coordinator", text.lower())
        self.assertIn("not mpd `ready@sha`", text.lower())


if __name__ == "__main__":
    unittest.main()

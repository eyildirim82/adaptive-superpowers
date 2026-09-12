from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "controller-gated-mpd" / "scripts"


def load_policy():
    path = SCRIPTS / "policy.py"
    if not path.exists():
        raise AssertionError(f"missing V6 policy module: {path}")
    spec = importlib.util.spec_from_file_location("cg_mpd_v6_policy", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_profile() -> dict:
    return {
        "schema_version": 4,
        "protocol_version": 6,
        "wave": "v6-foundation",
        "repository": {
            "repo": "owner/repo",
            "trunk": "main",
            "frozen_base_sha": "b" * 40,
        },
        "adaptive": {
            "risk_floor": "STANDARD",
            "authorization": {
                "push": "unknown",
                "merge": "denied",
                "deploy": "unknown",
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
            "path_floors": [
                {"level": "CRITICAL", "paths": ["src/auth/**", "supabase/migrations/**", ".github/workflows/**"]},
                {"level": "STANDARD", "paths": ["src/**", "app/**", "package.json"]},
                {"level": "FAST", "paths": ["docs/**", "README.md"]},
            ],
        },
        "hot_zones": ["src/runtime/**"],
        "lanes": [
            {
                "id": "lane-a",
                "branch": "agent/lane-a",
                "risk": "FAST",
                "prerequisites": [],
                "owned": ["docs/**"],
                "forbidden": ["src/runtime/**"],
                "downstream": [],
            }
        ],
        "merge": {
            "method": "squash",
            "approvals_dir": ".superpowers/mpd/v6-foundation/approvals",
            "trunk_green_after_each": True,
        },
    }


class V6PolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_policy()

    def test_v6_rejects_legacy_risk_names(self) -> None:
        p = base_profile()
        p["risk_policy"]["default_level"] = "normal"
        with self.assertRaises(self.policy.PolicyError):
            self.policy.validate_profile(p)

    def test_v6_accepts_only_adaptive_risk_names_and_monotonic_gates(self) -> None:
        p = base_profile()
        validated = self.policy.validate_profile(p)
        self.assertEqual(validated["schema_version"], 4)
        self.assertEqual(validated["protocol_version"], 6)
        bad = base_profile()
        bad["risk_policy"]["levels"]["STANDARD"]["gates"] = ["typecheck"]
        with self.assertRaises(self.policy.PolicyError):
            self.policy.validate_profile(bad)

    def test_mpd_wave_floor_cannot_be_fast(self) -> None:
        p = base_profile()
        p["adaptive"]["risk_floor"] = "FAST"
        with self.assertRaises(self.policy.PolicyError):
            self.policy.validate_profile(p)

    def test_lane_cannot_downgrade_inherited_floor(self) -> None:
        p = base_profile()
        result = self.policy.resolve_effective_risk(p, "lane-a", ["docs/guide.md"])
        self.assertEqual(result["declared"], "FAST")
        self.assertEqual(result["effective"], "STANDARD")
        self.assertEqual(result["floor"], "STANDARD")

    def test_sensitive_paths_escalate_to_critical(self) -> None:
        p = base_profile()
        p["lanes"][0]["owned"] = ["src/auth/**"]
        result = self.policy.resolve_effective_risk(p, "lane-a", ["src/auth/session.py"])
        self.assertEqual(result["effective"], "CRITICAL")
        self.assertTrue(result["escalations"])

    def test_authorization_is_validated_but_not_converted_to_risk(self) -> None:
        p = base_profile()
        p["adaptive"]["authorization"]["merge"] = "granted"
        validated = self.policy.validate_profile(p)
        result = self.policy.resolve_effective_risk(validated, "lane-a", ["docs/guide.md"])
        self.assertEqual(result["effective"], "STANDARD")
        self.assertEqual(validated["adaptive"]["authorization"]["merge"], "granted")

    def test_validator_cli_rejects_protocol_5_profile(self) -> None:
        p = base_profile()
        p["schema_version"] = 3
        p["protocol_version"] = 5
        with tempfile.TemporaryDirectory() as td:
            profile = Path(td) / "wave.json"
            profile.write_text(json.dumps(p), encoding="utf-8")
            result = subprocess.run(
                ["python3", str(SCRIPTS / "validate_wave_profile.py"), str(profile)],
                text=True,
                capture_output=True,
                timeout=20,
            )
        self.assertNotEqual(result.returncode, 0)
        message = result.stdout + result.stderr
        self.assertIn("schema_version", message)
        self.assertIn("protocol_version", message)


if __name__ == "__main__":
    unittest.main()

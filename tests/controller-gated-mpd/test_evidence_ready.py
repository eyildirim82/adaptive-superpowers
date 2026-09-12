from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/controller-gated-mpd/scripts"

class EvidenceReadyContractTests(unittest.TestCase):
    def test_v6_ready_scripts_exist(self) -> None:
        self.assertTrue((SCRIPTS / "approve_ready.py").exists(), "V6 READY materializer missing")
        self.assertTrue((SCRIPTS / "verify_ready.py").exists(), "V6 READY verifier missing")

    def test_worker_report_is_not_an_evidence_input(self) -> None:
        checker = SCRIPTS / "check_exact_head.py"
        self.assertTrue(checker.exists(), "exact-head evidence checker missing")
        text = checker.read_text(encoding="utf-8")
        self.assertNotIn("worker_result", text)

if __name__ == "__main__":
    unittest.main()

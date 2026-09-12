from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

class PromptHandoffContractTests(unittest.TestCase):
    def test_chatgpt_transport_has_renderer(self) -> None:
        renderer = ROOT / "skills/controller-gated-mpd/scripts/render_handoff_prompts.py"
        self.assertTrue(renderer.exists(), "Prompt-Handoff renderer is not implemented yet")

    def test_worker_result_contract_cannot_self_ready(self) -> None:
        contract = ROOT / "skills/controller-gated-mpd/references/worker-result-contract.md"
        self.assertTrue(contract.exists(), "worker result contract is not implemented yet")
        text = contract.read_text(encoding="utf-8")
        self.assertIn("not evidence", text.lower())
        self.assertIn("must not create ready", text.lower())

if __name__ == "__main__":
    unittest.main()

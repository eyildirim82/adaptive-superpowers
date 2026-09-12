from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

class MergeTrainContractTests(unittest.TestCase):
    def test_merge_train_exists_and_mentions_adaptive_merge_authorization(self) -> None:
        path = ROOT / "skills/controller-gated-mpd/scripts/merge_train.sh"
        self.assertTrue(path.exists(), "V6 merge train is not implemented yet")
        text = path.read_text(encoding="utf-8")
        self.assertIn("adaptive.authorization.merge", text)
        self.assertIn("granted", text)

if __name__ == "__main__":
    unittest.main()

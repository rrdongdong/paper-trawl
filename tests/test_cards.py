import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "cards.py")

GOOD = """# 10.23 早读报告

### 问题卡 #07

- 解决：P-SCALE-01 @ §III-A（E3）
- 遗留：P-THEORY-01 @ §V-D（E1）
- 假设：A-ASSUME-01 @ §III-A（E1）
- 局限：L-SCALE-01 @ §I（E3）
- 批评：M-SCALE-02 @ §II（E2，未对比）
- 异常：§V Table 4 = agent 数↑而上行反而↓，论文未解释
"""


def run(args):
    result = subprocess.run(
        [sys.executable, SCRIPT] + args, capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


class CardScriptTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="cards-test-")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, text, name="report.md"):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_good_card_passes(self):
        code, out, _ = run(["check", self.write(GOOD)])
        self.assertEqual(code, 0)
        self.assertIn("leaves_open=1", out)

    def test_emit_produces_relations_and_evidence(self):
        import json

        code, out, _ = run(["emit", self.write(GOOD)])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["solves"][0]["node"], "P-SCALE-01")
        self.assertEqual(payload["leaves_open"][0]["evidence"], "E1")
        self.assertEqual(payload["criticizes"][0]["compared"], False)
        self.assertEqual(payload["anomaly"][0]["loc"], "§V Table 4")

    def test_missing_vocabulary_id_is_refused(self):
        bad = "### 问题卡 #08\n- 遗留：通信预算的问题 @ §V（E3）\n"
        code, _, err = run(["check", self.write(bad)])
        self.assertEqual(code, 2)
        self.assertIn("no vocabulary id", err)

    def test_missing_location_is_refused(self):
        bad = "### 问题卡 #09\n- 局限：L-EVAL-01（E3）\n"
        code, _, err = run(["check", self.write(bad)])
        self.assertEqual(code, 2)
        self.assertIn("no location", err)

    def test_missing_evidence_grade_is_refused(self):
        bad = "### 问题卡 #10\n- 假设：A-ASSUME-02 @ §III\n"
        code, _, err = run(["check", self.write(bad)])
        self.assertEqual(code, 2)
        self.assertIn("no evidence grade", err)

    def test_all_faults_reported_at_once(self):
        bad = "### 问题卡 #11\n- 局限：L-EVAL-01\n"
        code, _, err = run(["check", self.write(bad)])
        self.assertEqual(code, 2)
        self.assertIn("no location", err)
        self.assertIn("no evidence grade", err)

    def test_compared_criticism_is_marked(self):
        import json

        text = "### 问题卡 #12\n- 批评：M-SCALE-02 @ §II（E2，已对比）\n"
        code, out, _ = run(["emit", self.write(text)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["criticizes"][0]["compared"], True)

    def test_missing_card_block_is_refused(self):
        code, _, err = run(["check", self.write("# 空报告\n")])
        self.assertEqual(code, 2)
        self.assertIn("no 问题卡 block", err)

    def test_paper_filter(self):
        text = GOOD + "\n### 问题卡 #08\n- 局限：L-EVAL-01 @ §V（E3）\n"
        path = self.write(text)
        code, out, _ = run(["emit", path, "--paper", "08"])
        self.assertEqual(code, 0)
        self.assertIn("L-EVAL-01", out)
        self.assertNotIn("P-SCALE-01", out)

    def test_emit_to_file(self):
        out_path = os.path.join(self.dir, "card.json")
        code, _, _ = run(["emit", self.write(GOOD), "-o", out_path])
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(out_path))

    def test_unreadable_file(self):
        code, _, err = run(["check", os.path.join(self.dir, "missing.md")])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()

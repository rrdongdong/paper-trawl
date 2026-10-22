#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger.py 的解析、校验与去重测试（用 fixtures/ledger_min.md）。"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ledger import parse_details, parse_entries, venue_tier  # noqa: E402

FIXTURE = (ROOT / "fixtures" / "ledger_min.md").read_text(encoding="utf-8")


class Parsing(unittest.TestCase):
    def test_index_rows(self):
        entries = parse_entries(FIXTURE)
        self.assertEqual([e["short"] for e in entries], ["ALPHA", "BETA", "GAMMA"])

    def test_detail_blocks(self):
        d = parse_details(FIXTURE)
        self.assertEqual(set(d), {"01", "02"})
        self.assertIn("Fixture University", d["01"]["fields"]["作者"])

    def test_venue_tier(self):
        self.assertEqual(venue_tier("IEEE Transactions on Image Processing"), "S")
        self.assertEqual(venue_tier("IEEE Robotics and Automation Letters"), "A")
        self.assertEqual(venue_tier("arXiv:2607.00001"), "B")


class CliBehaviour(unittest.TestCase):
    def setUp(self):
        self.ws = pathlib.Path(tempfile.mkdtemp())
        shutil.copy(ROOT / "fixtures" / "ledger_min.md", self.ws / "论文台账.md")
        (self.ws / "tools").mkdir()
        shutil.copy(ROOT / "scripts" / "venue_check.py", self.ws / "tools" / "paper_dedup_stub.py")

    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)

    def run_ledger(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "ledger.py"), *args,
                               "--workspace", str(self.ws)],
                              capture_output=True, text=True, timeout=60)

    def test_validate_passes_on_consistent_ledger(self):
        r = self.run_ledger("validate")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("全部通过", r.stdout)

    def test_validate_catches_missing_index_row(self):
        # 删掉 §2 的 #02 详情节 → 索引有、详情无
        p = self.ws / "论文台账.md"
        text = p.read_text(encoding="utf-8")
        start = text.index("### #02 BETA")
        end = text.index("## 3. 已筛查但未精读")
        p.write_text(text[:start] + text[end:], encoding="utf-8")
        r = self.run_ledger("validate")
        self.assertEqual(r.returncode, 2)
        self.assertIn("#02", r.stdout)

    def test_validate_catches_head_count_drift(self):
        p = self.ws / "论文台账.md"
        p.write_text(p.read_text(encoding="utf-8").replace("已精读 2 篇", "已精读 5 篇"), encoding="utf-8")
        r = self.run_ledger("validate")
        self.assertEqual(r.returncode, 2)
        self.assertIn("头部声称", r.stdout)

    def test_add_refuses_duplicate(self):
        r = self.run_ledger("add", "--short", "ALPHA", "--title", "dup", "--venue", "CVPR 2026")
        self.assertEqual(r.returncode, 3)
        self.assertIn("拒绝重复登记", r.stdout)

    def test_add_appends_index_and_detail(self):
        r = self.run_ledger("add", "--short", "DELTA", "--title", "DELTA: A Newly Added Fixture Paper",
                            "--venue", "IEEE Transactions on Image Processing", "--id", "10.1109/tip.2099.1",
                            "--date", "10.23", "--tags", "水下 / 重建", "--relation", "对标",
                            "--conclusion", "结论", "--facts", "- 事实", "--weakness", "弱点")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = (self.ws / "论文台账.md").read_text(encoding="utf-8")
        self.assertIn("| 03 | 10.23 | DELTA |", text)
        self.assertIn("### #03 DELTA — DELTA: A Newly Added Fixture Paper", text)
        self.assertIn("已精读 3 篇", text)
        self.assertEqual(self.run_ledger("validate").returncode, 0)


if __name__ == "__main__":
    unittest.main()

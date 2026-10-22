#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""summarize.py 冒烟测试：只验证"自动部分正确 + 人工部分留空"的边界。"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Summarize(unittest.TestCase):
    def setUp(self):
        self.ws = pathlib.Path(tempfile.mkdtemp())
        shutil.copy(ROOT / "fixtures" / "ledger_min.md", self.ws / "论文台账.md")

    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)

    def test_generates_sections_and_keeps_judgement_empty(self):
        out = self.ws / "summary.md"
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "summarize.py"),
                            "--workspace", str(self.ws), "--out", str(out)],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = out.read_text(encoding="utf-8")

        # 自动段：统计与逐篇摘录
        self.assertIn("## 0. 台账状态", text)
        self.assertIn("正式精读：**2 篇**", text)
        self.assertIn("## 1. 主题线", text)
        self.assertIn("| 多机 | 1 | #01 |", text)      # 夹具里 多机 只出现在 #01
        self.assertIn("ALPHA", text)

        # 人工段：必须留 `[待填]`，脚本不得代写结论
        for sec in ("## 3. 共识与分歧", "## 4. 技术路线的演进", "## 6. 阅读路径建议"):
            self.assertIn(sec, text)
        self.assertGreaterEqual(text.count("[待填]"), 3)

    def test_rejects_missing_ledger(self):
        ws = pathlib.Path(tempfile.mkdtemp())
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "summarize.py"),
                            "--workspace", str(ws)],
                           capture_output=True, text=True, timeout=60)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("找不到台账", r.stdout + r.stderr)
        shutil.rmtree(ws, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

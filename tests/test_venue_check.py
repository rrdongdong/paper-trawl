#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""venue_check 的分类回归测试。

每条用例都对应一次真实踩坑，见 docs/pitfalls.md：
  * 期刊层级必须按 "IEEE Transactions on <副名>" 的副名匹配，
    否则 "Journal of Medical Imaging" 会因为裸词 medical imaging 被误判为旗舰；
  * 拒绝词（Findings/Workshop）必须先于会议名匹配，否则 "CVPR Findings" 冒充主会；
  * "&" 要归一化成 "and"，否则 IROS 全称匹配不上；
  * Letters（RA-L）是期刊不是会议，且不是 Transactions。
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from venue_check import classify  # noqa: E402


class JournalTiers(unittest.TestCase):
    def test_flagship_transactions_are_S(self):
        for v in ("IEEE Transactions on Image Processing",
                  "IEEE Transactions on Pattern Analysis and Machine Intelligence",
                  "IEEE Transactions on Robotics",
                  "IEEE Transactions on Multimedia"):
            role, tier, _ = classify(v, "10.1109/x.2026.1")
            self.assertEqual((role, tier), ("journal", "S"), v)

    def test_letters_is_journal_A_not_conference(self):
        role, tier, msg = classify("IEEE Robotics and Automation Letters", "10.1109/lra.2026.1")
        self.assertEqual(role, "journal", msg)
        self.assertEqual(tier, "A", msg)
        self.assertIn("Letters", msg)

    def test_medical_imaging_journal_is_not_flagship(self):
        # 命中裸词 medical imaging，但出版方不是 IEEE → 交人工，绝不能给 S
        role, tier, _ = classify("Journal of medical imaging", "10.1117/1.jmi.1")
        self.assertNotEqual(tier, "S")
        role2, tier2, _ = classify("IEEE Transactions on Medical Imaging", "10.1109/tmi.1")
        self.assertEqual((role2, tier2), ("journal", "S"))

    def test_independent_journals(self):
        self.assertEqual(classify("Pattern Recognition", "10.1016/j.patcog.1")[1], "A")
        self.assertEqual(classify("Neurocomputing", "10.1016/j.neucom.1")[1], "B")
        self.assertEqual(classify("IEEE Access", "10.1109/access.1")[1], "B")

    def test_transactions_with_unknown_subname_is_A(self):
        role, tier, _ = classify("IEEE Transactions on Some New Topic", "10.1109/tnt.1")
        self.assertEqual((role, tier), ("journal", "A"))


class ConferenceTiers(unittest.TestCase):
    def test_ccf_a_conferences_are_S(self):
        for v in ("CVPR 2026", "ICCV 2025", "NeurIPS 2026", "ICML 2026", "AAAI 2026", "ACM MM 2026"):
            role, tier, _ = classify(v)
            self.assertEqual((role, tier), ("conference", "S"), v)

    def test_findings_is_not_main_conference(self):
        role, tier, msg = classify("CVPR 2026 Findings")
        self.assertEqual(role, "conference")
        self.assertEqual(tier, "A", msg)
        self.assertIn("Findings", msg)

    def test_reject_words_beat_venue_words(self):
        role, tier, msg = classify("CVPR 2026 Workshops")
        self.assertEqual(role, "conference")
        self.assertEqual(tier, "B", msg)

    def test_strong_non_ccf_a_conferences_are_A(self):
        for v in ("ECCV 2026", "ICRA 2026", "IROS 2026", "3DV 2026", "CoRL 2026"):
            role, tier, _ = classify(v)
            self.assertEqual((role, tier), ("conference", "A"), v)

    def test_ampersand_normalisation(self):
        role, tier, _ = classify("IEEE/RSJ International Conference on INTELLIGENT ROBOTS & SYSTEMS 2026")
        self.assertEqual((role, tier), ("conference", "A"))

    def test_spelled_out_venue_names(self):
        role, tier, _ = classify("IEEE/CVF Conference on Computer Vision and Pattern Recognition")
        self.assertEqual((role, tier), ("conference", "S"))


class Preprints(unittest.TestCase):
    def test_arxiv_is_unknown_B(self):
        role, tier, _ = classify("arXiv", "arXiv:2605.30342")
        self.assertEqual((role, tier), ("unknown", "B"))


if __name__ == "__main__":
    unittest.main()


class DedupSemantics(unittest.TestCase):
    """'无法查重' 不能等同于 '重复'。"""

    def test_missing_ledger_does_not_fail_the_pair(self):
        import subprocess, tempfile, pathlib
        ws = pathlib.Path(tempfile.mkdtemp())          # 空工作区：无台账、无查重脚本
        r = subprocess.run([sys.executable,
                            str(pathlib.Path(__file__).resolve().parents[1] / "scripts" / "venue_check.py"),
                            "--a-venue", "IEEE Transactions on Image Processing", "--a-doi", "10.1109/tip.2099.1",
                            "--b-venue", "CVPR 2099", "--b-id", "arXiv:2099.1",
                            "--workspace", str(ws)],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("跳过查重", r.stdout)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""venue_check.py — 给一期早读的两篇论文打 venue 标签并查重。

设计原则：**venue 只做标注，不做否决**。
只有一种情况判"不可用"：两篇都不是正式发表物（双预印本），且层级都不高。

用法：
    python3 venue_check.py --list
    python3 venue_check.py \
      --a-venue "IEEE Robotics and Automation Letters" --a-doi "10.1109/lra.2026.1234567" \
      --b-venue "CVPR 2026 Findings" --b-id "arXiv:2605.30342"

退出码：0 可用 / 2 双预印本且层级低 / 3 与台账重复 / 1 参数错误
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

# ------------------------------------------------------------------ 分层表

JOURNAL_S = [
    "pattern analysis and machine intelligence", "international journal of computer vision",
    "image processing", "transactions on multimedia", "neural networks and learning systems",
    "knowledge and data engineering", "software engineering", "transactions on robotics",
    "geoscience and remote sensing", "circuits and systems for video technology",
    "visualization and computer graphics", "medical imaging", "transactions on signal processing",
    "transactions on information forensics and security",
]

JOURNAL_A = [
    "robotics and automation letters", "automation science and engineering",
    "industrial informatics", "intelligent transportation systems",
    "computational social systems", "dependable and secure computing",
    "parallel and distributed systems", "mobile computing", "transactions on cybernetics",
    "transactions on artificial intelligence", "acm transactions on graphics",
    "isprs journal", "pattern recognition", "transactions on instrumentation and measurement",
    "journal of selected topics in signal processing", "robotics and autonomous systems",
]

JOURNAL_B = [
    "access", "sensors journal", "remote sensing", "electronics", "ieee sensors",
    "applied sciences", "neurocomputing", "information fusion",
    "expert systems with applications", "journal of real-time image processing",
]

# 期刊列表统一成"副名"形式（去掉 transactions on / journal of 前缀），
# 这样 'IEEE Transactions on Robotics' 抽出的副名 'robotics' 才能命中。
def _strip_prefix(x: str) -> str:
    return re.sub(r"^(transactions on|journal of)\s+", "", x.strip().lower())


JOURNAL_S = [_strip_prefix(x) for x in JOURNAL_S]
JOURNAL_A = [_strip_prefix(x) for x in JOURNAL_A]

CONF_S = {
    "cvpr": "IEEE/CVF CVPR",
    "computer vision and pattern recognition": "IEEE/CVF CVPR",
    "iccv": "ICCV",
    "international conference on computer vision": "ICCV",
    "neurips": "NeurIPS",
    "nips": "NeurIPS",
    "neural information processing systems": "NeurIPS",
    "icml": "ICML",
    "international conference on machine learning": "ICML",
    "iclr": "ICLR（CCF 未收录，社区按 A 类）",
    "aaai": "AAAI",
    "aaai conference on artificial intelligence": "AAAI",
    "ijcai": "IJCAI",
    "international joint conference on artificial intelligence": "IJCAI",
    "acl": "ACL",
    "annual meeting of the association for computational linguistics": "ACL",
    "emnlp": "EMNLP（CCF-B，语言方向常读）",
    "mm": "ACM MM",
    "acmmm": "ACM MM",
    "multimedia": "ACM MM",
    "acm international conference on multimedia": "ACM MM",
    "siggraph": "SIGGRAPH",
    "siggraph asia": "SIGGRAPH Asia",
}

#: 先于 S 层判定：Findings 等"主会之外的轨道"
CONF_A = {
    "findings": "Findings（主会之外的正式接收轨道）",
    "eccv": "ECCV（CCF-B，社区视为视觉顶会）",
    "european conference on computer vision": "ECCV（CCF-B）",
    "icra": "ICRA（CCF-B，机器人主场）",
    "iros": "IROS（CCF-C，机器人主场）",
    "intelligent robots and systems": "IROS（CCF-C，机器人主场）",
    "corl": "CoRL（机器人学习）",
    "rss": "RSS（Robotics: Science and Systems）",
    "3dv": "3DV（CCF-B）",
    "bmvc": "BMVC", "accv": "ACCV", "wacv": "WACV",
}

CONF_B = {"workshop": "Workshop（含 Workshops）"}

#: 独立期刊（非 IEEE/ACM 前缀），逐名匹配
JOURNAL_NAMED_A = [
    "pattern recognition", "isprs journal of photogrammetry and remote sensing",
    "international journal of computer vision", "remote sensing of environment",
    "robotics and autonomous systems", "computer vision and image understanding",
]
JOURNAL_NAMED_B = [
    "neurocomputing", "information fusion", "expert systems with applications",
    "applied sciences", "electronics", "sensors", "remote sensing",
    "journal of real-time image processing", "ieee access", "access",
]


_PLURAL = {"workshops": "workshop", "tutorials": "tutorial", "symposiums": "symposium"}


def norm(s: str) -> str:
    s = (s or "").strip().lower().replace("&", " and ")
    s = re.sub(r"\s+", " ", s)
    for k, v in _PLURAL.items():          # 复数归一，避免 \bworkshop\b 漏掉 workshops
        s = re.sub(rf"\b{k}\b", v, s)
    return s


def _hit(venue_norm: str, table):
    """取最长命中，避免短词抢占。"""
    best = None
    items = table.keys() if isinstance(table, dict) else table
    for key in items:
        k = norm(key)
        if re.search(rf"\b{re.escape(k)}\b", venue_norm) and (best is None or len(k) > len(best)):
            best = key
    return best


def classify(venue: str, doi: str = ""):
    """返回 (role, tier, message)。"""
    v = norm(venue)
    d = (doi or "").lower()
    is_preprint = "arxiv" in v or d.startswith("arxiv:")

    # —— IEEE/ACM Transactions / Journal：按"副名"查层级，避免"xxx medical imaging"
    #    这类非 IEEE 期刊因为裸词命中而被误判为旗舰。
    # —— 会议语境优先：'CVPR' 的全称里含 "pattern recognition"，会被独立期刊表
    #    误吞（'IEEE/CVF Conference on Computer Vision and Pattern Recognition'）。
    conference_ctx = bool(re.search(r"\b(conference|proceedings|workshop|symposium|congress)\b", v))
    if conference_ctx:
        # 顺序很重要：workshop 先于主会（"CVPR 2026 Workshops" 不能算主会），
        # findings 先于主会（"CVPR Findings" 是另一个轨道）。
        k = _hit(v, CONF_B)
        if k:
            return "conference", "B", f"🟠 {CONF_B[k]}：{venue}；层级 B，须写明并说明为何仍值得读"
        k = _hit(v, CONF_A)
        if k:
            return "conference", "A", f"🟡 {CONF_A[k]}：{venue}；venue 层级 A，报告中需注明"
        k = _hit(v, CONF_S)
        if k:
            return "conference", "S", f"✅ {CONF_S[k]}：{venue}"
        return "conference", "A", f"🟡 会议（清单外）：{venue}；层级 A，报告中需注明"

    # —— IEEE/ACM *Letters*（如 RA-L）：期刊，但非 Transactions，层级 A
    if re.search(r"\b(?:ieee|acm)\b.*\bletters\b", v) or "robotics and automation letters" in v:
        return "journal", "A", f"🟡 IEEE/ACM Letters（非 Transactions）：{venue}；层级 A，报告中需注明"

    m = re.search(r"(?:ieee|acm)\s+(?:transactions on|journal of)\s+(.+)", v)
    if m:
        sub = m.group(1)
        sub = re.sub(r"\s*\(.*?\)\s*$", "", sub).strip()
        if "robotics and automation letters" in sub:
            return "journal", "A", f"🟡 IEEE RA-L（Letters，非 Transactions）：{venue}；层级 A，报告中需注明"
        if not (d.startswith("10.1109/") or d.startswith("10.1145/") or not d):
            return "journal", "A", f"🟡 刊名像 Trans，但 DOI 前缀异常（{doi}）→ 核对是否同名非 IEEE 刊"
        if sub in JOURNAL_S:
            return "journal", "S", f"✅ IEEE/ACM Transactions（S 层）：{venue}"
        if sub in JOURNAL_A:
            return "journal", "A", f"🟡 IEEE/ACM Transactions（A 层）：{venue}；报告中需注明"
        return "journal", "A", f"🟡 IEEE/ACM Transactions（清单外副名：{sub}）：{venue}；层级 A，报告中需注明"

    # —— 独立期刊（非 IEEE/ACM），逐名匹配，不做裸词匹配
    for tier, named in (("A", JOURNAL_NAMED_A), ("B", JOURNAL_NAMED_B)):
        for name in named:
            if re.search(rf"\b{re.escape(name)}\b", v):
                return "journal", tier, f"🟡 {venue}（独立期刊，{tier} 层）；报告中需注明"

    # —— 含易混淆裸词但不属于上述清单 → 交人工
    if any(w in v for w in ("medical imaging", "image processing", "remote sensing", "robotics")):
        return "unknown", "?", f"❓ 疑似相关期刊但不在清单：{venue} → 人工确认出版方与层级后再用"


    k = _hit(v, CONF_A)
    if k:
        return "conference", "A", f"🟡 {CONF_A[k]}：{venue}；venue 层级 A，报告中需注明"
    k = _hit(v, CONF_S)
    if k:
        return "conference", "S", f"✅ {CONF_S[k]}：{venue}"
    k = _hit(v, CONF_B)
    if k:
        return "conference", "B", f"🟠 {CONF_B[k]}：{venue}；层级 B，须写明并说明为何仍值得读"

    if is_preprint:
        return "unknown", "B", f"🟠 预印本：{venue}；仅当另一篇为 S/A 时可用，且须注明未正式发表"

    return "unknown", "?", f"❓ 无法判定层级：{venue or '(空)'} → 请在报告中写明出版状态与检索渠道"


def dedup(ids, workspace: pathlib.Path):
    script = workspace / "tools" / "paper_dedup.py"
    if script.exists():
        try:
            r = subprocess.run([sys.executable, str(script), "--check", *ids],
                               capture_output=True, text=True, timeout=120)
            return r.returncode == 0, ((r.stdout or "") + (r.stderr or "")).strip()
        except Exception as e:  # noqa: BLE001
            return False, f"查重脚本执行失败：{e}"
    ledger = workspace / "论文台账.md"
    if not ledger.exists():
        # "查不了" ≠ "重复"：缺台账时放行并提示，不能把选文判死。
        return True, "⚠️ 找不到 tools/paper_dedup.py 与 论文台账.md → 跳过查重（请在含台账的工作区重跑）"
    text = ledger.read_text(encoding="utf-8").lower()
    hits = [i for i in ids if i and i.lower().strip() in text]
    return (not hits), ("⚠️ 台账已存在：" + ", ".join(hits)) if hits else "（文本扫描：未命中）"


TIER_ORDER = {"S": 3, "A": 2, "B": 1, "?": 0}


def main() -> int:
    ap = argparse.ArgumentParser(description="早读 venue 标注（不否决版）")
    ap.add_argument("--a-venue")
    ap.add_argument("--a-doi", default="")
    ap.add_argument("--b-venue")
    ap.add_argument("--b-id", default="")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for title, table in (("期刊 · S", JOURNAL_S), ("期刊 · A（含 Letters）", JOURNAL_A),
                             ("期刊 · B（需注明）", JOURNAL_B)):
            print(f"{title}:")
            for x in table:
                print("  -", x)
            print()
        for title, table in (("会议 · S", CONF_S), ("会议 · A（需注明）", CONF_A),
                             ("会议 · B（需注明）", CONF_B)):
            print(f"{title}:")
            for k, v in table.items():
                print(f"  - {k:<14} {v}")
            print()
        return 0

    if not args.a_venue or not args.b_venue:
        ap.error("需要 --a-venue 与 --b-venue（或 --list）")

    ra, ta, ma = classify(args.a_venue, args.a_doi)
    rb, tb, mb = classify(args.b_venue, args.b_id)
    print(f"论文一 [{ra}/{ta}] {ma}")
    print(f"论文二 [{rb}/{tb}] {mb}")

    both_unpublished = ra == "unknown" and rb == "unknown"
    neither_strong = TIER_ORDER[ta] < 2 and TIER_ORDER[tb] < 2
    if both_unpublished and neither_strong:
        print("\n结论: ❌ 两篇均非正式发表物且层级都不高 → 建议改期，或先放 S* 待定区等见刊")
        return 2

    ids = [x for x in (args.a_doi, args.b_id) if x]
    if ids:
        fresh, detail = dedup(ids, pathlib.Path(args.workspace).resolve())
        print("查重:", detail or ("未命中" if fresh else "命中"))
        if not fresh:
            print("\n结论: ❌ 与台账重复 —— 换论文（或把 S* 条目升级，不算新增）")
            return 3

    notes = []
    for tier, tag in ((ta, "论文一"), (tb, "论文二")):
        if tier == "A":
            notes.append(f"{tag}: 报告中写明「venue 层级 A（非 CCF-A，但为本领域主流）」")
        elif tier == "B":
            notes.append(f"{tag}: 报告中写明「venue 层级较低 / 预印本」，并说明为何仍值得精读")
    if notes:
        print("\n需在报告中补充的标注:")
        for n in notes:
            print("  ·", n)

    print("\n结论: ✅ 可用（venue 只作标注，不否决）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

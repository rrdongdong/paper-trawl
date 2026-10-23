#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""find_papers.py — 给一个研究方向，从 arXiv + OpenAlex 拉候选论文并打 venue 标签。

用法：
    python3 find_papers.py --topic "3D Gaussian Splatting active reconstruction"
    python3 find_papers.py --topic "underwater 3DGS" --days 180 --per-source 10
    python3 find_papers.py --topic "multi-agent active reconstruction" --workspace ~/.dsh

输出：按"期刊 / 会议 / 预印本"分组的候选表，并标出
      - venue 层级（S/A/B，来自 venue_check.classify）
      - 是否已在台账登记（重复会被标记 ⛔ 并默认隐藏）

设计约束：
  * 只用公开 API（arXiv Atom、OpenAlex、Crossref），不需要任何凭据；
  * 网络失败时**明确报错**，不静默返回空列表；
  * 候选只是起点，最终选文仍须人工判断相关性（脚本不替你决定）。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from xml.etree import ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from venue_check import classify  # noqa: E402
except Exception:  # pragma: no cover
    def classify(venue, doi=""):  # type: ignore[override]
        return "unknown", "?", f"❓ {venue}"

# arXiv 官方 API 礼仪要求：并发 ≤1 请求/3 秒，并在 User-Agent 里给出联系方式。
# 部署者可通过环境变量补上自己的邮箱；未设置时保留占位（arxiv 不强制，但鼓励）。
import os as _os

UA = {"User-Agent": "research-early-reading/1.0 (contact: %s)"
      % (_os.environ.get("EARLY_READING_CONTACT") or "set-EARLY_READING_CONTACT-env")}


def fetch(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ------------------------------------------------------------------ arXiv

def search_arxiv(topic: str, per_source: int, days: int) -> list[dict]:
    """查询 arXiv。调用方应保证同一进程内串行，相邻请求间隔 ≥3s（见 UA 处的说明）。"""
    # arXiv 语法：all:"短语"；多词用 AND 连接
    words = [w for w in re.split(r"\s+", topic.strip()) if w]
    phrase = "+AND+".join(f'all:%22{urllib.parse.quote(w)}%22' for w in words)
    url = ("http://export.arxiv.org/api/query?search_query=" + phrase
           + f"&sortBy=submittedDate&sortOrder=descending&max_results={max(per_source * 3, 30)}")
    raw = None
    for attempt in (1, 2):
        try:
            raw = fetch(url)
            break
        except urllib.error.URLError as e:
            if attempt == 2:
                print(f"[warn] arXiv 查询失败（已重试）：{e}", file=sys.stderr)
                return []
            import time as _t
            _t.sleep(3)   # arXiv 要求相邻请求间隔 ≥3s

    cutoff = date.today() - timedelta(days=days)
    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    out = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"[warn] arXiv 返回无法解析：{e}", file=sys.stderr)
        return []

    for e in root.findall("a:entry", ns):
        aid = (e.findtext("a:id", default="", namespaces=ns) or "").rsplit("/", 1)[-1]
        title = re.sub(r"\s+", " ", e.findtext("a:title", default="", namespaces=ns)).strip()
        pub = e.findtext("a:published", default="", namespaces=ns)[:10]
        comment = (e.findtext("arxiv:comment", default="", namespaces=ns) or "").strip()
        try:
            if pub and date.fromisoformat(pub) < cutoff:
                continue
        except ValueError:
            pass
        out.append({
            "source": "arxiv", "id": f"arXiv:{aid}", "title": title,
            "date": pub, "venue_hint": comment, "doi": "",
        })
        if len(out) >= per_source:
            break
    return out


# ------------------------------------------------------------------ OpenAlex

JOURNAL_ISSN_HINT = {
    "pattern analysis and machine intelligence": "TPAMI",
    "image processing": "TIP",
    "transactions on multimedia": "TMM",
    "neural networks and learning systems": "TNNLS",
    "knowledge and data engineering": "TKDE",
    "robotics": "TRO",
    "geoscience and remote sensing": "TGRS",
    "circuits and systems for video technology": "TCSVT",
    "automation science and engineering": "TASE",
    "robotics and automation letters": "RA-L",
    "visualization and computer graphics": "TVCG",
}


def search_openalex(topic: str, per_source: int, days: int) -> list[dict]:
    since = (date.today() - timedelta(days=days)).isoformat()
    url = ("https://api.openalex.org/works?search=" + urllib.parse.quote(topic)
           + f"&filter=from_publication_date:{since},type:article"
             "&sort=publication_date:desc&per-page=" + str(max(per_source * 3, 30))
           + "&select=doi,title,publication_date,primary_location")
    try:
        data = json.loads(fetch(url).decode("utf-8", "ignore"))
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"[warn] OpenAlex 查询失败：{e}", file=sys.stderr)
        return []

    out = []
    for w in data.get("results", []):
        src = ((w.get("primary_location") or {}).get("source") or {})
        name = src.get("display_name") or ""
        if not name:
            continue
        role, tier, _ = classify(name, w.get("doi") or "")
        if role != "journal":
            continue
        out.append({
            "source": "openalex", "id": w.get("doi") or "(no doi)",
            "title": (w.get("title") or "").strip(),
            "date": w.get("publication_date") or "", "venue_hint": name,
            "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
            "short": next((v for k, v in JOURNAL_ISSN_HINT.items() if k in name.lower()), ""),
        })
        if len(out) >= per_source:
            break
    return out


# ------------------------------------------------------------------ 查重

def known_ids(workspace: pathlib.Path) -> set[str]:
    """用 paper_dedup --list 拿到台账里已登记的标识（失败则返回空集）。"""
    script = workspace / "tools" / "paper_dedup.py"
    if not script.exists():
        return set()
    try:
        r = subprocess.run([sys.executable, str(script), "--list"],
                           capture_output=True, text=True, timeout=60)
        return {x.lower() for x in re.findall(r"[0-9]{4}\.[0-9]{4,5}|10\.\d{4,9}/[^\s,]+",
                                              r.stdout or "")}
    except Exception:  # noqa: BLE001
        return set()


def is_known(p: dict, known: set[str]) -> bool:
    blob = (p.get("id", "") + " " + p.get("doi", "")).lower()
    return any(k and k in blob for k in known)


# ------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser(description="按研究方向检索候选论文")
    ap.add_argument("--topic", required=True, help='研究方向，如 "3D Gaussian Splatting active reconstruction"')
    ap.add_argument("--days", type=int, default=150, help="只看最近 N 天（默认 150）")
    ap.add_argument("--per-source", type=int, default=8, help="每个源最多取多少条（默认 8）")
    ap.add_argument("--workspace", default=".", help="工作区根目录（用于查重）")
    ap.add_argument("--show-known", action="store_true", help="连重复命中也显示（标 ⛔）")
    args = ap.parse_args()

    ws = pathlib.Path(args.workspace).expanduser().resolve()
    known = known_ids(ws)
    print(f"[i] 方向：{args.topic}")
    print(f"[i] 时间窗：最近 {args.days} 天 | 台账已登记标识：{len(known)} 个\n")

    papers = search_arxiv(args.topic, args.per_source, args.days) \
        + search_openalex(args.topic, args.per_source, args.days)
    if not papers:
        print("❌ 两个源都没有返回候选。可能是：网络不可达 / 关键词太窄 / 时间窗太短。", file=sys.stderr)
        print("   建议：放宽 --days、把方向拆成 2~3 个关键词，或直接用 CVF/OpenReview 页面人工检索。",
              file=sys.stderr)
        return 2

    groups: dict[str, list[tuple[dict, str, str]]] = {"journal": [], "conference": [], "unknown": []}
    for p in papers:
        venue = p.get("venue_hint") or ("arXiv" if p["source"] == "arxiv" else "")
        role, tier, _msg = classify(venue, p.get("doi") or p.get("id", ""))
        dup = is_known(p, known)
        if dup and not args.show_known:
            continue
        p["_dup"] = dup
        groups.setdefault(role, []).append((p, tier, venue))

    total = sum(len(v) for v in groups.values())
    if total == 0:
        print("⚠️ 候选全部命中台账（已读过）。放宽 --days 或换关键词。")
        return 3

    TIER_MARK = {"S": "★★★", "A": "★★☆", "B": "★☆☆", "?": "?"}
    for role, title in (("journal", "期刊候选"), ("conference", "会议候选"), ("unknown", "未定/预印本")):
        items = groups.get(role) or []
        if not items:
            continue
        print(f"=== {title}（{len(items)}）===")
        for p, tier, venue in items:
            dup = " ⛔已在台账" if p.get("_dup") else ""
            short = f"[{p['short']}] " if p.get("short") else ""
            print(f"  {TIER_MARK.get(tier, '?')} {p['date']}  {short}{p['title'][:96]}{dup}")
            print(f"        {venue[:90]}")
            print(f"        {p['id']}")
        print()

    print("下一步：")
    print("  1) 从上面各挑 1~2 篇（优先方向相关性，venue 层级只作参考）")
    print("  2) 用 venue_check.py 正式标注并查重：")
    print('     python3 venue_check.py --a-venue "<刊名>" --a-doi "<doi>" --b-venue "<会议>" --b-id "<arXiv ID>"')
    print("  3) 用 pdf_fetch + pdf_extract 取全文，按 SKILL.md 的 8 问精读")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger.py — 维护 论文台账.md（防重复 + 结构校验 + 统计 + 追加登记）。

子命令：
    python3 ledger.py validate [--workspace W]      # 结构/编号/重复/一致性检查
    python3 ledger.py stats    [--workspace W]      # 按层级/年份/标签统计
    python3 ledger.py add --json paper.json         # 追加一篇（索引行 + 详情节）
    python3 ledger.py add --short GAVIS --title "..." --venue "CVPR 2026" \
        --id "arXiv:2605.30342" --link "https://..." --date 10.23 \
        --tags "不确定度 / 可见性场" --relation "方向二直接对标" \
        --conclusion "..." --facts "..." --weakness "..."

设计原则：
  * add 只做**机械插入**（保证编号连续、索引与详情同步），内容由人给；
  * validate 不通过 ⇒ 台账处于不可信状态，先修再选文；
  * 从不删除既有条目（历史不可篡改）；改判通过 §5 版本记录表达。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

DEFAULT_WS = pathlib.Path.home() / ".dsh"


# ------------------------------------------------------------------ 解析

def load(ws: pathlib.Path) -> str:
    p = ws / "论文台账.md"
    if not p.exists():
        sys.exit(f"❌ 找不到台账：{p}")
    return p.read_text(encoding="utf-8")


def parse_entries(text: str) -> list[dict]:
    """解析 §1 索引表（8 列）。"""
    entries = []
    for ln in text.splitlines():
        m = re.match(r"^\|\s*(S?\d+)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|\s*$", ln)
        if not m:
            continue
        num = m.group(1).strip()
        entries.append({
            "num": num, "date": m.group(2).strip(), "short": m.group(3).strip(),
            "venue": m.group(4).strip(), "type": m.group(5).strip(),
            "grade": m.group(6).strip(), "tags": m.group(7).strip(), "relation": m.group(8).strip(),
        })
    return entries


def parse_details(text: str) -> dict[str, dict]:
    """解析 §2 详情节（### #NN 简称 — 标题  + 字段表）。"""
    out: dict[str, dict] = {}
    blocks = re.split(r"^###\s+#(\w+)\s+([^—\n]+)—\s*(.+)$", text, flags=re.M)
    # blocks: [pre, num, short, title, body, num, short, title, body, ...]
    for i in range(1, len(blocks) - 3, 4):
        num, short, title, body = blocks[i], blocks[i + 1].strip(), blocks[i + 2].strip(), blocks[i + 3]
        fields = dict(re.findall(r"^\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*$", body, flags=re.M))
        fields = {k: v for k, v in fields.items() if k not in ("字段", "---", ":--")}
        out[num] = {"short": short, "title": title, "fields": fields, "body": body}
    return out


def numbers(entries: list[dict]) -> tuple[list[int], list[int]]:
    formal = sorted(int(e["num"]) for e in entries if e["num"].isdigit())
    scr = sorted(int(e["num"][1:]) for e in entries if e["num"].startswith("S"))
    return formal, scr


# ------------------------------------------------------------------ validate

REQUIRED_FIELDS = ("出处", "链接", "首次出现", "证据分级", "主题标签")


def cmd_validate(ws: pathlib.Path) -> int:
    text = load(ws)
    entries = parse_entries(text)
    details = parse_details(text)
    formal, scr = numbers(entries)
    problems: list[str] = []

    if not entries:
        problems.append("§1 总索引表没解析到任何条目（表格格式可能被改坏了）")

    # 编号连续性
    if formal and formal != list(range(1, len(formal) + 1)):
        problems.append(f"正式编号不连续：{formal}")
    s_in_index = set(scr)
    s_in_section = {int(x) for x in re.findall(r"^\|\s*S(\d+)\s*\|", text, flags=re.M)
                    if True}
    # §3 的 S 表也会被 §1 的正则扫到；两者取并集后检查是否有"只在 §3"的编号
    if s_in_section and not s_in_section <= s_in_index:
        problems.append(f"§3 有 S 条目未进 §1 索引：{sorted(s_in_section - s_in_index)}")

    # 索引 ↔ 详情 双向一致
    detail_keys = {k.zfill(2) for k in details if k.isdigit()}
    for n in formal:
        if f"{n:02d}" not in detail_keys:
            problems.append(f"#{n:02d} 在索引里但 §2 无详情节")
    for k in details:
        if k.isdigit() and int(k) not in formal:
            problems.append(f"§2 有 #{int(k):02d} 详情，但 §1 索引缺该行")

    # 详情必填字段
    for k, d in details.items():
        if not k.isdigit():
            continue
        missing = [f for f in REQUIRED_FIELDS if not any(f in key for key in d["fields"])]
        if missing:
            problems.append(f"#{int(k):02d} 详情缺字段：{', '.join(missing)}")
        if len(d["title"]) < 12:
            problems.append(f"#{int(k):02d} 标题过短（可能是短名而非完整标题）")

    # 重复：同名/同 ID 出现两次
    for key in ("short",):
        seen: dict[str, str] = {}
        for e in entries:
            v = e[key].strip()
            if not v:
                continue
            if v.lower() in seen:
                problems.append(f"重复 {key}「{v}」：# {seen[v.lower()]} 与 #{e['num']}")
            seen[v.lower()] = e["num"]

    ids = {}
    for e in entries:
        for tok in re.findall(r"\d{4}\.\d{4,5}|10\.\d{4,9}/[^\s|]+", e["venue"]):
            if tok.lower() in ids:
                problems.append(f"重复标识「{tok}」：# {ids[tok.lower()]} 与 #{e['num']}")
            ids[tok.lower()] = e["num"]

    # 头部累计数
    m = re.search(r"已精读\s*\**\s*(\d+)\s*篇", text)
    if m and int(m.group(1)) != len(formal):
        problems.append(f"头部声称已精读 {m.group(1)} 篇，实际正式条目 {len(formal)} 篇")

    print(f"台账：{ws / '论文台账.md'}")
    print(f"  正式条目 {len(formal)} 篇 | S 系列 {len(scr)} 条 | 详情节 {len([k for k in details if k.isdigit()])} 个")
    if problems:
        print(f"\n❌ 发现 {len(problems)} 个问题：")
        for p in problems:
            print("  -", p)
        return 2
    print("\n✅ 结构、编号、索引/详情一致性、重复项、头部计数：全部通过")
    return 0


# ------------------------------------------------------------------ stats

def venue_tier(venue: str) -> str:
    """层级判定复用 venue_check.classify（单一真相源），失败时退回关键词表。"""
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        from venue_check import classify  # noqa: PLC0415
        return classify(venue)[1]
    except Exception:  # noqa: BLE001
        v = venue.lower()
        for tier, pat in (
            ("S", r"tpami|tip|tmm|tnnls|tkde|tse|tro|tgrs|tcsvt|tvcg|cvpr|iccv|neurips|icml|iclr|aaai|ijcai|acl|siggraph"),
            ("A", r"ra-?l|tase|tii|tits|tcss|tdsc|tpds|tmc|tog|eccv|icra|iros|3dv|bmcv|accv|wacv|corl|rss|findings"),
            ("B", r"access|sensors|electronics|neurocomputing|fusion|workshop|arxiv"),
        ):
            if re.search(pat, v):
                return tier
        return "?"


def cmd_stats(ws: pathlib.Path) -> int:
    entries = parse_entries(load(ws))
    formal = [e for e in entries if e["num"].isdigit()]
    if not formal:
        print("台账里还没有正式条目。")
        return 0

    from collections import Counter
    tiers = Counter(venue_tier(e["venue"]) for e in formal)
    years = Counter((re.search(r"20\d\d", e["venue"]).group(0) if re.search(r"20\d\d", e["venue"]) else "?") for e in formal)
    tags = Counter(t.strip() for e in formal for t in re.split(r"[/,、]", e["tags"]) if t.strip())

    print(f"已精读 {len(formal)} 篇\n")
    print("按 venue 层级：", " | ".join(f"{k}:{v}" for k, v in sorted(tiers.items())))
    print("按年份：      ", " | ".join(f"{k}:{v}" for k, v in sorted(years.items())))
    print("\n主题标签出现次数（≥2 次说明已形成线）：")
    for t, c in tags.most_common(12):
        bar = "█" * min(c * 2, 20)
        print(f"  {t:<22} {c:>2}  {bar}")
    return 0


# ------------------------------------------------------------------ add

def cmd_add(ws: pathlib.Path, args) -> int:
    path = ws / "论文台账.md"
    text = load(ws)
    entries = parse_entries(text)
    formal, _ = numbers(entries)
    num = (max(formal) + 1) if formal else 1

    # 去重：同 short 或同 id
    blob = text.lower()
    for probe in filter(None, [args.short, args.id]):
        if probe.lower() in blob:
            print(f"❌ 台账里已存在「{probe}」——拒绝重复登记（用 §5 记版本，不要新增条目）")
            return 3

    tier = venue_tier(args.venue)
    index_row = (f"| {num:02d} | {args.date} | {args.short} | {args.venue} | {args.type} "
                 f"| {args.grade} | {args.tags} | {args.relation} |\n")
    detail = (
        f"\n### #{num:02d} {args.short} — {args.title}\n\n"
        f"| 字段 | 内容 |\n|---|---|\n"
        f"| 作者 | {args.authors} |\n"
        f"| 出处 | {args.venue}（venue 层级 {tier}） |\n"
        f"| 链接 | {args.link or args.id} |\n"
        f"| 首次出现 | {args.date} 早读报告 |\n"
        f"| 证据分级 | {args.grade} |\n"
        f"| 主题标签 | {args.tags} |\n\n"
        f"**一句话结论**：{args.conclusion}\n\n"
        f"**关键事实（可引用）**：\n{args.facts}\n\n"
        f"**弱点**：{args.weakness}\n\n---\n"
    )

    # 插入索引行：§1 表格最后一行之后
    lines = text.splitlines(keepends=True)
    idx_hdr = next(i for i, l in enumerate(lines) if l.startswith("## 1. 总索引"))
    insert_at = idx_hdr
    for i in range(idx_hdr, len(lines)):
        if re.match(r"^\|\s*S?\d+\s*\|", lines[i]):
            insert_at = i + 1
    lines.insert(insert_at, index_row)

    text = "".join(lines)
    # 插入详情：§3 之前
    anchor = "\n## 3. 已筛查但未精读（S 系列）"
    if anchor in text:
        text = text.replace(anchor, detail + anchor, 1)
    else:
        text = text.rstrip() + "\n" + detail

    # 头部累计数
    text = re.sub(r"(已精读\s*\**\s*)(\d+)(\s*篇)", lambda m: f"{m.group(1)}{num}{m.group(3)}", text, count=1)
    path.write_text(text, encoding="utf-8")
    print(f"✅ 已登记 #{num:02d} {args.short}（venue 层级 {tier}）→ {path}")
    return 0


# ------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser(description="论文台账维护")
    ap.add_argument("cmd", choices=["validate", "stats", "add"])
    ap.add_argument("--workspace", default=str(DEFAULT_WS))
    ap.add_argument("--json", help="add: 从 JSON 读字段")
    for f in ("short", "title", "venue", "id", "link", "date", "type", "grade",
              "tags", "relation", "conclusion", "facts", "weakness", "authors"):
        ap.add_argument("--" + f, default="")
    args = ap.parse_args()

    ws = pathlib.Path(args.workspace).expanduser()
    if args.cmd == "validate":
        return cmd_validate(ws)
    if args.cmd == "stats":
        return cmd_stats(ws)

    if args.json:
        data = json.loads(pathlib.Path(args.json).read_text(encoding="utf-8"))
        for k, v in data.items():
            setattr(args, k.replace("-", "_"), v)
    for f in ("short", "title", "venue"):
        if not getattr(args, f):
            ap.error(f"add 需要 --{f}（或用 --json）")
    args.date = args.date or date.today().strftime("%m.%d") if (date := __import__("datetime").date) else args.date
    args.type = args.type or "期刊/会议"
    args.grade = args.grade or "全文精读"
    args.authors = args.authors or "（待补）"
    return cmd_add(ws, args)


if __name__ == "__main__":
    sys.exit(main())

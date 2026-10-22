#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""summarize.py — 从台账生成"文献阅读总结"的骨架 + 自动统计。

用法：
    python3 summarize.py --workspace ~/.dsh                       # 打印到 stdout
    python3 summarize.py --workspace ~/.dsh --out 文献阅读总结.md   # 写文件
    python3 summarize.py --workspace ~/.dsh --since 2026-10-15     # 只看某日期之后

它做两件事，边界很清楚：
  1) **自动**：统计（篇数/层级/年份/标签线/机构）、按主题聚类、时间线、每篇的一句话结论与弱点摘录；
  2) **留空**：跨论文的"共识 / 分歧 / 我的判断"三节只给骨架与提示，
     由人（或 agent）填——**不允许脚本编造综述结论**。
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ledger import parse_details, parse_entries, venue_tier  # noqa: E402


def norm_tag(t: str) -> str:
    return re.sub(r"\s+", "", t.strip().lower())


def main() -> int:
    ap = argparse.ArgumentParser(description="生成文献阅读总结骨架")
    ap.add_argument("--workspace", default=str(pathlib.Path.home() / ".dsh"))
    ap.add_argument("--out", help="输出文件路径；省略则打印到 stdout")
    ap.add_argument("--since", help="只看该日期（MM.DD 或 YYYY-MM-DD）之后的条目")
    args = ap.parse_args()

    ws = pathlib.Path(args.workspace).expanduser()
    ledger = ws / "论文台账.md"
    if not ledger.exists():
        sys.exit(f"❌ 找不到台账：{ledger}")
    text = ledger.read_text(encoding="utf-8")
    entries = [e for e in parse_entries(text) if e["num"].isdigit()]
    details = parse_details(text)

    if args.since:
        want = args.since
        entries = [e for e in entries if e["date"] == want or e["date"].endswith(want[-5:])]
    if not entries:
        sys.exit("❌ 没有可汇总的正式条目")

    # ---------- 自动统计 ----------
    tiers = Counter(venue_tier(e["venue"]) for e in entries)
    years = Counter((re.search(r"20\d\d", e["venue"]).group(0)
                     if re.search(r"20\d\d", e["venue"]) else "未标注年份") for e in entries)
    tag_counter: Counter[str] = Counter()
    tag_index: dict[str, list[str]] = defaultdict(list)
    display: dict[str, str] = {}          # 归一化 key -> 首次出现的原始写法
    for e in entries:
        for t in re.split(r"[/,、]", e["tags"]):
            t = t.strip()
            if not t:
                continue
            k = norm_tag(t)
            display.setdefault(k, t)      # 保留原始大小写（NBV / LLM / Agent）
            tag_counter[k] += 1
            tag_index[k].append(e["num"])

    out: list[str] = []
    add = out.append

    add(f"# 文献阅读总结（截至 {date.today().isoformat()}）\n")
    add(f"> 自动生成自 `论文台账.md`（{len(entries)} 篇正式条目）；"
        f"标注 `[自动]` 的部分由脚本统计，`[待填]` 的部分必须由人/agent 判断后补写。\n")
    add("## 0. 台账状态\n")
    add(f"- 正式精读：**{len(entries)} 篇**；S 系列（已筛查未精读）："
        f"{len([e for e in parse_entries(text) if e['num'].startswith('S')])} 条")
    add(f"- venue 层级分布 [自动]：**" + " | ".join(f"{k}:{v}" for k, v in sorted(tiers.items())) + "**")
    add(f"- 年份分布 [自动]：**" + " | ".join(f"{k}:{v}" for k, v in sorted(years.items())) + "**")
    add("")

    add("## 1. 主题线（按标签聚类）[自动]\n")
    add("| 主题 | 篇数 | 涉及条目 |")
    add("|---|---|---|")
    for tag, nums in sorted(tag_index.items(), key=lambda kv: -len(kv[1])):
        if len(nums) < 1:
            continue
        add(f"| {display.get(tag, tag)} | {len(nums)} | {', '.join('#' + n for n in nums)} |")
    add("")
    add("> 篇数 ≥2 的标签说明已形成主线；篇数=1 的多为孤立论文，考虑是否值得继续深入。\n")

    add("## 2. 逐篇速览（一句话结论 + 弱点）[自动摘录]\n")
    for e in entries:
        d = details.get(e["num"].zfill(2)) or {}
        body = d.get("body") or ""
        concl = re.search(r"\*\*一句话结论\*\*[：:]\s*(.+)", body)
        weak = re.search(r"\*\*弱点\*\*[：:]\s*(.+)", body)
        add(f"### #{e['num']} {e['short']} — {e['venue']}（{venue_tier(e['venue'])} 层）")
        add(f"- 关系：{e['relation']}｜标签：{e['tags']}")
        add(f"- 结论：{concl.group(1).strip() if concl else '（台账未写，需补）'}")
        w = weak.group(1).strip() if weak else '（台账未写，需补）'
        add(f"- 弱点：{w[:220]}{'…' if len(w) > 220 else ''}")
        add("")

    add("## 3. 共识与分歧 `[待填]`\n")
    add("> 只写**多篇论文互相印证或互相矛盾**的判断，每条给出处编号。示例格式：\n")
    add("> - **共识**：<判断>（#NN、#NN 独立得出同一结论；证据：<具体实验/数字>）\n")
    add("> - **分歧**：<A 说 X，#NN；B 说 ¬X，#NN>；我的判断：<倾向谁、依据什么、还缺什么证据>\n")
    add("")

    add("## 4. 技术路线的演进 `[待填]`\n")
    add("> 按时间或范式画出 2~4 条路线（例如：启发式 → 信息增益 → 学策略），每条写：\n")
    add("> 起点（#NN）→ 关键改进（#NN）→ 当前 SOTA（#NN）→ 该路线失效的地方。\n")
    add("")

    add("## 5. 仍开放的空白（与台账 §4 联动）[自动搬运 + 待填]\n")
    sec4 = re.search(r"## 4\. 空白声明状态.*?\n(\|.*?)\n\n", text, flags=re.S)
    if sec4:
        add(sec4.group(1).strip())
        add("")
    add("> `[待填]`：结合上面的一致性/分歧，指出**最值得投入的一条空白**，并给出理由与第一步实验。\n")

    add("## 6. 阅读路径建议 `[待填]`\n")
    add("> 给新入门的自己（或合作者）一条 3~5 步路径：先读哪篇建立直觉、再读哪篇理解方法、最后读哪篇看边界。\n")

    text_out = "\n".join(out) + "\n"
    if args.out:
        p = pathlib.Path(args.out)
        if not p.is_absolute():
            p = ws / p
        p.write_text(text_out, encoding="utf-8")
        print(f"✅ 已生成：{p}（{len(out)} 行，{len(entries)} 篇）")
        print("   下一步：把 §3/§4/§5/§6 的 `[待填]` 补齐（脚本不会替你下结论）")
    else:
        print(text_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

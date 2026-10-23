#!/usr/bin/env python3
"""Turn the 问题卡 block of an early-read report into a card readproof can ingest.

The card is the only artefact of an early-read that feeds the problem graph, so this
script is deliberately strict about two things:

1. **Every entry needs a vocabulary id and a location.** An id without a location is a
   recollection; a location without an id cannot be connected to anything.
2. **Every entry needs an evidence grade** (E1–E5). `E1` may be written as "作者承认";
   `E3`–`E5` are our own observation and must not borrow that phrasing. This is the one
   rule in the whole pipeline that is easiest to break while feeling honest.

It resolves nothing on its own: mapping a phrase to a canonical id is a human decision,
because that is exactly where a graph forks one concept into two nodes.

Usage
  cards.py check  report.md                 # validate the card block(s)
  cards.py emit   report.md [-o card.json]  # emit readproof-compatible JSON
  cards.py emit   report.md --paper 07      # pick one card out of a multi-paper report

Exit codes
  0 ok · 2 the card block is invalid · 1 file/parse error
"""

import json
import os
import re
import sys

EXIT_OK = 0
EXIT_INVALID = 2

#: relation labels as they appear in reports -> readproof relation names
RELATIONS = {
    "解决": "solves",
    "解决的问题": "solves",
    "solves": "solves",
    "遗留": "leaves_open",
    "遗留问题": "leaves_open",
    "未解": "leaves_open",
    "leaves open": "leaves_open",
    "leaves_open": "leaves_open",
    "假设": "assumes",
    "assumes": "assumes",
    "局限": "admits",
    "承认的局限": "admits",
    "admits": "admits",
    "批评": "criticizes",
    "criticizes": "criticizes",
    "异常": "anomaly",
    "anomaly": "anomaly",
}

CARD_HEADING = re.compile(r"^#{2,4}\s*问题卡\s*#?(?P<paper>[0-9A-Za-z]+)?", re.IGNORECASE)
ITEM = re.compile(r"^\s*[-*]\s*(?P<body>.+?)\s*$")
NODE_ID = re.compile(r"\b(?P<id>[PLAM]-(?:SCALE|ROBUST|ASSUME|THEORY|EVAL|ENGINEER)-\d{2})\b")
GRADE = re.compile(r"\bE(?P<grade>[1-5])\b")
COMPARED_NO = ("未对比", "没有对比", "not compared", "uncompared")
COMPARED_YES = ("已对比", "对比过", "compared")

GRADE_MEANING = {
    "E1": "paper states it itself",
    "E2": "paper's criticism of prior work",
    "E3": "we observe it (experiments avoid it)",
    "E4": "a later survey says so",
    "E5": "our inference",
}


class CardError(Exception):
    exit_code = EXIT_INVALID


def _label_relation(label):
    key = label.strip().lower().rstrip(":：")
    if key in RELATIONS:
        return RELATIONS[key]
    for name, relation in RELATIONS.items():
        if key.startswith(name):
            return relation
    return None


def parse_card_block(lines):
    """Parse one card block. Returns ``(paper_id, card, problems)``."""
    paper = ""
    entries = []
    for line in lines:
        heading = CARD_HEADING.match(line)
        if heading:
            paper = heading.group("paper") or ""
            continue
        item = ITEM.match(line)
        if not item:
            continue
        body = item.group("body")
        if "：" in body or ":" in body:
            separator = "：" if "：" in body else ":"
            label, _, rest = body.partition(separator)
        else:
            label, rest = "", body
        relation = _label_relation(label) if label else None
        entries.append({"label": label, "relation": relation, "text": rest.strip()})

    card = {}
    problems = []
    for entry in entries:
        relation = entry["relation"]
        text = entry["text"]
        if relation is None:
            problems.append("unknown relation label %r in %r" % (entry["label"], text))
            continue

        if relation == "anomaly":
            loc, _, note = text.partition("=")
            if not note.strip():
                problems.append("anomaly needs `loc=note`, got %r" % text)
                continue
            card.setdefault("anomaly", []).append(
                {"loc": loc.strip(), "note": note.strip()}
            )
            continue

        node = NODE_ID.search(text)
        if not node:
            problems.append(
                "%s entry has no vocabulary id: %r (map it first; never invent one)"
                % (relation, text)
            )
            continue
        loc = ""
        if "@" in text:
            loc = text.split("@", 1)[1]
            loc = NODE_ID.sub("", loc)
            loc = GRADE.sub("", loc)
            loc = re.sub(r"[（(][^)）]*[)）]", "", loc)
            loc = loc.strip(" ，,、；;")

        # Report everything wrong with the entry at once: fixing one omission only to
        # be told about the next is how people give up on a format.
        grade = GRADE.search(text)
        faults = []
        if not loc:
            faults.append("no location (an edge without a location is a recollection)")
        if not grade:
            faults.append("no evidence grade (E1–E5)")
        if faults:
            for fault in faults:
                problems.append(
                    "%s %s: %s" % (relation, node.group("id"), fault)
                )
            continue

        payload = {
            "node": node.group("id"),
            "loc": loc,
            "evidence": "E%s" % grade.group("grade"),
        }
        if relation == "criticizes":
            lowered = text.lower()
            if any(marker in text or marker in lowered for marker in COMPARED_NO):
                payload["compared"] = False
            elif any(marker in text or marker in lowered for marker in COMPARED_YES):
                payload["compared"] = True
        card.setdefault(relation, []).append(payload)

    return paper, card, problems


def split_cards(text):
    """Split a report into ``[(paper_id, [lines])]`` — one entry per card block."""
    blocks = []
    current = None
    for line in text.splitlines():
        if CARD_HEADING.match(line):
            current = [line]
            blocks.append(current)
        elif current is not None:
            current.append(line)
    return blocks


def collect(text, paper=None):
    """Return ``(cards, problems)`` for every card block in ``text``."""
    cards = []
    problems = []
    blocks = split_cards(text)
    if not blocks:
        problems.append(
            "no 问题卡 block found; add one per paper (see 早读报告_SOP.md §5.6)"
        )
        return cards, problems
    for lines in blocks:
        block_paper, card, block_problems = parse_card_block(lines)
        if paper and block_paper and block_paper != paper:
            continue
        problems.extend(block_problems)
        if card:
            cards.append({"paper": block_paper or paper or "", "card": card})
    return cards, problems


def render(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2)


def main(argv):
    if len(argv) < 3:
        sys.stderr.write(__doc__)
        return 1
    action, path = argv[1], argv[2]
    paper = None
    out = None
    index = 3
    while index < len(argv):
        if argv[index] == "--paper" and index + 1 < len(argv):
            paper = argv[index + 1]
            index += 2
        elif argv[index] in ("-o", "--out") and index + 1 < len(argv):
            out = argv[index + 1]
            index += 2
        else:
            sys.stderr.write("unknown argument: %s\n" % argv[index])
            return 1

    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        sys.stderr.write("cannot read %s: %s\n" % (path, exc))
        return 1

    cards, problems = collect(text, paper=paper)

    if action == "check":
        if problems:
            for problem in problems:
                print("INVALID: %s" % problem, file=sys.stderr)
            return EXIT_INVALID
        for item in cards:
            counts = ", ".join("%s=%d" % (k, len(v)) for k, v in sorted(item["card"].items()))
            print("ok  %s: %s" % (item["paper"] or "(unlabelled)", counts))
        return EXIT_OK

    if action == "emit":
        if problems:
            for problem in problems:
                print("INVALID: %s" % problem, file=sys.stderr)
            return EXIT_INVALID
        if not cards:
            print("no card for paper %r" % paper, file=sys.stderr)
            return 1
        payload = cards[0]["card"] if len(cards) == 1 else [c["card"] for c in cards]
        text_out = render(payload)
        if out:
            with open(out, "w", encoding="utf-8") as handle:
                handle.write(text_out + "\n")
            print("wrote %s" % out)
        else:
            print(text_out)
        return EXIT_OK

    sys.stderr.write("unknown action %r (use check or emit)\n" % action)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

#!/usr/bin/env python3
"""Check this documentation repository against its own rules.

Usage:

    python3 scripts/check_manual.py [--root PATH] [--only a,b,c] [--require-all]
    python3 scripts/check_manual.py moved BASE HEAD [--root PATH] [-- PATH ...]

The first form runs the ten checks and prints one line per check, in a
fixed order. The second form compares the Markdown paragraphs of two git
revisions.

Rules shared by all checks:

- A problem is one line of text, usually "path:line: message". The path is
  relative to the root and uses forward slashes.
- A check that inspects zero items fails with the problem "inspected
  nothing". There is no exception.
- The checker reads every "*.md" file under the root, at any depth. It
  skips every directory whose name starts with a dot, such as ".git/" and
  ".remember/". Other files, such as LICENSE, are never read.
- "Prose" is the text of a Markdown file with these parts removed: fenced
  code blocks (fence lines included), inline code spans, link targets, and
  table separator rows. A link "[text](target)" becomes "text". Removed
  lines stay as blank lines, so line numbers do not move. A "prose line" is
  a line of prose that is not blank.
- A section of FIELD-MANUAL.md is a line "## N. Title". Section N runs to
  the next "## " heading.
- A date "YYYY-MM" has a month from 01 to 12.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import os
import pathlib
import re
import subprocess
import sys
import urllib.parse

NOT_RUN = None

PRACTICE_SECTIONS = range(1, 12)
GLANCE_SECTION = 12

MANUAL = "FIELD-MANUAL.md"
CONTRACT = "AGENT-CONTRACT.md"
LEDGER = "INCIDENTS.md"


@dataclasses.dataclass
class Result:
    """What one check found.

    items: how many things the check inspected.
    problems: one line of text per rule broken.
    """

    items: int
    problems: list[str] = dataclasses.field(default_factory=list)


SHARED_LISTS = {
    "authority-order": [
        {"file": "METHOD.md", "kind": "list", "after": r"^Use this authority order:"},
        {"file": "FIELD-MANUAL.md", "kind": "list", "after": r"^When signals disagree, use an authority order"},
        {"file": "AGENT-CONTRACT.md", "kind": "list", "after": r"^When sources disagree, use this order:"},
        {"file": "STARTER-CLAUDE-MD.md", "kind": "list", "after": r"^## Authority order",
         "replace": [("This file", "The project guide")]},
    ],
    "stop-list": [
        {"file": "AGENT-CONTRACT.md", "kind": "list", "after": r"^Stop and ask the human before:"},
        {"file": "FIELD-MANUAL.md", "kind": "list", "after": r"^Most agent work is reversible"},
        {"file": "STARTER-CLAUDE-MD.md", "kind": "list", "after": r"^- Stop and ask before:"},
    ],
    "review-order": [
        {"file": "METHOD.md", "kind": "list", "after": r"^Run review in this order:"},
        {"file": "AGENT-CONTRACT.md", "kind": "list", "after": r"^Check in this order:"},
        {"file": "STARTER-CLAUDE-MD.md", "kind": "list", "after": r"^- Review order:"},
    ],
    "proof-levels": [
        {"file": "METHOD.md", "kind": "list", "after": r"^Useful proof levels are:"},
        {"file": "templates/claims-proof-matrix.md", "kind": "list", "after": r"^## Status definitions"},
    ],
    "result-states": [
        {"file": "FIELD-MANUAL.md", "kind": "inline", "pattern": r"^\| Result \| One check \| (.+?) \|$"},
        {"file": "METHOD.md", "kind": "inline", "pattern": r"Use explicit states: (.+?)\."},
        {"file": "AGENT-CONTRACT.md", "kind": "inline", "pattern": r"Use explicit states: (.+?)\."},
    ],
    "reporting-names": [
        {"file": "AGENT-CONTRACT.md", "kind": "inline", "pattern": r"Report validation with explicit states: (.+?)\."},
        {"file": "STARTER-CLAUDE-MD.md", "kind": "inline", "pattern": r"Validation reports use exact states: (.+?)\."},
    ],
    "rule-names": [
        {"file": "METHOD.md", "kind": "headings", "section": r"^## 3\. "},
        {"file": "AGENT-CONTRACT.md", "kind": "list", "after": r"^These are the rules of section 3",
         "match": "startswith"},
    ],
}


# Reading Markdown

FENCE = re.compile(r"^\s*(`{3,})(.*)$")
CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]*)(?:\s+\"[^\"]*\")?\)")
TABLE_SEPARATOR = re.compile(r"\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
SECTION = re.compile(r"^(\d+)\. ")
CITATION = re.compile(r"\((S\d+(?:,\s*S\d+)*)\)")
DATE = r"\d{4}-(?:0[1-9]|1[0-2])"
LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")


def split_lines(text: str) -> list[str]:
    """Split text into lines without a final empty line."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [line.rstrip("\r") for line in lines]


def scan_fences(lines: list[str]):
    """Find fenced blocks.

    Returns (code, blocks). code[i] is true when line i belongs to a block,
    fence lines included. Each block is (open_index, close_index, ticks,
    info), with close_index None when the file ends inside the block.
    """
    code = [False] * len(lines)
    blocks = []
    opened = None
    for index, line in enumerate(lines):
        match = FENCE.match(line)
        if opened is None:
            if match and "`" not in match.group(2):
                opened = (index, len(match.group(1)), match.group(2).strip())
                code[index] = True
            continue
        code[index] = True
        if match and len(match.group(1)) >= opened[1] and match.group(2).strip() == "":
            blocks.append((opened[0], index, opened[1], opened[2]))
            opened = None
    if opened is not None:
        blocks.append((opened[0], None, opened[1], opened[2]))
    return code, blocks


class Doc:
    """One Markdown file: its lines, code flags, prose, and headings."""

    def __init__(self, root: pathlib.Path, path: pathlib.Path):
        self.path = path
        self.rel = path.relative_to(root).as_posix()
        self.lines = split_lines(path.read_text(encoding="utf-8"))
        self.code, self.blocks = scan_fences(self.lines)
        self.prose = ["" if self.code[i] else prose_line(line) for i, line in enumerate(self.lines)]
        self.headings = []
        counts = collections.Counter()
        for index, line in enumerate(self.lines):
            if self.code[index]:
                continue
            match = HEADING.match(line)
            if not match:
                continue
            text = re.sub(r"\s+#+$", "", match.group(2))
            base = slug(text)
            number = counts[base]
            counts[base] += 1
            self.headings.append((index, len(match.group(1)), text, f"{base}-{number}" if number else base))

    def slugs(self) -> set[str]:
        return {heading[3] for heading in self.headings}

    def where(self, index: int) -> str:
        return f"{self.rel}:{index + 1}"


def strip_code_spans(line: str) -> str:
    return CODE_SPAN.sub("", line)


def prose_line(line: str) -> str:
    """Return the prose of one line that is outside fenced code."""
    stripped = line.strip()
    if "|" in stripped and "-" in stripped and TABLE_SEPARATOR.fullmatch(stripped):
        return ""
    return LINK.sub(lambda match: match.group(1), strip_code_spans(line))


def slug(text: str) -> str:
    """Return GitHub's slug for a heading, before repeat numbering."""
    text = LINK.sub(lambda match: match.group(1), text).lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def markdown_files(root: pathlib.Path) -> list[pathlib.Path]:
    """Every "*.md" file under root, skipping directories that start with a dot."""
    found = []
    for directory, subdirs, files in os.walk(root):
        subdirs[:] = sorted(name for name in subdirs if not name.startswith("."))
        for name in sorted(files):
            if name.endswith(".md"):
                found.append(pathlib.Path(directory) / name)
    return found


def load(root: pathlib.Path, rel: str) -> Doc | None:
    """Load one file under root, or None when it is missing or outside root."""
    path = inside(root, root / rel)
    if path is None or not path.is_file():
        return None
    return Doc(root, path)


def inside(root: pathlib.Path, path: pathlib.Path) -> pathlib.Path | None:
    """Return the normalized path when it lies within root, else None."""
    normal = pathlib.Path(os.path.normpath(path))
    if normal == root or root in normal.parents:
        return normal
    return None


def sections(doc: Doc | None) -> set[int]:
    """The section numbers of a manual."""
    if doc is None:
        return set()
    found = set()
    for _, level, text, _ in doc.headings:
        match = SECTION.match(text)
        if level == 2 and match:
            found.add(int(match.group(1)))
    return found


def heading_sections(doc: Doc):
    """Yield (index, level, text, slug, section) for every heading.

    section is the number of the "## N. " section the heading sits in, or
    None outside numbered sections.
    """
    current = None
    for index, level, text, heading_slug in doc.headings:
        if level == 2:
            match = SECTION.match(text)
            current = int(match.group(1)) if match else None
        yield index, level, text, heading_slug, current


def section_range(doc: Doc, number: int, stop_at_rule: bool):
    """Return (start, end) line indexes of section N, or None.

    The section runs from its heading to the next "## " heading, or to a
    "---" line when stop_at_rule is true.
    """
    start = None
    for index, level, text, _ in doc.headings:
        if level == 2 and start is None and text.startswith(f"{number}. "):
            start = index
    if start is None:
        return None
    for index in range(start + 1, len(doc.lines)):
        if doc.code[index]:
            continue
        line = doc.lines[index]
        if line.startswith("## ") or (stop_at_rule and line.strip() == "---"):
            return start, index
    return start, len(doc.lines)


def finish(items: int, problems: list[str]) -> Result:
    if items == 0 and "inspected nothing" not in problems:
        problems.append("inspected nothing")
    return Result(items=items, problems=problems)


# 1. links

WEB = re.compile(r"^(?:https?|mailto):", re.IGNORECASE)


def check_links(root: pathlib.Path) -> Result | None:
    """Check links and section references.

    Items: every Markdown link "[text](target)" outside code, in every
    file, and every bare section reference. Links to http:, https:, and
    mailto: count as items but are not followed.

    - A target that starts with "/" or resolves outside the root fails,
      and the checker never opens it.
      Problem: "path:line: link target is outside the repository: TARGET".
    - Any other target must name a file or a directory that exists,
      relative to the file that holds the link. A directory counts,
      because the repository links to "templates" and "examples".
      Problem: "path:line: link target does not exist: TARGET".
    - A "#fragment" must equal the slug of a heading in the target file.
      A target of only "#fragment" points into the same file. Headings
      inside fenced code are not headings. Slugs follow GitHub's rule,
      with "-1", "-2" for repeats over the whole file.
      Problem: "path:line: no heading for fragment: TARGET".
    - In FIELD-MANUAL.md, each "§N" in prose must name an existing
      section. In any other file, each "FIELD-MANUAL.md, section N" in
      prose must do the same.
      Problem: "path:line: no section N in FIELD-MANUAL.md".
    """
    root = pathlib.Path(os.path.abspath(root))
    docs = {}

    def doc_for(path: pathlib.Path) -> Doc | None:
        if path not in docs:
            docs[path] = Doc(root, path) if path.is_file() and path.suffix == ".md" else None
        return docs[path]

    manual_sections = sections(load(root, MANUAL))
    items = 0
    problems = []
    for path in markdown_files(root):
        doc = doc_for(path)
        for index, line in enumerate(doc.lines):
            if doc.code[index]:
                continue
            for match in LINK.finditer(strip_code_spans(line)):
                items += 1
                problem = link_problem(root, doc, match.group(2), doc_for)
                if problem:
                    problems.append(f"{doc.where(index)}: {problem}")
            if doc.rel == MANUAL:
                numbers = re.findall(r"§(\d+)", doc.prose[index])
            else:
                numbers = re.findall(r"FIELD-MANUAL\.md, section (\d+)", doc.prose[index])
            for number in numbers:
                items += 1
                if int(number) not in manual_sections:
                    problems.append(f"{doc.where(index)}: no section {number} in {MANUAL}")
    return finish(items, problems)


def link_problem(root, doc, target, doc_for) -> str | None:
    """Return the problem with one link target, or None."""
    if WEB.match(target):
        return None
    file_part, has_fragment, fragment = target.partition("#")
    if file_part.startswith("/"):
        return f"link target is outside the repository: {target}"
    if file_part:
        dest = inside(root, doc.path.parent / urllib.parse.unquote(file_part))
        if dest is None:
            return f"link target is outside the repository: {target}"
        if not dest.exists():
            return f"link target does not exist: {target}"
    else:
        dest = doc.path
    if has_fragment:
        target_doc = doc_for(dest)
        if target_doc is None or fragment not in target_doc.slugs():
            return f"no heading for fragment: {target}"
    return None


# 2. fences


def check_fences(root: pathlib.Path) -> Result | None:
    """Check fenced code blocks.

    Items: every line that opens or closes a block. A backtick run that
    is only content inside an open block is not an item. Leading spaces
    before a fence are allowed. Trailing spaces after a closing fence are
    ignored.

    - A line of three or more backticks opens a block. Only a line of at
      least as many backticks, with nothing after them, closes it.
    - A file must not end inside an open block.
      Problem: "path:line: block opened here is never closed".
    - A block whose info string starts with the word "markdown" or "md",
      in any letter case, must open with four or more backticks.
      Problem: "path:line: a markdown example block needs a fence of four
      or more backticks".
    """
    root = pathlib.Path(os.path.abspath(root))
    items = 0
    problems = []
    for path in markdown_files(root):
        doc = Doc(root, path)
        for opened, closed, ticks, info in doc.blocks:
            items += 1 if closed is None else 2
            words = info.split()
            if words and words[0].lower() in ("markdown", "md") and ticks < 4:
                problems.append(
                    f"{doc.where(opened)}: a markdown example block needs a fence of four or more backticks"
                )
            if closed is None:
                problems.append(f"{doc.where(opened)}: block opened here is never closed")
    return finish(items, problems)


# 3. punctuation

FORBIDDEN = ("\u2014", "\u2013", "\u2018", "\u2019", "\u201c", "\u201d")


def doubled_hyphen(line: str) -> bool:
    """True when a run of two or more hyphens is used as punctuation."""
    if re.fullmatch(r"[-\s]+", line):
        return False
    for match in re.finditer(r"-{2,}", line):
        before = line[match.start() - 1] if match.start() > 0 else None
        after = line[match.end()] if match.end() < len(line) else None
        if (before is None or before.isspace()) and (after is None or after.isspace()):
            return True
        if before is not None and after is not None and re.match(r"\w", before) and re.match(r"\w", after):
            return True
    return False


def check_punctuation(root: pathlib.Path) -> Result | None:
    """Check prose punctuation.

    Items: every prose line in every file.

    - No em dash (U+2014), en dash (U+2013), or curly quote (U+2018,
      U+2019, U+201C, U+201D). One problem per character per line.
      Problem: "path:line: forbidden character U+2014".
    - No doubled hyphen as punctuation: a run of two or more hyphens with
      a space or a line edge on each side, or with a word character on
      each side. One problem per line.
      Problem: "path:line: doubled hyphen used as punctuation".
    - A line that holds only hyphens and spaces (rules and front matter
      delimiters) and table separator rows are never flagged.
    """
    root = pathlib.Path(os.path.abspath(root))
    items = 0
    problems = []
    for path in markdown_files(root):
        doc = Doc(root, path)
        for index, line in enumerate(doc.prose):
            if not line.strip():
                continue
            items += 1
            for char in FORBIDDEN:
                if char in line:
                    problems.append(f"{doc.where(index)}: forbidden character U+{ord(char):04X}")
            if doubled_hyphen(line):
                problems.append(f"{doc.where(index)}: doubled hyphen used as punctuation")
    return finish(items, problems)


# 4. sources

ENTRY_SHAPE = re.compile(
    r"^\s*[-*+]\s+\*\*S\d+\.\*\* \[[^\]]+\]\(https?://[^)\s]+\) \([^)]+\)\. "
    r"Supports .*: \".+\"\. Read " + DATE + r"\.$"
)
ENTRY_KEY = re.compile(r"^\s*[-*+]\s+\*\*(S\d+)\.\*\*")
SECTION_NAMES = re.compile(r"\bsections? (\d+(?:(?:,\s*|,?\s+and\s+)\d+)*)")


def supported_sections(entry: str) -> list[int]:
    """The section numbers named after "Supports", with quoted passages removed."""
    match = re.search(r"\bSupports\b(.*)", entry)
    if not match:
        return []
    phrase = re.sub(r'"[^"]*"', "", match.group(1))
    numbers = []
    for group in SECTION_NAMES.finditer(phrase):
        numbers.extend(int(number) for number in re.findall(r"\d+", group.group(1)))
    return numbers


def check_sources(root: pathlib.Path) -> Result | None:
    """Check the source list of FIELD-MANUAL.md and its citations.

    The section starts at the line "## Sources" and ends at the next "## "
    heading or a "---" line. Each list item in it is an entry. Items:
    every entry, plus every citation group such as "(S3)" or "(S2, S3)"
    in the prose above "## Sources". A group counts as one item.

    - An entry has the shape: a bold key "**S3.**", a link, a
      parenthesis, the word "Supports", at least one quoted passage, and
      a final "Read YYYY-MM.".
      Problem: "FIELD-MANUAL.md:line: source entry does not match the
      required shape".
      An entry whose key can still be read counts for the key rules.
    - Keys are unique.
      Problem: "FIELD-MANUAL.md:line: duplicate source key S3".
    - Every "section N" or "sections N, M, and K" after "Supports" must
      name an existing section. Quoted passages are removed first, so a
      quote that holds "section 9" names nothing.
      Problem: "FIELD-MANUAL.md:line: source S3 names missing section N".
    - Every cited key has an entry.
      Problem: "FIELD-MANUAL.md:line: citation S9 has no source entry".
    - Every entry is cited at least once.
      Problem: "FIELD-MANUAL.md:line: source S3 is never cited".
    """
    root = pathlib.Path(os.path.abspath(root))
    doc = load(root, MANUAL)
    if doc is None:
        return finish(0, [])
    start = next((i for i, line in enumerate(doc.lines) if line == "## Sources" and not doc.code[i]), None)
    if start is None:
        return finish(0, [])
    end = len(doc.lines)
    for index in range(start + 1, len(doc.lines)):
        line = doc.lines[index]
        if not doc.code[index] and (line.startswith("## ") or line.strip() == "---"):
            end = index
            break
    known = sections(doc)
    items = 0
    problems = []
    first_line = {}
    for index in range(start + 1, end):
        line = doc.lines[index]
        if doc.code[index] or not LIST_ITEM.match(line):
            continue
        items += 1
        where = doc.where(index)
        if not ENTRY_SHAPE.match(line):
            problems.append(f"{where}: source entry does not match the required shape")
        key_match = ENTRY_KEY.match(line)
        if not key_match:
            continue
        key = key_match.group(1)
        if key in first_line:
            problems.append(f"{where}: duplicate source key {key}")
        else:
            first_line[key] = index
        for number in supported_sections(line):
            if number not in known:
                problems.append(f"{where}: source {key} names missing section {number}")
    cited = set()
    for index in range(start):
        for group in CITATION.finditer(doc.prose[index]):
            items += 1
            for key in re.findall(r"S\d+", group.group(1)):
                cited.add(key)
                if key not in first_line:
                    problems.append(f"{doc.where(index)}: citation {key} has no source entry")
    for key, index in first_line.items():
        if key not in cited:
            problems.append(f"{doc.where(index)}: source {key} is never cited")
    return finish(items, problems)


# 5. evidence and 6. ledger

EVIDENCE = re.compile(r"^\*Evidence: (.+)\.\*$")
TAGS = ("converged", "researched", "observed", "incident", "incident (undated)")
ENTRY_HEADING = re.compile(r"^## (I-\d+): \S")
FIELD = re.compile(r"^(When|What happened|Rule|Supports|Record):\s*(.*)$")
FIELDS = ["When", "What happened", "Rule", "Supports", "Record"]
SUPPORTS = re.compile(r'^(\S+), ("[^"]+"(?: and "[^"]+")*)$')


def parse_ledger(doc: Doc):
    """Split a ledger into entries and stray "## " headings.

    Returns (entries, stray). Each entry is a dict with id, index, and
    items (the text of each list item, whitespace collapsed). Each stray
    heading is (index, text).
    """
    entries = []
    stray = []
    current = None
    for index, line in enumerate(doc.lines):
        if doc.code[index]:
            continue
        if line.startswith("## "):
            match = ENTRY_HEADING.match(line)
            if match:
                current = {"id": match.group(1), "index": index, "items": []}
                entries.append(current)
            else:
                stray.append((index, line[3:].strip()))
                current = None
            continue
        if current is None or not line.strip():
            continue
        if line.startswith("- "):
            current["items"].append(line[2:])
        elif current["items"]:
            current["items"][-1] += " " + line
    for entry in entries:
        entry["items"] = [" ".join(item.split()) for item in entry["items"]]
        entry["fields"] = {}
        names = []
        for item in entry["items"]:
            match = FIELD.match(item)
            names.append(match.group(1) if match else None)
            if match:
                entry["fields"][match.group(1)] = match.group(2).strip()
        entry["ordered"] = names == FIELDS
    return entries, stray


def supported_headings(value: str):
    """Return (file, [headings]) from a Supports value, or None."""
    match = SUPPORTS.match(value)
    if not match:
        return None
    return match.group(1), re.findall(r'"([^"]+)"', match.group(2))


def is_dated(when: str) -> bool:
    return re.fullmatch(DATE, when) is not None


def check_evidence(root: pathlib.Path) -> Result | None:
    """Check the evidence line of every practice in FIELD-MANUAL.md.

    Items: every "### " heading inside sections 1 to 11. A practice is the
    heading plus its text up to the next heading of any level. Line
    numbers in problems are the heading line.

    - The first non-blank line after the heading is "*Evidence: tag, tag.*".
      Problem: 'practice "H" has no evidence line'.
    - Tags are converged, researched, observed, incident, incident
      (undated). Problem: 'practice "H" has unknown evidence tag "T"'.
    - incident and incident (undated) never appear together.
      Problem: 'practice "H" has both incident and incident (undated)'.
      The date rules below are then skipped.
    - researched or converged needs a citation in the practice's own text.
      Problem: 'practice "H" is tagged researched but cites no source'.
    - incident or incident (undated) needs a ledger entry in INCIDENTS.md
      whose Supports names FIELD-MANUAL.md and this heading.
      Problem: 'practice "H" is tagged incident but no ledger entry names it'.
    - incident needs at least one dated entry. Problem: 'practice "H" is
      tagged incident but no ledger entry naming it has a date; use
      incident (undated)'.
    - incident (undated) needs no dated entry. Problem: 'practice "H" is
      tagged incident (undated) but a ledger entry naming it has a date;
      use incident'.
    """
    root = pathlib.Path(os.path.abspath(root))
    doc = load(root, MANUAL)
    if doc is None:
        return finish(0, [])
    named = collections.defaultdict(list)
    ledger = load(root, LEDGER)
    if ledger is not None:
        for entry in parse_ledger(ledger)[0]:
            supports = supported_headings(entry["fields"].get("Supports", ""))
            if supports and supports[0] == MANUAL:
                for heading in supports[1]:
                    named[heading].append(is_dated(entry["fields"].get("When", "")))
    heading_lines = [heading[0] for heading in doc.headings]
    items = 0
    problems = []
    for index, level, text, _, section in heading_sections(doc):
        if level != 3 or section not in PRACTICE_SECTIONS:
            continue
        items += 1
        later = [line for line in heading_lines if line > index]
        end = later[0] if later else len(doc.lines)
        body = range(index + 1, end)
        where = doc.where(index)
        first = next((doc.lines[i] for i in body if doc.lines[i].strip()), "")
        match = EVIDENCE.match(first.strip())
        if not match:
            problems.append(f'{where}: practice "{text}" has no evidence line')
            continue
        tags = [tag.strip() for tag in match.group(1).split(",")]
        for tag in tags:
            if tag not in TAGS:
                problems.append(f'{where}: practice "{text}" has unknown evidence tag "{tag}"')
        cites = any(CITATION.search(doc.prose[i]) for i in body)
        for tag in ("researched", "converged"):
            if tag in tags and not cites:
                problems.append(f'{where}: practice "{text}" is tagged {tag} but cites no source')
        both = "incident" in tags and "incident (undated)" in tags
        if both:
            problems.append(f'{where}: practice "{text}" has both incident and incident (undated)')
            continue
        for tag in ("incident", "incident (undated)"):
            if tag not in tags:
                continue
            dates = named.get(text, [])
            if not dates:
                problems.append(f'{where}: practice "{text}" is tagged {tag} but no ledger entry names it')
            elif tag == "incident" and not any(dates):
                problems.append(
                    f'{where}: practice "{text}" is tagged incident but no ledger entry naming it '
                    "has a date; use incident (undated)"
                )
            elif tag == "incident (undated)" and any(dates):
                problems.append(
                    f'{where}: practice "{text}" is tagged incident (undated) but a ledger entry '
                    "naming it has a date; use incident"
                )
    return finish(items, problems)


def check_ledger(root: pathlib.Path) -> Result | None:
    """Check the incident ledger in INCIDENTS.md.

    Items: every entry. An entry starts at a heading "## I-07: Title" and
    runs to the next "## " heading. A line that is not a list item
    continues the list item above it.

    - Any other "## " heading is a problem and not an item.
      Problem: "INCIDENTS.md:line: heading is not an entry: TEXT".
    - The entry's list items are exactly "- When:", "- What happened:",
      "- Rule:", "- Supports:", "- Record:", in that order. When they are
      not, the entry's values are not checked.
      Problem: "INCIDENTS.md:line: entry I-07 needs the list items When,
      What happened, Rule, Supports, Record, in that order".
    - No field is empty.
      Problem: "INCIDENTS.md:line: entry I-07 has an empty Rule".
    - When is "YYYY-MM" or "not recorded".
      Problem: 'INCIDENTS.md:line: entry I-07 has a bad When value "X"'.
    - Supports is 'FILE, "Heading"', with more headings joined by "and".
      Problem: "INCIDENTS.md:line: entry I-07 has a bad Supports value".
    - Each heading exists as a "### " heading in FILE, as exact text.
      A FILE outside the root is never opened and counts as missing.
      Problem: 'INCIDENTS.md:line: entry I-07 names a missing heading:
      FILE, "Heading"'.
    - Identifiers are unique.
      Problem: "INCIDENTS.md:line: duplicate entry identifier I-07".
    - A missing file means the check inspected nothing.
    """
    root = pathlib.Path(os.path.abspath(root))
    doc = load(root, LEDGER)
    if doc is None:
        return finish(0, [])
    entries, stray = parse_ledger(doc)
    problems = []
    found = []
    for entry in entries:
        found.append((entry["index"], entry_problems(root, doc, entry)))
    for index, text in stray:
        found.append((index, [f"{doc.where(index)}: heading is not an entry: {text}"]))
    seen = set()
    for entry in entries:
        if entry["id"] in seen:
            found.append((entry["index"], [f"{doc.where(entry['index'])}: duplicate entry identifier {entry['id']}"]))
        seen.add(entry["id"])
    for _, entry_list in sorted(found, key=lambda pair: pair[0]):
        problems.extend(entry_list)
    return finish(len(entries), problems)


def entry_problems(root: pathlib.Path, doc: Doc, entry) -> list[str]:
    where = f"{doc.where(entry['index'])}: entry {entry['id']}"
    if not entry["ordered"]:
        return [f"{where} needs the list items When, What happened, Rule, Supports, Record, in that order"]
    problems = []
    fields = entry["fields"]
    for name in FIELDS:
        if not fields[name]:
            problems.append(f"{where} has an empty {name}")
    when = fields["When"]
    if when and not (is_dated(when) or when == "not recorded"):
        problems.append(f'{where} has a bad When value "{when}"')
    supports = fields["Supports"]
    if supports:
        parsed = supported_headings(supports)
        if parsed is None:
            problems.append(f"{where} has a bad Supports value")
        else:
            file_name, headings = parsed
            target = load(root, file_name)
            present = set()
            if target is not None:
                present = {text for _, level, text, _ in target.headings if level == 3}
            for heading in headings:
                if heading not in present:
                    problems.append(f'{where} names a missing heading: {file_name}, "{heading}"')
    return problems


# 7. shared-lists


def extract_copy(root: pathlib.Path, copy):
    """Return the items of one copy, or None when it cannot be found."""
    path = inside(root, root / copy["file"])
    if path is None or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    lines = split_lines(text)
    kind = copy["kind"]
    items = None
    if kind == "list":
        anchor = next((i for i, line in enumerate(lines) if re.search(copy["after"], line)), None)
        if anchor is None:
            return None
        index = anchor + 1
        while index < len(lines) and not lines[index].strip():
            index += 1
        first = LIST_ITEM.match(lines[index]) if index < len(lines) else None
        if not first:
            return None
        indent = len(first.group(1))
        items = []
        while index < len(lines):
            match = LIST_ITEM.match(lines[index])
            if not match or len(match.group(1)) != indent:
                break
            items.append(" ".join(match.group(2).split()))
            index += 1
    elif kind == "inline":
        match = re.search(copy["pattern"], text, re.MULTILINE)
        if not match:
            return None
        items = []
        for part in match.group(1).split(","):
            part = part.strip()
            part = re.sub(r"^(?:and|or) ", "", part)
            items.append(" ".join(part.split()))
    elif kind == "headings":
        start = next((i for i, line in enumerate(lines)
                      if line.startswith("## ") and re.search(copy["section"], line)), None)
        if start is None:
            return None
        items = []
        for line in lines[start + 1:]:
            if line.startswith("## "):
                break
            if line.startswith("### "):
                items.append(" ".join(line[4:].split()))
    else:
        return None
    for old, new in copy.get("replace", []):
        items = [item.replace(old, new) for item in items]
    return items


def check_shared_lists(root: pathlib.Path, table: dict = SHARED_LISTS) -> Result | None:
    """Check that each shared list reads the same in every copy.

    Items: every declared copy in the table. Copies are read from the raw
    file text, so an anchor inside a fenced block is found. The starter
    template keeps its lists inside a fence.

    - list: the run of list items right after the first line that matches
      "after". Blank lines before the run are skipped. The run holds the
      consecutive lines that are list items at the indent of the first
      one. Any other line ends it.
    - inline: the first match of "pattern" (multiline mode). Its group is
      split on commas; each part is stripped, and a leading "and " or
      "or " is dropped.
    - headings: every "### " heading inside the "## " section whose
      heading line matches "section".
    - A copy that cannot be found, or that has fewer than two items, fails.
      Problems: "FILE: LIST: copy not found" and "FILE: LIST: copy has
      fewer than two items".
    - Each other copy is compared with the first copy, after "replace".
      Report only the first differing item. A missing or extra item counts
      as different. Problem: 'FILE: LIST: item N differs: "GOT" does not
      match "WANT"', with "(missing)" for a missing item.
    - When the first copy is not found, the others are not compared.
    """
    root = pathlib.Path(os.path.abspath(root))
    items = 0
    problems = []
    for name, copies in table.items():
        found = []
        for copy in copies:
            items += 1
            values = extract_copy(root, copy)
            if values is None:
                problems.append(f"{copy['file']}: {name}: copy not found")
            elif len(values) < 2:
                problems.append(f"{copy['file']}: {name}: copy has fewer than two items")
                values = None
            found.append(values)
        if not copies or found[0] is None:
            continue
        want_all = found[0]
        for copy, got_all in zip(copies[1:], found[1:]):
            if got_all is None:
                continue
            startswith = copy.get("match", "equal") == "startswith"
            for number in range(max(len(want_all), len(got_all))):
                want = want_all[number] if number < len(want_all) else None
                got = got_all[number] if number < len(got_all) else None
                if want is None or got is None:
                    same = False
                elif startswith:
                    same = got.startswith(want[:-1] if want.endswith(".") else want)
                else:
                    same = got == want
                if not same:
                    problems.append(
                        f'{copy["file"]}: {name}: item {number + 1} differs: '
                        f'"{got if got is not None else "(missing)"}" does not match '
                        f'"{want if want is not None else "(missing)"}"'
                    )
                    break
    return finish(items, problems)


# 8. terms

BANNED = re.compile(r"\boperating[\s-](?:manual|guide)", re.IGNORECASE)
ASSISTANT = re.compile(r"\bassistants?\b", re.IGNORECASE)
DEFINES_ASSISTANT = re.compile(r"agent.*\bmeans\b.*assistant", re.IGNORECASE)


def check_terms(root: pathlib.Path) -> Result | None:
    """Check banned terms in prose.

    Items: every prose line in every file.

    - No "operating manual" or "operating guide", in any letter case, and
      no hyphenated "operating-manual" or "operating-guide".
      Problem: 'path:line: banned term "operating manual"'.
    - No word "assistant" or "assistants", in any letter case, unless the
      line also matches "agent.*\\bmeans\\b.*assistant", ignoring case.
      One problem per line.
      Problem: 'path:line: banned term "assistant"'.
    """
    root = pathlib.Path(os.path.abspath(root))
    items = 0
    problems = []
    for path in markdown_files(root):
        doc = Doc(root, path)
        for index, line in enumerate(doc.prose):
            if not line.strip():
                continue
            items += 1
            for match in BANNED.finditer(line):
                problems.append(f'{doc.where(index)}: banned term "{match.group(0).lower()}"')
            if ASSISTANT.search(line) and not DEFINES_ASSISTANT.search(line):
                problems.append(f'{doc.where(index)}: banned term "assistant"')
    return finish(items, problems)


# 9. glance

CHECKBOX = re.compile(r"^\s*- \[ \] ")
FRAGMENT_LINK = re.compile(r"\[[^\]]*\]\(#([^)\s]+)\)")


def check_glance(root: pathlib.Path) -> Result | None:
    """Check the checklist in section 12 of FIELD-MANUAL.md.

    Section 12 runs from "## 12. " to the next "## " heading or "---"
    line. Items: every checkbox item "- [ ] ..." inside it.

    - Each item holds at least one link "[text](#fragment)".
      Problem: "FIELD-MANUAL.md:line: checklist item has no
      [text](#fragment) link".
    - Each such fragment is the slug of a "### " heading inside sections
      1 to 11. Repeated slugs are numbered over the whole file.
      Problem: "FIELD-MANUAL.md:line: #FRAGMENT is not a practice heading
      in sections 1 to 11".
    """
    root = pathlib.Path(os.path.abspath(root))
    doc = load(root, MANUAL)
    if doc is None:
        return finish(0, [])
    practices = {heading_slug for _, level, _, heading_slug, section in heading_sections(doc)
                 if level == 3 and section in PRACTICE_SECTIONS}
    span = section_range(doc, GLANCE_SECTION, stop_at_rule=True)
    if span is None:
        return finish(0, [])
    items = 0
    problems = []
    for index in range(span[0] + 1, span[1]):
        line = doc.lines[index]
        if doc.code[index] or not CHECKBOX.match(line):
            continue
        items += 1
        fragments = FRAGMENT_LINK.findall(strip_code_spans(line))
        if not fragments:
            problems.append(f"{doc.where(index)}: checklist item has no [text](#fragment) link")
        for fragment in fragments:
            if fragment not in practices:
                problems.append(f"{doc.where(index)}: #{fragment} is not a practice heading in sections 1 to 11")
    return finish(items, problems)


# 10. version

VERSION_LINE = re.compile(r"^\*Version (v\d+(?:\.\d+)*), " + DATE + r"\.\*$")
GITHUB_REF = re.compile(r"^https://github\.com/[^/]+/[^/]+/(?:blob|tree)/([^/#?]+)")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def check_version(root: pathlib.Path) -> Result | None:
    """Check that the contract links pin the manual's version.

    Items: every link in AGENT-CONTRACT.md whose target has the form
    "https://github.com/OWNER/REPO/blob/REF/..." or ".../tree/REF/...",
    and every relative link to a file. Links that are only "#fragment",
    and links to other web addresses, are not items.

    - FIELD-MANUAL.md holds exactly one line "*Version v2.0, 2026-11.*".
      A line that does not match that shape is not a version line.
      Problems: "FIELD-MANUAL.md: no version line" and
      "FIELD-MANUAL.md: N version lines, expected exactly one".
      Without exactly one version line, links are not compared.
    - Every such GitHub link uses the version as REF.
      Problem: "AGENT-CONTRACT.md:line: link uses REF, but the manual
      version is VERSION".
    - A relative link breaks when the contract is handed out alone.
      Problem: "AGENT-CONTRACT.md:line: relative link breaks when the
      contract is copied: TARGET".
    """
    root = pathlib.Path(os.path.abspath(root))
    manual = load(root, MANUAL)
    versions = []
    if manual is not None:
        versions = [match.group(1) for match in map(VERSION_LINE.match, manual.lines) if match]
    problems = []
    if not versions:
        problems.append(f"{MANUAL}: no version line")
    elif len(versions) > 1:
        problems.append(f"{MANUAL}: {len(versions)} version lines, expected exactly one")
    version = versions[0] if len(versions) == 1 else None
    contract = load(root, CONTRACT)
    items = 0
    if contract is not None:
        for index, line in enumerate(contract.lines):
            if contract.code[index]:
                continue
            for match in LINK.finditer(strip_code_spans(line)):
                target = match.group(2)
                ref = GITHUB_REF.match(target)
                if ref:
                    items += 1
                    if version is not None and ref.group(1) != version:
                        problems.append(
                            f"{contract.where(index)}: link uses {ref.group(1)}, "
                            f"but the manual version is {version}"
                        )
                elif target.startswith("#") or SCHEME.match(target):
                    continue
                else:
                    items += 1
                    problems.append(
                        f"{contract.where(index)}: relative link breaks when the contract is copied: {target}"
                    )
    return finish(items, problems)


CHECKS = {
    "links": check_links,
    "fences": check_fences,
    "punctuation": check_punctuation,
    "sources": check_sources,
    "evidence": check_evidence,
    "ledger": check_ledger,
    "shared-lists": check_shared_lists,
    "terms": check_terms,
    "glance": check_glance,
    "version": check_version,
}


def _count(number: int, word: str) -> str:
    """Return "1 item" or "3 items"."""
    return f"{number} {word}" if number == 1 else f"{number} {word}s"


def run(root, only=None, require_all=False):
    """Run the checks and return (lines, exit_status).

    only: names of the checks to run, or None for all. The others print
    "not run". An unknown name raises ValueError.
    Exit status is 1 when a check failed, or when require_all is true and
    a check did not run. Otherwise it is 0.
    """
    root = pathlib.Path(root)
    if only is not None:
        only = list(only)
        unknown = [name for name in only if name not in CHECKS]
        if unknown:
            raise ValueError(f"unknown check: {', '.join(unknown)}")
    lines = []
    status = 0
    for name, function in CHECKS.items():
        result = NOT_RUN
        if only is None or name in only:
            result = function(root)
        if result is NOT_RUN:
            lines.append(f"{name}: not run")
            if require_all:
                status = 1
            continue
        problems = list(result.problems)
        if result.items == 0 and "inspected nothing" not in problems:
            problems.append("inspected nothing")
        if problems:
            status = 1
            lines.append(
                f"{name}: failed ({_count(result.items, 'item')}, "
                f"{_count(len(problems), 'problem')})"
            )
            lines.extend(f"  {problem}" for problem in problems)
        else:
            lines.append(f"{name}: passed ({_count(result.items, 'item')})")
    return lines, status


# moved


class GitError(Exception):
    pass


def _git(root: pathlib.Path, *args: str) -> str:
    """Run git with an argument list in root and return its output."""
    try:
        done = subprocess.run(["git", *args], cwd=root, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
    except OSError as error:
        raise GitError(str(error)) from error
    if done.returncode != 0:
        raise GitError(done.stderr.strip() or f"git {args[0]} failed")
    return done.stdout


def paragraphs(text: str) -> list[str]:
    """Split text into paragraphs at blank lines, whitespace collapsed."""
    found = []
    block = []
    for line in split_lines(text) + [""]:
        if line.strip():
            block.append(line)
        elif block:
            found.append(" ".join(" ".join(block).split()))
            block = []
    return found


def revision_paragraphs(root, revision, paths):
    """Return [(file, paragraph)] for the Markdown files of one revision."""
    args = ["ls-tree", "-r", "-z", "--name-only", revision, "--"]
    if paths:
        args.extend(paths)
    names = [name for name in _git(root, *args).split("\0") if name.endswith(".md")]
    found = []
    for name in sorted(names):
        text = _git(root, "show", f"{revision}:{name}")
        found.extend((name, paragraph) for paragraph in paragraphs(text))
    return found


def moved(root, base, head, paths=None):
    """Compare the Markdown paragraphs of two git revisions.

    Returns (lines, exit_status).

    Reads every "*.md" file in each revision, or only the given paths
    (relative to root). Each revision is read on its own, so a file that
    exists in only one revision still counts. A paragraph is a block of
    lines between blank lines, compared after collapsing whitespace.
    Paragraphs are compared as multisets across all files, so a paragraph
    that moved within a file or between files counts as unchanged, and a
    paragraph that appears twice in BASE and once in HEAD is one removed.

    Output: "added: N", "removed: N", "unchanged: N", then one line per
    added paragraph "+ FILE: first 80 characters", then one line per
    removed paragraph "- FILE: first 80 characters", each in file order.
    Exit status 0, or 2 when git fails. Git runs with an argument list,
    never through a shell.
    """
    root = pathlib.Path(root)
    try:
        before = revision_paragraphs(root, base, paths)
        after = revision_paragraphs(root, head, paths)
    except GitError as error:
        print(f"moved: git failed: {error}", file=sys.stderr)
        return [], 2
    old = collections.Counter(paragraph for _, paragraph in before)
    new = collections.Counter(paragraph for _, paragraph in after)
    added = new - old
    removed = old - new
    lines = [
        f"added: {sum(added.values())}",
        f"removed: {sum(removed.values())}",
        f"unchanged: {sum((old & new).values())}",
    ]
    for sign, listing, extra in (("+", after, added), ("-", before, removed)):
        left = collections.Counter(extra)
        for name, paragraph in listing:
            if left[paragraph] > 0:
                left[paragraph] -= 1
                lines.append(f"{sign} {name}: {paragraph[:80]}")
    return lines, 0


# Command line


def _default_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent


def _main_checks(argv):
    parser = argparse.ArgumentParser(prog="check_manual.py")
    parser.add_argument("--root", type=pathlib.Path, default=_default_root())
    parser.add_argument("--only", default=None)
    parser.add_argument("--require-all", action="store_true")
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        parser.error(f"root is not a directory: {args.root}")
    only = None
    if args.only is not None:
        only = [name.strip() for name in args.only.split(",") if name.strip()]
        if not only:
            parser.error("--only names no check")
    try:
        lines, status = run(args.root, only=only, require_all=args.require_all)
    except ValueError as error:
        parser.error(str(error))
    for line in lines:
        print(line)
    return status


def _main_moved(argv):
    # Split the paths off by hand. Argparse does not mix a "*" positional
    # with options reliably.
    paths = None
    if "--" in argv:
        cut = argv.index("--")
        argv, paths = argv[:cut], argv[cut + 1:]
    parser = argparse.ArgumentParser(prog="check_manual.py moved")
    parser.add_argument("base")
    parser.add_argument("head")
    parser.add_argument("--root", type=pathlib.Path, default=_default_root())
    args = parser.parse_args(argv)
    lines, status = moved(args.root, args.base, args.head, paths or None)
    for line in lines:
        print(line)
    return status


def main(argv=None) -> int:
    """Run the command line and return the exit status.

    A usage error returns 2. The "moved" command must come first.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv and argv[0] == "moved":
            return _main_moved(argv[1:])
        return _main_checks(argv)
    except SystemExit as exit_:
        return exit_.code if isinstance(exit_.code, int) else 2


if __name__ == "__main__":
    sys.exit(main())

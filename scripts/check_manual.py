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
- The checker never reads a file outside the root. Symbolic links are
  resolved before that test, in the path and in the root. The walk does
  not follow a linked directory, because its target is walked at its real
  place. A linked "*.md" file inside the root is read as a normal file. A
  linked "*.md" file or directory whose target is outside the root is not
  read, and each check that walks the files reports "PATH: symbolic link
  leaves the repository, not read".
- A file that cannot be read, or that is not valid UTF-8, is a problem for
  the check that tried to read it: "PATH: cannot read: REASON". The check
  goes on with the other files.
- A fence is a line of three or more backticks or three or more tildes.
  It opens a block. Only a line of the same character, at least as long,
  with nothing after it, closes the block. A backtick fence may not hold a
  backtick in its info string; a tilde fence may.
- "Prose" is the text of a Markdown file with these parts removed: fenced
  code blocks (fence lines included), inline code spans, link targets, and
  table separator rows. A link "[text](target)" becomes "[text]", and a
  reference definition "[label]: target" becomes "[label]:". Removed lines
  stay as blank lines, so line numbers do not move. A "prose line" is a
  line of prose that is not blank.
- A paragraph is a run of prose lines. It ends at a blank line. A heading,
  a list item, and a table row each start a new paragraph, and a heading
  is a paragraph of its own.
- A section of FIELD-MANUAL.md is a line "## N. Title". Section N runs to
  the next "## " heading.
- A date "YYYY-MM" has a month from 01 to 12.
- No pattern takes quadratic time, so a long line cannot stall a check.
"""

from __future__ import annotations

import argparse
import bisect
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

FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
BACKTICKS = re.compile(r"`+")
# The target part of an inline link: "](target)", "](<target>)", with an
# optional title in double or single quotes.
LINK_TARGET = re.compile(r"\]\(\s*(?:<([^<>\n]*)>|([^\s()]*))(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'))?\s*\)")
# A reference definition: "[label]: target", with an optional title.
REFERENCE = re.compile(
    r"^( {0,3}\[([^\]\n]+)\]:)[ \t]*(?:<([^<>\n]*)>|(\S+))"
    r"(?:[ \t]+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^()\n]*\)))?[ \t]*$"
)
TABLE_SEPARATOR = re.compile(r"\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?")
HEADING = re.compile(r"^(#{1,6})[ \t]+(.*)$")
SECTION = re.compile(r"^(\d+)\. ")
CITATION = re.compile(r"\((S\d+(?:,\s*S\d+)*)\)")
DATE = r"\d{4}-(?:0[1-9]|1[0-2])"
LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")


class Unreadable(Exception):
    """A file that cannot be read as UTF-8 text. The message is the reason."""


def read_text(path: pathlib.Path) -> str:
    """Read a file as UTF-8, or raise Unreadable with a short reason."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise Unreadable(f"not valid UTF-8 at byte {error.start}") from error
    except OSError as error:
        raise Unreadable(error.strerror or str(error)) from error


def split_lines(text: str) -> list[str]:
    """Split text into lines without a final empty line."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [line.rstrip("\r") for line in lines]


def scan_fences(lines: list[str]):
    """Find fenced blocks.

    Returns (code, blocks). code[i] is true when line i belongs to a block,
    fence lines included. Each block is (open_index, close_index, char,
    length, info): char is "`" or "~", and close_index is None when the
    file ends inside the block.
    """
    code = [False] * len(lines)
    blocks = []
    opened = None
    for index, line in enumerate(lines):
        match = FENCE.match(line)
        if opened is None:
            if match:
                run, info = match.group(1), match.group(2)
                if run[0] == "`" and "`" in info:
                    continue
                opened = (index, run[0], len(run), info.strip())
                code[index] = True
            continue
        code[index] = True
        if (match and match.group(1)[0] == opened[1] and len(match.group(1)) >= opened[2]
                and match.group(2).strip() == ""):
            blocks.append((opened[0], index, opened[1], opened[2], opened[3]))
            opened = None
    if opened is not None:
        blocks.append((opened[0], None, opened[1], opened[2], opened[3]))
    return code, blocks


def is_markdown_info(info: str) -> bool:
    """True when an info string starts with the word "markdown" or "md", in any letter case."""
    words = info.split()
    return bool(words) and words[0].lower() in ("markdown", "md")


def heading_text(raw: str) -> str:
    """Strip a heading's text and its closing run of "#" characters."""
    text = raw.strip()
    bare = text.rstrip("#")
    if bare != text and (not bare or bare[-1] in " \t"):
        text = bare.rstrip()
    return text


def relative(root: pathlib.Path, path: pathlib.Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


class Doc:
    """One Markdown file: its lines, code flags, prose, and headings.

    Raises Unreadable when the file cannot be read.
    """

    def __init__(self, root: pathlib.Path, path: pathlib.Path):
        self.path = path
        self.rel = relative(root, path)
        self.lines = split_lines(read_text(path))
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
            text = heading_text(match.group(2))
            base = slug(text)
            number = counts[base]
            counts[base] += 1
            self.headings.append((index, len(match.group(1)), text, f"{base}-{number}" if number else base))

    def slugs(self) -> set[str]:
        return {heading[3] for heading in self.headings}

    def where(self, index: int) -> str:
        return f"{self.rel}:{index + 1}"

    def example_prose(self) -> list[str]:
        """The prose, with the inside of each Markdown example read as prose too.

        A Markdown example is a fenced block whose info string starts with
        the word "markdown" or "md". Its inside is read as a Markdown
        document of its own: its own fenced blocks are code, and the rest
        is prose. Line numbers stay those of this file.
        """
        prose = list(self.prose)
        for opened, closed, _, _, info in self.blocks:
            if not is_markdown_info(info):
                continue
            end = len(self.lines) if closed is None else closed
            inner = self.lines[opened + 1:end]
            code, _ = scan_fences(inner)
            for offset, line in enumerate(inner):
                prose[opened + 1 + offset] = "" if code[offset] else prose_line(line)
        return prose


def strip_code_spans(line: str) -> str:
    """Remove inline code spans from one line.

    A run of backticks opens a span, and the next run of the same length
    closes it. A run with no closing run is plain text. This takes linear
    time.
    """
    runs = [match.span() for match in BACKTICKS.finditer(line)]
    if not runs:
        return line
    closer = [None] * len(runs)
    seen = {}
    for number in range(len(runs) - 1, -1, -1):
        length = runs[number][1] - runs[number][0]
        closer[number] = seen.get(length)
        seen[length] = number
    pieces = []
    position = 0
    number = 0
    while number < len(runs):
        close = closer[number]
        if close is None:
            number += 1
            continue
        pieces.append(line[position:runs[number][0]])
        position = runs[close][1]
        number = close + 1
    pieces.append(line[position:])
    return "".join(pieces)


def reference_definition(text: str):
    """Return the match of a reference definition "[label]: target", or None."""
    match = REFERENCE.match(text)
    if match and match.group(2).strip():
        return match
    return None


def link_targets(text: str):
    """Yield the target of every link in text that has no code spans.

    A link is found by its "](target)" part, so its text may wrap over
    lines or hold brackets. A reference definition gives its target too.
    """
    reference = reference_definition(text)
    if reference:
        yield reference.group(3) if reference.group(3) is not None else reference.group(4)
        return
    for match in LINK_TARGET.finditer(text):
        yield match.group(1) if match.group(1) is not None else match.group(2)


def prose_line(line: str) -> str:
    """Return the prose of one line that is outside fenced code."""
    stripped = line.strip()
    if "|" in stripped and "-" in stripped and TABLE_SEPARATOR.fullmatch(stripped):
        return ""
    text = strip_code_spans(line)
    reference = reference_definition(text)
    if reference:
        return reference.group(1)
    return LINK_TARGET.sub("]", text)


def slug(text: str) -> str:
    """Return GitHub's slug for a heading, before repeat numbering."""
    text = LINK_TARGET.sub("]", text).lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def prose_paragraphs(prose: list[str]):
    """Group prose lines into paragraphs.

    Returns a list of (text, starts). text is the lines of one paragraph,
    stripped and joined with single spaces. starts holds (offset, index)
    for each line: where the line begins in text, and its line index.
    """
    groups = []
    current = []
    for index, line in enumerate(prose):
        stripped = line.strip()
        if not stripped:
            if current:
                groups.append(current)
                current = []
            continue
        heading = HEADING.match(stripped)
        if current and (heading or LIST_ITEM.match(line) or stripped.startswith("|")):
            groups.append(current)
            current = []
        current.append(index)
        if heading:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    paragraphs = []
    for indexes in groups:
        parts = []
        starts = []
        offset = 0
        for index in indexes:
            part = prose[index].strip()
            starts.append((offset, index))
            parts.append(part)
            offset += len(part) + 1
        paragraphs.append((" ".join(parts), starts))
    return paragraphs


def line_at(starts, position: int) -> int:
    """Return the line index that holds a position in a paragraph's text."""
    offsets = [offset for offset, _ in starts]
    return starts[bisect.bisect_right(offsets, position) - 1][1]


def inside(root: pathlib.Path, path: pathlib.Path) -> pathlib.Path | None:
    """Return the normalized path when it lies within root, else None.

    Symbolic links are resolved, in the path and in root, before the test.
    The path returned is not resolved, so it keeps the name it was given.
    """
    normal = pathlib.Path(os.path.normpath(path))
    real = pathlib.Path(os.path.realpath(normal))
    real_root = pathlib.Path(os.path.realpath(root))
    if real == real_root or real_root in real.parents:
        return normal
    return None


def markdown_files(root: pathlib.Path):
    """Walk root for "*.md" files.

    Returns (paths, problems). Directories whose name starts with a dot are
    skipped. A linked directory is not followed. A linked "*.md" file or
    directory whose target is outside root is not read; it gives the
    problem "PATH: symbolic link leaves the repository, not read". A
    directory that cannot be listed gives "PATH: cannot read: REASON".
    """
    found = []
    problems = []

    def listing_failed(error):
        name = relative(root, pathlib.Path(error.filename)) if error.filename else "."
        problems.append(f"{name}: cannot read: {error.strerror or error}")

    for directory, subdirs, files in os.walk(root, onerror=listing_failed):
        here = pathlib.Path(directory)
        keep = []
        for name in sorted(subdirs):
            if name.startswith("."):
                continue
            path = here / name
            if path.is_symlink():
                if inside(root, path) is None:
                    problems.append(f"{relative(root, path)}: symbolic link leaves the repository, not read")
                continue
            keep.append(name)
        subdirs[:] = keep
        for name in sorted(files):
            if not name.endswith(".md"):
                continue
            path = here / name
            if path.is_symlink() and inside(root, path) is None:
                problems.append(f"{relative(root, path)}: symbolic link leaves the repository, not read")
                continue
            found.append(path)
    return found, problems


class Reader:
    """Reads the Markdown files of one root, for one check.

    Each file is read once. A file that cannot be read gives one problem,
    "PATH: cannot read: REASON", and then counts as absent.
    """

    def __init__(self, root):
        self.root = pathlib.Path(os.path.abspath(root))
        self.docs = {}
        self.problems = []

    def doc(self, path: pathlib.Path) -> Doc | None:
        if path not in self.docs:
            try:
                self.docs[path] = Doc(self.root, path)
            except Unreadable as error:
                self.problems.append(f"{relative(self.root, path)}: cannot read: {error}")
                self.docs[path] = None
        return self.docs[path]

    def load(self, rel: str) -> Doc | None:
        """Read one file named relative to the root.

        Returns None when the file is missing, is a directory, lies outside
        the root, or cannot be read.
        """
        path = inside(self.root, self.root / rel)
        if path is None or not os.path.lexists(path) or path.is_dir():
            return None
        return self.doc(path)

    def walk(self) -> list[Doc]:
        """Read every Markdown file under the root that can be read."""
        paths, problems = markdown_files(self.root)
        self.problems.extend(problems)
        return [doc for doc in map(self.doc, paths) if doc is not None]

    def finish(self, items: int, problems: list[str]) -> Result:
        return finish(items, self.problems + problems)


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
MD_MENTION = re.compile(r"\.md\b")
SECTION_NAMES = re.compile(r"\bsections? (\d+(?:(?:,\s*|,?\s+and\s+)\d+)*)")
MANUAL_STEM = MANUAL[:-len(".md")]


def manual_section_numbers(text: str):
    """Yield (position, number) for each section number a paragraph names in the manual.

    A number counts when it follows a mention of FIELD-MANUAL.md with no
    mention of another ".md" file between them. Numbers are read from
    "section N" and "sections N, M, and K".
    """
    mentions = []
    for match in MD_MENTION.finditer(text):
        start = match.start() - len(MANUAL_STEM)
        manual = (start >= 0 and text[start:match.start()] == MANUAL_STEM
                  and (start == 0 or not re.match(r"[\w-]", text[start - 1])))
        mentions.append((match.end(), manual))
    if not any(manual for _, manual in mentions):
        return
    next_mention = 0
    active = False
    for group in SECTION_NAMES.finditer(text):
        while next_mention < len(mentions) and mentions[next_mention][0] <= group.start():
            active = mentions[next_mention][1]
            next_mention += 1
        if not active:
            continue
        for number in re.finditer(r"\d+", group.group(1)):
            yield group.start(1) + number.start(), int(number.group())


def check_links(root: pathlib.Path) -> Result | None:
    """Check links and section references.

    Items: every Markdown link outside code, in every file, and every
    section reference. A link is found by its "](target)" part, so its
    text may wrap over two lines or hold brackets. The target may sit in
    angle brackets, and a title in double or single quotes may follow it.
    A reference definition "[label]: target" at the start of a line is a
    link too. Links to http:, https:, and mailto: count as items but are
    not followed.

    - An empty target fails.
      Problem: "path:line: empty link target".
    - A target that starts with "/" or resolves outside the root fails,
      and the checker never opens it. Symbolic links are resolved first.
      Problem: "path:line: link target is outside the repository: TARGET".
    - Any other target must name a file or a directory that exists,
      relative to the file that holds the link. A directory counts,
      because the repository links to "templates" and "examples".
      Problem: "path:line: link target does not exist: TARGET".
    - A "#fragment" must equal the slug of a heading in the target file.
      A target of only "#fragment" points into the same file. Headings
      inside fenced code are not headings. A closing run of "#" is not
      part of a heading. Slugs follow GitHub's rule, with "-1", "-2" for
      repeats over the whole file.
      Problem: "path:line: no heading for fragment: TARGET".
    - In FIELD-MANUAL.md, each "§N" in prose must name an existing section.
      In any other file, a mention of FIELD-MANUAL.md in prose starts a
      reference: every "section N" or "sections N, M, and K" that follows,
      up to the end of the paragraph or the next mention of another ".md"
      file, must name an existing section. Each number is one item. The
      lines of a paragraph are joined first, so a reference may wrap. The
      problem names the line that holds the number.
      Problem: "path:line: no section N in FIELD-MANUAL.md".
    """
    reader = Reader(root)
    manual_sections = sections(reader.load(MANUAL))
    items = 0
    problems = []
    for doc in reader.walk():
        for index, line in enumerate(doc.lines):
            if doc.code[index]:
                continue
            for target in link_targets(strip_code_spans(line)):
                items += 1
                problem = link_problem(reader, doc, target)
                if problem:
                    problems.append(f"{doc.where(index)}: {problem}")
            if doc.rel == MANUAL:
                for number in re.findall(r"§(\d+)", doc.prose[index]):
                    items += 1
                    if int(number) not in manual_sections:
                        problems.append(f"{doc.where(index)}: no section {number} in {MANUAL}")
        if doc.rel == MANUAL:
            continue
        for text, starts in prose_paragraphs(doc.prose):
            for position, number in manual_section_numbers(text):
                items += 1
                if number not in manual_sections:
                    problems.append(f"{doc.where(line_at(starts, position))}: no section {number} in {MANUAL}")
    return reader.finish(items, problems)


def link_problem(reader: Reader, doc: Doc, target: str) -> str | None:
    """Return the problem with one link target, or None."""
    if target == "":
        return "empty link target"
    if WEB.match(target):
        return None
    file_part, has_fragment, fragment = target.partition("#")
    if file_part.startswith("/"):
        return f"link target is outside the repository: {target}"
    if file_part:
        dest = inside(reader.root, doc.path.parent / urllib.parse.unquote(file_part))
        if dest is None:
            return f"link target is outside the repository: {target}"
        if not dest.exists():
            return f"link target does not exist: {target}"
    else:
        dest = doc.path
    if has_fragment:
        target_doc = reader.doc(dest) if dest.is_file() and dest.suffix == ".md" else None
        if target_doc is None or fragment not in target_doc.slugs():
            return f"no heading for fragment: {target}"
    return None


# 2. fences


def check_fences(root: pathlib.Path) -> Result | None:
    """Check fenced code blocks.

    Items: every line that opens or closes a block. A fence run that is
    only content inside an open block is not an item. Leading spaces
    before a fence are allowed. Trailing spaces after a closing fence are
    ignored.

    - A line of three or more backticks, or three or more tildes, opens a
      block. Only a line of the same character, at least as long, with
      nothing after it, closes it. A backtick fence may not hold a
      backtick in its info string; a tilde fence may.
    - A file must not end inside an open block.
      Problem: "path:line: block opened here is never closed".
    - A backtick block whose info string starts with the word "markdown"
      or "md", in any letter case, must open with four or more backticks.
      Markdown examples hold backtick fences, and a three-backtick outer
      fence is closed by the first inner one. A tilde block is not closed
      by backticks, so this rule does not apply to it.
      Problem: "path:line: a markdown example block needs a fence of four
      or more backticks".
    """
    reader = Reader(root)
    items = 0
    problems = []
    for doc in reader.walk():
        for opened, closed, char, length, info in doc.blocks:
            items += 1 if closed is None else 2
            if char == "`" and is_markdown_info(info) and length < 4:
                problems.append(
                    f"{doc.where(opened)}: a markdown example block needs a fence of four or more backticks"
                )
            if closed is None:
                problems.append(f"{doc.where(opened)}: block opened here is never closed")
    return reader.finish(items, problems)


# 3. punctuation

FORBIDDEN = ("\u2014", "\u2013", "\u2018", "\u2019", "\u201c", "\u201d")


def doubled_hyphen(line: str) -> bool:
    """True when a run of two or more hyphens is used as punctuation.

    A run that looks like a command-line option (a space or the line start
    before it, and a word character after it) is allowed. So is a line
    that holds only hyphens and spaces.
    """
    if re.fullmatch(r"[-\s]+", line):
        return False
    for match in re.finditer(r"-{2,}", line):
        start, end = match.span()
        before = line[start - 1] if start > 0 else ""
        after = line[end] if end < len(line) else ""
        option = (before == "" or before.isspace()) and re.match(r"\w", after) is not None
        if not option:
            return True
    return False


def check_punctuation(root: pathlib.Path) -> Result | None:
    """Check prose punctuation.

    Items: every prose line in every file. The inside of a Markdown
    example block is read as prose too (see Doc.example_prose), because
    readers copy that text.

    - No em dash (U+2014), en dash (U+2013), or curly quote (U+2018,
      U+2019, U+201C, U+201D). One problem per character per line.
      Problem: "path:line: forbidden character U+2014".
    - No run of two or more hyphens, unless it looks like a command-line
      option: a space or the line start before it, and a word character
      after it. One problem per line.
      Problem: "path:line: doubled hyphen used as punctuation".
    - A line that holds only hyphens and spaces (rules and front matter
      delimiters) and table separator rows are never flagged.
    """
    reader = Reader(root)
    items = 0
    problems = []
    for doc in reader.walk():
        for index, line in enumerate(doc.example_prose()):
            if not line.strip():
                continue
            items += 1
            for char in FORBIDDEN:
                if char in line:
                    problems.append(f"{doc.where(index)}: forbidden character U+{ord(char):04X}")
            if doubled_hyphen(line):
                problems.append(f"{doc.where(index)}: doubled hyphen used as punctuation")
    return reader.finish(items, problems)


# 4. sources

# The start of an entry, up to the word "Supports". Each part is bounded,
# so the match takes linear time.
ENTRY_START = re.compile(
    r"^\s*[-*+]\s+\*\*(S\d+)\.\*\* \[[^\]]+\]\(https?://[^)\s]+\) \([^)]+\)\. Supports\b"
)
ENTRY_KEY = re.compile(r"^\s*[-*+]\s+\*\*(S\d+)\.\*\*")
ENTRY_SECTION = re.compile(r" sections? \d")
ENTRY_END = re.compile(r'"\. Read ' + DATE + r"\.$")
PARENTHESIS = re.compile(r"\(([^()]*)\)")
STRICT_CITATION = re.compile(r"S\d+(?:,\s*S\d+)*")
SOURCE_KEY = re.compile(r"\bS\d+\b")
CITATION_JOINERS = re.compile(r"\b(?:and|or|see|also|cf)\b|[\s,;/&.:]", re.IGNORECASE)


def entry_has_shape(line: str) -> bool:
    """True when a source entry has the required shape.

    The shape: a bold key "**S3.**", a link, a parenthesis, "Supports
    section N" or "Supports sections N" in lower case, at least one quoted
    passage after a colon, and a final "Read YYYY-MM.".
    """
    start = ENTRY_START.match(line)
    if not start:
        return False
    rest = line[start.end():]
    if not ENTRY_SECTION.match(rest):
        return False
    end = ENTRY_END.search(rest)
    if not end:
        return False
    body = rest[:end.start() + 1]
    quote = body.find(': "')
    return quote != -1 and quote + 3 < len(body) - 1


def supported_sections(entry: str) -> list[int]:
    """The section numbers named after "Supports", with quoted passages removed.

    "Supports" is the word that follows the link and the parenthesis, so a
    title that holds the word names nothing. An entry without that start
    names nothing.
    """
    start = ENTRY_START.match(entry)
    if not start:
        return []
    phrase = re.sub(r'"[^"]*"', "", entry[start.end():])
    numbers = []
    for group in SECTION_NAMES.finditer(phrase):
        numbers.extend(int(number) for number in re.findall(r"\d+", group.group(1)))
    return numbers


def citation_kind(content: str) -> str | None:
    """Classify the text inside one parenthesis.

    Returns "citation" for the strict form "S3" or "S2, S3". Returns
    "malformed" when it holds source keys joined in any other way: only
    keys, spaces, the punctuation , ; / & . :, and the words and, or, see,
    also, cf. Returns None for anything else, such as "stored in S3".
    """
    if STRICT_CITATION.fullmatch(content):
        return "citation"
    if SOURCE_KEY.search(content) and not CITATION_JOINERS.sub("", SOURCE_KEY.sub("", content)):
        return "malformed"
    return None


def check_sources(root: pathlib.Path) -> Result | None:
    """Check the source list of FIELD-MANUAL.md and its citations.

    The section starts at the line "## Sources" and ends at the next "## "
    heading or a "---" line. Each list item in it is an entry. Items:
    every entry, plus every citation group such as "(S3)" or "(S2, S3)"
    in the prose above "## Sources", plus every malformed citation. A
    group counts as one item.

    - An entry has the shape: a bold key "**S3.**", a link, a
      parenthesis, the word "Supports" followed by "section N" or
      "sections N" in lower case, at least one quoted passage, and a
      final "Read YYYY-MM.".
      Problem: "FIELD-MANUAL.md:line: source entry does not match the
      required shape".
      An entry whose key can still be read counts for the key rules.
    - Keys are unique.
      Problem: "FIELD-MANUAL.md:line: duplicate source key S3".
    - Every "section N" or "sections N, M, and K" after the "Supports"
      that follows the link and the parenthesis must name an existing
      section. Quoted passages are removed first, so a quote that holds
      "section 9" names nothing.
      Problem: "FIELD-MANUAL.md:line: source S3 names missing section N".
    - A parenthesis that holds only source keys, joined in any way other
      than the strict form (see citation_kind), is malformed. Its keys
      do not count as cited.
      Problem: "FIELD-MANUAL.md:line: malformed citation (TEXT)".
    - Every cited key has an entry.
      Problem: "FIELD-MANUAL.md:line: citation S9 has no source entry".
    - Every entry is cited at least once.
      Problem: "FIELD-MANUAL.md:line: source S3 is never cited".
    """
    reader = Reader(root)
    doc = reader.load(MANUAL)
    if doc is None:
        return reader.finish(0, [])
    start = next((i for i, line in enumerate(doc.lines) if line == "## Sources" and not doc.code[i]), None)
    if start is None:
        return reader.finish(0, [])
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
        if not entry_has_shape(line):
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
        for group in PARENTHESIS.finditer(doc.prose[index]):
            kind = citation_kind(group.group(1))
            if kind is None:
                continue
            items += 1
            if kind == "malformed":
                problems.append(f"{doc.where(index)}: malformed citation ({group.group(1)})")
                continue
            for key in re.findall(r"S\d+", group.group(1)):
                cited.add(key)
                if key not in first_line:
                    problems.append(f"{doc.where(index)}: citation {key} has no source entry")
    for key, index in first_line.items():
        if key not in cited:
            problems.append(f"{doc.where(index)}: source {key} is never cited")
    return reader.finish(items, problems)


# 5. evidence and 6. ledger

EVIDENCE = re.compile(r"^\*Evidence: (.+)\.\*$")
TAGS = ("converged", "researched", "observed", "incident", "incident (undated)")
ENTRY_TITLE = re.compile(r"^(I-\d+): \S")
FIELD = re.compile(r"^(When|What happened|Rule|Supports|Record):\s*(.*)$")
FIELDS = ["When", "What happened", "Rule", "Supports", "Record"]
SUPPORTS = re.compile(r'^(\S+), ("[^"]+"(?: and "[^"]+")*)$')


def parse_ledger(doc: Doc):
    """Split a ledger into entries and stray headings.

    An entry heading is a "## " heading "I-07: Title". A first-level
    heading is the title and is allowed. Every other heading is stray and
    ends the entry above it.

    Returns (entries, stray). Each entry is a dict with id, index, and
    items (the text of each list item, whitespace collapsed). Each stray
    heading is (index, text).
    """
    headings = {index: (level, text) for index, level, text, _ in doc.headings}
    entries = []
    stray = []
    current = None
    for index, line in enumerate(doc.lines):
        if doc.code[index]:
            continue
        if index in headings:
            level, text = headings[index]
            match = ENTRY_TITLE.match(text) if level == 2 else None
            if match:
                current = {"id": match.group(1), "index": index, "items": []}
                entries.append(current)
            else:
                if level != 1:
                    stray.append((index, text))
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
    - researched or converged needs a citation in the practice's own
      prose. A citation inside a code span does not count.
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
    reader = Reader(root)
    doc = reader.load(MANUAL)
    if doc is None:
        return reader.finish(0, [])
    named = collections.defaultdict(list)
    ledger = reader.load(LEDGER)
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
    return reader.finish(items, problems)


def check_ledger(root: pathlib.Path) -> Result | None:
    """Check the incident ledger in INCIDENTS.md.

    Items: every entry. An entry starts at a heading "## I-07: Title" and
    runs to the next heading. A line that is not a list item continues
    the list item above it. Headings inside fenced code are not headings.

    - A first-level heading is the title. Every other heading, of any
      level or shape, that is not an entry heading is a problem and not
      an item.
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
    reader = Reader(root)
    doc = reader.load(LEDGER)
    if doc is None:
        return reader.finish(0, [])
    entries, stray = parse_ledger(doc)
    problems = []
    found = []
    for entry in entries:
        found.append((entry["index"], entry_problems(reader, doc, entry)))
    for index, text in stray:
        found.append((index, [f"{doc.where(index)}: heading is not an entry: {text}"]))
    seen = set()
    for entry in entries:
        if entry["id"] in seen:
            found.append((entry["index"], [f"{doc.where(entry['index'])}: duplicate entry identifier {entry['id']}"]))
        seen.add(entry["id"])
    for _, entry_list in sorted(found, key=lambda pair: pair[0]):
        problems.extend(entry_list)
    return reader.finish(len(entries), problems)


def entry_problems(reader: Reader, doc: Doc, entry) -> list[str]:
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
            target = reader.load(file_name)
            present = set()
            if target is not None:
                present = {text for _, level, text, _ in target.headings if level == 3}
            for heading in headings:
                if heading not in present:
                    problems.append(f'{where} names a missing heading: {file_name}, "{heading}"')
    return problems


# 7. shared-lists


def read_list(lines: list[str], first: int) -> list[str]:
    """Read the list whose first item is at line index first.

    An item starts at a list-item line at the indent of the first item. A
    line with a deeper indent belongs to the item above it, and so does a
    line that is not a list item and comes right after a line of the item
    (a lazy continuation). A blank line does not end the list. The list
    ends at a non-blank line after a blank line that is at or left of the
    list's indent and is not a list item at that indent, at a list item
    left of the list's indent, or at a heading or a fence line.
    """
    indent = len(LIST_ITEM.match(lines[first]).group(1))
    items = []
    after_blank = False
    for line in lines[first:]:
        if not line.strip():
            after_blank = True
            continue
        stripped = line.lstrip()
        depth = len(line) - len(stripped)
        item = LIST_ITEM.match(line)
        if FENCE.match(line) or HEADING.match(stripped):
            break
        if item and depth == indent:
            items.append([item.group(2)])
        elif item and depth < indent:
            break
        elif depth > indent or not after_blank:
            items[-1].append(stripped)
        else:
            break
        after_blank = False
    return [" ".join(" ".join(parts).split()) for parts in items]


def extract_copy(root: pathlib.Path, copy):
    """Return the items of one copy, or None when it cannot be found.

    Raises Unreadable when the file exists but cannot be read.
    """
    path = inside(root, root / copy["file"])
    if path is None or not os.path.lexists(path) or path.is_dir():
        return None
    text = read_text(path)
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
        if index >= len(lines) or not LIST_ITEM.match(lines[index]):
            return None
        items = read_list(lines, index)
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


def starts_item(got: str, want: str) -> bool:
    """The startswith rule: got starts with want, then ends or goes on with a non-alphanumeric character.

    A trailing period on want is ignored.
    """
    prefix = want[:-1] if want.endswith(".") else want
    if not got.startswith(prefix):
        return False
    rest = got[len(prefix):]
    return rest == "" or not rest[0].isalnum()


def check_shared_lists(root: pathlib.Path, table: dict = SHARED_LISTS) -> Result | None:
    """Check that each shared list reads the same in every copy.

    Items: every declared copy in the table. Copies are read from the raw
    file text, so an anchor inside a fenced block is found. The starter
    template keeps its lists inside a fence.

    - list: the list right after the first line that matches "after".
      Blank lines before it are skipped; any other line there means the
      copy is not found. See read_list for how items and the end of the
      list are found. An item's lines are joined with single spaces.
    - inline: the first match of "pattern" (multiline mode). Its group is
      split on commas; each part is stripped, and a leading "and " or
      "or " is dropped.
    - headings: every "### " heading inside the "## " section whose
      heading line matches "section".
    - A copy that cannot be found, or that has fewer than two items, fails.
      Problems: "FILE: LIST: copy not found" and "FILE: LIST: copy has
      fewer than two items". A file that cannot be read gives "FILE:
      cannot read: REASON" instead.
    - Each other copy is compared with the first copy, after "replace".
      With "match": "startswith", each item must start with the first
      copy's item (a trailing period on it is ignored), and then end or go
      on with a character that is not a letter or a digit. Report only
      the first differing item. A missing or extra item counts as
      different. Problem: 'FILE: LIST: item N differs: "GOT" does not
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
            try:
                values = extract_copy(root, copy)
            except Unreadable as error:
                problems.append(f"{copy['file']}: cannot read: {error}")
                found.append(None)
                continue
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
                    same = starts_item(got, want)
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

BANNED = re.compile(r"\boperating(?:\s+|-)(?:manual|guide)s?\b", re.IGNORECASE)
ASSISTANT = re.compile(r"\bassistants?\b", re.IGNORECASE)
AGENT_WORD = re.compile(r"agent", re.IGNORECASE)
MEANS_WORD = re.compile(r"\bmeans\b", re.IGNORECASE)
ASSISTANT_TEXT = re.compile(r"assistant", re.IGNORECASE)


def defines_assistant(line: str) -> bool:
    """True when the line matches "agent.*\\bmeans\\b.*assistant", ignoring case.

    It takes the first "agent", then the first "means" after it, then
    looks for "assistant" after that. Each search runs once, so this takes
    linear time.
    """
    agent = AGENT_WORD.search(line)
    if not agent:
        return False
    means = MEANS_WORD.search(line, agent.end())
    if not means:
        return False
    return ASSISTANT_TEXT.search(line, means.end()) is not None


def check_terms(root: pathlib.Path) -> Result | None:
    """Check banned terms in prose.

    Items: every prose line in every file. The inside of a Markdown
    example block is read as prose too (see Doc.example_prose).

    - No "operating manual" or "operating guide", in any letter case, and
      no plural. The two words may be joined by a hyphen or by any run of
      spaces, or sit on two lines of one paragraph. A word boundary must
      follow, so "operating guidelines" passes. The problem names the
      line of the first word.
      Problem: 'path:line: banned term "operating manual"'.
    - No word "assistant" or "assistants", in any letter case, unless the
      line also matches "agent.*\\bmeans\\b.*assistant", ignoring case.
      One problem per line.
      Problem: 'path:line: banned term "assistant"'.
    """
    reader = Reader(root)
    items = 0
    problems = []
    for doc in reader.walk():
        prose = doc.example_prose()
        found = []
        for text, starts in prose_paragraphs(prose):
            for match in BANNED.finditer(text):
                term = " ".join(match.group(0).lower().split())
                found.append((line_at(starts, match.start()), f'banned term "{term}"'))
        for index, line in enumerate(prose):
            if not line.strip():
                continue
            items += 1
            if ASSISTANT.search(line) and not defines_assistant(line):
                found.append((index, 'banned term "assistant"'))
        for index, message in sorted(found, key=lambda pair: pair[0]):
            problems.append(f"{doc.where(index)}: {message}")
    return reader.finish(items, problems)


# 9. glance

CHECKBOX = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+\[[ xX]\]")


def item_end(doc: Doc, start: int, end: int) -> int:
    """Return the index after the last line of the list item at start.

    A line belongs to the item when it is not a list item, not a heading,
    and not code, and either comes right after a line of the item or, after
    a blank line, is indented deeper than the item's marker.
    """
    indent = len(CHECKBOX.match(doc.lines[start]).group(1))
    last = start
    after_blank = False
    for index in range(start + 1, end):
        line = doc.lines[index]
        if doc.code[index]:
            break
        if not line.strip():
            after_blank = True
            continue
        stripped = line.lstrip()
        if LIST_ITEM.match(line) or HEADING.match(stripped):
            break
        if after_blank and len(line) - len(stripped) <= indent:
            break
        last = index
        after_blank = False
    return last + 1


def check_glance(root: pathlib.Path) -> Result | None:
    """Check the checklist in section 12 of FIELD-MANUAL.md.

    Section 12 runs from "## 12. " to the next "## " heading or "---"
    line. Items: every checklist item inside it. A checklist item is a
    list item (marker "-", "*", "+", or a number) whose text starts with
    "[ ]", "[x]", or "[X]". Its continuation lines belong to it (see
    item_end), so a link on a wrapped line counts. Checkboxes inside
    fenced code are not items. Problems name the item's first line.

    - Each item holds at least one link "[text](#fragment)".
      Problem: "FIELD-MANUAL.md:line: checklist item has no
      [text](#fragment) link".
    - Each such fragment is the slug of a "### " heading inside sections
      1 to 11. Repeated slugs are numbered over the whole file.
      Problem: "FIELD-MANUAL.md:line: #FRAGMENT is not a practice heading
      in sections 1 to 11".
    """
    reader = Reader(root)
    doc = reader.load(MANUAL)
    if doc is None:
        return reader.finish(0, [])
    practices = {heading_slug for _, level, _, heading_slug, section in heading_sections(doc)
                 if level == 3 and section in PRACTICE_SECTIONS}
    span = section_range(doc, GLANCE_SECTION, stop_at_rule=True)
    if span is None:
        return reader.finish(0, [])
    items = 0
    problems = []
    for index in range(span[0] + 1, span[1]):
        if doc.code[index] or not CHECKBOX.match(doc.lines[index]):
            continue
        items += 1
        stop = item_end(doc, index, span[1])
        text = " ".join(strip_code_spans(doc.lines[i]) for i in range(index, stop))
        fragments = [target[1:] for target in link_targets(text) if target.startswith("#")]
        if not fragments:
            problems.append(f"{doc.where(index)}: checklist item has no [text](#fragment) link")
        for fragment in fragments:
            if fragment not in practices:
                problems.append(f"{doc.where(index)}: #{fragment} is not a practice heading in sections 1 to 11")
    return reader.finish(items, problems)


# 10. version

VERSION_LINE = re.compile(r"^\*Version (v\d+(?:\.\d+)*), " + DATE + r"\.\*$")
GITHUB_REF = re.compile(r"^https://github\.com/[^/]+/[^/]+/(?:blob|tree)/([^/#?]+)")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def check_version(root: pathlib.Path) -> Result | None:
    """Check that the contract links pin the manual's version.

    Items: every link in AGENT-CONTRACT.md, outside code, whose target has
    the form "https://github.com/OWNER/REPO/blob/REF/..." or
    ".../tree/REF/...", and every relative link to a file. Links that are
    only "#fragment", links to other web addresses, and empty targets are
    not items.

    - FIELD-MANUAL.md holds exactly one line "*Version v2.0, 2026-11.*",
      outside fenced code. A line that does not match that shape is not a
      version line, and neither is a line inside a fenced block.
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
    reader = Reader(root)
    manual = reader.load(MANUAL)
    versions = []
    if manual is not None:
        for index, line in enumerate(manual.lines):
            match = VERSION_LINE.match(line)
            if match and not manual.code[index]:
                versions.append(match.group(1))
    problems = []
    if not versions:
        problems.append(f"{MANUAL}: no version line")
    elif len(versions) > 1:
        problems.append(f"{MANUAL}: {len(versions)} version lines, expected exactly one")
    version = versions[0] if len(versions) == 1 else None
    contract = reader.load(CONTRACT)
    items = 0
    if contract is not None:
        for index, line in enumerate(contract.lines):
            if contract.code[index]:
                continue
            for target in link_targets(strip_code_spans(line)):
                ref = GITHUB_REF.match(target)
                if ref:
                    items += 1
                    if version is not None and ref.group(1) != version:
                        problems.append(
                            f"{contract.where(index)}: link uses {ref.group(1)}, "
                            f"but the manual version is {version}"
                        )
                elif target == "" or target.startswith("#") or SCHEME.match(target):
                    continue
                else:
                    items += 1
                    problems.append(
                        f"{contract.where(index)}: relative link breaks when the contract is copied: {target}"
                    )
    return reader.finish(items, problems)


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


class UnknownCheck(ValueError):
    """A name passed to run() that is not a check."""


def run(root, only=None, require_all=False):
    """Run the checks and return (lines, exit_status).

    only: names of the checks to run, or None for all. The others print
    "not run". An unknown name raises UnknownCheck, a ValueError.
    Exit status is 1 when a check failed, or when require_all is true and
    a check did not run. Otherwise it is 0.
    """
    root = pathlib.Path(root)
    if only is not None:
        only = list(only)
        unknown = [name for name in only if name not in CHECKS]
        if unknown:
            raise UnknownCheck(f"unknown check: {', '.join(unknown)}")
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
    """Return [(file, paragraph)] for the Markdown files of one revision.

    Git runs in root, so names are relative to root and only files under
    it are listed, even when root is a subdirectory of the repository. A
    file under a directory whose name starts with a dot is skipped.
    """
    args = ["ls-tree", "-r", "-z", "--name-only", revision, "--"]
    if paths:
        args.extend(paths)
    names = []
    for name in _git(root, *args).split("\0"):
        if name.endswith(".md") and not any(part.startswith(".") for part in name.split("/")[:-1]):
            names.append(name)
    found = []
    for name in sorted(names):
        text = _git(root, "show", f"{revision}:./{name}")
        found.extend((name, paragraph) for paragraph in paragraphs(text))
    return found


def moved(root, base, head, paths=None):
    """Compare the Markdown paragraphs of two git revisions.

    Returns (lines, exit_status).

    Reads every "*.md" file under root in each revision, or only the given
    paths (relative to root). Files under a directory whose name starts
    with a dot are skipped. Each revision is read on its own, so a file
    that exists in only one revision still counts. A paragraph is a block
    of lines between blank lines, compared after collapsing whitespace.
    Paragraphs are compared as multisets across all files, so a paragraph
    that moved within a file or between files counts as unchanged, and a
    paragraph that appears twice in BASE and once in HEAD is one removed.

    Output: "added: N", "removed: N", "unchanged: N", then one line per
    added paragraph "+ FILE: first 80 characters", then one line per
    removed paragraph "- FILE: first 80 characters", each in file order.
    An added or removed paragraph is listed under a file whose own count
    of that paragraph changed in that direction.

    Exit status 0. Exit status 2 when git fails, or when neither revision
    gives any paragraph; the latter prints "moved: compared nothing" to
    standard error. Git runs with an argument list, never through a shell.
    """
    root = pathlib.Path(root)
    try:
        before = revision_paragraphs(root, base, paths)
        after = revision_paragraphs(root, head, paths)
    except GitError as error:
        print(f"moved: git failed: {error}", file=sys.stderr)
        return [], 2
    if not before and not after:
        print("moved: compared nothing", file=sys.stderr)
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
    old_by_file = collections.Counter(before)
    new_by_file = collections.Counter(after)
    for sign, listing, extra, room in (("+", after, added, new_by_file - old_by_file),
                                       ("-", before, removed, old_by_file - new_by_file)):
        left = collections.Counter(extra)
        for name, paragraph in listing:
            if left[paragraph] > 0 and room[(name, paragraph)] > 0:
                left[paragraph] -= 1
                room[(name, paragraph)] -= 1
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
    except UnknownCheck as error:
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

    A usage error returns 2. Only an unknown check name from run() is a
    usage error; any other error in a check is a bug and is raised. The
    "moved" command must come first.
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

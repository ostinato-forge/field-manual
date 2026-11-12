"""Unit tests for check_manual.py.

Every fixture is a small tree of files in a temporary directory. No test
reads the real repository.

Run from the repository root:

    env -i HOME="$(mktemp -d)" PATH="$PATH" python3 -m unittest scripts/test_check_manual.py -v
"""

from __future__ import annotations

import contextlib
import inspect
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import check_manual as cm  # noqa: E402

NOT_RUN_MESSAGE = "the check returned None, which prints as not run"

CHECK_ORDER = [
    "links",
    "fences",
    "punctuation",
    "sources",
    "evidence",
    "ledger",
    "shared-lists",
    "terms",
    "glance",
    "version",
]


def md(*lines: str) -> str:
    """Join lines into file text. Line N of the file is lines[N - 1]."""
    return "\n".join(lines) + "\n"


class FixtureCase(unittest.TestCase):
    """A test with a fresh temporary root directory."""

    check_name = None

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def check(self, *args) -> cm.Result:
        result = cm.CHECKS[self.check_name](self.root, *args)
        self.assertIsInstance(result, cm.Result, NOT_RUN_MESSAGE)
        return result

    def assertPassed(self, result, items=None):
        self.assertEqual(result.problems, [])
        self.assertGreater(result.items, 0)
        if items is not None:
            self.assertEqual(result.items, items)

    def assertOneProblem(self, result, *fragments):
        self.assertEqual(len(result.problems), 1, result.problems)
        for fragment in fragments:
            self.assertIn(fragment, result.problems[0])

    def assertHasProblem(self, result, *fragments):
        for problem in result.problems:
            if all(fragment in problem for fragment in fragments):
                return
        self.fail(f"no problem holds {fragments!r}: {result.problems!r}")

    def assertInspectedNothing(self, result):
        self.assertEqual(result.items, 0)
        self.assertIn("inspected nothing", result.problems)


# Structure


class StructureTest(unittest.TestCase):
    def test_checks_are_in_table_order(self):
        self.assertEqual(list(cm.CHECKS), CHECK_ORDER)

    def test_result_has_items_and_problems(self):
        result = cm.Result(items=3, problems=["a"])
        self.assertEqual((result.items, result.problems), (3, ["a"]))

    def test_shared_lists_constant_names(self):
        self.assertEqual(
            list(cm.SHARED_LISTS),
            [
                "authority-order",
                "stop-list",
                "review-order",
                "proof-levels",
                "result-states",
                "reporting-names",
                "rule-names",
            ],
        )

    def test_shared_lists_anchors_from_the_corrections(self):
        stop = {copy["file"]: copy for copy in cm.SHARED_LISTS["stop-list"]}
        rules = {copy["file"]: copy for copy in cm.SHARED_LISTS["rule-names"]}
        self.assertEqual(stop["FIELD-MANUAL.md"]["after"], r"^Most agent work is reversible")
        self.assertEqual(rules["AGENT-CONTRACT.md"]["after"], r"^These are the rules of section 3")

    def test_shared_lists_check_defaults_to_the_constant(self):
        parameters = list(inspect.signature(cm.CHECKS["shared-lists"]).parameters.values())
        self.assertEqual(len(parameters), 2)
        self.assertIs(parameters[1].default, cm.SHARED_LISTS)


# 1. links


class LinksTest(FixtureCase):
    check_name = "links"

    def test_valid_links_pass_and_count_items(self):
        self.write("FIELD-MANUAL.md", md(
            "# Manual",
            "",
            "## 1. Start",
            "",
            "See §1 and [b](docs/b.md#second-part).",
            "Web [w](https://example.com) and [m](mailto:a@example.com) and [self](#manual).",
            "Directory [d](docs).",
        ))
        self.write("docs/b.md", md(
            "# B",
            "",
            "## Second part",
            "",
            "Back [up](../FIELD-MANUAL.md#1-start).",
            "FIELD-MANUAL.md, section 1 has more.",
        ))
        self.assertPassed(self.check(), items=8)

    def test_slug_rule_removes_punctuation_and_keeps_underscores(self):
        self.write("a.md", md(
            "## What's new: v2 (beta)_ok",
            "",
            "[x](#whats-new-v2-beta_ok)",
        ))
        self.assertPassed(self.check(), items=1)

    def test_missing_target_file_fails(self):
        self.write("a.md", md("# A", "", "[x](missing.md)"))
        self.assertOneProblem(self.check(), "a.md:3:", "does not exist", "missing.md")

    def test_target_resolves_relative_to_the_linking_file(self):
        self.write("sub/a.md", md("[x](b.md)"))
        self.write("b.md", md("# B"))
        self.assertOneProblem(self.check(), "sub/a.md:1:", "does not exist", "b.md")

    def test_target_outside_the_root_fails(self):
        repo = self.root / "repo"
        self.write("outside.md", md("# Outside"))
        self.write("repo/a.md", md("# A", "", "[x](../outside.md)", "[y](../outside.md#outside)"))
        result = cm.CHECKS["links"](repo)
        self.assertIsInstance(result, cm.Result, NOT_RUN_MESSAGE)
        self.assertEqual(result.items, 2)
        self.assertEqual(result.problems, [
            "a.md:3: link target is outside the repository: ../outside.md",
            "a.md:4: link target is outside the repository: ../outside.md#outside",
        ])

    def test_absolute_target_fails(self):
        self.write("a.md", md("# A", "", "[x](/etc/hostname)"))
        self.assertOneProblem(self.check(), "a.md:3:", "outside the repository", "/etc/hostname")

    def test_fragment_missing_in_target_file_fails(self):
        self.write("a.md", md("[x](b.md#nope)"))
        self.write("b.md", md("# B"))
        self.assertOneProblem(self.check(), "a.md:1:", "no heading for fragment", "b.md#nope")

    def test_fragment_missing_in_own_file_fails(self):
        self.write("a.md", md("# A", "", "[x](#nope)"))
        self.assertOneProblem(self.check(), "a.md:3:", "no heading for fragment", "#nope")

    def test_repeated_heading_gets_numbered_slug(self):
        self.write("b.md", md("## Notes", "", "## Notes", "", "[ok](#notes-1)", "[bad](#notes-2)"))
        result = self.check()
        self.assertEqual(result.items, 2)
        self.assertOneProblem(result, "b.md:6:", "#notes-2")

    def test_heading_inside_fence_has_no_slug(self):
        self.write("a.md", md("[x](b.md#hidden)"))
        self.write("b.md", md("# B", "", "````markdown", "## Hidden", "````"))
        self.assertOneProblem(self.check(), "a.md:1:", "b.md#hidden")

    def test_missing_section_sign_reference_fails(self):
        self.write("FIELD-MANUAL.md", md("# Manual", "", "## 1. Start", "", "See §1 and §2."))
        result = self.check()
        self.assertEqual(result.items, 2)
        self.assertOneProblem(result, "FIELD-MANUAL.md:5:", "section 2")

    def test_missing_section_reference_in_other_file_fails(self):
        self.write("FIELD-MANUAL.md", md("# Manual", "", "## 1. Start"))
        self.write("METHOD.md", md("# Method", "", "Why: FIELD-MANUAL.md, section 3."))
        result = self.check()
        self.assertEqual(result.items, 1)
        self.assertOneProblem(result, "METHOD.md:3:", "section 3")

    def test_links_and_references_inside_code_are_ignored(self):
        self.write("FIELD-MANUAL.md", md(
            "# Manual",
            "",
            "Code `[x](missing.md)` and `§9` here.",
            "",
            "```text",
            "[y](missing.md) §9",
            "```",
            "",
            "[ok](#manual)",
        ))
        self.assertPassed(self.check(), items=1)

    def test_no_links_inspects_nothing(self):
        self.write("a.md", md("# A", "", "Plain text."))
        self.assertInspectedNothing(self.check())


# 2. fences


class FencesTest(FixtureCase):
    check_name = "fences"

    def test_valid_fences_pass_and_count_fence_lines(self):
        self.write("a.md", md(
            "```text",
            "code",
            "```",
            "",
            "````markdown",
            "```text",
            "inner",
            "```",
            "````",
        ))
        self.assertPassed(self.check(), items=4)

    def test_backtick_line_with_info_does_not_close(self):
        self.write("a.md", md("```", "code", "```text", "```"))
        self.assertPassed(self.check(), items=2)

    def test_longer_run_closes_a_shorter_fence(self):
        self.write("a.md", md("```", "code", "````"))
        self.assertPassed(self.check(), items=2)

    def test_file_ending_inside_a_block_fails(self):
        self.write("a.md", md("# A", "", "```text", "code"))
        self.assertOneProblem(self.check(), "a.md:3:", "never closed")

    def test_shorter_run_does_not_close_so_block_stays_open(self):
        self.write("a.md", md("````text", "code", "```"))
        self.assertOneProblem(self.check(), "a.md:1:", "never closed")

    def test_markdown_block_with_three_backticks_fails(self):
        for info in ("markdown", "md", "Markdown"):
            with self.subTest(info=info):
                self.write("a.md", md("Intro.", f"```{info}", "# Title", "```"))
                self.assertOneProblem(
                    self.check(),
                    "a.md:2: a markdown example block needs a fence of four or more backticks",
                )

    def test_no_fences_inspects_nothing(self):
        self.write("a.md", md("# A", "", "Plain text."))
        self.assertInspectedNothing(self.check())


# 3. punctuation


class PunctuationTest(FixtureCase):
    check_name = "punctuation"

    def test_clean_prose_passes_and_counts_prose_lines(self):
        self.write("a.md", md(
            "---",
            "title: Notes",
            "---",
            "# Notes",
            "",
            "A well-known fact; use `a -- b` in code, and the --only flag.",
            "-----",
            "| a | b |",
            "|---|---|",
            "| 1 | 2 |",
        ))
        self.assertPassed(self.check(), items=8)

    def test_forbidden_characters_fail(self):
        for char in ("\u2014", "\u2013", "\u2018", "\u2019", "\u201c", "\u201d"):
            with self.subTest(code=f"U+{ord(char):04X}"):
                self.write("a.md", md("# A", f"Bad{char}here."))
                self.assertOneProblem(self.check(), "a.md:2:", f"U+{ord(char):04X}")

    def test_doubled_hyphen_fails(self):
        for line in ("one -- two", "one --- two", "one--two", "one---two", "ends with --",
                     "-- starts here"):
            with self.subTest(line=line):
                self.write("a.md", md("# A", line))
                self.assertOneProblem(self.check(), "a.md:2:", "doubled hyphen")

    def test_hyphen_forms_that_pass(self):
        for line in ("the --only flag", "-----", "well-known", "- - -", "<!-- a note -->"):
            with self.subTest(line=line):
                self.write("a.md", md("# A", line))
                self.assertPassed(self.check(), items=2)

    def test_code_is_not_prose(self):
        self.write("a.md", md(
            "# A",
            "Inline `a\u2014b` is fine.",
            "",
            "```text",
            "one -- two \u2019",
            "```",
        ))
        self.assertPassed(self.check(), items=2)

    def test_reads_markdown_at_any_depth_and_nothing_else(self):
        self.write("a.md", md("Fine."))
        self.write("sub/dir/x.md", md("Bad\u2014here."))
        self.write(".git/x.md", md("Bad\u2014here."))
        self.write("LICENSE", md("Bad\u2014here."))
        self.write("notes.txt", md("Bad\u2014here."))
        result = self.check()
        self.assertEqual(result.items, 2)
        self.assertOneProblem(result, "sub/dir/x.md:1:", "U+2014")

    def test_skips_every_dot_directory(self):
        self.write("a.md", md("Fine."))
        self.write(".remember/x.md", md("Bad\u2014here."))
        self.write("sub/.cache/y.md", md("Bad\u2014here."))
        self.assertPassed(self.check(), items=1)

    def test_no_prose_inspects_nothing(self):
        self.write("a.md", md("```text", "only code", "```"))
        self.assertInspectedNothing(self.check())


# 4. sources

E1 = '- **S1.** [First](https://example.com/1) (2026-01). Supports section 1: "first quote". Read 2026-11.'
E2 = ('- **S2.** [Second](https://example.com/2) (2025, a journal). '
      'Supports sections 1 and 2, on things: "second quote". Read 2026-10.')


def sources_manual(body, entries, after=()):
    """A manual with sections 1 and 2, a Sources section, and a License.

    The body starts at line 5. The first entry is at line len(body) + 15.
    """
    return md(
        "# Manual",
        "",
        "## 1. One",
        "",
        *body,
        "",
        "## 2. Two",
        "",
        "Text.",
        "",
        "## Sources",
        "",
        "Each entry names a section.",
        "",
        "### Research",
        *entries,
        "",
        "---",
        "",
        "## License",
        "",
        *after,
    )


class SourcesTest(FixtureCase):
    check_name = "sources"

    def test_valid_sources_pass_and_count_entries_and_citation_groups(self):
        self.write("FIELD-MANUAL.md", sources_manual(
            ["Claim (S1).", "Other claim (S1, S2)."],
            [E1, E2],
            after=["- Not an entry."],
        ))
        self.assertPassed(self.check(), items=4)

    def test_entry_with_wrong_shape_fails(self):
        third = {
            "no link": '- **S3.** Third (2026-01). Supports section 1: "q". Read 2026-11.',
            "no parenthesis": '- **S3.** [Third](https://example.com/3). Supports section 1: "q". Read 2026-11.',
            "no Supports": '- **S3.** [Third](https://example.com/3) (2026-01). About section 1: "q". Read 2026-11.',
            "no quote": '- **S3.** [Third](https://example.com/3) (2026-01). Supports section 1: q. Read 2026-11.',
            "no Read": '- **S3.** [Third](https://example.com/3) (2026-01). Supports section 1: "q".',
            "bad Read date": '- **S3.** [Third](https://example.com/3) (2026-01). Supports section 1: "q". Read November.',
            "Read month 13": '- **S3.** [Third](https://example.com/3) (2026-01). Supports section 1: "q". Read 2026-13.',
        }
        for name, entry in third.items():
            with self.subTest(name):
                self.write("FIELD-MANUAL.md", sources_manual(
                    ["Claim (S1, S2, S3)."], [E1, E2, entry]))
                self.assertOneProblem(self.check(), "FIELD-MANUAL.md:18:", "does not match")

    def test_entry_without_key_fails(self):
        entry = '- [Third](https://example.com/3) (2026-01). Supports section 1: "q". Read 2026-11.'
        self.write("FIELD-MANUAL.md", sources_manual(["Claim (S1, S2)."], [E1, E2, entry]))
        self.assertOneProblem(self.check(), "FIELD-MANUAL.md:18:", "does not match")

    def test_duplicate_key_fails(self):
        self.write("FIELD-MANUAL.md", sources_manual(["Claim (S1)."], [E1, E1]))
        self.assertOneProblem(self.check(), "FIELD-MANUAL.md:17:", "duplicate source key S1")

    def test_supports_names_missing_section(self):
        entry = ('- **S2.** [Second](https://example.com/2) (2026-01). '
                 'Supports sections 1, 2, and 9: "q". Read 2026-11.')
        self.write("FIELD-MANUAL.md", sources_manual(["Claim (S1, S2)."], [E1, entry]))
        self.assertOneProblem(self.check(), "FIELD-MANUAL.md:17:", "S2", "section 9")

    def test_supports_names_missing_section_in_a_later_phrase(self):
        entry = ('- **S2.** [Second](https://example.com/2) (2026-01). '
                 'Supports section 1, "One"; and section 7, "Seven": "q". Read 2026-11.')
        self.write("FIELD-MANUAL.md", sources_manual(["Claim (S1, S2)."], [E1, entry]))
        self.assertOneProblem(self.check(), "S2", "section 7")

    def test_section_words_inside_a_quote_are_not_read(self):
        entry = ('- **S2.** [Second](https://example.com/2) (2026-01). '
                 'Supports section 2, "As section 9 says": "see section 9 too". Read 2026-11.')
        self.write("FIELD-MANUAL.md", sources_manual(["Claim (S1, S2)."], [E1, entry]))
        self.assertPassed(self.check(), items=3)

    def test_citation_without_entry_fails(self):
        self.write("FIELD-MANUAL.md", sources_manual(["Claim (S1).", "More (S7)."], [E1]))
        self.assertOneProblem(self.check(), "FIELD-MANUAL.md:6:", "S7", "no source entry")

    def test_entry_never_cited_fails(self):
        self.write("FIELD-MANUAL.md", sources_manual(["Claim (S1)."], [E1, E2]))
        self.assertOneProblem(self.check(), "FIELD-MANUAL.md:17:", "S2", "never cited")

    def test_citation_below_sources_does_not_count(self):
        self.write("FIELD-MANUAL.md", sources_manual(["Claim (S1)."], [E1, E2], after=["See (S2)."]))
        self.assertOneProblem(self.check(), "S2", "never cited")

    def test_no_sources_section_inspects_nothing(self):
        self.write("FIELD-MANUAL.md", md("# Manual", "", "## 1. One", "", "Text."))
        self.assertInspectedNothing(self.check())

    def test_missing_manual_inspects_nothing(self):
        self.write("a.md", md("# A"))
        self.assertInspectedNothing(self.check())


# 5. evidence


def evidence_manual(alpha_tags="researched, observed", alpha_text="Alpha text (S1).",
                    beta_tags="incident", beta_text="Beta text (S1)."):
    """A manual with practices Alpha (line 7) and Beta (line 10) in section 1,
    and Gamma (line 15) and Delta (line 18) in section 11.
    """
    return md(
        "# Manual",
        "## What This Is",
        "### Intro heading",
        "Text.",
        "",
        "## 1. One",
        "### Alpha",
        f"*Evidence: {alpha_tags}.*",
        alpha_text,
        "### Beta",
        "",
        f"*Evidence: {beta_tags}.*",
        beta_text,
        "## 11. Eleven",
        "### Gamma",
        "*Evidence: converged.*",
        "Text (S1, S2).",
        "### Delta",
        "*Evidence: incident (undated).*",
        "Text.",
        "## 12. Glance",
        "### Before",
        "- [ ] thing",
    )


def ledger_entry(ident, when, supports, record="Notes."):
    return [
        f"## {ident}: A failure",
        "",
        f"- When: {when}",
        "- What happened: A thing broke.",
        "- Rule: Check first.",
        f"- Supports: {supports}",
        f"- Record: {record}",
        "",
    ]


BETA_DATED = ledger_entry("I-01", "2026-03", 'FIELD-MANUAL.md, "Beta"')
DELTA_UNDATED = ledger_entry("I-02", "not recorded", 'FIELD-MANUAL.md, "Delta"')


class EvidenceTest(FixtureCase):
    check_name = "evidence"

    def write_ledger(self, *entries):
        lines = ["# Incidents", ""]
        for entry in entries:
            lines.extend(entry)
        self.write("INCIDENTS.md", md(*lines))

    def test_valid_practices_pass_and_count_headings_in_sections_1_to_11(self):
        self.write("FIELD-MANUAL.md", evidence_manual())
        self.write_ledger(BETA_DATED, DELTA_UNDATED)
        self.assertPassed(self.check(), items=4)

    def test_missing_evidence_line_fails(self):
        self.write("FIELD-MANUAL.md", evidence_manual().replace("*Evidence: incident.*\n", ""))
        self.write_ledger(BETA_DATED, DELTA_UNDATED)
        self.assertOneProblem(self.check(), "FIELD-MANUAL.md:10:", '"Beta"', "no evidence line")

    def test_evidence_line_without_asterisks_is_not_an_evidence_line(self):
        self.write("FIELD-MANUAL.md", evidence_manual().replace(
            "*Evidence: incident.*", "Evidence: incident."))
        self.write_ledger(BETA_DATED, DELTA_UNDATED)
        self.assertOneProblem(self.check(), '"Beta"', "no evidence line")

    def test_unknown_tag_fails(self):
        self.write("FIELD-MANUAL.md", evidence_manual(alpha_tags="researched, vibes"))
        self.write_ledger(BETA_DATED, DELTA_UNDATED)
        self.assertOneProblem(self.check(), "FIELD-MANUAL.md:7:", '"Alpha"', '"vibes"')

    def test_both_incident_tags_fail(self):
        self.write("FIELD-MANUAL.md", evidence_manual(beta_tags="incident, incident (undated)"))
        self.write_ledger(BETA_DATED, DELTA_UNDATED)
        self.assertHasProblem(self.check(), '"Beta"', "both incident and incident (undated)")

    def test_researched_or_converged_without_own_citation_fails(self):
        for tag in ("researched", "converged"):
            with self.subTest(tag=tag):
                self.write("FIELD-MANUAL.md", evidence_manual(alpha_tags=tag, alpha_text="No citation."))
                self.write_ledger(BETA_DATED, DELTA_UNDATED)
                self.assertOneProblem(
                    self.check(), "FIELD-MANUAL.md:7:", '"Alpha"', f"tagged {tag}", "cites no source")

    def test_incident_without_ledger_entry_fails(self):
        self.write("FIELD-MANUAL.md", evidence_manual())
        self.write_ledger(DELTA_UNDATED)
        self.assertOneProblem(self.check(), "FIELD-MANUAL.md:10:", '"Beta"', "no ledger entry names it")

    def test_ledger_entry_for_another_file_does_not_count(self):
        self.write("FIELD-MANUAL.md", evidence_manual())
        self.write_ledger(ledger_entry("I-01", "2026-03", 'METHOD.md, "Beta"'), DELTA_UNDATED)
        self.assertOneProblem(self.check(), '"Beta"', "no ledger entry names it")

    def test_incident_with_only_undated_entries_fails(self):
        self.write("FIELD-MANUAL.md", evidence_manual())
        self.write_ledger(ledger_entry("I-01", "not recorded", 'FIELD-MANUAL.md, "Beta"'), DELTA_UNDATED)
        result = self.check()
        self.assertOneProblem(result, "FIELD-MANUAL.md:10:", '"Beta"', "use incident (undated)")

    def test_undated_incident_with_a_dated_entry_fails(self):
        self.write("FIELD-MANUAL.md", evidence_manual())
        self.write_ledger(BETA_DATED, ledger_entry("I-02", "2026-04", 'FIELD-MANUAL.md, "Delta"'))
        result = self.check()
        self.assertOneProblem(result, "FIELD-MANUAL.md:18:", '"Delta"')
        self.assertTrue(result.problems[0].endswith("use incident"), result.problems)

    def test_no_practices_inspects_nothing(self):
        self.write("FIELD-MANUAL.md", md("# Manual", "## 1. One", "Text.", "## 12. Glance", "### Before"))
        self.assertInspectedNothing(self.check())


# 6. ledger


class LedgerTest(FixtureCase):
    check_name = "ledger"

    def setUp(self):
        super().setUp()
        self.write("FIELD-MANUAL.md", md(
            "# Manual",
            "## 1. One",
            "### Alpha",
            "### Beta",
            "## Delta",
        ))

    def write_ledger(self, *entries):
        lines = ["# Incidents", "", "Intro text.", ""]
        for entry in entries:
            lines.extend(entry)
        self.write("INCIDENTS.md", md(*lines))

    def first(self, **changes):
        """Entry I-01 starts at line 5 of the ledger."""
        fields = {"when": "2026-03", "supports": 'FIELD-MANUAL.md, "Alpha"'}
        fields.update(changes)
        return ledger_entry("I-01", fields["when"], fields["supports"])

    SECOND = ledger_entry("I-02", "not recorded", 'FIELD-MANUAL.md, "Alpha" and "Beta"')

    def test_valid_ledger_passes_and_counts_entries(self):
        self.write_ledger(self.first(), self.SECOND)
        self.assertPassed(self.check(), items=2)

    def test_wrapped_field_continues_the_item(self):
        entry = self.first()
        entry.insert(4, "  across two lines.")
        self.write_ledger(entry, self.SECOND)
        self.assertPassed(self.check(), items=2)

    def test_fields_missing_out_of_order_or_extra_fail(self):
        base = self.first()
        variants = {
            "missing Record": base[:6] + base[7:],
            "out of order": base[:3] + [base[4], base[3]] + base[5:],
            "extra item": base[:7] + ["- Note: more."] + base[7:],
        }
        for name, entry in variants.items():
            with self.subTest(name):
                self.write_ledger(entry, self.SECOND)
                self.assertOneProblem(self.check(), "INCIDENTS.md:5:", "I-01", "in that order")

    def test_empty_field_fails(self):
        entry = self.first()
        entry[4] = "- Rule:"
        self.write_ledger(entry, self.SECOND)
        self.assertOneProblem(self.check(), "INCIDENTS.md:5:", "I-01", "empty Rule")

    def test_bad_when_fails(self):
        for when in ("March 2026", "2026-3", "unknown", "2026-13", "2026-00"):
            with self.subTest(when=when):
                self.write_ledger(self.first(when=when), self.SECOND)
                self.assertOneProblem(self.check(), "I-01", "When", f'"{when}"')

    def test_bad_supports_shape_fails(self):
        for supports in ("FIELD-MANUAL.md Alpha", 'FIELD-MANUAL.md, Alpha', '"Alpha"'):
            with self.subTest(supports=supports):
                self.write_ledger(self.first(supports=supports), self.SECOND)
                self.assertOneProblem(self.check(), "I-01", "bad Supports value")

    def test_missing_heading_fails(self):
        cases = {
            "absent": ('FIELD-MANUAL.md, "Gamma"', "Gamma"),
            "letter case differs": ('FIELD-MANUAL.md, "alpha"', "alpha"),
            "not a ### heading": ('FIELD-MANUAL.md, "Delta"', "Delta"),
            "second of two": ('FIELD-MANUAL.md, "Alpha" and "Gamma"', "Gamma"),
            "file missing": ('NOPE.md, "Alpha"', "NOPE.md"),
        }
        for name, (supports, fragment) in cases.items():
            with self.subTest(name):
                self.write_ledger(self.first(supports=supports), self.SECOND)
                self.assertOneProblem(self.check(), "I-01", "missing heading", fragment)

    def test_heading_that_is_not_an_entry_fails(self):
        for heading in ("I-7 Missing colon", "I-07:No space", "About this file", "I-x: Letters"):
            with self.subTest(heading=heading):
                self.write_ledger(self.first(), self.SECOND, [f"## {heading}", "", "Text.", ""])
                result = self.check()
                self.assertEqual(result.items, 2)
                self.assertOneProblem(result, f"INCIDENTS.md:21: heading is not an entry: {heading}")

    def test_duplicate_identifier_fails(self):
        second = ledger_entry("I-01", "not recorded", 'FIELD-MANUAL.md, "Beta"')
        self.write_ledger(self.first(), second)
        self.assertOneProblem(self.check(), "INCIDENTS.md:13:", "duplicate entry identifier I-01")

    def test_missing_file_inspects_nothing(self):
        self.assertInspectedNothing(self.check())

    def test_file_without_entries_inspects_nothing(self):
        self.write("INCIDENTS.md", md("# Incidents", "", "## About", "", "Text."))
        self.assertInspectedNothing(self.check())


# 7. shared-lists


class SharedListsTest(FixtureCase):
    check_name = "shared-lists"

    def two_copies(self, second, first=None):
        first = first or {"file": "a.md", "kind": "list", "after": r"^Use this order:"}
        return {"order": [first, second]}

    def test_equal_copies_pass_and_count_copies(self):
        self.write("a.md", md("Use this order:", "", "- One thing.", "- Two  things.", "", "After."))
        self.write("b.md", md("Intro.", "Check in this order:", "1. One thing.", "2. Two things."))
        table = self.two_copies({"file": "b.md", "kind": "list", "after": r"^Check in this order:"})
        self.assertPassed(self.check(table), items=2)

    def test_changed_item_fails(self):
        self.write("a.md", md("Use this order:", "", "- One thing.", "- Two things."))
        self.write("b.md", md("Check in this order:", "", "- One thing.", "- Three things."))
        table = self.two_copies({"file": "b.md", "kind": "list", "after": r"^Check in this order:"})
        self.assertOneProblem(self.check(table), "b.md", "order", "item 2", "Three things.", "Two things.")

    def test_missing_item_fails(self):
        self.write("a.md", md("Use this order:", "", "- One.", "- Two.", "- Three."))
        self.write("b.md", md("Check in this order:", "", "- One.", "- Two."))
        table = self.two_copies({"file": "b.md", "kind": "list", "after": r"^Check in this order:"})
        self.assertOneProblem(self.check(table), "b.md", "item 3", "(missing)")

    def test_extra_item_fails(self):
        self.write("a.md", md("Use this order:", "", "- One.", "- Two."))
        self.write("b.md", md("Check in this order:", "", "- One.", "- Two.", "- Three."))
        table = self.two_copies({"file": "b.md", "kind": "list", "after": r"^Check in this order:"})
        self.assertOneProblem(self.check(table), "b.md", "item 3", "Three.", "(missing)")

    def test_missing_anchor_fails(self):
        self.write("a.md", md("Use this order:", "", "- One.", "- Two."))
        self.write("b.md", md("Some other text.", "", "- One.", "- Two."))
        table = self.two_copies({"file": "b.md", "kind": "list", "after": r"^Check in this order:"})
        self.assertOneProblem(self.check(table), "b.md", "order", "not found")

    def test_anchor_followed_by_text_is_not_found(self):
        self.write("a.md", md("Use this order:", "", "- One.", "- Two."))
        self.write("b.md", md("Check in this order:", "", "A paragraph first.", "", "- One.", "- Two."))
        table = self.two_copies({"file": "b.md", "kind": "list", "after": r"^Check in this order:"})
        self.assertOneProblem(self.check(table), "b.md", "not found")

    def test_missing_file_fails(self):
        self.write("a.md", md("Use this order:", "", "- One.", "- Two."))
        table = self.two_copies({"file": "b.md", "kind": "list", "after": r"^Check in this order:"})
        self.assertOneProblem(self.check(table), "b.md", "not found")

    def test_copy_with_one_item_fails(self):
        self.write("a.md", md("Use this order:", "", "- One.", "- Two."))
        self.write("b.md", md("Check in this order:", "", "- One.", "", "- Two."))
        table = self.two_copies({"file": "b.md", "kind": "list", "after": r"^Check in this order:"})
        self.assertOneProblem(self.check(table), "b.md", "fewer than two items")

    def test_replace_substitutes_before_comparing(self):
        self.write("a.md", md("Use this order:", "", "1. The user.", "2. The project guide, then code."))
        self.write("b.md", md("## Authority order", "", "1. The user.", "2. This file, then code."))
        table = self.two_copies({"file": "b.md", "kind": "list", "after": r"^## Authority order",
                                 "replace": [("This file", "The project guide")]})
        self.assertPassed(self.check(table), items=2)

    def test_inline_lists_compare_and_drop_and_or(self):
        self.write("a.md", md("# A", "| Result | One check | passed, failed, not run |"))
        self.write("b.md", md("Use explicit states: passed, failed, and not run. More."))
        self.write("c.md", md("Use explicit states: passed, failed, or not run."))
        table = {"states": [
            {"file": "a.md", "kind": "inline", "pattern": r"^\| Result \| One check \| (.+?) \|$"},
            {"file": "b.md", "kind": "inline", "pattern": r"Use explicit states: (.+?)\."},
            {"file": "c.md", "kind": "inline", "pattern": r"Use explicit states: (.+?)\."},
        ]}
        self.assertPassed(self.check(table), items=3)

    def test_inline_difference_fails(self):
        self.write("a.md", md("Use explicit states: passed, failed."))
        self.write("b.md", md("Use explicit states: passed, broken."))
        table = {"states": [
            {"file": "a.md", "kind": "inline", "pattern": r"Use explicit states: (.+?)\."},
            {"file": "b.md", "kind": "inline", "pattern": r"Use explicit states: (.+?)\."},
        ]}
        self.assertOneProblem(self.check(table), "b.md", "item 2", "broken")

    def test_inline_without_match_fails(self):
        self.write("a.md", md("Use explicit states: passed, failed."))
        self.write("b.md", md("No states here."))
        table = {"states": [
            {"file": "a.md", "kind": "inline", "pattern": r"Use explicit states: (.+?)\."},
            {"file": "b.md", "kind": "inline", "pattern": r"Use explicit states: (.+?)\."},
        ]}
        self.assertOneProblem(self.check(table), "b.md", "not found")

    def rules_table(self):
        return {"rules": [
            {"file": "a.md", "kind": "headings", "section": r"^## 3\. "},
            {"file": "b.md", "kind": "list", "after": r"^## The rules", "match": "startswith"},
        ]}

    def write_rule_headings(self):
        self.write("a.md", md(
            "## 2. Before",
            "### Not a rule",
            "## 3. The rules",
            "### Keep one plan.",
            "Text.",
            "### Prove the slice",
            "## 4. After",
            "### Also not a rule",
        ))

    def test_headings_with_startswith_and_trailing_period_pass(self):
        self.write_rule_headings()
        self.write("b.md", md("## The rules", "", "1. Keep one plan, always.", "2. Prove the slice first."))
        self.assertPassed(self.check(self.rules_table()), items=2)

    def test_startswith_mismatch_fails(self):
        self.write_rule_headings()
        self.write("b.md", md("## The rules", "", "1. Keep one plan, always.", "2. Ship the slice."))
        self.assertOneProblem(self.check(self.rules_table()), "b.md", "item 2", "Ship the slice.")

    def test_headings_without_section_fails(self):
        self.write("a.md", md("## 2. Before", "### One", "### Two"))
        self.write("b.md", md("## The rules", "", "1. One.", "2. Two."))
        self.assertOneProblem(self.check(self.rules_table()), "a.md", "not found")

    def test_nested_list_under_a_list_item_anchor(self):
        self.write("a.md", md("Stop and ask the human before:", "", "- Deleting data.", "- Publishing."))
        self.write("b.md", md(
            "## Working together",
            "",
            "- Push back.",
            "- Stop and ask before:",
            "  - Deleting data.",
            "  - Publishing.",
            "- Report only what you saw.",
        ))
        table = {"stops": [
            {"file": "a.md", "kind": "list", "after": r"^Stop and ask the human before:"},
            {"file": "b.md", "kind": "list", "after": r"^- Stop and ask before:"},
        ]}
        self.assertPassed(self.check(table), items=2)

    def test_anchor_inside_a_fence_is_found(self):
        self.write("a.md", md("Use this order:", "", "1. One.", "2. Two."))
        self.write("b.md", md("Copy this:", "", "````markdown", "## Order", "", "1. One.", "2. Two.", "````"))
        table = self.two_copies({"file": "b.md", "kind": "list", "after": r"^## Order"})
        self.assertPassed(self.check(table), items=2)

    def test_empty_table_inspects_nothing(self):
        self.assertInspectedNothing(self.check({}))


# 8. terms


class TermsTest(FixtureCase):
    check_name = "terms"

    def test_clean_prose_passes_and_counts_lines(self):
        self.write("a.md", md(
            "# Agents",
            "",
            "In this guide, agent means any coding assistant.",
            "An assistantship is a job.",
        ))
        self.assertPassed(self.check(), items=3)

    def test_operating_terms_fail(self):
        for line in ("Write an operating manual.", "The Operating Guide.", "OPERATING MANUAL",
                     "A starter operating-manual template.", "The Operating-Guide."):
            with self.subTest(line=line):
                self.write("a.md", md("# A", line))
                self.assertOneProblem(self.check(), "a.md:2:", "operating")

    def test_assistant_fails(self):
        for line in ("An assistant helps.", "Assistants help.", "[assistant](x.md) here."):
            with self.subTest(line=line):
                self.write("a.md", md("# A", line))
                self.assertOneProblem(self.check(), "a.md:2:", "assistant")

    def test_definition_on_another_line_does_not_excuse(self):
        self.write("a.md", md("Agent means a coding tool.", "An assistant helps."))
        self.assertOneProblem(self.check(), "a.md:2:", "assistant")

    def test_code_and_link_targets_are_not_prose(self):
        self.write("a.md", md(
            "Use `operating manual` and [the page](https://example.com/assistant).",
            "",
            "```text",
            "assistant",
            "```",
        ))
        self.assertPassed(self.check(), items=1)

    def test_no_prose_inspects_nothing(self):
        self.write("a.md", md("```text", "only code", "```"))
        self.assertInspectedNothing(self.check())


# 9. glance


def glance_manual(*items):
    """A manual whose section 12 checklist items start at line 11."""
    return md(
        "# Manual",
        "## 1. One",
        "### Alpha",
        "Text.",
        "## 11. Eleven",
        "### Beta",
        "Text.",
        "## 12. The Practices at a Glance",
        "Intro.",
        "### Before you start",
        *items,
        "",
        "---",
        "",
        "## Worked Example",
        "### Gamma",
        "- [ ] Outside item without a link",
    )


class GlanceTest(FixtureCase):
    check_name = "glance"

    def test_valid_checklist_passes_and_counts_items(self):
        self.write("FIELD-MANUAL.md", glance_manual(
            "- [ ] Do alpha ([Alpha](#alpha))",
            "- [ ] Do beta, see [Beta](#beta) and [Alpha](#alpha)",
        ))
        self.assertPassed(self.check(), items=2)

    def test_item_without_fragment_link_fails(self):
        for item in ("- [ ] Do things", "- [ ] See [the method](METHOD.md)"):
            with self.subTest(item=item):
                self.write("FIELD-MANUAL.md", glance_manual("- [ ] Do alpha ([Alpha](#alpha))", item))
                self.assertOneProblem(self.check(), "FIELD-MANUAL.md:12:", "no [text](#fragment) link")

    def test_fragment_that_is_not_a_practice_fails(self):
        for fragment in ("nope", "gamma", "1-one", "before-you-start"):
            with self.subTest(fragment=fragment):
                self.write("FIELD-MANUAL.md", glance_manual(
                    "- [ ] Do alpha ([Alpha](#alpha))", f"- [ ] Do it ([x](#{fragment}))"))
                self.assertOneProblem(self.check(), "FIELD-MANUAL.md:12:", f"#{fragment}")

    def test_repeated_slugs_are_numbered_over_the_whole_file(self):
        for fragment, problems in (("alpha", 1), ("alpha-1", 0)):
            with self.subTest(fragment=fragment):
                self.write("FIELD-MANUAL.md", md(
                    "## What This Is",
                    "### Alpha",
                    "## 1. One",
                    "### Alpha",
                    "## 12. Glance",
                    f"- [ ] Do alpha ([Alpha](#{fragment}))",
                ))
                result = self.check()
                self.assertEqual(result.items, 1)
                self.assertEqual(len(result.problems), problems, result.problems)

    def test_section_12_ends_at_next_section_heading(self):
        self.write("FIELD-MANUAL.md", md(
            "## 1. One",
            "### Alpha",
            "## 12. Glance",
            "- [ ] Do alpha ([Alpha](#alpha))",
            "## Worked Example",
            "- [ ] Outside item without a link",
        ))
        self.assertPassed(self.check(), items=1)

    def test_no_section_12_inspects_nothing(self):
        self.write("FIELD-MANUAL.md", md("## 1. One", "### Alpha"))
        self.assertInspectedNothing(self.check())

    def test_section_12_without_checkboxes_inspects_nothing(self):
        self.write("FIELD-MANUAL.md", glance_manual("Plain text."))
        self.assertInspectedNothing(self.check())


# 10. version


class VersionTest(FixtureCase):
    check_name = "version"

    def write_contract(self, ref_two="v2.0"):
        self.write("AGENT-CONTRACT.md", md(
            "# Agent Contract",
            "",
            "The method is [METHOD.md](https://github.com/o/r/blob/v2.0/METHOD.md).",
            f"The manual is [here](https://github.com/o/r/blob/{ref_two}/FIELD-MANUAL.md#x).",
            "Other [page](https://example.com) and [top](#agent-contract).",
        ))

    def test_matching_version_passes_and_counts_links(self):
        self.write("FIELD-MANUAL.md", md("# Manual", "", "*Version v2.0, 2026-11.*"))
        self.write_contract()
        self.assertPassed(self.check(), items=2)

    def test_link_with_other_ref_fails(self):
        self.write("FIELD-MANUAL.md", md("# Manual", "", "*Version v2.0, 2026-11.*"))
        self.write_contract(ref_two="main")
        result = self.check()
        self.assertEqual(result.items, 2)
        self.assertOneProblem(result, "AGENT-CONTRACT.md:4:", "main", "v2.0")

    def test_no_version_line_fails(self):
        for line in ("Plain text.", "*Version 2.0, 2026-11.*", "*Version v2.0, Nov 2026.*",
                     "*Version v2.0, 2026-13.*"):
            with self.subTest(line=line):
                self.write("FIELD-MANUAL.md", md("# Manual", "", line))
                self.write_contract()
                self.assertOneProblem(self.check(), "FIELD-MANUAL.md", "no version line")

    def test_two_version_lines_fail(self):
        self.write("FIELD-MANUAL.md", md("*Version v2.0, 2026-11.*", "*Version v2.1, 2026-12.*"))
        self.write_contract()
        self.assertOneProblem(self.check(), "FIELD-MANUAL.md", "2 version lines")

    def test_tree_links_count_and_must_match(self):
        self.write("FIELD-MANUAL.md", md("*Version v2.0, 2026-11.*"))
        self.write("AGENT-CONTRACT.md", md(
            "# Contract",
            "[a](https://github.com/o/r/tree/v2.0/templates)",
            "[b](https://github.com/o/r/tree/main/examples)",
        ))
        result = self.check()
        self.assertEqual(result.items, 2)
        self.assertOneProblem(result, "AGENT-CONTRACT.md:3:", "main", "v2.0")

    def test_relative_link_in_contract_fails(self):
        self.write("FIELD-MANUAL.md", md("*Version v2.0, 2026-11.*"))
        self.write("AGENT-CONTRACT.md", md(
            "# Contract",
            "[a](https://github.com/o/r/blob/v2.0/METHOD.md)",
            "See [the method](METHOD.md).",
        ))
        result = self.check()
        self.assertEqual(result.items, 2)
        self.assertOneProblem(
            result, "AGENT-CONTRACT.md:3: relative link breaks when the contract is copied: METHOD.md")

    def test_contract_without_versioned_links_inspects_nothing(self):
        self.write("FIELD-MANUAL.md", md("*Version v2.0, 2026-11.*"))
        self.write("AGENT-CONTRACT.md", md("# Contract", "", "See [a page](https://example.com/page)."))
        self.assertInspectedNothing(self.check())

    def test_missing_contract_inspects_nothing(self):
        self.write("FIELD-MANUAL.md", md("*Version v2.0, 2026-11.*"))
        self.assertInspectedNothing(self.check())


# Command line


def stub(items, problems=()):
    return lambda root, *args: cm.Result(items=items, problems=list(problems))


ALL_PASS = {name: stub(1) for name in CHECK_ORDER}


class RunTest(FixtureCase):
    def test_output_has_one_line_per_check_in_table_order(self):
        lines, _ = cm.run(self.root)
        names = [line.split(":", 1)[0] for line in lines if not line.startswith(" ")]
        self.assertEqual(names, CHECK_ORDER)

    def test_line_formats(self):
        stubs = dict(ALL_PASS)
        stubs["links"] = stub(57)
        stubs["fences"] = stub(12, ["a.md:1: x", "b.md:2: y"])
        stubs["punctuation"] = stub(1, ["c.md:3: z"])
        with mock.patch.dict(cm.CHECKS, stubs):
            lines, status = cm.run(self.root, only=["links", "fences", "punctuation"])
        self.assertEqual(lines[:7], [
            "links: passed (57 items)",
            "fences: failed (12 items, 2 problems)",
            "  a.md:1: x",
            "  b.md:2: y",
            "punctuation: failed (1 item, 1 problem)",
            "  c.md:3: z",
            "sources: not run",
        ])
        self.assertIn("terms: not run", lines)
        self.assertEqual(status, 1)

    def test_zero_items_fails_even_when_a_check_forgets(self):
        stubs = dict(ALL_PASS)
        stubs["terms"] = stub(0)
        with mock.patch.dict(cm.CHECKS, stubs):
            lines, status = cm.run(self.root)
        self.assertIn("terms: failed (0 items, 1 problem)", lines)
        self.assertIn("  inspected nothing", lines)
        self.assertEqual(status, 1)

    def test_only_runs_named_checks_in_table_order(self):
        with mock.patch.dict(cm.CHECKS, ALL_PASS):
            lines, status = cm.run(self.root, only=["terms", "links"])
        self.assertEqual(lines[0], "links: passed (1 item)")
        self.assertEqual(lines[7], "terms: passed (1 item)")
        self.assertEqual(sum(line.endswith(": not run") for line in lines), 8)
        self.assertEqual(status, 0)

    def test_unknown_name_raises(self):
        with self.assertRaises(ValueError):
            cm.run(self.root, only=["links", "bogus"])

    def test_require_all(self):
        with mock.patch.dict(cm.CHECKS, ALL_PASS):
            self.assertEqual(cm.run(self.root, require_all=True)[1], 0)
            self.assertEqual(cm.run(self.root, only=["links"])[1], 0)
            self.assertEqual(cm.run(self.root, only=["links"], require_all=True)[1], 1)

    def test_exit_status_from_real_checks(self):
        self.write("a.md", md("```text", "x", "```"))
        self.write("b.md", md("```text", "x"))
        self.assertEqual(cm.run(self.root, only=["fences"])[0][1], "fences: failed (3 items, 1 problem)")
        (self.root / "b.md").unlink()
        lines, status = cm.run(self.root, only=["fences"])
        self.assertEqual((lines[1], status), ("fences: passed (2 items)", 0))


class MainTest(FixtureCase):
    def call(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = cm.main(list(argv))
        return status, out.getvalue(), err.getvalue()

    def test_main_prints_run_lines(self):
        with mock.patch.dict(cm.CHECKS, ALL_PASS):
            status, out, _ = self.call("--root", str(self.root), "--only", "links,terms")
            lines, expected = cm.run(self.root, only=["links", "terms"])
        self.assertEqual(out.splitlines(), lines)
        self.assertEqual(status, expected)

    def test_exit_statuses(self):
        stubs = dict(ALL_PASS)
        stubs["glance"] = stub(1, ["FIELD-MANUAL.md:1: bad"])
        with mock.patch.dict(cm.CHECKS, stubs):
            self.assertEqual(self.call("--root", str(self.root), "--only", "links")[0], 0)
            self.assertEqual(self.call("--root", str(self.root))[0], 1)
            self.assertEqual(self.call("--root", str(self.root), "--only", "links", "--require-all")[0], 1)

    def test_unknown_check_name_is_a_usage_error(self):
        status, out, err = self.call("--root", str(self.root), "--only", "links,bogus")
        self.assertEqual(status, 2)
        self.assertEqual(out, "")
        self.assertIn("bogus", err)

    def test_only_that_names_no_check_is_a_usage_error(self):
        for value in ("", ",", " , ,"):
            with self.subTest(value=value):
                status, out, _ = self.call("--root", str(self.root), "--only", value)
                self.assertEqual(status, 2)
                self.assertEqual(out, "")

    def test_unknown_option_is_a_usage_error(self):
        self.assertEqual(self.call("--root", str(self.root), "--bogus")[0], 2)

    def test_root_that_is_not_a_directory_is_a_usage_error(self):
        self.assertEqual(self.call("--root", str(self.root / "missing"))[0], 2)

    def test_script_runs_as_a_program(self):
        script = HERE / "check_manual.py"

        def run_script(*args):
            return subprocess.run([sys.executable, str(script), "--root", str(self.root), *args],
                                  capture_output=True, text=True)

        all_lines = run_script("--require-all")
        self.assertEqual(all_lines.returncode, 1)
        self.assertEqual(len([l for l in all_lines.stdout.splitlines() if not l.startswith(" ")]), 10)
        self.assertEqual(run_script("--only", "bogus").returncode, 2)


# moved

GIT_CONFIG = [
    "-c", "core.hooksPath=/dev/null",
    "-c", "commit.gpgsign=false",
    "-c", "user.name=t",
    "-c", "user.email=t@example.invalid",
]

BASE_A = md("# Title", "", "First paragraph here.", "", "Second paragraph", "spans two lines.")
BASE_B = md("# B", "", "B one.")


class MovedTest(FixtureCase):
    def setUp(self):
        super().setUp()
        self.git("init", "-b", "main")
        self.write("a.md", BASE_A)
        self.write("b.md", BASE_B)
        self.write("notes.txt", "Not markdown.\n")
        self.base = self.commit()

    def git(self, *args):
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1")
        return subprocess.run(["git", *GIT_CONFIG, *args], cwd=self.root, env=env,
                              check=True, capture_output=True, text=True).stdout.strip()

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "change")
        return self.git("rev-parse", "HEAD")

    def moved(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        head = self.git("rev-parse", "HEAD")
        argv = ["moved", self.base, head, "--root", str(self.root), *extra]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = cm.main(argv)
        return status, out.getvalue().splitlines()

    def test_paragraph_moved_within_a_file_is_unchanged(self):
        self.write("a.md", md("# Title", "", "Second paragraph spans", "two   lines.", "", "First paragraph here."))
        self.write("notes.txt", "Changed.\n")
        self.commit()
        status, lines = self.moved()
        self.assertEqual(status, 0)
        self.assertEqual(lines, ["added: 0", "removed: 0", "unchanged: 5"])

    def test_paragraph_moved_between_files_is_unchanged(self):
        self.write("a.md", md("# Title", "", "Second paragraph", "spans two lines."))
        self.write("b.md", md("# B", "", "First paragraph here.", "", "B one."))
        self.commit()
        status, lines = self.moved()
        self.assertEqual(status, 0)
        self.assertEqual(lines, ["added: 0", "removed: 0", "unchanged: 5"])

    def test_added_paragraph_is_listed_with_its_first_80_characters(self):
        long_text = " ".join(["abcdef"] * 20)
        self.assertNotEqual(long_text[79], " ")
        self.write("b.md", BASE_B + "\n" + long_text + "\n")
        self.commit()
        status, lines = self.moved()
        self.assertEqual(status, 0)
        self.assertEqual(lines, ["added: 1", "removed: 0", "unchanged: 5", f"+ b.md: {long_text[:80]}"])

    def test_removed_paragraph_is_listed(self):
        self.write("a.md", md("# Title", "", "First paragraph here."))
        self.commit()
        status, lines = self.moved()
        self.assertEqual(status, 0)
        self.assertEqual(lines, ["added: 0", "removed: 1", "unchanged: 4",
                                 "- a.md: Second paragraph spans two lines."])

    def test_counts_are_multiset_counts(self):
        self.write("a.md", BASE_A + "\nSame.\n\nSame.\n")
        self.base = self.commit()
        self.write("a.md", BASE_A + "\nSame.\n")
        self.commit()
        status, lines = self.moved()
        self.assertEqual(status, 0)
        self.assertEqual(lines, ["added: 0", "removed: 1", "unchanged: 6", "- a.md: Same."])

    def test_files_that_exist_in_only_one_revision(self):
        (self.root / "b.md").unlink()
        self.write("c.md", md("B one.", "", "C new."))
        self.commit()
        status, lines = self.moved()
        self.assertEqual(status, 0)
        self.assertEqual(lines, ["added: 1", "removed: 1", "unchanged: 4", "+ c.md: C new.", "- b.md: # B"])

    def test_paths_limit_the_comparison(self):
        self.write("a.md", md("# Title", "", "Second paragraph", "spans two lines."))
        self.write("b.md", md("# B", "", "First paragraph here.", "", "B one."))
        self.commit()
        status, lines = self.moved("--", "a.md")
        self.assertEqual(status, 0)
        self.assertEqual(lines, ["added: 0", "removed: 1", "unchanged: 2", "- a.md: First paragraph here."])

    def test_git_failure_exits_2(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = cm.main(["moved", "no-such-rev", "HEAD", "--root", str(self.root)])
        self.assertEqual(status, 2)


if __name__ == "__main__":
    unittest.main()

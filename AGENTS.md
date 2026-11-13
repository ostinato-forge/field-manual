# AGENTS.md

## Project

This repo contains "The Solo Builder's Field Manual": a concise, agent-agnostic guide for humans building real software with coding agents. The product is the manual itself, plus a starter project guide template that readers can adapt for their own projects.

## Files

- `FIELD-MANUAL.md` - the practices, their evidence, the worked example, and the source list. Slow-changing.
- `METHOD.md` - the ordered method for the human owner. States steps; links to the manual for the why.
- `AGENT-CONTRACT.md` - the portable operating contract handed to an agent on a product. Not this file.
- `PRODUCT-DIRECTOR-MODE.md` - the product-shaping contract.
- `STARTER-CLAUDE-MD.md` - project guide template.
- `CHECKLISTS.md` - checkpoint checklists for the method.
- `PRACTICE-LIFECYCLE.md` - how techniques enter and leave guidance.
- `CAPABILITY-STACK.md` - capability layers, adoption ladder, trust boundaries. Capabilities, never brands or private tool names. The one named tool is the author's own, and the file's evidence statement discloses that.
- `INCIDENTS.md` - the incident ledger. One entry per real event, with the practices it supports.
- `templates/` - fill-in artifacts. `examples/` - a worked slice, and the case study of one product built two ways.
- `README.md`, `LICENSE` (CC BY 4.0), and this file.
- `CLAUDE.md` - one line that imports this file, so Claude Code loads it even when another `CLAUDE.md` sits above the repository.
- `scripts/check_manual.py` - checks the repository against its own rules. `scripts/test_check_manual.py` - its unit tests. Python 3, standard library only.
- `.github/workflows/check.yml` - runs the unit tests and the checks that CI requires, on every push to `main` and on every pull request.

## Where things belong

- A practice with its evidence and the reason it works: `FIELD-MANUAL.md`.
- A step, an order, a list to run through: `METHOD.md` or `CHECKLISTS.md`. State it once; link to the manual for the why. Do not restate the manual's reasoning in the method or the reasoning's steps in the manual.
- An incident: one entry in `INCIDENTS.md`, with the month, what happened, the rule, the practices it supports, and what kind of record exists. The manual keeps one or two sentences of it.
- A fill-in artifact: `templates/`. The manual never carries templates.
- A rule an agent must follow on any project: `AGENT-CONTRACT.md`. A rule for editing this repo: this file.
- A rule a script can check: a check in `scripts/check_manual.py`, with a unit test that fails without it.
- Real project lore, private tool names, personal workflow: nowhere in this repo. Generalize the lesson first or leave it out.

## Working Principles

- Preserve the manual's voice: practical, direct, evidence-aware, and allergic to ceremony for its own sake.
- Keep the audience universal: software builders using coding agents across tools, stacks, organizations, and project sizes.
- Do not encode the author's personal preferences, private workflows, local project lore, or house style as general advice.
- Local project artifacts may be used as pattern evidence, but only after the lesson is generalized beyond that specific project.
- Prefer durable practices over tool-specific instructions. Mention specific tools only as examples or when the claim is sourced.
- Keep advice actionable. If a principle can become a checklist item, template, or concrete rule, make it concrete.
- Label opinion as opinion. Do not present vibes, preferences, or unsourced trend claims as research.
- When a claim could go stale, either verify it against current primary sources or phrase it in a time-bounded way.
- Keep the guide concise. Add sections only when they introduce a distinct practice or failure mode.

## Evidence Bar

Practices should meet at least one of these bars. The word in code is the tag used in the practice's evidence line.

- Independently converged: two or more independent sources describe it (`converged`).
- Empirically researched: a study, or an engineering report of experiments, supports it (`researched`).
- Repeatedly observed across real projects (`observed`).
- Recorded as an incident on a real project, with the rule it produced, in `INCIDENTS.md` (`incident`, or `incident (undated)` when no dated record exists).

Every practice heading in sections 1 to 11 of `FIELD-MANUAL.md` carries an evidence line. A `researched` or `converged` practice cites its sources in its own text. An `incident` practice is named by a ledger entry.

How a practice enters:

- A practice from a single incident enters on the owner's decision. It is tagged `incident`, and its ledger entry is its record. It needs a practice card and a trial only if it claims a measured effect, such as cost or speed.
- Any other practice enters through the review in `PRACTICE-LIFECYCLE.md`: candidate, reviewed, trial where the claim is testable, then promotion by a human.

The bar says what counts as evidence; the lifecycle says how it is checked.

When adding sources, prefer primary sources, practitioner posts with concrete workflows, or project artifacts that show the practice in use. Avoid generic listicles.

## Editing Conventions

- Documents are Markdown only; keep formatting simple. The only code in the repo is the checker in `scripts/`.
- Use short headings and tight paragraphs.
- Keep examples small and copy-pasteable.
- No em dashes and no doubled hyphens as punctuation anywhere in the repo; use a period, comma, colon, semicolon, or parentheses. Straight quotes. Section signs and arrows in existing text are fine.
- Plain, direct sentences. Avoid the "not X, but Y" construction as a stylistic tic; state what is true.
- One term per thing: write "agent" and "project guide". The `terms` check names the words that are not allowed.
- A list that appears in more than one file reads the same in every copy. The `shared-lists` check holds the table of copies.
- Do not add broad rewrites unless explicitly requested.
- Do not duplicate advice across sections; cross-reference or sharpen the existing section instead.
- Every item in "The Practices at a Glance" links to its practice. The `glance` check fails an item with no link, or with a link to a heading that is not a practice.

## Quality Checks

Before finishing edits:

- Read the changed section in context.
- Run `python3 -m unittest scripts/test_check_manual.py` from the repository root. It must pass.
- Run `python3 scripts/check_manual.py`. It prints one line for each of its ten checks. CI requires the checks named after `--only` in `.github/workflows/check.yml`, and each of those must print `passed`. A check that is not named there does not pass yet, because the documents do not meet its rule. A change must not add a new problem to any check's output.
- Open every outside link you added or changed. The checker does not fetch web pages.
- Check heading numbering and duplicate headings.
- Confirm the starter template still matches the manual's guidance.

## Security and Safety

- Never include real secrets, private tokens, or credential examples that look live.
- Keep security advice specific and enforceable.
- For destructive or irreversible workflows, require explicit human approval, a rollback path, and evidence of a dry run when applicable.


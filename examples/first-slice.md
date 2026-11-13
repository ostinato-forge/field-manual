# Example: First Product Slice

## Situation

A team wants an agent to build a web tool that reads a deployment record and tells an operator whether a release is safe to promote.

## Product decision

The first slice answers one question for one operator:

> Did every required check run and pass for this exact revision?

It does not deploy, approve, or repair anything.

## Contract

Input:

- Revision identifier.
- Required check list.
- Check results bound to the revision.

Output:

- Passed.
- Failed.
- Incomplete because evidence is missing or stale.

## Architecture

- Pure evaluator owns the verdict.
- File or API adapter loads check evidence.
- Web interface renders the evaluator result.
- Interface cannot invent readiness.
- Human owns promotion.

## Work packet

Build one page that loads a fixture, calls the evaluator, and displays the verdict plus missing evidence.

Acceptance:

- Complete green fixture returns passed.
- One failed check returns failed.
- One missing check returns incomplete.
- Evidence for another revision returns incomplete.
- Refresh preserves the same backend-owned result.

## Builder pass

The builder writes evaluator tests, implements the core, adds the adapter, and builds the page.

## Reviewer pass

The reviewer checks:

- Specification compliance.
- Whether missing checks can appear green.
- Whether the interface reimplements verdict logic.
- Whether revision identity is enforced.
- Error and empty states.
- Test quality and unnecessary complexity.

## Red team

Hostile fixtures (test inputs built to break the tool) include:

- Duplicate check names.
- Unknown status.
- Empty revision.
- Stale evidence.
- Malformed timestamp.
- Partial file write.
- Oversized response.

## Proof

Automated proof covers the evaluator and adapter contract. Browser proof covers the main path, failure, and incomplete state. The evidence record stores the exact revision and test run.

## Human stop

The human decides whether the product truth is clear enough to add a real service adapter. No second integration starts until the fixture-backed slice is accepted.

## Learning

If review finds that duplicate checks can hide a required failure, the defect becomes:

- A regression test in this project.
- A project-guide rule if the pattern may recur here.
- A candidate practice card only if the lesson is useful across projects.

# Case Study: Two Ways to Build the Same Product

*From the build record of usabl, an accessibility proof engine. The product is public and the build record is private; its source documents are named at the end of this file. Where the lesson is specific to that product it is labeled as such. The practices it draws on are in [FIELD-MANUAL.md](../FIELD-MANUAL.md).*

There is no one way to build with agents. The same product, under the same owner and the same quality bar, was built two different ways in two consecutive releases. Both worked. The parts that stayed fixed are the parts worth copying.

## What never flexed

The team wrote down the invariants before the first line of code and pasted them into every dispatch:

- One component is the only verdict authority. Everything else returns drafts.
- A passing result and its receipt (the record the product issues for that result) are reserved for deterministic evidence. Preview and model judgment can surface findings but can never mint a pass.
- An unbuilt path fails honestly or stays unwired. No placeholder returns success.
- Text taken from the thing under test is untrusted and is neutralized at every output.
- Test first. Tests assert behavior. A reviewer pass after every unit of work. A security review before every merge.
- The orchestrating session does not write product code and does not rubber-stamp.

The product-specific invariants (verdicts, receipts) are the shape of a proof engine. The last three apply anywhere.

## Method one: phased build, four roles, three vendors

The first release followed a plan set written before any code: thesis and positioning, one consolidated design document, a dated decisions file that closed the design's open forks, then numbered implementation plans. Only then did building start.

Four roles ran on models from three different vendors. The human founder owned product, UX, and every push and merge. An architect session owned the design, the slice map, the briefs, and enforcement of the bar, and wrote no product code. One vendor's model implemented, test first, one task at a time. A second vendor's model reviewed after every task as both senior engineer and engineering manager, with "needs fixes" as the answer to any patch that matched the spec but was not senior work. A third vendor's model reviewed every pull request against main for security, independent of the code reviewer, and a green CI run plus an approved code review did not skip it.

Work shipped in what the project called coherence slices: one pull request per idea a reader can hold in a sentence, not one per task and not one per phase. Lessons the team kept from this method:

- A slice is a PR. A task is not. Fifteen task commits on a working branch became three PRs a reviewer could read.
- Stacked PRs plus squash merges rewrite branch history for every other clone. The second release did not stack.
- A code comment that cites a plan section rots. A comment that states the invariant does not.
- A merge gate that CI cannot enforce (a free-tier repository could not require the check) is recorded as a known gap and shown to the owner, never papered over.

## Method two: builder-reviewer loop, one environment, one vendor

The second release was a finish to team-pickup readiness, and it was built differently. Everything ran in one environment under one orchestrating session. For each slice, a builder agent built test first, a reviewer agent reviewed, and the loop repeated until the reviewer was satisfied. Then a separate security lane reviewed the slice, at slice granularity rather than per PR, so a four-slice feature that shipped as one PR got four security reviews. Pull requests on ordinary paths were pre-authorized and reviewed as they opened; changes to guarded paths and the release tag required explicit human approval.

Independence came from separate dispatches and adversarial framing rather than from different vendors. The record shows that was enough to catch real defects:

- On one slice, five review lanes ran at once. Three returned the same shape of finding: a confident wrong success, where recognition failed toward "already done" (a commented-out line read as wired, a substring match rewrote an operator's unrelated command, a 404 of any kind read as "no protection"). The fix in every case was to recognize only exact, anchored, positively confirmed forms and let everything else fall to refuse or cannot-verify.
- Every honesty guard was mutation-tested: remove the guard, confirm exactly its own tests go red and nothing else. Reviewers re-derived the checks themselves rather than accept the claim.
- A security lane recorded, for the record, that its first pass had accepted a byte-exact "already wired" check and missed a placeholder embedded in the draft it was checking. On re-derivation it ran crafted inputs and confirmed every one fell to not-wired.
- The release-critical merge needed two-person control and the sole code owner was also the author. The tool refused. The situation was surfaced for a human decision, the branch ruleset was snapshotted, bypassed once, restored, and confirmed byte-identical, and the commit body records the override. The security model proving itself on the release path is a result, not a defect.
- Clean-clone onboarding was run by a background agent from fresh clones and took 109 seconds. Four of eight commands exited non-zero, each an honest refusal. The result was labeled agent-run, not human-confirmed.

## Keeping the bar as sessions get long

Both methods shared one document whose only job was to stop quality from sliding as context filled. Its premise: subagents start empty, so a forgotten paste is the default failure, not a surprise. Every builder and reviewer dispatch had to carry the scoring criteria, the roles one-liner, the honesty list, and pointers to the few files that mattered, never the whole plan set. A dispatch missing any of the first three was not a legal dispatch and was rewritten.

The document also named the decline signals: skipping a reviewer because "it is small", the orchestrator writing product code "just this once", a rubber stamp on a spec-matching shrug, briefs getting shorter while diffs get sloppier, the same Important finding shipped twice. The response to any of them was to name it to the owner, restore the gate, and continue, and never to narrate a recovery that did not happen.

## What generalizes

- Fix the invariants and the review structure first. Vendors, model lineups, and process shape can change between releases without the bar moving.
- Independence between builder and reviewer is structural. Separate context, separate prompt, adversarial framing. Different vendors add diversity but are not what makes the separation work.
- Match review granularity to risk, not to the PR boundary. A security review per slice caught what a review per PR would have averaged away.
- Recognition that fails toward success is a recurring defect class in any tool that reports state. Recognize only exact positive forms; everything else is "cannot verify".
- Write the quality bar as a document the orchestrator pastes, not a habit it remembers.
- Keep an append-only build log, dated, that records what became true and what is still not built. Do not rewrite it to look smoother than it was.

Sources for this case study: the usabl build logs, quality bars, and role definitions for both releases (`how-we-built-this.md`, `quality-bar.md`, `roles.md`, and the `v0.2.0/` versions of each). They are kept in the project's planning repository, which is private. The product is at [usabl-dev/usabl](https://github.com/usabl-dev/usabl).

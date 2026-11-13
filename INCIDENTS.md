# Incident Ledger

Real events from projects built with this method. Each entry is the evidence behind one or more practices in [FIELD-MANUAL.md](FIELD-MANUAL.md), and `Supports` names them. Identifying details are removed. Dates are month and year. The records themselves are private, so `Record` says what kind of record exists and nothing more. An entry with no dated record says `not recorded`.

Entries are in date order. The two with no date come last.

## I-01: A signing default that would have published private names

- When: 2026-06
- What happened: A release plan called for keyless signing. By default, that step would have written private organization and repository names into a public transparency log, and a log entry cannot be removed. The agent flagged it before running it. The pause surfaced a staging option that the default path never mentioned, and the work used it.
- Rule: Flag the risk and stop before an action that cannot be undone or that publishes, even when the action follows from the task.
- Supports: FIELD-MANUAL.md, "Stop before anything irreversible or outward-facing"
- Record: private project history and session notes

## I-02: One written rule in place of repeated corrections

- When: 2026-06
- What happened: During a build, the agent kept recommending the smaller or faster option, and the owner kept correcting it. They stopped and named the rule: build each capability to the bar, sequence a separable capability for later if needed, and never cut scope to save effort. They also named the phrases that signal the problem, such as "land it green" and "least code". The rule was written into the project's standing guidance.
- Rule: When the same correction repeats, stop and agree on the principle, then write it down.
- Supports: FIELD-MANUAL.md, "Sync the operating model when it drifts" and "Recommending on effort, not merit"
- Record: private session notes

## I-03: The account that flipped

- When: 2026-07
- What happened: A push failed with a misleading permission error. The active hosting account had switched to another identity between commands. It happened three times in one month. The lasting fix was to run the identity check in the same command as the operation, and to add a guard that runs before every push.
- Rule: Identity is part of release state. Check it each time instead of assuming it.
- Supports: FIELD-MANUAL.md, "Match proof to the claim"
- Record: private session notes

## I-04: The review that hunted false-clear states

- When: 2026-07
- What happened: Before a release, an independent review of a context-checking product looked only for ways the system could report a clean state without evidence. It found several: incomplete API results rendered as clear, malformed responses rendered as clear, and cancelled checks that disappeared. Each became an explicit state and a regression test.
- Rule: Missing evidence is never success. A reviewer who hunts for false-clear paths finds defects the builder cannot see.
- Supports: FIELD-MANUAL.md, "Absence of evidence never renders as success" and "Coverage honesty"
- Record: private review findings

## I-05: Three blinded attempts, zero survivors

- When: 2026-07
- What happened: A product experiment built three independent approaches to the same creative problem. The quality bar and the consequence of missing it were written down before any result existed. Reviewers judged the outputs without knowing which approach produced which. All three failed the bar. The direction stopped instead of shipping the least bad result.
- Rule: Define what counts as a pass before you see results, and let the stop rule fire.
- Supports: FIELD-MANUAL.md, "Define the pass before you run it"
- Record: private decision record

## I-06: A design nobody could approve from prose

- When: 2026-07
- What happened: An architect presented a plan's design decisions as written text and asked the owner to approve them. The owner answered that they could not make design calls without seeing the thing, and that it would have to be built and iterated. The written review had produced no usable decision.
- Rule: Treat written design calls as provisional. Put something the owner can see or run in front of them early.
- Supports: FIELD-MANUAL.md, "Design decisions need a visible artifact"
- Record: private session notes

## I-07: A review of the wrong revision

- When: 2026-08
- What happened: A full accuracy review ran against a stale local checkout that was behind the head of the pull request under review. The findings were consistent with each other and described code that had already changed. The owner rejected the work. The review was repeated against the correct revision.
- Rule: Confirm the exact revision before reviewing, auditing, or building.
- Supports: FIELD-MANUAL.md, "Re-orient before acting"
- Record: private session notes

## I-08: A plan edited while it was being executed

- When: 2026-08
- What happened: The owner was executing a plan in one session. In another session, an architect added two items to the same plan after a scope decision, and then removed them again. The document under the executing session changed twice. The owner had to ask twice for the editing to stop and then ask for a full restore.
- Rule: A plan that a session is executing is frozen. New scope goes in a new file that names the plan it extends.
- Supports: FIELD-MANUAL.md, "A plan in execution is frozen"
- Record: private session notes

## I-09: Guards that were removed to prove their tests

- When: 2026-08
- What happened: On one release every honesty guard was mutation-tested. Each guard was removed, and the builder confirmed that exactly its own tests went red and nothing else did. Reviewers repeated the checks themselves instead of accepting the claim. One reviewer's first pass had accepted an exact-match check and missed a placeholder inside the text it was checking. The repeat with crafted inputs caught it.
- Rule: A test proves little until you have seen it fail for the right reason.
- Supports: FIELD-MANUAL.md, "Mutation-test the tests"
- Record: private build log

## I-10: A fix proven only against a fake

- When: 2026-09
- What happened: A readiness fix shipped with tests that modelled a browser event as blocking until the network settled. In the real browser the event resolves in a few milliseconds. The builder, the reviewer, and the shared fake all agreed the fix worked, and it did nothing. A reviewer who was required to run the real browser caught it, and the fix was reworked.
- Rule: Before a fake counts as proof, check its behavior against the real dependency, and record how.
- Supports: FIELD-MANUAL.md, "Check your fakes against the real dependency" and "Live verification is the definition of done"
- Record: private project history and session notes

## I-11: Two wrong premises caught before any code

- When: 2026-09
- What happened: One project split its briefs for changes to user-visible behavior into two phases. Phase one was an audit of current behavior plus a failing test, then a stop. The architect read both before allowing phase two. Two of the first several briefs showed that the premise of the change was wrong, before any implementation existed.
- Rule: When the premise might be wrong, ask for the audit and the failing test first, and stop there.
- Supports: FIELD-MANUAL.md, "Two-phase briefs: audit and failing test first"
- Record: private session notes

## I-12: A commit that did not exist

- When: 2026-09
- What happened: A builder reported that it had committed its work, gave a commit hash, and said the tree was clean and 19 commits ahead. The hash did not exist. The work was uncommitted. The gates and an external review had already started against a revision that did not contain it.
- Rule: A builder's report is a claim. Read the repository before any gate, review, or push.
- Supports: FIELD-MANUAL.md, "Verify the builder's report against the repository"
- Record: private session notes

## I-13: A builder kept alive for four fix rounds

- When: 2026-09
- What happened: One builder session was resumed across four fix rounds on the same slice. Its history grew to roughly 425,000 tokens, and it misreported its commits twice. An external reviewer ran after every round and spent roughly 563,000 tokens in total. The owner saw the numbers and approved a new cadence.
- Rule: Use a fresh builder for each sub-batch and one independent review per sub-batch. Fix rounds get the architect's review and the automated gates.
- Supports: FIELD-MANUAL.md, "Fresh context per batch, bounded review cadence" and "Rules that came from numbers"
- Record: private session notes

## I-14: The invented roster

- When: 2026-09
- What happened: One project needed a creative review structure. The first roster of agent roles was invented, and it read well. Research then found that the pairing it proposed had existed in advertising since 1949 under other names, and that its review panel copied a well-known studio practice with the authority reversed. The roster was rebuilt from the researched roles.
- Rule: Research how people in the domain organize before you invent agent roles, and name the sources.
- Supports: FIELD-MANUAL.md, "Design agent roles from real professions"
- Record: private session notes

## I-15: A monitor that reported zero because it could not see

- When: 2026-09
- What happened: One builder's efficiency monitor reported zero interventions for weeks. The detectors were not quiet. A settings file had disabled the plugin, and two components were writing to different databases. Zero looked exactly like success.
- Rule: A tool that reports on quality must also report when it could not observe anything.
- Supports: FIELD-MANUAL.md, "Absence of evidence never renders as success" and "Reading silence as success"
- Record: private session notes

## I-16: Documentation taken as behavior

- When: 2026-10
- What happened: A project wrote a page of operational cautions about a library. The page drew on the library's own documentation and on a design plan in an unmerged pull request, and it was presented as verified. A live test showed that the library worked unmodified and that the cautions were wrong.
- Rule: A documentation page proves what a source says. A belief about how a dependency behaves is a hypothesis until something probes it.
- Supports: FIELD-MANUAL.md, "Match proof to the claim"
- Record: private session notes

## I-17: The script that changed what it never named

- When: 2026-10
- What happened: A script edited eleven items in a structured document, and its log was accurate for all eleven. It also converted the list formatting of the whole surrounding section, because the glyph was a property of the list and not of the item. The repair measured it: eighty-five list items in the section, the glyph set on four of them, sixty-six changed.
- Rule: When a tool applies a change, the proof includes a sample of what the change was not meant to touch.
- Supports: FIELD-MANUAL.md, "Prove the unchanged set"
- Record: private session notes

## I-18: Nineteen corrections, six arrived

- When: 2026-10
- What happened: Nineteen corrections went into a source document, and six of them reached the published page. The other thirteen sat in parts of the source that the page generator does not read. The same facts on the page came from hand-written blocks. All thirteen happened to be right on the page, because both edits were made in the same sitting. The pipeline would have reported nothing either way.
- Rule: Know which parts of a published artifact are generated. A source correction is unfinished until the hand-written parts have been checked for the same fact.
- Supports: FIELD-MANUAL.md, "A correction only propagates through the generated part"
- Record: private session notes

## I-19: Decisions kept in comments

- When: 2026-10
- What happened: A team was asked to record a set of decisions as comments on a document. The export that generated the downstream guide stripped comment markup. Comments could be resolved and then hidden. A PDF made for stakeholders carried none of them.
- Rule: Put a decision in the layer that survives every later transform of the artifact: the body, or the repository.
- Supports: FIELD-MANUAL.md, "Don't accumulate decisions in conversation"
- Record: private session notes

## I-20: A stop that checked the exposure first

- When: 2026-10
- What happened: An instruction to publish a document to a project's hosting site looked like a new public release and a reason to stop. One call to the hosting API showed that the site was already enabled, was private to the repository's members, and already carried two earlier publications of the same document by the owner. The action was an update to an existing private surface, not a new release.
- Rule: Establish the actual exposure before you escalate. The stop is for new exposure or a wider audience.
- Supports: FIELD-MANUAL.md, "Stop before anything irreversible or outward-facing"
- Record: private session notes

## I-21: A project guide that was never loaded

- When: 2026-11
- What happened: A repository kept its maintainer rules in `AGENTS.md`. A `CLAUDE.md` file in a directory above the repository made the coding tool skip `AGENTS.md` at session start, so sessions worked in the repository without its rules. Three probe sessions with tools turned off confirmed it: the file was not loaded by default, was loaded with a setting, and was loaded when a one-line `CLAUDE.md` in the repository imported it.
- Rule: A guide in the repository is not a guide in the agent's context. Check that it loaded.
- Supports: FIELD-MANUAL.md, "The project operating manual"
- Record: private session notes

## I-22: Nine built, zero good

- When: not recorded
- What happened: A generation pipeline produced nine of ten planned creative artifacts. Structural review of the outputs read as strong progress. Then the human experienced the artifacts in their real medium and judged the words unusable. A reduced retest confirmed the gap. Quality had been judged from text descriptions and structure.
- Rule: A thing is done when someone has experienced it working in its real medium.
- Supports: FIELD-MANUAL.md, "Live verification is the definition of done"
- Record: none located

## I-23: A release blocked by its own evidence gate

- When: not recorded
- What happened: A release candidate had green focused tests. The release gate compared the recorded evidence hash with the exact source revision and found that the evidence came from older source. The release stopped until the evidence was regenerated.
- Rule: Bind proof to the exact revision. A green focused run is not a green release.
- Supports: FIELD-MANUAL.md, "Absence of evidence never renders as success"
- Record: none located

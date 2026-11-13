# Incident Ledger

Real events from projects built with this method. Each entry is the evidence behind one or more practices in [FIELD-MANUAL.md](FIELD-MANUAL.md), and `Supports` names them. Identifying details are removed. Dates are month and year. The records themselves are private, so `Record` says what kind of record exists and nothing more. An entry with no dated record says `not recorded`.

Entries are in date order. The one with no date comes last.

## I-01: A signing default that would have published private names

- When: 2026-06
- What happened: A build phase called for a proof of keyless signing. By default, that step would have written private organization and repository names into a public transparency log, and a log entry cannot be removed. The agent flagged it before running it. The pause surfaced a staging option that the default path never mentioned, and the work used it.
- Rule: Flag the risk and stop before an action that cannot be undone or that publishes, even when the action follows from the task.
- Supports: FIELD-MANUAL.md, "Stop before anything irreversible or outward-facing"
- Record: private project history and session notes

## I-02: A recommendation made on effort

- When: 2026-06
- What happened: During a build, the agent justified a recommendation by effort: the smaller, faster option. The owner rejected it. They stopped and agreed on the rule: build each capability to the bar, sequence a separable capability for later if needed, and never cut scope to save effort. They also named the phrases that signal the problem, such as "land green" and "least code". The rule went into the agent's standing guidance for every project. Two days later the owner had to restate it once.
- Rule: When a correction is about how you build, stop and agree on the principle, then write it down.
- Supports: FIELD-MANUAL.md, "Sync the operating model when it drifts" and "Recommending on effort, not merit"
- Record: private session notes

## I-03: The reviews that hunted false-clear states

- When: 2026-06
- What happened: Over four days, adversarial reviews of a context-checking product hunted for ways it could report a clean state without evidence. They found several. Two connectors read only the first page of results from a hosting API, so a failing check beyond that page read as clear. A cancelled check read as passing. A malformed response dropped a failing run without a trace. Each was fixed so that the product reports an explicit unknown or failing state.
- Rule: Missing evidence is never success. A reviewer who hunts for false-clear paths finds defects the builder cannot see.
- Supports: FIELD-MANUAL.md, "Absence of evidence never renders as success" and "Coverage honesty"
- Record: private project history and review findings

## I-04: The account that flipped

- When: 2026-07
- What happened: A push failed with a misleading "repository not found" error. The active hosting account had switched to another identity between commands, because several sessions shared one login configuration. It was seen three times in one month. The lasting fix was to switch the account and run the operation in the same command, and to add a hook that rejects a push whose commits carry the wrong author identity.
- Rule: Identity is part of release state. Check it each time instead of assuming it.
- Supports: FIELD-MANUAL.md, "Match proof to the claim"
- Record: private session notes

## I-05: Three strategies, nine blind results, none passed

- When: 2026-07
- What happened: A product experiment tried three strategies for the same creative problem on three fresh cases each. The pass bar and the consequence of missing it were written down before any result existed. The outputs were judged blind. None of the nine passed. The planned consequence was taken, and the work that depended on the strategies stopped.
- Rule: Define what counts as a pass before you see results, and let the stop rule fire.
- Supports: FIELD-MANUAL.md, "Define the pass before you run it"
- Record: private decision record

## I-06: A design nobody could approve from prose

- When: 2026-07
- What happened: An architect presented a plan's design decisions as written text and asked the owner to approve them. The owner answered that they could not make design calls without seeing the thing, and that it would have to be built and iterated. No design call was made from the document.
- Rule: Treat written design calls as provisional. Put something the owner can see or run in front of them early.
- Supports: FIELD-MANUAL.md, "Design decisions need a visible artifact"
- Record: private session notes

## I-07: Nine built, zero good

- When: 2026-08
- What happened: A generation pipeline produced nine of ten planned creative artifacts. Structural review of the outputs read as strong progress. Then the owner experienced the artifacts in their real medium and graded all nine as misses, because the words did not work. A follow-up experiment on the words confirmed the gap.
- Rule: A thing is done when someone has experienced it working in its real medium.
- Supports: FIELD-MANUAL.md, "Live verification is the definition of done"
- Record: private session notes

## I-08: A review of the wrong revision

- When: 2026-08
- What happened: A full accuracy review of a set of scripts, with a long corrected document, was done against a stale local checkout that was behind the head of the pull request under review. The owner called the work not valid, and it was rolled back. One fetch and a comparison with the pull request head would have caught it.
- Rule: Confirm the exact revision before reviewing, auditing, or building.
- Supports: FIELD-MANUAL.md, "Re-orient before acting"
- Record: private session notes

## I-09: A plan edited while it was being executed

- When: 2026-08
- What happened: The owner was executing a plan in one session. In another session, an architect added two items to the same plan after a scope decision, and then removed them again. The document under the executing session changed twice. The owner had to ask twice for the editing to stop and then ask for a full restore.
- Rule: A plan that a session is executing is frozen. New scope goes in a new file that names the plan it extends.
- Supports: FIELD-MANUAL.md, "A plan in execution is frozen"
- Record: private session notes

## I-10: Guards that were broken to prove their tests

- When: 2026-08
- What happened: On one release, the engineer checked each tightened or new honesty guard by breaking it. Exactly that guard's own tests went red and nothing else did. Reviewers derived the checks again themselves instead of accepting the claim. A security reviewer recorded that its first pass had accepted an exact-match check and missed a placeholder inside the draft it was checking. On its repeat it ran crafted inputs and confirmed that every one was refused.
- Rule: A test proves little until you have seen it fail for the right reason.
- Supports: FIELD-MANUAL.md, "Mutation-test the tests"
- Record: private build log

## I-11: A fix proven only against a fake

- When: 2026-09
- What happened: A readiness fix reached review with green unit tests. The tests used a fake that modelled a browser event as blocking until the network settled. In the real browser the event resolves in a few milliseconds, so the fix did nothing. A review that included a probe of the real browser caught it. The fix was rejected before merge and reworked.
- Rule: Before a fake counts as proof, check its behavior against the real dependency, and record how.
- Supports: FIELD-MANUAL.md, "Check your fakes against the real dependency" and "Live verification is the definition of done"
- Record: private project history and session notes

## I-12: Two wrong premises caught before any code

- When: 2026-09
- What happened: One project split a brief for a change to user-visible behavior into two phases. Phase one was an audit of current behavior plus a failing test, then a stop. The architect read both before allowing phase two. On that first use, the audit showed two wrong premises before any implementation existed.
- Rule: When the premise might be wrong, ask for the audit and the failing test first, and stop there.
- Supports: FIELD-MANUAL.md, "Two-phase briefs: audit and failing test first"
- Record: private session notes

## I-13: A commit that did not exist

- When: 2026-09
- What happened: A builder reported that it had committed its work, gave a commit hash, and said the tree was clean and 19 commits ahead. The hash did not exist. The work was uncommitted. The gates and an external review had already started against a revision that did not contain it.
- Rule: A builder's report is a claim. Read the repository before any gate, review, or push.
- Supports: FIELD-MANUAL.md, "Verify the builder's report against the repository"
- Record: private session notes

## I-14: A builder kept alive for four fix rounds

- When: 2026-09
- What happened: One builder session was resumed across four fix rounds on the same slice. Its history grew to roughly 425,000 tokens, and it misreported its commits twice. An external reviewer ran after every round and spent roughly 563,000 tokens across the four reviews. The owner saw the numbers and approved a new cadence.
- Rule: Use a fresh builder for each sub-batch and one independent review per sub-batch. Fix rounds get the architect's review and the automated gates.
- Supports: FIELD-MANUAL.md, "Fresh context per batch, bounded review cadence" and "Rules that came from numbers"
- Record: private session notes

## I-15: The invented roster

- When: 2026-09
- What happened: One project needed a creative review structure, and the agent proposed a roster of roles it had made up. The owner stopped it and asked for research on how experts do this work. The research changed the answer. The proposed line of roles matched the arrangement that advertising used before a 1949 pairing of writer and art director replaced it. The proposed review panel prescribed fixes and held authority, and the well-known studio panel it resembled does neither. The roster was rebuilt from the researched roles.
- Rule: Research how people in the domain organize before you invent agent roles, and name the sources.
- Supports: FIELD-MANUAL.md, "Design agent roles from real professions"
- Record: private session notes

## I-16: A monitor that reported zero because it could not see

- When: 2026-09
- What happened: One builder's efficiency monitor reported zero interventions in its seven-day report. The detectors were not quiet. A settings problem had left the plugin's hooks disabled, and two components were writing to different databases. Zero looked exactly like success.
- Rule: A tool that reports on quality must also report when it could not observe anything.
- Supports: FIELD-MANUAL.md, "Absence of evidence never renders as success" and "Reading silence as success"
- Record: private session notes

## I-17: Documentation taken as behavior

- When: 2026-10
- What happened: A project wrote a section of operational cautions about a library. The cautions came from the documentation of the platform the library talks to and from a design plan in an unmerged pull request. A live test environment did not behave that way, and the library needed no change. The section was deleted.
- Rule: A documentation page proves what a source says. A belief about how a dependency behaves is a hypothesis until something probes it.
- Supports: FIELD-MANUAL.md, "Match proof to the claim"
- Record: private session notes

## I-18: The script that changed what it never named

- When: 2026-10
- What happened: A script edited eleven items in a structured document, and its log was accurate for all eleven. It also converted the list formatting of the whole surrounding section, including items it never touched, because the glyph was a property of the list and not of the item. The repair measured it: eighty-five list items in the section, the glyph set on four of them, sixty-six changed.
- Rule: When a tool applies a change, the proof includes a sample of what the change was not meant to touch.
- Supports: FIELD-MANUAL.md, "Prove the unchanged set"
- Record: private session notes

## I-19: Eighteen corrections, six arrived

- When: 2026-10
- What happened: Eighteen corrections went into a source document, and six of them reached the published page. The page generator reads only some sections of the source. The other twelve corrections sat in sections it does not read, and those facts reach readers only through hand-written parts of the page. All twelve were checked by hand and were stated correctly there. The pipeline would have reported nothing either way.
- Rule: Know which parts of a published artifact are generated. A source correction is unfinished until the hand-written parts have been checked for the same fact.
- Supports: FIELD-MANUAL.md, "A correction only propagates through the generated part"
- Record: private session notes

## I-20: Decisions that comments would have lost

- When: 2026-10
- What happened: A set of decisions had to be recorded on a shared document, and comments were one option. A check of the pipeline showed that the export that builds the downstream guide strips comment markup, that a comment can be resolved and hidden, and that a PDF for stakeholders would not carry comments. The decisions went into the body of the document. Nothing was lost, because the check came first.
- Rule: Put a decision in the layer that survives every later transform of the artifact: the body, or the repository.
- Supports: FIELD-MANUAL.md, "Don't accumulate decisions in conversation"
- Record: private session notes

## I-21: A publish that was an update

- When: 2026-10
- What happened: An instruction to publish a document to a project's hosting site looked like a new public release, which is a reason to stop. One call to the hosting API showed that the site was already enabled, was private to the repository's collaborators, and already carried the owner's earlier publication of the same document. The action was an update to an existing private surface.
- Rule: Establish the actual exposure before you escalate. The stop is for new exposure or a wider audience. The check clears a stop only for an action the human asked for.
- Supports: FIELD-MANUAL.md, "Stop before anything irreversible or outward-facing"
- Record: private session notes

## I-22: A project guide that was never loaded

- When: 2026-11
- What happened: A repository kept its maintainer rules in `AGENTS.md`. A `CLAUDE.md` file in a directory above the repository made the coding tool skip `AGENTS.md` at session start, so sessions worked in the repository without its rules. Three probe sessions with tools turned off confirmed it: the file was not loaded by default, was loaded with a setting, and was loaded when a one-line `CLAUDE.md` in the repository imported it.
- Rule: A guide in the repository is not a guide in the agent's context. Check that it loaded.
- Supports: FIELD-MANUAL.md, "The project guide"
- Record: private session notes

## I-23: A release blocked by its own evidence gate

- When: not recorded
- What happened: A release candidate had green focused tests. The release gate compared the recorded evidence hash with the exact source revision and found that the evidence came from older source. The release stopped until the evidence was regenerated.
- Rule: Bind proof to the exact revision. A green focused run is not a green release.
- Supports: FIELD-MANUAL.md, "Absence of evidence never renders as success"
- Record: none located

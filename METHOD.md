# The Method: How to Develop Products with AI Coding Assistants

This file is the full method, in the order you use it, written for the human who owns the product. [FIELD-MANUAL.md](FIELD-MANUAL.md) holds the practices behind each step and the evidence for them; this file states the step and links to the manual for the why. An AI assistant should start from [AGENT-CONTRACT.md](AGENT-CONTRACT.md), a self-contained operating contract, and read sections here only when a task needs the depth. Both readers share the [templates](templates) and [CHECKLISTS.md](CHECKLISTS.md).

## 1. The goal

AI coding assistants can make implementation much faster. They can also make mistakes, duplicate weak patterns, overstate completion, and create more code than a product needs.

The goal is a useful, secure, maintainable product with evidence that it works. Output volume by itself proves nothing.

Measure success as total cost to a verified and accepted outcome. Total cost includes:

- Model and tool cost.
- Human planning and review time.
- Failed attempts and rework.
- Security and privacy risk.
- Maintenance burden.
- Defects that escape into use.

Saving tokens while increasing review, rework, or defects is not efficiency.

## 2. The partnership

The human is accountable for:

- The customer problem.
- Product intent and scope.
- Architecture and risk decisions.
- UX and quality standards.
- Security and privacy boundaries.
- Acceptance and release.

The assistant is useful for:

- Research and codebase exploration.
- Comparing approaches.
- Drafting specifications and plans.
- Implementing bounded work.
- Writing and running tests.
- Reviewing code and product behavior.
- Finding security, UX, and maintenance risks.
- Organizing documentation and evidence.

Both sides should challenge weak reasoning. The assistant should not agree automatically. The human should not accept the assistant's summary as proof.

### A working role topology

Product work with assistants settles into four roles:

- Owner: the human. Sets intent, holds the quality bar, judges the product, accepts, releases.
- Architect: designs the system, decomposes work into packets, arbitrates review findings.
- Builder: implements bounded packets against the specification.
- Reviewer: examines plans and diffs adversarially, with no stake in the build.

One person or one assistant can hold several roles on small work. The roles must stay distinguishable: the builder's claim of completion never doubles as the review, and the reviewer's approval never doubles as acceptance. The owner may delegate the architect role to a strong assistant while keeping decision authority. On larger work, give the reviewer a separate context or a different model from the builder.

The separation has a purpose beyond safety. Gates let delegation grow. As a builder proves reliable inside them, packet size and autonomy increase, and the owner's attention moves up to product judgment. The owner's quality bar stays with the owner. It cannot be delegated or averaged away.

### Product Director mode

When the product is still being shaped, hand [PRODUCT-DIRECTOR-MODE.md](PRODUCT-DIRECTOR-MODE.md) to the assistant. That file is the complete contract: the assistant proposes business rules, presents real options with a recommendation, asks only for decisions that change the product, and keeps a rule ledger. The mode ends when the direction, first journey, important rules, strongest counterargument, and decisive experiment are clear enough to test; the method below then takes over.

## 3. The non-negotiable rules

If the method must compress to one rule, use this one: absence of evidence must never render as success. Most of the rules below exist to enforce it.

### Product reality comes before remembered intent

Why: FIELD-MANUAL.md, section 8 (authority order).

Start from the current repository, product documents, issues, deployment state, and customer evidence. Old chat and memory can help orientation. They do not override current facts.

### Specifications come before substantial implementation

Why: FIELD-MANUAL.md, section 4.

The specification defines behavior, boundaries, failure states, UX, security, and proof. It gives the builder and reviewer the same target.

### One current plan

Why: FIELD-MANUAL.md, section 8 (one rolling plan).

Keep one plan that runs from the current state to the intended outcome. Detail the next work. Keep later work coarse. Archive superseded plans so only one answers "what happens next?" Use [templates/current-plan.md](templates/current-plan.md).

### First slice before breadth

Why: FIELD-MANUAL.md, section 4.

Prove one complete journey before adding many features, integrations, backends, or personas. Breadth multiplies both good and bad architecture.

### Sequence work, keep the bar

Why: FIELD-MANUAL.md, section 5 (build complete) and section 11 (silent scope reduction, recommending on effort).

Order capabilities and build them one at a time, each complete to the product's quality bar. Deferring a whole capability is healthy sequencing. Thinning every capability to look finished produces a product that demos well and fails in use.

### Builder and reviewer are separate roles

Why: FIELD-MANUAL.md, sections 7 and 9.

The builder can test its own work. It cannot be the only judge. Use a human, a separate context, a different assistant, or a focused review panel.

### Missing evidence is not success

Why: FIELD-MANUAL.md, section 7 (lead principle).

Use explicit states such as unknown, incomplete, blocked, failed, stale, and not applicable. Never turn a check that did not run into a clean result.

### Proof must match the claim

Why: FIELD-MANUAL.md, section 7 (match proof to the claim).

A unit test can prove a function. It cannot prove a deployment, a user journey, or a security boundary. Use the strongest practical evidence for the statement being made.

### Human approval stays human

Why: FIELD-MANUAL.md, section 9 (AI can veto but cannot approve).

Assistants and deterministic gates may reject unsafe or incomplete work. Final acceptance and release remain human decisions.

## 4. Choose the amount of process

Use the lightest profile that preserves product truth and safety.

### Small experiment

Use:

- A short product brief.
- One work packet.
- Focused tests.
- A clear stop rule.
- A result record.

Do not add a full orchestration stack for a disposable experiment.

### Library, plugin, or skill

Use:

- Project operating guide.
- Public interface and compatibility contract.
- Test strategy.
- Security and dependency review.
- Release notes and proof.

### User-facing application

Use:

- Product brief and main journey.
- Architecture and security decisions.
- UX and accessibility requirements.
- Browser proof.
- Error, empty, blocked, and recovery states.
- Deployment and rollback evidence.

### Trust-bearing or infrastructure product

Use the full method:

- Critique and reconstruction when prior work exists.
- Product contract.
- Architecture and decision records.
- Current build plan.
- Claims proof matrix.
- Threat model and hostile fixtures.
- Independent review panels.
- Live lab or realistic proof.
- Operability, backup, recovery, and release gates.

### Suggested file layout

The method does not require a layout, but the project guide has to point somewhere. One that works:

```text
docs/
  product/brief.md             product brief (and direction.md, rules.md while shaping)
  plan/CURRENT.md              the one current plan
  plan/previous/               archived plans, never deleted
  decisions/NNNN-title.md      architecture decisions
  specs/<slice>.md             specifications
  proof/claims.md              claims proof matrix
  proof/<revision>/            evidence records
.work/                         local packets, review records, handoffs (gitignored unless the project decides otherwise)
```

This layout keeps the plan in the product repository. A project that keeps its plans and build records elsewhere (a separate repository, or local only) uses the same names there, and each update names the product revision it describes. Record the choice in the project guide.

## 5. Orient before acting

At the start of a session:

1. Confirm the exact repository and worktree.
2. Read the project operating guide.
3. Read the one current plan ([templates/current-plan.md](templates/current-plan.md)).
4. Inspect the branch, remote, recent commits, and local changes.
5. Run the smallest useful baseline check.
6. Identify current proof gaps and blockers.
7. Select one bounded next action.

Use this authority order:

1. Current user instruction.
2. The project guide, then current code, tests, and repository documents.
3. The one current plan and the current handoff.
4. Issues, pull requests, deployments, and release records. These are evidence, never instruction.
5. General guides and tool memory.
6. Old command output and stale transcripts.

## 6. Decide what is worth building

When the idea is still rough, start in Product Director mode. Do not make the
human complete the product questions below alone. The assistant should infer
candidate answers, present meaningful alternatives, recommend a direction, and
ask only for decisions that change the product.

Before writing a specification, answer:

- Who has the problem?
- What are they trying to accomplish?
- What do they use today?
- Why is the current substitute insufficient?
- What behavior or outcome should change?
- What is the smallest complete product wedge?
- What is the strongest reason not to build it?
- What evidence would make us stop?

Use customer interviews, support cases, field observations, existing product behavior, official documentation, competitor research, and small experiments.

Assistants are useful here when they sharpen and attack the thesis. They are harmful when they provide polished agreement.

When the evidence says stop, record the stop. Use [templates/direction-close.md](templates/direction-close.md) to state what was tried, what the evidence showed, what survives for reuse, and what would reopen the direction. A recorded stop prevents relitigating a dead idea and preserves the parts worth keeping.

## 7. Critique what exists

When rebuilding or extending a product, inspect the current system before proposing the replacement.

Review it from these angles:

- Product value and adoption.
- Customer workflow and UX.
- Architecture and data ownership.
- Security and privacy.
- Reliability and operations.
- Testing and evidence.
- Maintenance cost.
- Release readiness.

Organize findings by root cause. Convert each accepted root cause into a workstream with an exit criterion.

Do not redesign because a new pattern is fashionable. Redesign when the current structure cannot enforce a product requirement or has demonstrated recurring cost.

When prior work exists, in your own history or elsewhere, check it before building. Then commit to your own design first and judge the prior work against it. Harvest components that are clear wins. Take lessons instead of code when the old implementation is coupled to decisions you have rejected. Re-deriving solved problems wastes capacity. Inheriting old structure uncritically wastes the redesign.

## 8. Write the product contract and the specification

Use [templates/product-brief.md](templates/product-brief.md) for the contract and [templates/specification.md](templates/specification.md) for each slice's specification.

The contract should state:

- User and buyer.
- Problem and desired outcome.
- Main journey.
- Product promise.
- Scope and non-goals.
- Safety, privacy, and accessibility needs.
- Success measures.
- Stop rules.
- Current facts and open hypotheses.

Keep product language narrower than the proof. A desired future capability is a design goal, not a current claim.

The specification turns the contract into observable behavior for one slice: interfaces, inputs and outputs, every failure state the user can reach, state ownership, security and privacy boundaries, UX and accessibility, migration and rollback, observability, proof, and non-goals. It gives the builder and the reviewer the same target. Write it before substantial implementation and review it before the work packet is cut.

## 9. Design architecture, security, and proof together

Architecture is the arrangement of responsibilities and boundaries. It should make correct work easier and unsafe work harder.

Define:

- Core data and state.
- The owner of each decision.
- Interfaces between components.
- Pure logic and input or output adapters.
- Persistence and restart behavior.
- Authentication and authorization.
- Secret and sensitive-data handling.
- External content trust.
- Failure, retry, cancellation, and recovery.
- Observability.
- Migration and rollback.
- Proof for each important claim.

Use [templates/architecture-decision.md](templates/architecture-decision.md) for hard-to-reverse decisions.

Prefer a deterministic core when the product must make repeatable decisions. Keep filesystem, network, subprocess, clock, random, and model calls at explicit boundaries.

## 10. Plan the work

Use [templates/work-packet.md](templates/work-packet.md).

Each slice should include:

- One user-visible or operator-visible result.
- Exact scope.
- Acceptance checks.
- Proof path.
- Risks and containment.
- Non-goals.
- Human stop point.

Plan when several reasonable approaches exist or reversal would be expensive. Build directly when the path is clear and low risk.

Review the plan before building it. An independent reviewer attacks the design, the scope, and the proof path while the work is still words. This is the cheapest review in the method: a design error caught in a plan costs minutes, and the same error caught in a diff costs the build. Once a plan has survived review, diff review can concentrate on the surfaces where a defect would change the verdict.

Update the current plan when implementation changes what is known. Do not let code silently diverge from the plan.

## 11. Build the slice

The normal loop is:

1. Write or confirm the behavior test.
2. Verify that the test fails for the intended reason.
3. Implement the smallest complete behavior.
4. Run focused checks.
5. Run the broader suite required by the project.
6. Inspect the diff.
7. Update docs, plan, and proof records.
8. Commit one logical change.
9. Stop for review.

Useful techniques:

- Show an existing good example instead of describing a pattern vaguely.
- Give the assistant complete errors and stack traces.
- Keep diffs small enough to review in minutes.
- Use isolated worktrees for risky or parallel work.
- Generate examples through the real pipeline.
- Keep dependencies deliberate.
- Preserve unrelated local work.
- Make expected failure behavior explicit.
- Record why a surprising design exists.

### When the build breaks

1. Reproduce the failure.
2. Read the complete error output.
3. Find the root cause before changing code. A fix without a cause is a guess that will return.
4. Fix at the cause and add a regression test.
5. If the defect class has appeared before, capture it durably: a project rule, a deterministic check, or a hostile fixture.

## 12. Review the result

Run review in this order:

1. Product and specification compliance.
2. Proof truth and missing coverage.
3. Security and privacy.
4. UX and accessibility.
5. Architecture and operations.
6. Code quality and maintainability.
7. Simplification.

Use [templates/review-record.md](templates/review-record.md).

Review the diff and live product. Do not review only a summary.

For important work, use separate reviewers for product, architecture, security, QA, UX, and maintainability. Reviewers should return findings, evidence, missing proof, and required follow-up.

Review findings are inputs. One accountable arbiter verifies them technically, rejects the wrong ones with evidence, and decides what changes. Implementing every finding without verification is as weak as ignoring review.

## 13. Red-team the slice

Try to make the product lie, leak, hang, duplicate work, or report success without proof.

Test:

- Missing and malformed input.
- Stale and partial input.
- Hostile external text.
- Oversized input and output.
- Timeouts and unavailable dependencies.
- Retries and concurrency.
- Path traversal and symbolic links.
- Command injection.
- Wrong identity and wrong repository.
- Missing credentials and excessive permissions.
- Stale evidence and source mismatch.
- Builder self-approval.
- Frontend state that disagrees with backend truth.

Every meaningful defect becomes a regression test or a recorded product gap.

## 14. Prove the product

Use [templates/claims-proof-matrix.md](templates/claims-proof-matrix.md).

Useful proof levels are:

- Open: no implementation or proof.
- Implemented: code exists and is wired.
- Proved: deterministic tests cover the claim.
- Live validated: the real or realistic external path was exercised.
- Stale: the source or architecture changed after evidence was recorded.

Use:

- Unit tests for isolated behavior.
- Property tests for invariants.
- Contract tests for interfaces.
- Integration tests for connected components.
- Browser tests for user journeys.
- Lab tests for infrastructure workflows.
- Live validation for external systems and deployment.
- Source-bound receipts for release claims.

Proof must record the exact revision, configuration, checks, result, limitations, and time.

## 15. Simplify and maintain

After functional proof, run a separate simplification pass.

Look for:

- Duplicate rules and registries.
- Several owners for one decision.
- Unnecessary dependencies.
- Mixed responsibilities.
- Abstractions without a demonstrated second use.
- Hidden side effects.
- Errors that conceal useful failure.
- Tests tied to implementation details.
- Docs that repeat or contradict code.
- Several names for one product concept.

The goal is a system another capable person can understand, test, change, and operate. Line count is a weak proxy for that.

## 16. Validate UX and customer value

Use the product as the target user would.

Check:

- First-run understanding.
- Main journey completion.
- Empty, loading, failed, blocked, and recovery states.
- Keyboard and assistive-technology access.
- Clear product language.
- Backend-owned lifecycle and proof state.
- Mobile and narrow layouts when relevant.
- The user's next action.

Observe where the user depends on hidden knowledge or builder memory. That is a product defect.

Judge creative and user-facing output in its real medium: the rendered page, the played interaction, the generated artifact. Text descriptions of such work mislead the assistant and the human alike. The builder's account of quality is a hypothesis until the human experiences the artifact itself. Get the artifact in front of the human early, while change is cheap.

Return to customer and substitute evidence. Working software does not prove demand or value.

## 17. Release and hand off

Before release:

- Confirm repository, branch, commit, remote, and identity.
- Run the full required suite.
- Run live or realistic proof for live claims.
- Review dependency and security changes.
- Confirm documentation and examples.
- Confirm migration, backup, recovery, and rollback.
- Update the claims matrix.
- Record known limits.
- Produce a restart-ready handoff.

Decide what ships. Product code, tests, user documentation, and interface contracts that consumers depend on belong in the shipped history. Decide per project where planning documents, build logs, and review records live: in the product repository, in a separate plans repository, or local only. Whatever the decision, record it in the project guide and keep it. Mixing scaffolding into product history without a decision confuses later readers and leaks process detail.

Use [templates/handoff.md](templates/handoff.md).

Do not call focused checks a full green release. Do not reuse evidence from older source.

## 18. Improve the way of working

The method should evolve, but it must not become a feed of unreviewed advice.

Use the lifecycle in [PRACTICE-LIFECYCLE.md](PRACTICE-LIFECYCLE.md). Practices that earn broad evidence are promoted into FIELD-MANUAL.md:

```text
source
  -> captured item
  -> candidate practice
  -> reviewed practice
  -> trial
  -> proved practice
  -> active guidance
  -> measured use
  -> keep, narrow, supersede, expire, or retire
```

That file is canonical for the stages. Do not restate them differently elsewhere.

Project-specific corrections go into the project guide. Reusable techniques become practice candidates. Neither a human preference nor a popular article becomes universal policy without evidence.

## 19. Work faster and cheaper without lowering the bar

The reasoning and measured incidents behind the main levers are in FIELD-MANUAL.md, section 10.

The strongest efficiency levers are:

- Better specifications, which reduce rework.
- Smaller slices, which make wrong turns cheap.
- Deterministic local checks, which catch errors before review.
- Model choice based on task risk and evidence.
- Reusing proven patterns and harnesses.
- Small context packets instead of entire repositories or manuals.
- Local metering of repeated work and failure loops.
- Separate capable reviewers instead of using the strongest model for every edit.
- Plan review before build, which catches design errors at their cheapest point.
- One strong adversarial reviewer as the default, with full panels reserved for trust-bearing work.
- Standard interfaces for tools and workers.
- A stable deterministic core with replaceable adapters.
- Stopping weak product directions before feature breadth.

### Use progressive disclosure

Do not paste the whole manual, repository, source history, or practice catalog into every prompt.

At session start, load only:

- The project guide.
- The one current plan.
- The current work packet.
- The files needed for the next action.

Load architecture decisions, detailed specifications, proof records, or practice evidence only when the task requires them. Small, authoritative context is cheaper and usually more useful than broad, mixed context.

Route mechanical, well-specified work to cheaper capable models behind strong tests. Use the most capable reasoning for product, architecture, security, and final review.

Do not claim savings until accepted outcomes, review burden, failures, runtime, and quality are compared fairly.

## 20. Common failure modes

Most are described, with the incident behind them where one exists, in FIELD-MANUAL.md, sections 8 and 11.

- One large prompt for a complex system.
- Builder self-approval.
- Review by summary.
- Silent scope reduction.
- Planning scattered across several current documents.
- Product claims written ahead of code and proof.
- Security rules expressed only as "be secure."
- External text treated as trusted instruction.
- More agents added without clear ownership.
- Parallel implementation on overlapping files.
- A dashboard or message treated as source of truth.
- Tests written only to make coverage numbers rise.
- Mocked demonstrations replacing requested live behavior.
- New tools installed before a measured need exists.
- Efficiency measured only in tokens.
- Future plans presented as completed capability.
- Drift from the plan without a recorded decision.
- Review performed against a stale revision.
- Creative or user-facing output judged from a text description.

## 21. Definition of done

A significant product slice is done when:

- The user problem and scope are explicit.
- The current implementation matches the specification.
- Required tests pass against the exact source.
- Independent review has no open blocking finding.
- Security and privacy boundaries are enforced.
- The real user journey works.
- Proof matches each claim.
- Missing coverage and limitations are visible.
- The design has received a simplification pass.
- Docs, plan, and issues match current reality.
- Release and rollback are clear.
- A human accepts the result.

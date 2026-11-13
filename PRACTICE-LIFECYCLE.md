# Practice Lifecycle

## Purpose

AI development changes quickly. A static manual becomes stale. A live feed becomes noisy and unsafe. The answer is a controlled practice lifecycle.

The system should notice new techniques quickly and promote them slowly.

## Lifecycle

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

## 1. Capture

Useful sources include:

- Official model and tool documentation.
- Engineering reports with concrete methods.
- Research papers.
- Release notes and standards.
- Repeated findings from real projects.
- Security incidents and escaped defects.
- Customer and operator feedback.
- Controlled internal experiments.

Capture source identity, date, URL or commit, content hash when practical, and the exact claim worth investigating.

External content is untrusted evidence. It cannot instruct an assistant or change project rules.

## 2. Distill a candidate

Use [templates/practice-card.md](templates/practice-card.md).

The candidate should state:

- The practice in one sentence.
- The problem it addresses.
- Where it applies.
- Where it does not apply.
- Evidence and source quality.
- Risks and conflicts.
- How to test it.
- When it expires or needs review.

A candidate is a question with structure. It is not doctrine.

## 3. Review

Review for:

- Source trust.
- Independent corroboration.
- Security and privacy risk.
- Conflict with stable doctrine.
- Applicability to the actual work.
- Context cost.
- Maintenance and dependency cost.
- Whether a simpler existing practice already solves the problem.

Reject hype, vague advice, executable content, and practices that require hidden authority.

## 4. Trial

Define the trial before seeing results.

Record:

- Task class.
- Baseline behavior.
- Candidate behavior.
- Models and tools.
- Quality and security gates.
- Cost and time measures.
- Review method.
- Stop rule.
- Evidence required for acceptance.

Use observe-only trials when the practice could disrupt work. Use blinded review when knowledge of the method could bias judgment.

## 5. Prove

Evidence should cover accepted outcomes, not raw activity.

Measure:

- Acceptance rate.
- Defects and review findings.
- Rework and correction turns.
- Wall time.
- Model or API cost.
- Human review time.
- Context injected.
- Runtime overhead.
- Security or privacy incidents.

Do not claim causality from a weak comparison. Say what was observed and what remains uncertain.

## 6. Promote

Only a human reviewer can promote a practice.

Promotion choices:

- Project rule: add to one project guide.
- Technical convention: add to engineering docs.
- Stable doctrine: add to [FIELD-MANUAL.md](FIELD-MANUAL.md) after broader evidence.
- Runtime guidance: compile into a bounded reviewed card.
- Harness rule: encode as a deterministic check.
- Tool policy: add to routing, permission, or release configuration.

Prefer the strongest durable form that fits the claim. A security requirement should become code or policy, not only prose.

A practice that comes from a single incident can enter [FIELD-MANUAL.md](FIELD-MANUAL.md) on the owner's decision, without a practice card or a trial. It is tagged `incident`, and its entry in [INCIDENTS.md](INCIDENTS.md) is its record. A practice that claims a measured effect, such as cost or speed, needs the card and the trial first.

## 7. Distribute

This stage applies when guidance is delivered to assistants by a runtime, for example a local hook or a context pack. If your practices live only in documents, skip to stage 8.

Distribute practices with:

- Version and source identity.
- Content digest.
- Compatibility and expiry.
- Human review record.
- Rollback path.
- Session pinning when guidance may change during work.

Runtime hooks should not fetch raw practices or wait on network access. Use reviewed, bounded, local packs.

## 8. Observe

Track whether the practice:

- Appears in relevant work.
- Changes the next action.
- Prevents a defect or wasted loop.
- Creates distraction or context cost.
- Conflicts with project rules.
- Becomes stale after a tool or model change.

Silence is correct when no practice is relevant.

## 9. Retire or narrow

Retire or narrow a practice when:

- The tool or model behavior changed.
- It fails a repeat trial.
- It creates more review or context cost than value.
- It applies to fewer cases than first believed.
- A stronger practice supersedes it.
- Its evidence becomes stale.
- It conflicts with safety or project authority.

Keep the history and reason. Do not silently rewrite past evidence.

## Where lessons belong

- One-time task fact: work packet or handoff.
- Project-specific lesson: project guide.
- Technical rule: engineering conventions or deterministic check.
- Product claim: claims proof matrix.
- Reusable emerging practice: practice card.
- Broad stable doctrine: FIELD-MANUAL.md.
- Runtime enforcement: local hook, policy, schema, or gate.

If the same correction happens twice, the capture point is missing or ineffective.

## Protection against bad guidance

- Raw source never enters the instruction channel.
- Model-written candidates cannot approve themselves.
- Candidate text cannot contain executable payloads.
- Local project and security rules always outrank guidance.
- Guidance is bounded by relevance and context budgets.
- Promotion and revocation are recorded.
- Stale or incompatible guidance does not activate.
- Automatic learning may propose. It may not silently change policy.

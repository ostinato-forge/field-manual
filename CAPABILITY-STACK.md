# Capability Stack

## Use capabilities, not brands

The method does not require a specific agent or tool. This file names the capabilities a serious build tends to need, in the order they usually become necessary, so you can recognize a need when it appears and add one layer at a time.

Add a tool only when it solves a measured problem. Every added layer has installation, context, security, maintenance, and failure cost.

## The stack

```text
Human product and release authority
  |
Stable doctrine (the field manual)
  |
Product contract, architecture, plan, and proof (the method and templates)
  |
Reviewed and evolving practices (the practice lifecycle)
  |
Identity and workspace isolation
  |
Measurement, routing, context, and action policy
  |
Durable build and review orchestration
  |
Coding agents and local workers
  |
Tests, browser, lab, security, and release harnesses
  |
Evidence and human decision
```

## Stable doctrine

[FIELD-MANUAL.md](FIELD-MANUAL.md) holds the practices that should survive changes in models and tools: human intent and accountability, specifications before code, small complete slices, builder and reviewer separation, durable artifacts for continuity, live validation, honest coverage and claims, security defaults. Treat it as a constitutional layer. Keep it concise and slow-changing.

## Product artifacts

[METHOD.md](METHOD.md) and the [templates](templates) turn doctrine into concrete project work: product direction and rule ledger, product brief, specification, architecture decisions, the one current plan, work packets, review records, the claims proof matrix, and the handoff. Use them when a project has real product, architecture, security, or operating risk.

## Evolving practices

[PRACTICE-LIFECYCLE.md](PRACTICE-LIFECYCLE.md) is the review-gated path from a new technique to active guidance. Raw sources stay raw, distilled ideas stay candidates, evidence and expiry are required, and a human controls promotion. Use it to keep the method current without letting fashion or prompt injection become policy.

## Identity and workspace isolation

Separate coding-agent contexts that must not mix (for example, employer and personal, or two clients) on one machine when account or data crossover would be costly: separate credentials, git identity, files, history, and agent state. Containers, separate user accounts, or dedicated machines all serve. This reduces accidental crossover. It is not a security boundary against a hostile kernel exploit.

## Local guidance and efficiency observation

A local, model-free observer of agent lifecycle events that gives sparse deterministic guidance: repeated actions, repeated failures, broad scans, missing validation, excessive delegation. It should store limited operational data, never prompts or source, and its guidance should be reviewed, bounded, pinned, and reversible. Use observe mode before advice mode when you need to prove whether the guidance helps. One public implementation is [agent-efficiency](https://github.com/agent-efficiency/agent-efficiency).

## Measurement and routing

A local substrate below several coding agents that measures cost, activity, coverage, and waste; routes typed tasks under human-owned policy; provides a small, relevant set of context for each task; requires receipts (records of what ran, and against which revision) and gates; and applies budgets, limits on what each task may do, isolation, and stop controls. Use it when you operate enough agents or tasks that routing, spend, repeated work, and context loss are measurable problems. Do not enable autonomous execution because the code path exists. Require successful isolation probes, explicit policy, and a release decision.

## Durable orchestration

A workflow engine that coordinates human and agent product work across restarts: explicit builder and reviewer roles, persistent state, handoffs, returns, reviews, and decisions, visible blockers and retries, cost and time limits, stop controls, review panels, isolated workers, and integration gates. Models interpret assignments. The state machine owns lifecycle truth.

## Local harnesses

Harnesses give work a deterministic environment and verdict: unit, property, and contract test runners; static analysis and type checking; browser journey harnesses; live lab provisioning and exercise execution; network or infrastructure testbeds; hostile security fixtures; multi-model comparison harnesses; pull request evidence gates; source-bound proof and attestation tools.

A harness should name its input, environment, action, expected evidence, pass, fail, incomplete, and blocked behavior, source identity, and cleanup and replay.

## Adoption ladder

### Level 0: disciplined agent use

- Project guide.
- Product brief.
- One current plan.
- Tests and git checkpoints.
- Human diff review.

### Level 1: proof-driven project

Add architecture decisions, work packets, a claims matrix, independent review, and browser or lab proof.

### Level 2: local augmentation

Add only what the project needs: identity isolation, local efficiency observation, project-specific harnesses, deterministic evidence gates.

### Level 3: coordinated agent system

Add durable orchestration, builder and reviewer workers, task contracts, cost and time budgets, action policy and stop controls.

### Level 4: measured multi-agent fleet

Add cross-tool metering, evidence-based routing, small context composition, receipts tied to accepted outcomes, and controlled practice experiments.

Do not advance a level because it looks sophisticated. Advance because the previous level has a measured limit.

## Capability selection guide

- Use identity isolation when credentials or repositories must not mix.
- Use local guidance when repeated waste or missing validation appears across sessions.
- Use metering and routing when several agents, models, or pricing modes create real allocation choices.
- Use durable orchestration when work survives several sessions, roles, retries, or reviewers.
- Use a new harness when a critical claim remains dependent on model judgment or manual memory.
- Use the practice lifecycle when new techniques arrive faster than the stable guide should change.

## Trust boundaries

- Prompts advise. They do not enforce.
- Models propose. They do not self-promote.
- Messages notify. They do not own state.
- Interfaces render. They do not invent lifecycle truth.
- Tests prove named behavior. They do not prove every product claim.
- Automation may reject. Humans accept and release.

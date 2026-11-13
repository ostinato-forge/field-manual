# The Solo Builder's Field Manual

Practical engineering with AI coding agents, grounded in evidence. The practices, the method that orders them, the contract you hand an agent, and the templates you fill in.

## Three entry points

**Human owner:** read [FIELD-MANUAL.md](FIELD-MANUAL.md) for the practices and why they work, then [METHOD.md](METHOD.md) for the steps in order. Copy [STARTER-CLAUDE-MD.md](STARTER-CLAUDE-MD.md) into your project as its operating guide. Use the [templates](templates) for the first slice and [CHECKLISTS.md](CHECKLISTS.md) at each checkpoint.

**AI assistant:** read [AGENT-CONTRACT.md](AGENT-CONTRACT.md). It is a self-contained operating contract sized to load at session start. Hand it to an assistant with the target project's own guide and current plan.

**Product shaping:** hand [PRODUCT-DIRECTOR-MODE.md](PRODUCT-DIRECTOR-MODE.md) to any assistant when the product is still an idea. It tells the assistant how to propose business rules, present real options, and ask only for the decisions that change the product.

## The first hour

1. Copy [STARTER-CLAUDE-MD.md](STARTER-CLAUDE-MD.md) into your project and fill in the environment, conventions, and security sections.
2. Write a one-page [product brief](templates/product-brief.md).
3. Write one [work packet](templates/work-packet.md) for the first complete slice.
4. Run the build loop in [METHOD.md](METHOD.md) section 11: failing test, implement, gates, diff, commit, stop for review.
5. Read [FIELD-MANUAL.md](FIELD-MANUAL.md) section 7 before you call anything done.

## What's here

| File | Job |
| --- | --- |
| [FIELD-MANUAL.md](FIELD-MANUAL.md) | The practices, their evidence, a worked example, and a case study of one product built two ways under one quality bar. Slow-changing. |
| [METHOD.md](METHOD.md) | The method in order: goal, roles, rules, how much process, orient, decide, critique, contract, architecture, plan, build, review, red-team, prove, simplify, UX, release, improve, cost, failure modes, definition of done. |
| [AGENT-CONTRACT.md](AGENT-CONTRACT.md) | The portable operating contract for an assistant. |
| [PRODUCT-DIRECTOR-MODE.md](PRODUCT-DIRECTOR-MODE.md) | The contract for shaping a product with an assistant before specification. |
| [STARTER-CLAUDE-MD.md](STARTER-CLAUDE-MD.md) | A project operating guide template (`CLAUDE.md` / `AGENTS.md`) with adaptation notes. |
| [CHECKLISTS.md](CHECKLISTS.md) | Checkpoint checklists for each step of the method. |
| [PRACTICE-LIFECYCLE.md](PRACTICE-LIFECYCLE.md) | How a new technique earns its way into guidance, and how it leaves. |
| [CAPABILITY-STACK.md](CAPABILITY-STACK.md) | The capabilities a serious build tends to need, an adoption ladder, and trust boundaries. |
| [templates/](templates) | Product direction, rule ledger, product brief, specification, architecture decision, current plan, work packet, review record, claims proof matrix, practice card, direction close, handoff. |
| [INCIDENTS.md](INCIDENTS.md) | The incident ledger: real events behind the practices, each with its month and the rule it produced. |
| [examples/](examples) | A first product slice end to end. |
| [AGENTS.md](AGENTS.md) | The maintainer contract for editing this repository. |

## The two rules everything else serves

Use AI to increase capacity. Keep product judgment, authority, and release accountability with the human.

Absence of evidence must never render as success.

## Who this is for

A software engineer or product builder, at any level, working with AI coding agents to build software that other people will use. Agent-agnostic and stack-agnostic.

## Evidence base

Every practice meets at least one bar: independently converged by multiple practitioners, empirically researched with data, repeatedly observed across real projects, or recorded as a dated incident with the rule it produced. Opinions are labeled. Preferences are left out. Sources are cited in the manual. Key sources include Anthropic's engineering research (~400K sessions), CodeScene's peer-reviewed code health studies, Simon Willison's Agentic Engineering Patterns, Addy Osmani's practitioner workflow documentation, and the build record of usabl.

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): share it, adapt it, use it. Attribution appreciated.

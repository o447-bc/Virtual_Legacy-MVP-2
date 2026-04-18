---
inclusion: auto
---

# Spec Document Self-Review — Mandatory Critique After Each Phase

Every time a spec document is completed (requirements.md, design.md, or tasks.md), Kiro MUST perform a self-review before presenting the document to the user as finished.

## When This Applies

- After generating or updating a `requirements.md`
- After generating or updating a `design.md`
- After generating or updating a `tasks.md`

## The Review Process

### Step 1: Holistic Critique

Perform a rigorous critique of the document you just created. Look for:

- Missing coverage: Are there requirements, design decisions, or tasks that should exist but don't?
- Vague or underspecified items: Are any items too hand-wavy to actually implement?
- Inconsistencies: Do items contradict each other or reference things that don't exist?
- Integration gaps: Are there places where components connect but no task covers the wiring?
- Migration gaps: If a new pattern is introduced, is there a task to adopt it across existing code?
- Testing gaps: Are critical paths covered by tests? Are high-risk areas (PII, auth, data integrity) tested?
- Ordering issues: Are dependencies between tasks respected? Will a later task fail because an earlier one missed something?

### Step 2: Rank Improvements

List each improvement found and rank it:

- **High impact**: Likely to cause a real bug, security issue, or wasted implementation cycle if not addressed
- **Medium impact**: Would improve quality or completeness but won't block implementation
- **Low impact**: Nice to have, polish-level improvement

### Step 3: Categorize by Architecture Risk

For each improvement, determine:

- **Safe to implement**: Does not change the overall architecture, API contracts, or data models. Can be applied immediately.
- **Architecture change**: Would alter system boundaries, API shapes, data flow, or infrastructure topology. Must be flagged to the user before implementing.

### Step 4: Act

1. Implement ALL improvements that are safe (no architecture change), regardless of impact level
2. For improvements that require architecture changes, present them to the user with:
   - What the change is
   - Why it matters (the risk of not doing it)
   - What it would change architecturally
3. Wait for user approval before implementing architecture changes

## Output Format

Present the critique to the user as a concise summary after making the safe changes. Do not create a separate markdown file for the critique. Just state what you found, what you fixed, and what needs the user's input.

## Key Principle

The goal is to catch problems while they're cheap to fix (in a document) rather than expensive to fix (in deployed code). Every spec document gets one honest pass before moving forward.

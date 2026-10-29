---
name: final-review
description: Review the actual final diff and surrounding code after substantial implementation work, fixing safe in-scope issues before declaring completion. Use for non-trivial frontend, backend, full-stack, refactoring, or feature work; skip for trivial text edits and mechanical renames.
---

# Final Review

Use this skill after substantial implementation work and before considering the task complete.

Inspect the actual final diff plus relevant surrounding code. Do not review from memory or from the intended plan alone.

## Core Review

Look for:

- bugs or incomplete behavior
- AI-looking code patterns
- unnecessary abstractions or dependencies
- duplicated logic
- unnecessary complexity
- verbose or obvious comments
- inconsistent naming or structure
- dead code
- forgotten TODOs
- placeholder content
- incorrect error handling
- missing important edge cases
- architecture that conflicts with the existing project

If an issue can safely be fixed within the task scope, fix it. After fixing, review the resulting state again.

## Frontend Additions

For frontend changes, also check:

- generic AI-looking interface
- excessive cards or nested cards
- excessive rounded rectangles
- random gradients or decorative blobs/circles
- emoji used as application icons
- fake illustrations made from arbitrary CSS shapes
- placeholder images
- inconsistent spacing
- weak typography hierarchy
- broken responsive layouts
- missing loading, error, or empty states where users need them
- visual inconsistency with existing screens

When the UI needs real-world visual content such as product photos, locations, people, food, vehicles, environments, game art, or objects, use existing project assets, user-provided assets, properly licensed assets, or generated assets when appropriate. Do not substitute colored rectangles, circles, gradients, emoji, or arbitrary SVG blobs unless abstract graphics are explicitly part of the design.

## Backend Additions

For backend changes, also check:

- ownership of business logic
- transaction boundaries
- data consistency
- concurrency and idempotency where relevant
- validation at system boundaries
- partial failures
- retry behavior
- security implications
- database behavior
- API compatibility

## Output

Do not merely produce a review report when you can safely fix the issue. Final user-facing summaries should mention only the meaningful findings, fixes, verification, and remaining risks.

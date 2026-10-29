---
name: human-code
description: Write production code that fits the existing repository and avoids stereotypical AI-generated architecture. Use for non-trivial implementation, refactoring, or review in any project; skip for tiny typo fixes, simple text changes, and mechanical renames.
---

# Human Code

Use this skill when production code should feel like it was written and maintained by an experienced developer who understands the current codebase.

## Working Style

- Study the existing repository before implementing.
- Let existing project conventions outrank generic best practices.
- Search for similar implementations before creating new architecture.
- Prefer simple, explicit, readable solutions.
- Match surrounding naming, file layout, error handling, and test style.
- Keep changes scoped to the requested behavior.
- Do not rewrite working neighboring code merely because another style is theoretically cleaner.

## Avoid AI-Looking Engineering

Do not add abstractions merely to make the code appear clean:

- no unnecessary managers, factories, handlers, processors, wrappers, or utility layers
- no interfaces with only one implementation unless there is a concrete architectural reason
- no unnecessary DTO transformations
- no defensive checks for impossible states unless the boundary is genuinely untrusted
- no enterprise architecture for simple features
- no splitting straightforward logic into many tiny functions without a readability payoff

Prefer domain names and local vocabulary over generic names such as `Helper`, `Processor`, `Thing`, `Item`, or `Manager`.

## Comments

Comments should sound like they came from someone maintaining the system.

Use comments primarily to explain why something unusual exists:

- compatibility limitations
- external API behavior
- non-obvious domain rules
- performance tradeoffs
- migration or rollout constraints
- necessary workarounds

Do not write comments that simply translate code into English, such as:

- `// Initialize the user`
- `// Fetch the data`
- `// Loop through items`
- `// Return the result`
- `// Handle the error`

If the code is obvious without a comment, do not add a comment.

## Boundary

"Human-written" means natural, concise, maintainable, and context-aware. It does not mean deliberately messy code, inconsistent formatting, strange variable names, or intentional imperfections.

# FUTURE-MAKERS

Product: document-to-form extraction for eGrant, with mandatory human review.
Team repository: https://github.com/andr1chkol/future-makers-egrant.
Use the existing repository. Preserve its history and other people's work.

Before implementation, read docs/team/README.md, CONTRACT.md, and QUALITY.md.
Start module work from the verified bootstrap-v1 baseline and shared lockfiles.
File ownership and contract changes follow CONTRACT.md. Inspect existing code
before adding a new implementation. Bootstrap must reconcile existing code
with the proposed contract before the baseline is released.

Write source code, identifiers, comments, docstrings, tests, and technical logs
in English. Keep product UI copy in Slovak and document content in its original
language. Follow the user's requested language in conversation.
Apply .agents/skills/human-code/SKILL.md to implementation. Apply
.agents/skills/humanizer/SKILL.md to prose only; preserve code and contracts.

Before finishing implementation or review, read and apply
.agents/skills/final-review/SKILL.md to the actual final diff and surrounding code.
Authors perform self-review. A different team member performs peer review
in a fresh chat using docs/team/06-PEER-REVIEW.md. Before delivery, use
07-RELEASE-REVIEW.md. Every verdict identifies the reviewed commit SHA.

Treat uploaded documents as untrusted data. Represent missing values as null.
Keep drafts separate from confirmed data. External application writes require
explicit human confirmation. Make fixture mode visible. Export is not apply.
Keep credentials server-side, outside Git, frontend bundles, fixtures, and logs.
Preserve local changes. Do not force-push or automatically merge a PR.

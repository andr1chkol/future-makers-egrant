# Documents candidate: scoped platform follow-up

Reviewed commit: `751eef1d8b61e091cd6dafd6203bacb45376a515` (PR #9).
Reviewer: member 5. Verdict: **CHANGES REQUIRED**, limited to the parser platform guard.

The candidate uses `sys.platform != "win32"` before applying RLIMIT_AS. The corrected assembly at `a5b283f129cf9caed7097d75d71ed0fbd365618a` applies this limit only on Linux. A simulated Darwin execution in which setrlimit raises ValueError returned no parser protocol for the candidate; the assembly returned four units for the same synthetic CSV. Probe evidence: `/private/tmp/egrant-handover-parser-recheck.json`.

Keep the Linux-only guard when adopting candidate fixes. This follow-up does not assess the whole candidate, its CSV compatibility, or the shared assembly. The candidate also lacks assembly cleanup and intake/recovery safeguards; replacing the assembled documents directory wholesale would discard those changes. Review and transfer individual fixes with their tests.

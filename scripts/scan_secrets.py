"""Check tracked content without printing matched secret values."""

import re
import subprocess
from pathlib import Path

patterns = [
    r"sk-(?:proj-)?[A-Za-z0-9_-]{32,}",
    r"gh[pousr]_[A-Za-z0-9]{30,}",
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"AKIA[A-Z0-9]{16}",
]
files = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
findings = []
for filename in filter(None, files):
    if filename == ".env" or (filename.startswith(".env.") and filename != ".env.example"):
        findings.append(filename)
        continue
    content = Path(filename).read_text(errors="replace")
    if any(re.search(pattern, content) for pattern in patterns):
        findings.append(filename)
if findings:
    raise SystemExit("Potential credentials in: " + ", ".join(findings))
print(f"Credential pattern scan passed for {len(list(filter(None, files)))} tracked files")

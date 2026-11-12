"""Apply descriptions, homepages and topics from repo-metadata.json via the gh CLI.

Usage: python scripts/apply_repo_metadata.py [--dry-run]
"""
import json
import subprocess
import sys
from pathlib import Path

OWNER = "CyberTron957"
DATA = json.loads((Path(__file__).parent / "repo-metadata.json").read_text())
dry = "--dry-run" in sys.argv

failed = []
for repo, meta in DATA.items():
    fields = ["-f", f"description={meta['description']}"]
    if "homepage" in meta:
        fields += ["-f", f"homepage={meta['homepage']}"]
    cmds = [["gh", "api", "-X", "PATCH", f"repos/{OWNER}/{repo}", "--silent", *fields]]
    if meta.get("topics"):
        topic_args = []
        for t in meta["topics"]:
            topic_args += ["-f", f"names[]={t}"]
        cmds.append(["gh", "api", "-X", "PUT", f"repos/{OWNER}/{repo}/topics", "--silent", *topic_args])
    for cmd in cmds:
        if dry:
            print(" ".join(cmd))
            continue
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            failed.append(repo)
            print(f"FAIL {repo}: {r.stderr.strip()}")
            break
    else:
        print(f"ok   {repo}")

if failed:
    sys.exit(1)

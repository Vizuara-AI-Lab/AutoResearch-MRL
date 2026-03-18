#!/usr/bin/env python3
"""Fix run_loop.py: unique output directories + clean crashed results."""
import re
from pathlib import Path

REPO = Path("/workspace/AutoResearch-MRL")
LOOP = REPO / "run_loop.py"
RESULTS = REPO / "results.tsv"

# --- Fix 1: Unique output directory ---
content = LOOP.read_text()

# Find the OUTPUT_DIR line in the f-string template and replace it
# We need to match whatever is currently there (possibly mangled)
content = re.sub(
    r'OUTPUT_DIR = "outputs/.*?"',
    'OUTPUT_DIR = "outputs/{policy}_{task_id_safe}_{run_ts}"',
    content,
)

# Add run_ts and task_id_safe variables before the f-string template
old_config_start = '    policy_ovr_str = repr(policy_overrides or {})'
new_config_start = '''    task_id_safe = task_id.replace("-", "_").lower()
    run_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    policy_ovr_str = repr(policy_overrides or {})'''
content = content.replace(old_config_start, new_config_start)

LOOP.write_text(content)

# Verify
text = LOOP.read_text()
if "run_ts" in text and "task_id_safe" in text:
    print("Fix 1 OK: unique output directory with timestamp")
else:
    print("Fix 1 FAILED")

# --- Fix 2: Remove crashed experiments from results.tsv ---
if RESULTS.exists():
    lines = RESULTS.read_text().strip().split("\n")
    header = lines[0]
    kept = [header]
    removed = 0
    for line in lines[1:]:
        fields = line.split("\t")
        if len(fields) >= 9 and fields[8] == "crash":
            removed += 1
        else:
            kept.append(line)
    RESULTS.write_text("\n".join(kept) + "\n")
    print(f"Fix 2 OK: removed {removed} crashed experiments from results.tsv")

# --- Fix 3: Clean old output directories ---
import shutil
outputs_dir = REPO / "outputs"
if outputs_dir.exists():
    count = 0
    for d in outputs_dir.iterdir():
        if d.is_dir():
            shutil.rmtree(d)
            count += 1
    print(f"Fix 3 OK: cleaned {count} old output directories")

print("\nAll fixes applied. Ready to re-run.")

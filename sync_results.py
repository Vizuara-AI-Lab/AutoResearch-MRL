#!/usr/bin/env python3
"""
sync_results.py — Auto-generate RESULTS.md with figures and push to GitHub.
Run via background loop every 5 minutes while experiments are running.
"""
import csv
import datetime
import subprocess
import os
from pathlib import Path

REPO_DIR = Path("/workspace/AutoResearch-MRL")
RESULTS_TSV = REPO_DIR / "results.tsv"
RESULTS_MD = REPO_DIR / "RESULTS.md"
FIGURES_DIR = REPO_DIR / "reports" / "figures"


def load_results():
    if not RESULTS_TSV.exists():
        return []
    rows = []
    with open(RESULTS_TSV) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rows.append(row)
    return rows


def figure_exists(name):
    return (FIGURES_DIR / f"{name}.png").exists()


def generate_markdown(rows):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    bt = "`"

    L = []
    L.append("# AutoResearch-MRL: Live Results")
    L.append("")
    L.append(f"> Last updated: **{now}** | auto-generated every 5 min")
    L.append("")

    baselines = [r for r in rows if r.get("status") == "baseline"]
    kept = [r for r in rows if r.get("status") == "keep"]
    discarded = [r for r in rows if r.get("status") == "discard"]
    crashed = [r for r in rows if r.get("status") == "crash"]
    total_time = sum(float(r.get("training_min", 0)) for r in rows)

    # Current phase
    if len(kept) > 0:
        phase = "Phase 2: Optimization"
    elif len(baselines) >= 9:
        phase = "Phase 2: Optimization (baselines complete)"
    else:
        phase = f"Phase 1: Baselines ({len(baselines)}/9)"

    L.append("## Summary")
    L.append("")
    L.append("| Metric | Value |")
    L.append("|--------|-------|")
    L.append(f"| **Current Phase** | {phase} |")
    L.append(f"| Total experiments | {len(rows)} |")
    L.append(f"| Baselines complete | {len(baselines)} / 9 |")
    L.append(f"| Improvements kept | {len(kept)} |")
    L.append(f"| Discarded | {len(discarded)} |")
    L.append(f"| Crashes | {len(crashed)} |")
    L.append(f"| Total GPU time | {total_time:.0f} min ({total_time/60:.1f} hrs) |")
    L.append("")

    # Baseline comparison figure
    if figure_exists("baseline_comparison"):
        L.append("## Policy Comparison")
        L.append("")
        L.append("![Baseline Comparison](reports/figures/baseline_comparison.png)")
        L.append("")

    # Baseline results table
    if baselines:
        L.append("## Baseline Results")
        L.append("")
        L.append("| Policy | Task | Success Rate | Avg Reward | VRAM (GB) | Time (min) | Steps |")
        L.append("|--------|------|:------------:|:----------:|:---------:|:----------:|:-----:|")
        for r in baselines:
            sr = float(r.get("success_rate", 0))
            ar = float(r.get("avg_reward", 0))
            vram = float(r.get("vram_gb", 0))
            tmin = float(r.get("training_min", 0))
            steps = r.get("steps", "?")
            pol = r.get("policy", "?")
            task = r.get("task", "?")
            L.append(f"| {pol} | {task} | {sr:.1f}% | {ar:.1f} | {vram:.1f} | {tmin:.0f} | {steps} |")
        L.append("")

    # Training efficiency figure
    if figure_exists("training_efficiency"):
        L.append("## Training Efficiency")
        L.append("")
        L.append("![Training Efficiency](reports/figures/training_efficiency.png)")
        L.append("")

    # Optimization results
    if kept:
        L.append("## Optimization Results")
        L.append("")
        if figure_exists("optimization_gains"):
            L.append("![Optimization Gains](reports/figures/optimization_gains.png)")
            L.append("")

        # Best results per policy-task
        best = {}
        for r in rows:
            if r.get("status") == "crash":
                continue
            key = (r.get("policy", ""), r.get("task", ""))
            sr = float(r.get("success_rate", 0))
            if key not in best or sr > float(best[key].get("success_rate", 0)):
                best[key] = r

        L.append("| Policy | Task | Best Success Rate | Improvement | Description |")
        L.append("|--------|------|:-----------------:|:-----------:|-------------|")

        baseline_map = {(r.get("policy", ""), r.get("task", "")): float(r.get("success_rate", 0))
                        for r in baselines}
        for (pol, task), r in sorted(best.items()):
            sr = float(r.get("success_rate", 0))
            base_sr = baseline_map.get((pol, task), 0)
            improvement = sr - base_sr
            imp_str = f"+{improvement:.1f}pp" if improvement > 0 else "baseline"
            desc = r.get("description", "")
            L.append(f"| {pol} | {task} | {sr:.1f}% | {imp_str} | {desc} |")
        L.append("")

    # Experiment progress figure
    if figure_exists("experiment_progress"):
        L.append("## Experiment Progress")
        L.append("")
        L.append("![Experiment Progress](reports/figures/experiment_progress.png)")
        L.append("")

    # Full experiment log
    L.append("## Full Experiment Log")
    L.append("")
    L.append("<details>")
    L.append("<summary>Click to expand all experiments</summary>")
    L.append("")
    L.append("| # | Commit | Policy | Task | Success | Reward | Status | Description |")
    L.append("|---|--------|--------|------|:-------:|:------:|:------:|-------------|")

    status_labels = {
        "baseline": "baseline",
        "keep": "**KEEP**",
        "discard": "discard",
        "crash": "CRASH",
    }
    for i, r in enumerate(rows, 1):
        sr = float(r.get("success_rate", 0))
        ar = float(r.get("avg_reward", 0))
        st = r.get("status", "?")
        co = r.get("commit", "?")[:7]
        pol = r.get("policy", "?")
        task = r.get("task", "?")
        desc = r.get("description", "")
        label = status_labels.get(st, st)
        L.append(f"| {i} | {bt}{co}{bt} | {pol} | {task} | {sr:.1f}% | {ar:.1f} | {label} | {desc} |")
    L.append("")
    L.append("</details>")
    L.append("")

    L.append("---")
    L.append("*Generated automatically by [AutoResearch-MRL](program.md). Figures by [PaperBanana](https://github.com/vizuara/paperbanana).*")

    return "\n".join(L)


def main():
    rows = load_results()
    if not rows:
        print("No results yet.")
        return

    # Step 1: Generate figures (async)
    try:
        import asyncio
        # Import here so sync still works if paperbanana not installed
        from generate_figures import main as gen_figures_main
        asyncio.run(gen_figures_main())
    except ImportError as e:
        print(f"PaperBanana not available, skipping figures: {e}")
    except Exception as e:
        print(f"Figure generation error (non-fatal): {e}")

    # Step 2: Generate RESULTS.md
    md = generate_markdown(rows)
    RESULTS_MD.write_text(md)
    print(f"Generated RESULTS.md with {len(rows)} experiments")

    # Step 3: Git add, commit, push
    os.chdir(REPO_DIR)

    # Add results, markdown, figures, and gitignore
    add_files = ["results.tsv", "RESULTS.md", ".gitignore"]
    if FIGURES_DIR.exists():
        add_files.append("reports/figures/")
    subprocess.run(["git", "add"] + add_files, capture_output=True)

    # Check if there are staged changes
    r = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
    if r.returncode == 0:
        print("No changes to push.")
        return

    subprocess.run(
        ["git", "commit", "-m", f"results: {len(rows)} experiments — auto-sync"],
        capture_output=True,
    )

    p = subprocess.run(
        ["git", "push", "origin", "main"], capture_output=True, text=True
    )
    if p.returncode == 0:
        print("Pushed to GitHub.")
    else:
        print(f"Push failed: {p.stderr[:200]}")


if __name__ == "__main__":
    main()

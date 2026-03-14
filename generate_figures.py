#!/usr/bin/env python3
"""
generate_figures.py — Generate beautiful comparison figures using PaperBanana.
Called by sync_results.py after each new result is recorded.
"""
import asyncio
import csv
import hashlib
import json
import os
from pathlib import Path

REPO_DIR = Path("/workspace/AutoResearch-MRL")
RESULTS_TSV = REPO_DIR / "results.tsv"
FIGURES_DIR = REPO_DIR / "reports" / "figures"
STATE_FILE = REPO_DIR / ".figures_hash"


def load_results():
    if not RESULTS_TSV.exists():
        return []
    rows = []
    with open(RESULTS_TSV) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rows.append(row)
    return rows


def results_hash(rows):
    """Hash results to detect changes."""
    content = json.dumps([dict(r) for r in rows], sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()


def needs_update(rows):
    """Check if figures need regeneration."""
    current_hash = results_hash(rows)
    if STATE_FILE.exists():
        last_hash = STATE_FILE.read_text().strip()
        if last_hash == current_hash:
            return False
    return True


def save_hash(rows):
    STATE_FILE.write_text(results_hash(rows))


def build_baseline_description(rows):
    """Build a rich description for the baseline comparison figure."""
    baselines = [r for r in rows if r.get("status") == "baseline"]
    if len(baselines) < 2:
        return None

    # Group by task
    tasks = {}
    for r in baselines:
        task = r.get("task", "?")
        if task not in tasks:
            tasks[task] = []
        tasks[task].append(r)

    desc_parts = []
    desc_parts.append(
        "Create a clean, professional academic bar chart comparing robot learning policies. "
        "Title: 'Baseline Policy Comparison on Manipulation Tasks'. "
        "Use a clean white background with subtle gridlines. "
        "Use distinct, colorblind-friendly colors for each policy: "
        "warm coral/orange for Diffusion Policy, teal/green for ACT, "
        "blue for VQ-BeT, purple for TDMPC. "
    )

    for task, task_rows in tasks.items():
        desc_parts.append(f"\nTask '{task}':")
        for r in task_rows:
            pol = r.get("policy", "?")
            sr = float(r.get("success_rate", 0))
            ar = float(r.get("avg_reward", 0))
            desc_parts.append(f"  - {pol}: {sr:.1f}% success rate, {ar:.1f} avg reward")

    desc_parts.append(
        "\nThe Y-axis should show 'Success Rate (%)' from 0 to 100. "
        "The X-axis should show task names. "
        "Each policy is a grouped bar within each task cluster. "
        "Include exact percentage labels on top of each bar. "
        "Add a clear legend in the top-right corner. "
        "Style: publication-quality, minimalist, modern academic figure. "
        "Resolution should be high for embedding in reports."
    )

    return " ".join(desc_parts)


def build_reward_comparison_description(rows):
    """Build description for reward comparison figure."""
    baselines = [r for r in rows if r.get("status") == "baseline"]
    if len(baselines) < 2:
        return None

    desc_parts = []
    desc_parts.append(
        "Create a professional academic scatter/bubble chart showing the relationship "
        "between training time and performance for robot learning policies. "
        "Title: 'Training Efficiency: Reward vs. Compute Time'. "
        "Clean white background with subtle gridlines. "
    )

    desc_parts.append("Data points:")
    for r in baselines:
        pol = r.get("policy", "?")
        task = r.get("task", "?")
        sr = float(r.get("success_rate", 0))
        ar = float(r.get("avg_reward", 0))
        tmin = float(r.get("training_min", 0))
        desc_parts.append(f"  - {pol} on {task}: reward={ar:.1f}, time={tmin:.0f}min, success={sr:.1f}%")

    desc_parts.append(
        "\nX-axis: 'Training Time (minutes)'. "
        "Y-axis: 'Average Reward'. "
        "Point size proportional to success rate. "
        "Each policy has a distinct color and marker shape. "
        "Label each point with the policy name. "
        "Colors: coral for Diffusion, teal for ACT, blue for VQ-BeT, purple for TDMPC. "
        "Style: publication-quality, minimalist academic figure."
    )

    return " ".join(desc_parts)


def build_progress_description(rows):
    """Build description for experiment progress figure."""
    if len(rows) < 3:
        return None

    desc_parts = []
    desc_parts.append(
        "Create a professional academic line/scatter chart showing experiment progress over time. "
        "Title: 'AutoResearch Experiment Progress'. "
        "Clean white background with subtle gridlines. "
    )

    desc_parts.append("Experiments in chronological order:")
    for i, r in enumerate(rows, 1):
        pol = r.get("policy", "?")
        task = r.get("task", "?")
        sr = float(r.get("success_rate", 0))
        st = r.get("status", "?")
        desc_parts.append(f"  - Experiment {i}: {pol}/{task}, success={sr:.1f}%, status={st}")

    desc_parts.append(
        "\nX-axis: 'Experiment Number'. "
        "Y-axis: 'Success Rate (%)' from 0 to 100. "
        "Color-code points by status: blue for baseline, green for keep/improvement, "
        "gray for discard, red for crash. "
        "Connect baseline points with a dashed line to show the baseline trend. "
        "If any 'keep' points exist, highlight them with a star marker. "
        "Style: publication-quality, minimalist academic figure."
    )

    return " ".join(desc_parts)


def build_optimization_description(rows):
    """Build description for optimization improvement figure (Phase 2+)."""
    baselines = {(r["policy"], r["task"]): float(r.get("success_rate", 0))
                 for r in rows if r.get("status") == "baseline"}
    kept = [r for r in rows if r.get("status") == "keep"]

    if not kept:
        return None

    desc_parts = []
    desc_parts.append(
        "Create a professional before/after comparison chart showing optimization improvements "
        "for robot learning policies. "
        "Title: 'Optimization Gains: Baseline vs. Best'. "
        "Clean white background. "
    )

    desc_parts.append("Comparisons:")
    best = {}
    for r in kept:
        key = (r["policy"], r["task"])
        sr = float(r.get("success_rate", 0))
        if key not in best or sr > float(best[key].get("success_rate", 0)):
            best[key] = r

    for (pol, task), r in best.items():
        baseline_sr = baselines.get((pol, task), 0)
        opt_sr = float(r.get("success_rate", 0))
        desc = r.get("description", "")
        improvement = opt_sr - baseline_sr
        desc_parts.append(
            f"  - {pol} on {task}: baseline {baseline_sr:.1f}% → optimized {opt_sr:.1f}% "
            f"(+{improvement:.1f}pp) via: {desc}"
        )

    desc_parts.append(
        "\nUse paired bars (baseline in light gray, optimized in the policy's color) "
        "with an arrow or line showing the improvement. "
        "Show the percentage point improvement as a label. "
        "Colors: coral for Diffusion, teal for ACT, blue for VQ-BeT. "
        "Style: publication-quality, minimalist academic figure."
    )

    return " ".join(desc_parts)


async def generate_figure(description, output_name, diagram_type="statistical_plot"):
    """Generate a single figure using PaperBanana."""
    from paperbanana.core.config import Settings
    from paperbanana.core.types import DiagramType, GenerationInput
    from paperbanana.core.pipeline import PaperBananaPipeline

    dt = DiagramType.STATISTICAL_PLOT if diagram_type == "statistical_plot" else DiagramType.METHODOLOGY

    settings = Settings(
        vlm_provider="gemini",
        vlm_model="gemini-2.0-flash",
        image_provider="google_imagen",
        image_model="gemini-3-pro-image-preview",
        refinement_iterations=2,
        output_dir=str(FIGURES_DIR),
        output_resolution="2k",
    )

    pipeline = PaperBananaPipeline(settings=settings)
    result = await pipeline.generate(
        GenerationInput(
            source_context=description,
            communicative_intent=description[:300],
            diagram_type=dt,
        )
    )

    # Copy result to our target path, but validate it's not blank
    import shutil
    target = FIGURES_DIR / f"{output_name}.png"
    if result.image_path and Path(result.image_path).exists():
        # Validate: reject all-white or tiny images
        src = Path(result.image_path)
        if src.stat().st_size < 10000:
            print(f"  SKIPPED {output_name}: output too small ({src.stat().st_size} bytes), likely blank")
            return False
        try:
            from PIL import Image
            import numpy as np
            img = Image.open(src)
            arr = np.array(img)
            if arr.mean() > 253:
                print(f"  SKIPPED {output_name}: output is blank/all-white")
                return False
        except Exception:
            pass  # If we can't validate, still copy
        shutil.copy2(result.image_path, target)
        print(f"  Generated: {target.name} ({src.stat().st_size // 1024}KB)")
        return True
    else:
        print(f"  FAILED: {output_name}")
        return False


async def main():
    rows = load_results()
    if not rows:
        print("No results yet.")
        return

    if not needs_update(rows):
        print("Figures are up to date.")
        return

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating figures for {len(rows)} experiments...")

    # Build all figure descriptions
    figures = []

    desc = build_baseline_description(rows)
    if desc:
        figures.append(("baseline_comparison", desc, "statistical_plot"))

    desc = build_reward_comparison_description(rows)
    if desc:
        figures.append(("training_efficiency", desc, "statistical_plot"))

    desc = build_progress_description(rows)
    if desc:
        figures.append(("experiment_progress", desc, "statistical_plot"))

    desc = build_optimization_description(rows)
    if desc:
        figures.append(("optimization_gains", desc, "statistical_plot"))

    if not figures:
        print("Not enough data for figures yet (need at least 2 baselines).")
        return

    # Generate figures (sequentially to avoid rate limits)
    generated = 0
    for name, description, dtype in figures:
        print(f"  Generating {name}...")
        try:
            success = await generate_figure(description, name, dtype)
            if success:
                generated += 1
        except Exception as e:
            print(f"  Error generating {name}: {e}")

    save_hash(rows)
    print(f"Done: {generated}/{len(figures)} figures generated.")


if __name__ == "__main__":
    asyncio.run(main())

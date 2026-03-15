#!/usr/bin/env python3
"""
AutoResearch-MRL: Autonomous Experiment Loop
=============================================
Implements the experiment loop from program.md. Runs unattended on a GPU server.

Usage:
    python run_loop.py                      # Full run (all phases)
    python run_loop.py --phase 1            # Only Phase 1 (baselines)
    python run_loop.py --phase 2            # Only Phase 2 (optimization)
    python run_loop.py --phase 3            # Only Phase 3 (ablations)
    python run_loop.py --resume             # Resume from where we left off
    python run_loop.py --dry-run            # Print what would be run, don't execute
"""

import subprocess
import sys
import os
import re
import time
import json
import shutil
import signal
import argparse
import datetime
import textwrap
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


# ============================================================
# CONFIGURATION
# ============================================================

REPO_DIR = Path(__file__).parent.resolve()
RESULTS_FILE = REPO_DIR / "results.tsv"
TRAIN_SCRIPT = REPO_DIR / "train.py"
LOG_FILE = REPO_DIR / "run.log"
REPORTS_DIR = REPO_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# TSV header
TSV_HEADER = "commit\tpolicy\ttask\tsuccess_rate\tavg_reward\tvram_gb\ttraining_min\tsteps\tstatus\tdescription"

# Maximum retries per experiment on crash
MAX_CRASH_RETRIES = 2

# Phase 2: stop optimizing after this many consecutive discards
MAX_CONSECUTIVE_DISCARDS = 5


# ============================================================
# BENCHMARK DEFINITIONS
# ============================================================

@dataclass
class TaskConfig:
    env_type: str
    env_task: str
    dataset: str
    tier: int
    time_budget: int  # seconds
    steps: int
    batch_size: int = 64
    eval_freq: int = 10_000
    eval_n_episodes: int = 50
    save_freq: int = 10_000


TASKS = {
    "PushT-v0": TaskConfig(
        env_type="pusht", env_task="PushT-v0",
        dataset="lerobot/pusht", tier=1,
        time_budget=1800, steps=50_000,
    ),
    "AlohaTransferCube-v0": TaskConfig(
        env_type="aloha", env_task="AlohaTransferCube-v0",
        dataset="lerobot/aloha_sim_transfer_cube_human", tier=2,
        time_budget=3600, steps=100_000,
    ),
    "AlohaInsertion-v0": TaskConfig(
        env_type="aloha", env_task="AlohaInsertion-v0",
        dataset="lerobot/aloha_sim_insertion_human", tier=2,
        time_budget=3600, steps=100_000,
    ),
}

# Core policies to benchmark
CORE_POLICIES = ["diffusion", "act", "vqbet"]

# Baseline experiments: (policy, task_id) in priority order
BASELINE_EXPERIMENTS = [
    ("diffusion", "PushT-v0"),
    ("act", "PushT-v0"),
    ("vqbet", "PushT-v0"),
    ("diffusion", "AlohaTransferCube-v0"),
    ("act", "AlohaTransferCube-v0"),
    ("vqbet", "AlohaTransferCube-v0"),
    ("diffusion", "AlohaInsertion-v0"),
    ("act", "AlohaInsertion-v0"),
    ("vqbet", "AlohaInsertion-v0"),
]


# ============================================================
# PHASE 2: OPTIMIZATION SEARCH SPACE
# ============================================================

# Hyperparameter variations to try for each policy
# Each entry is: (description, policy_overrides, optimizer_overrides)
OPTIMIZATION_SWEEPS = {
    "diffusion": [
        # Learning rate
        ("lr=5e-5", {}, {"lr": 5e-5}),
        ("lr=5e-4", {}, {"lr": 5e-4}),
        ("lr=1e-3", {}, {"lr": 1e-3}),
        # Batch size
        ("batch_size=32", {}, {}),   # handled specially
        ("batch_size=128", {}, {}),   # handled specially
        # Observation steps
        ("n_obs_steps=1", {"n_obs_steps": 1}, {}),
        ("n_obs_steps=4", {"n_obs_steps": 4}, {}),
        # Action horizon
        ("horizon=8", {"horizon": 8, "n_action_steps": 4}, {}),
        ("horizon=32", {"horizon": 32, "n_action_steps": 16}, {}),
        # Architecture
        ("smaller_unet down_dims=[256,512]", {"down_dims": "[256,512]"}, {}),
        ("larger_unet down_dims=[512,1024,2048]", {"down_dims": "[512,1024,2048]"}, {}),
        # Diffusion steps
        ("num_train_timesteps=50", {"num_train_timesteps": 50}, {}),
        ("num_train_timesteps=200", {"num_train_timesteps": 200}, {}),
        # Vision backbone
        ("resnet50 backbone", {"vision_backbone": "resnet50"}, {}),
        # FiLM conditioning
        ("no FiLM", {"use_film_scale_modulation": False}, {}),
        # Prediction type
        ("predict sample (not epsilon)", {"prediction_type": "sample"}, {}),
    ],
    "act": [
        # Learning rate
        ("lr=1e-4", {}, {"lr": 1e-4}),
        ("lr=5e-6", {}, {"lr": 5e-6}),
        ("lr=1e-3", {}, {"lr": 1e-3}),
        # Chunk size
        ("chunk_size=50", {"chunk_size": 50, "n_action_steps": 50}, {}),
        ("chunk_size=20", {"chunk_size": 20, "n_action_steps": 20}, {}),
        # Architecture
        ("dim_model=256", {"dim_model": 256}, {}),
        ("dim_model=768", {"dim_model": 768}, {}),
        ("deeper encoder n_encoder_layers=6", {"n_encoder_layers": 6}, {}),
        ("fewer decoder n_decoder_layers=4", {"n_decoder_layers": 4}, {}),
        # VAE
        ("no VAE", {"use_vae": False}, {}),
        ("larger latent latent_dim=64", {"latent_dim": 64}, {}),
        # Batch size
        ("batch_size=32", {}, {}),
        ("batch_size=128", {}, {}),
    ],
    "vqbet": [
        # Learning rate
        ("lr=5e-5", {}, {"lr": 5e-5}),
        ("lr=5e-4", {}, {"lr": 5e-4}),
        # Codebook
        ("vqvae_n_embed=256", {"vqvae_n_embed": 256}, {}),
        ("vqvae_n_embed=1024", {"vqvae_n_embed": 1024}, {}),
        # GPT depth
        ("gpt_n_layer=4", {"gpt_n_layer": 4}, {}),
        ("gpt_n_layer=8", {"gpt_n_layer": 8}, {}),
        # Action chunk
        ("action_chunk_size=8", {"action_chunk_size": 8}, {}),
        ("action_chunk_size=32", {"action_chunk_size": 32}, {}),
        # Batch size
        ("batch_size=32", {}, {}),
        ("batch_size=128", {}, {}),
    ],
}


# ============================================================
# PHASE 3: ABLATION DEFINITIONS
# ============================================================

# Data efficiency: fraction of episodes to use
DATA_FRACTIONS = [0.1, 0.25, 0.5, 1.0]

# Seed sensitivity
SEEDS = [1000, 2000, 3000, 4000, 5000]

# Action horizon sweep
HORIZONS = [4, 8, 16, 32]


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def log(msg, level="INFO"):
    """Print timestamped log message."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def init_results_file():
    """Create results.tsv with header if it doesn't exist."""
    if not RESULTS_FILE.exists():
        with open(RESULTS_FILE, "w") as f:
            f.write(TSV_HEADER + "\n")
        log(f"Created {RESULTS_FILE}")


def append_result(commit, policy, task, success_rate, avg_reward,
                  vram_gb, training_min, steps, status, description):
    """Append one row to results.tsv."""
    row = f"{commit}\t{policy}\t{task}\t{success_rate:.2f}\t{avg_reward:.3f}\t{vram_gb:.1f}\t{training_min:.1f}\t{steps}\t{status}\t{description}"
    with open(RESULTS_FILE, "a") as f:
        f.write(row + "\n")
    log(f"Recorded: {status} | {policy}/{task} | success={success_rate:.1f}% | {description}")


def load_results():
    """Load results.tsv as a list of dicts."""
    if not RESULTS_FILE.exists():
        return []
    results = []
    with open(RESULTS_FILE, "r") as f:
        header = f.readline().strip().split("\t")
        for line in f:
            vals = line.strip().split("\t")
            if len(vals) == len(header):
                row = dict(zip(header, vals))
                row["success_rate"] = float(row["success_rate"])
                row["avg_reward"] = float(row["avg_reward"])
                row["vram_gb"] = float(row["vram_gb"])
                row["training_min"] = float(row["training_min"])
                row["steps"] = int(row["steps"])
                results.append(row)
    return results


def get_best_result(policy, task):
    """Get the best success_rate for a (policy, task) pair from results."""
    results = load_results()
    best = 0.0
    for r in results:
        if r["policy"] == policy and r["task"] == task and r["status"] in ("baseline", "keep"):
            best = max(best, r["success_rate"])
    return best


def has_baseline(policy, task):
    """Check if baseline exists for (policy, task)."""
    results = load_results()
    return any(
        r["policy"] == policy and r["task"] == task and r["status"] == "baseline"
        for r in results
    )


def git_commit(message):
    """Create a git commit with the given message. Returns short hash."""
    subprocess.run(["git", "add", "train.py"], cwd=REPO_DIR, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=REPO_DIR, check=True,
                   capture_output=True)
    result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_DIR,
                           capture_output=True, text=True, check=True)
    return result.stdout.strip()


def git_reset_last():
    """Revert the last commit (discard experiment)."""
    subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=REPO_DIR, check=True,
                   capture_output=True)
    log("Reverted last commit (experiment discarded)")


def _fix_last_result_status(new_status):
    """Update the status of the last row in results.tsv."""
    if not RESULTS_FILE.exists():
        return
    lines = RESULTS_FILE.read_text().strip().split("\n")
    if len(lines) < 2:
        return
    parts = lines[-1].split("\t")
    if len(parts) >= 9:
        parts[8] = new_status  # status column
        lines[-1] = "\t".join(parts)
        RESULTS_FILE.write_text("\n".join(lines) + "\n")


def get_gpu_vram_gb():
    """Get current GPU memory usage in GB."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            values = [int(x.strip()) for x in result.stdout.strip().split("\n") if x.strip()]
            return max(values) / 1024 if values else 0.0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return 0.0


# ============================================================
# TRAIN.PY MODIFICATION
# ============================================================

def write_train_config(policy, task_id, policy_overrides=None,
                       optimizer_overrides=None, batch_size=None,
                       seed=1000, extra_args=None):
    """
    Rewrite the CONFIGURATION section of train.py.
    """
    task = TASKS[task_id]
    bs = batch_size or task.batch_size

    task_id_safe = task_id.replace("-", "_").lower()
    run_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    policy_ovr_str = repr(policy_overrides or {})
    optim_ovr_str = repr(optimizer_overrides or {})
    extra_str = repr(extra_args or [])

    config_section = f'''# ============================================================
# CONFIGURATION — The AI agent modifies this section
# ============================================================

# ---- Policy ----
POLICY_TYPE = "{policy}"

# ---- Task ----
DATASET_REPO_ID = "{task.dataset}"
ENV_TYPE = "{task.env_type}"
ENV_TASK = "{task.env_task}"

# ---- Training ----
TRAINING_STEPS = {task.steps}
BATCH_SIZE = {bs}
SEED = {seed}

# ---- Evaluation ----
EVAL_FREQ = {task.eval_freq}
EVAL_N_EPISODES = {task.eval_n_episodes}
SAVE_FREQ = {task.save_freq}

# ---- Time Budget (seconds) ----
TIME_BUDGET = {task.time_budget}

# ---- Output ----
OUTPUT_DIR = "outputs/{policy}_{task_id_safe}_{run_ts}"

# ---- Policy-Specific Overrides ----
POLICY_OVERRIDES = {policy_ovr_str}

# ---- Optimizer Overrides ----
OPTIMIZER_OVERRIDES = {optim_ovr_str}

# ---- Scheduler Overrides ----
SCHEDULER_OVERRIDES = {{}}

# ---- Extra CLI Arguments ----
EXTRA_ARGS = {extra_str}
'''

    # Read the full train.py
    with open(TRAIN_SCRIPT, "r") as f:
        content = f.read()

    # Replace the configuration section
    pattern = r'# ={60,}\n# CONFIGURATION.*?# ={60,}\n# INFRASTRUCTURE'
    replacement = config_section + '\n# ============================================================\n# INFRASTRUCTURE'

    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    with open(TRAIN_SCRIPT, "w") as f:
        f.write(new_content)


# ============================================================
# EXPERIMENT RUNNER
# ============================================================

def run_experiment(policy, task_id, description, status_type,
                   policy_overrides=None, optimizer_overrides=None,
                   batch_size=None, seed=1000, extra_args=None,
                   dry_run=False):
    """
    Run a single experiment:
    1. Write config to train.py
    2. Git commit
    3. Run training
    4. Extract metrics
    5. Record results
    6. Return (success_rate, commit_hash)
    """
    task = TASKS[task_id]
    log(f"{'[DRY RUN] ' if dry_run else ''}Starting: {policy}/{task_id} — {description}")

    # Step 1: Write config
    write_train_config(
        policy=policy,
        task_id=task_id,
        policy_overrides=policy_overrides,
        optimizer_overrides=optimizer_overrides,
        batch_size=batch_size,
        seed=seed,
        extra_args=extra_args,
    )

    if dry_run:
        log(f"[DRY RUN] Would train {policy} on {task_id} for {task.steps} steps")
        return 0.0, "dry_run"

    # Step 2: Git commit
    commit_msg = f"{status_type}: {policy}/{task_id} — {description}"
    try:
        commit_hash = git_commit(commit_msg)
    except subprocess.CalledProcessError:
        # Nothing to commit (no changes)
        result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_DIR,
                               capture_output=True, text=True)
        commit_hash = result.stdout.strip()

    # Step 3: Run training
    log(f"Training {policy} on {task_id} ({task.steps} steps, budget={task.time_budget}s)...")
    start_time = time.time()
    timeout = task.time_budget * 2 + 300  # 2x budget + 5 min grace

    # Set up environment with MUJOCO_GL for headless rendering
    env = os.environ.copy()
    env["MUJOCO_GL"] = "egl"
    env["WANDB_MODE"] = "disabled"

    # IMPORTANT: Do NOT redirect train.py stdout to run.log here.
    # train.py internally redirects the lerobot subprocess to run.log.
    # If we also redirect here, both processes fight over the same file.
    # Instead, capture train.py's stdout separately.
    wrapper_log = REPO_DIR / "wrapper.log"

    try:
        with open(wrapper_log, "w") as wlog:
            proc = subprocess.Popen(
                [sys.executable, str(TRAIN_SCRIPT)],
                stdout=wlog,
                stderr=subprocess.STDOUT,
                cwd=REPO_DIR,
                env=env,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
            )
            proc.wait(timeout=timeout)

    except subprocess.TimeoutExpired:
        if hasattr(os, "killpg"):
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                time.sleep(5)
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        else:
            proc.kill()
        log(f"TIMEOUT after {timeout}s", "ERROR")
        elapsed = time.time() - start_time
        append_result(commit_hash, policy, task_id, 0.0, 0.0, 0.0,
                      elapsed / 60, 0, "crash", f"timeout — {description}")
        return 0.0, commit_hash

    elapsed = time.time() - start_time

    # Step 4: Extract metrics
    metrics = {
        "success_rate": 0.0,
        "avg_reward": 0.0,
        "peak_vram_mb": 0.0,
        "steps_completed": 0,
    }

    # Read both log files: run.log (lerobot output) and wrapper.log (train.py output)
    combined_log = ""
    if LOG_FILE.exists():
        combined_log += LOG_FILE.read_text()
    if wrapper_log.exists():
        combined_log += "\n" + wrapper_log.read_text()

    if combined_log:
        log_text = combined_log

        # Success rate (check train.py format first, then lerobot format)
        # LeRobot format: 'pc_success': 0.0
        matches = re.findall(r"success_rate:\s+([0-9.]+)", log_text)
        if not matches:
            matches = re.findall(r"'?pc_success'?[:\s]+([0-9.]+)", log_text)
        if matches:
            metrics["success_rate"] = float(matches[-1])

        # Avg reward
        matches = re.findall(r"avg_reward:\s+([0-9.]+)", log_text)
        if not matches:
            matches = re.findall(r"'?avg_sum_reward'?[:\s]+([0-9.]+)", log_text)
        if matches:
            metrics["avg_reward"] = float(matches[-1])

        # VRAM
        matches = re.findall(r"peak_vram_mb:\s+([0-9.]+)", log_text)
        if matches:
            metrics["peak_vram_mb"] = float(matches[-1])

        # Steps
        matches = re.findall(r"steps_completed:\s+(\d+)", log_text)
        if not matches:
            matches = re.findall(r"step[:\s]+(\d+)", log_text)
        if matches:
            metrics["steps_completed"] = int(matches[-1])

    # Fallback VRAM from nvidia-smi
    if metrics["peak_vram_mb"] == 0:
        metrics["peak_vram_mb"] = get_gpu_vram_gb() * 1024

    vram_gb = metrics["peak_vram_mb"] / 1024

    # Check if training crashed (no success rate)
    if metrics["success_rate"] == 0.0 and metrics["steps_completed"] == 0:
        log(f"CRASH: No metrics found. Check run.log and wrapper.log", "ERROR")
        # Print last 30 lines of both logs for debugging
        for lf in [LOG_FILE, wrapper_log]:
            if lf.exists() and lf.read_text().strip():
                lines = lf.read_text().strip().split("\n")
                log(f"Last 20 lines of {lf.name}:")
                for line in lines[-20:]:
                    print(f"  | {line}")

        append_result(commit_hash, policy, task_id, 0.0, 0.0, 0.0,
                      elapsed / 60, 0, "crash", description)
        return 0.0, commit_hash

    # Step 5: Record results
    append_result(
        commit_hash, policy, task_id,
        metrics["success_rate"], metrics["avg_reward"],
        vram_gb, elapsed / 60,
        metrics["steps_completed"], status_type, description,
    )

    log(f"Finished: success_rate={metrics['success_rate']:.1f}% | "
        f"time={elapsed/60:.1f}min | vram={vram_gb:.1f}GB")

    return metrics["success_rate"], commit_hash


# ============================================================
# PHASE 1: BASELINE SWEEP
# ============================================================

def run_phase1(dry_run=False):
    """Run all baseline experiments."""
    log("=" * 60)
    log("PHASE 1: BASELINE SWEEP")
    log("=" * 60)

    completed = 0
    total = len(BASELINE_EXPERIMENTS)

    for policy, task_id in BASELINE_EXPERIMENTS:
        if has_baseline(policy, task_id):
            log(f"Skipping {policy}/{task_id} — baseline already exists")
            completed += 1
            continue

        log(f"Baseline [{completed+1}/{total}]: {policy} on {task_id}")

        success_rate, commit = run_experiment(
            policy=policy,
            task_id=task_id,
            description=f"default {policy} on {task_id}",
            status_type="baseline",
            dry_run=dry_run,
        )

        completed += 1
        log(f"Progress: {completed}/{total} baselines complete")

    # Generate baseline report
    if not dry_run:
        generate_baseline_report()

    log("Phase 1 complete!")
    return True


def generate_baseline_report():
    """Generate reports/01_baselines.md from results."""
    results = load_results()
    baselines = [r for r in results if r["status"] == "baseline"]

    if not baselines:
        return

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Phase 1: Baseline Results\n",
        f"*Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
        "## Results Table\n",
        "| Policy | Task | Success Rate (%) | Avg Reward | VRAM (GB) | Training (min) | Steps |",
        "|--------|------|-----------------|------------|-----------|----------------|-------|",
    ]

    for r in baselines:
        lines.append(
            f"| {r['policy']} | {r['task']} | {r['success_rate']:.1f} | "
            f"{r['avg_reward']:.3f} | {r['vram_gb']:.1f} | "
            f"{r['training_min']:.1f} | {r['steps']} |"
        )

    # Per-task ranking
    tasks = list(set(r["task"] for r in baselines))
    lines.append("\n## Rankings by Task\n")
    for task in sorted(tasks):
        task_results = sorted(
            [r for r in baselines if r["task"] == task],
            key=lambda r: r["success_rate"],
            reverse=True,
        )
        lines.append(f"### {task}\n")
        for i, r in enumerate(task_results, 1):
            lines.append(f"{i}. **{r['policy']}** — {r['success_rate']:.1f}%")
        lines.append("")

    report_path = REPORTS_DIR / "01_baselines.md"
    report_path.write_text("\n".join(lines))
    log(f"Generated baseline report: {report_path}")


# ============================================================
# PHASE 2: OPTIMIZATION LOOP
# ============================================================

def run_phase2(dry_run=False):
    """Run optimization loop for each (policy, task) pair."""
    log("=" * 60)
    log("PHASE 2: OPTIMIZATION LOOP")
    log("=" * 60)

    for policy, task_id in BASELINE_EXPERIMENTS:
        if not has_baseline(policy, task_id):
            log(f"Skipping {policy}/{task_id} — no baseline yet")
            continue

        optimize_pair(policy, task_id, dry_run=dry_run)

    # Generate optimization report
    if not dry_run:
        generate_optimization_report()

    log("Phase 2 complete!")
    return True


def optimize_pair(policy, task_id, dry_run=False):
    """Run optimization loop for one (policy, task) pair."""
    log(f"\nOptimizing: {policy} on {task_id}")
    log("-" * 40)

    current_best = get_best_result(policy, task_id)
    log(f"Current best: {current_best:.1f}%")

    sweeps = OPTIMIZATION_SWEEPS.get(policy, [])
    consecutive_discards = 0

    # Check which experiments have already been tried
    results = load_results()
    tried_descriptions = set(
        r["description"] for r in results
        if r["policy"] == policy and r["task"] == task_id
    )

    for desc, policy_ovr, optim_ovr in sweeps:
        if consecutive_discards >= MAX_CONSECUTIVE_DISCARDS:
            log(f"Converged: {MAX_CONSECUTIVE_DISCARDS} consecutive discards. Moving on.")
            break

        full_desc = f"{desc}"
        if full_desc in tried_descriptions:
            log(f"Skipping (already tried): {full_desc}")
            continue

        # Handle batch_size overrides
        batch_size = None
        if "batch_size=" in desc:
            bs_match = re.search(r"batch_size=(\d+)", desc)
            if bs_match:
                batch_size = int(bs_match.group(1))

        # For Phase 2, we determine keep/discard AFTER the run
        success_rate, commit = run_experiment(
            policy=policy,
            task_id=task_id,
            description=full_desc,
            status_type="keep",  # Tentatively "keep" — we'll fix if discarding
            policy_overrides=policy_ovr if policy_ovr else None,
            optimizer_overrides=optim_ovr if optim_ovr else None,
            batch_size=batch_size,
            dry_run=dry_run,
        )

        if dry_run:
            continue

        if success_rate > current_best:
            log(f"IMPROVEMENT: {current_best:.1f}% -> {success_rate:.1f}% (+{success_rate - current_best:.1f}%)")
            current_best = success_rate
            consecutive_discards = 0
            # Status was already recorded as "keep" — correct
        else:
            log(f"No improvement: {success_rate:.1f}% vs best {current_best:.1f}%")
            consecutive_discards += 1
            # Revert the commit
            if commit != "dry_run":
                git_reset_last()
            # Fix status from "keep" to "discard" in results.tsv
            _fix_last_result_status("discard")

    log(f"Optimization complete for {policy}/{task_id}. Best: {current_best:.1f}%")


def generate_optimization_report():
    """Generate reports/02_optimization.md."""
    results = load_results()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Phase 2: Optimization Results\n",
        f"*Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
        "## Best Configs Found\n",
        "| Policy | Task | Baseline | Best | Improvement | Best Config |",
        "|--------|------|----------|------|-------------|-------------|",
    ]

    for policy, task_id in BASELINE_EXPERIMENTS:
        baseline = [r for r in results if r["policy"] == policy and r["task"] == task_id and r["status"] == "baseline"]
        kept = [r for r in results if r["policy"] == policy and r["task"] == task_id and r["status"] in ("keep", "opt")]

        if not baseline:
            continue

        baseline_sr = baseline[0]["success_rate"]
        if kept:
            best = max(kept, key=lambda r: r["success_rate"])
            best_sr = best["success_rate"]
            best_desc = best["description"]
        else:
            best_sr = baseline_sr
            best_desc = "default (no improvement found)"

        improvement = best_sr - baseline_sr
        lines.append(
            f"| {policy} | {task_id} | {baseline_sr:.1f}% | {best_sr:.1f}% | "
            f"+{improvement:.1f}% | {best_desc} |"
        )

    # Experiment stats
    total = len(results)
    kept = len([r for r in results if r["status"] == "keep"])
    discarded = len([r for r in results if r["status"] == "discard"])
    crashed = len([r for r in results if r["status"] == "crash"])

    lines.extend([
        "\n## Experiment Statistics\n",
        f"- Total experiments: {total}",
        f"- Kept (improvements): {kept}",
        f"- Discarded: {discarded}",
        f"- Crashed: {crashed}",
        f"- Keep rate: {kept / max(1, total) * 100:.1f}%",
    ])

    report_path = REPORTS_DIR / "02_optimization.md"
    report_path.write_text("\n".join(lines))
    log(f"Generated optimization report: {report_path}")


# ============================================================
# PHASE 3: ABLATION STUDIES
# ============================================================

def run_phase3(dry_run=False):
    """Run ablation studies."""
    log("=" * 60)
    log("PHASE 3: ABLATION STUDIES")
    log("=" * 60)

    run_ablation_data_efficiency(dry_run)
    run_ablation_seed_sensitivity(dry_run)
    run_ablation_action_horizon(dry_run)

    if not dry_run:
        generate_ablation_report()

    log("Phase 3 complete!")
    return True


def run_ablation_data_efficiency(dry_run=False):
    """Study 1: Data efficiency — vary amount of training data."""
    log("\n--- Ablation: Data Efficiency ---")

    # Run on PushT with all core policies (fastest)
    for policy in CORE_POLICIES:
        if not has_baseline(policy, "PushT-v0"):
            continue

        total_episodes = 206  # PushT dataset size

        for fraction in DATA_FRACTIONS:
            n_episodes = max(1, int(total_episodes * fraction))
            desc = f"data_efficiency {int(fraction*100)}% ({n_episodes} episodes)"

            # Build episode list for subset training
            episode_indices = list(range(n_episodes))
            extra = [f"--dataset.episodes={json.dumps(episode_indices)}"] if fraction < 1.0 else []

            run_experiment(
                policy=policy,
                task_id="PushT-v0",
                description=desc,
                status_type="ablation",
                extra_args=extra if extra else None,
                dry_run=dry_run,
            )


def run_ablation_seed_sensitivity(dry_run=False):
    """Study 4: Seed sensitivity — run multiple seeds."""
    log("\n--- Ablation: Seed Sensitivity ---")

    # Run on PushT with all core policies
    for policy in CORE_POLICIES:
        if not has_baseline(policy, "PushT-v0"):
            continue

        for seed in SEEDS:
            if seed == 1000:
                continue  # Already have this from baseline

            desc = f"seed_sensitivity seed={seed}"

            run_experiment(
                policy=policy,
                task_id="PushT-v0",
                description=desc,
                status_type="ablation",
                seed=seed,
                dry_run=dry_run,
            )


def run_ablation_action_horizon(dry_run=False):
    """Study 3: Action horizon sweep."""
    log("\n--- Ablation: Action Horizon ---")

    # Only for diffusion and act on PushT
    for policy in ["diffusion", "act"]:
        if not has_baseline(policy, "PushT-v0"):
            continue

        for horizon in HORIZONS:
            n_action = max(1, horizon // 2)
            desc = f"horizon_sweep horizon={horizon} n_action_steps={n_action}"

            if policy == "diffusion":
                policy_ovr = {"horizon": horizon, "n_action_steps": n_action}
            elif policy == "act":
                policy_ovr = {"chunk_size": horizon, "n_action_steps": horizon}
            else:
                continue

            run_experiment(
                policy=policy,
                task_id="PushT-v0",
                description=desc,
                status_type="ablation",
                policy_overrides=policy_ovr,
                dry_run=dry_run,
            )


def generate_ablation_report():
    """Generate reports/03_ablations.md."""
    results = load_results()
    ablations = [r for r in results if r["status"] == "ablation"]

    if not ablations:
        return

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Phase 3: Ablation Study Results\n",
        f"*Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
        f"Total ablation experiments: {len(ablations)}\n",
    ]

    # Data efficiency
    data_eff = [r for r in ablations if "data_efficiency" in r["description"]]
    if data_eff:
        lines.extend([
            "## Study 1: Data Efficiency\n",
            "| Policy | Data Fraction | Success Rate (%) |",
            "|--------|--------------|-----------------|",
        ])
        for r in sorted(data_eff, key=lambda x: (x["policy"], x["description"])):
            lines.append(f"| {r['policy']} | {r['description']} | {r['success_rate']:.1f} |")
        lines.append("")

    # Seed sensitivity
    seed_exp = [r for r in ablations if "seed_sensitivity" in r["description"]]
    if seed_exp:
        lines.extend([
            "## Study 4: Seed Sensitivity\n",
            "| Policy | Seed | Success Rate (%) |",
            "|--------|------|-----------------|",
        ])
        for r in sorted(seed_exp, key=lambda x: (x["policy"], x["description"])):
            lines.append(f"| {r['policy']} | {r['description']} | {r['success_rate']:.1f} |")
        lines.append("")

    # Action horizon
    horizon_exp = [r for r in ablations if "horizon_sweep" in r["description"]]
    if horizon_exp:
        lines.extend([
            "## Study 3: Action Horizon\n",
            "| Policy | Config | Success Rate (%) |",
            "|--------|--------|-----------------|",
        ])
        for r in sorted(horizon_exp, key=lambda x: (x["policy"], x["description"])):
            lines.append(f"| {r['policy']} | {r['description']} | {r['success_rate']:.1f} |")
        lines.append("")

    report_path = REPORTS_DIR / "03_ablations.md"
    report_path.write_text("\n".join(lines))
    log(f"Generated ablation report: {report_path}")


# ============================================================
# PHASE 4: FINAL REPORT
# ============================================================

def run_phase4():
    """Generate the final comprehensive report."""
    log("=" * 60)
    log("PHASE 4: FINAL REPORT")
    log("=" * 60)

    results = load_results()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "# AutoResearch-MRL: Final Report\n",
        f"*Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*\n",
        "## Executive Summary\n",
    ]

    # Summary stats
    total = len(results)
    baselines = [r for r in results if r["status"] == "baseline"]
    kept = [r for r in results if r["status"] == "keep"]
    discarded = [r for r in results if r["status"] == "discard"]
    crashed = [r for r in results if r["status"] == "crash"]
    ablations = [r for r in results if r["status"] == "ablation"]

    total_time_hrs = sum(r["training_min"] for r in results) / 60

    lines.extend([
        f"- **Total experiments:** {total}",
        f"- **Baselines:** {len(baselines)}",
        f"- **Optimization kept:** {len(kept)}",
        f"- **Optimization discarded:** {len(discarded)}",
        f"- **Ablation experiments:** {len(ablations)}",
        f"- **Crashes:** {len(crashed)}",
        f"- **Total training time:** {total_time_hrs:.1f} hours",
        f"- **Keep rate (Phase 2):** {len(kept) / max(1, len(kept) + len(discarded)) * 100:.1f}%\n",
    ])

    # Best results per (policy, task)
    lines.extend([
        "## Best Results\n",
        "| Policy | Task | Best Success Rate (%) | Config |",
        "|--------|------|----------------------|--------|",
    ])

    for policy, task_id in BASELINE_EXPERIMENTS:
        pair_results = [r for r in results if r["policy"] == policy and r["task"] == task_id
                       and r["status"] in ("baseline", "keep")]
        if pair_results:
            best = max(pair_results, key=lambda r: r["success_rate"])
            lines.append(f"| {policy} | {task_id} | {best['success_rate']:.1f} | {best['description']} |")

    lines.extend([
        "\n## Recommendations\n",
        "*(Based on experimental results — see individual phase reports for details)*\n",
        "See also:",
        "- `reports/01_baselines.md` — Baseline comparison",
        "- `reports/02_optimization.md` — Optimization results",
        "- `reports/03_ablations.md` — Ablation studies",
    ])

    report_path = REPORTS_DIR / "final_report.md"
    report_path.write_text("\n".join(lines))
    log(f"Generated final report: {report_path}")


# ============================================================
# MAIN LOOP
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="AutoResearch-MRL Experiment Loop")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4],
                       help="Run only a specific phase")
    parser.add_argument("--resume", action="store_true",
                       help="Resume from where we left off (skip completed experiments)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Print what would be run without executing")
    args = parser.parse_args()

    log("=" * 60)
    log("AutoResearch-MRL: Autonomous Experiment Loop")
    log(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    # Initialize
    init_results_file()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Print GPU info
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            log(f"GPU: {result.stdout.strip()}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        log("WARNING: nvidia-smi not found. Are you on a GPU machine?", "WARN")

    start_time = time.time()

    try:
        if args.phase:
            # Run specific phase
            if args.phase == 1:
                run_phase1(dry_run=args.dry_run)
            elif args.phase == 2:
                run_phase2(dry_run=args.dry_run)
            elif args.phase == 3:
                run_phase3(dry_run=args.dry_run)
            elif args.phase == 4:
                run_phase4()
        else:
            # Run all phases sequentially
            run_phase1(dry_run=args.dry_run)
            run_phase2(dry_run=args.dry_run)
            run_phase3(dry_run=args.dry_run)
            run_phase4()

    except KeyboardInterrupt:
        log("\nInterrupted by user. Results saved to results.tsv.", "WARN")
    except Exception as e:
        log(f"Unexpected error: {e}", "ERROR")
        import traceback
        traceback.print_exc()

    elapsed_hrs = (time.time() - start_time) / 3600
    log(f"\nTotal runtime: {elapsed_hrs:.1f} hours")
    log(f"Results: {RESULTS_FILE}")
    log("Done.")


if __name__ == "__main__":
    main()

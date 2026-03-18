#!/usr/bin/env python3
"""
AutoResearch-MRL: Training Script
==================================
The AI agent modifies the CONFIGURATION section below.
Everything below the divider is infrastructure — do not modify.

Usage:
    python train.py              # Full training run
    python train.py --smoke-test # Quick 100-step verification
"""

import subprocess
import sys
import time
import re
import os
import signal
import argparse
from pathlib import Path

VENV_PYTHON = "/workspace/venv/bin/python"

# ============================================================
# CONFIGURATION — The AI agent modifies this section
# ============================================================

# ---- Policy ----
POLICY_TYPE = "diffusion"

# ---- Task ----
DATASET_REPO_ID = "lerobot/aloha_sim_transfer_cube_human"
ENV_TYPE = "aloha"
ENV_TASK = "AlohaTransferCube-v0"

# ---- Training ----
TRAINING_STEPS = 100000
BATCH_SIZE = 32
SEED = 1000

# ---- Evaluation ----
EVAL_FREQ = 10000
EVAL_N_EPISODES = 50
SAVE_FREQ = 10000

# ---- Time Budget (seconds) ----
TIME_BUDGET = 3600

# ---- Output ----
OUTPUT_DIR = "outputs/diffusion_alohatransfercube_v0_20260317_202434"

# ---- Policy-Specific Overrides ----
POLICY_OVERRIDES = {}

# ---- Optimizer Overrides ----
OPTIMIZER_OVERRIDES = {}

# ---- Scheduler Overrides ----
SCHEDULER_OVERRIDES = {}

# ---- Extra CLI Arguments ----
EXTRA_ARGS = []

# ============================================================
# INFRASTRUCTURE — Do not modify below this line
# ============================================================

def build_command(smoke_test=False):
    """Construct the lerobot-train CLI command from configuration."""
    steps = 100 if smoke_test else TRAINING_STEPS
    eval_freq = 50 if smoke_test else EVAL_FREQ
    eval_episodes = 5 if smoke_test else EVAL_N_EPISODES
    save_freq = steps if smoke_test else SAVE_FREQ
    output_dir = "outputs/smoke_test" if smoke_test else OUTPUT_DIR

    cmd = [
        VENV_PYTHON, "-m", "lerobot.scripts.lerobot_train",
        f"--policy.type={POLICY_TYPE}",
        f"--policy.repo_id=autoresearch-mrl/{POLICY_TYPE}_{ENV_TASK.lower().replace('-', '_')}",
        f"--policy.push_to_hub=false",
        f"--dataset.repo_id={DATASET_REPO_ID}",
        f"--env.type={ENV_TYPE}",
        f"--env.task={ENV_TASK}",
        f"--steps={steps}",
        f"--batch_size={BATCH_SIZE}",
        f"--eval_freq={eval_freq}",
        f"--eval.n_episodes={eval_episodes}",
        f"--eval.batch_size={eval_episodes}",
        f"--save_freq={save_freq}",
        f"--output_dir={output_dir}",
        f"--seed={SEED}",
    ]

    for k, v in POLICY_OVERRIDES.items():
        cmd.append(f"--policy.{k}={v}")
    for k, v in OPTIMIZER_OVERRIDES.items():
        cmd.append(f"--optimizer.{k}={v}")
    for k, v in SCHEDULER_OVERRIDES.items():
        cmd.append(f"--scheduler.{k}={v}")

    cmd.extend(EXTRA_ARGS)
    return cmd


def extract_metrics(log_path):
    """Extract metrics from the training log file."""
    metrics = {
        "success_rate": None,
        "avg_reward": None,
        "final_loss": None,
        "peak_vram_mb": None,
        "steps_completed": 0,
        "inference_fps": None,
    }

    if not os.path.exists(log_path):
        return metrics

    with open(log_path, "r") as f:
        log_text = f.read()

    # Extract last evaluation success rate (pc_success)
    # Format in LeRobot logs: 'pc_success': 0.0  or  pc_success: 0.0
    success_matches = re.findall(r"'?pc_success'?[:\s]+([0-9.]+)", log_text)
    if success_matches:
        metrics["success_rate"] = float(success_matches[-1])

    # Extract last avg_sum_reward
    # Format: 'avg_sum_reward': 4.924  or  avg_sum_reward: 4.924
    reward_matches = re.findall(r"'?avg_sum_reward'?[:\s]+([0-9.]+)", log_text)
    if reward_matches:
        metrics["avg_reward"] = float(reward_matches[-1])

    # Extract final loss
    loss_matches = re.findall(r"loss[:\s]+([0-9.]+)", log_text)
    if loss_matches:
        metrics["final_loss"] = float(loss_matches[-1])

    # Extract step count — look for tqdm "Training: 100%|...| 100/100"
    # or LeRobot INFO logs
    step_matches = re.findall(r"Training:.*\|\s*(\d+)/\d+", log_text)
    if step_matches:
        metrics["steps_completed"] = int(step_matches[-1])
    else:
        step_matches = re.findall(r"step[:\s]+(\d+)", log_text)
        if step_matches:
            metrics["steps_completed"] = int(step_matches[-1])

    # Extract peak VRAM if reported
    vram_matches = re.findall(r"peak_vram_mb[:\s]+([0-9.]+)", log_text)
    if vram_matches:
        metrics["peak_vram_mb"] = float(vram_matches[-1])

    return metrics


def get_gpu_memory():
    """Get peak GPU memory usage via nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            # Return max across all GPUs in MB
            values = [int(x.strip()) for x in result.stdout.strip().split("\n") if x.strip()]
            return max(values) if values else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def run_training(smoke_test=False):
    """Run the training and report results."""
    cmd = build_command(smoke_test=smoke_test)
    budget = 300 if smoke_test else TIME_BUDGET
    timeout = budget + 300  # Grace period for startup/compilation/eval

    # Print experiment header
    print("=" * 60)
    print("AutoResearch-MRL Training")
    print("=" * 60)
    print(f"Policy:      {POLICY_TYPE}")
    print(f"Task:        {ENV_TASK}")
    print(f"Dataset:     {DATASET_REPO_ID}")
    print(f"Steps:       {100 if smoke_test else TRAINING_STEPS}")
    print(f"Batch Size:  {BATCH_SIZE}")
    print(f"Time Budget: {budget}s")
    print(f"Seed:        {SEED}")
    if POLICY_OVERRIDES:
        print(f"Policy Overrides: {POLICY_OVERRIDES}")
    if OPTIMIZER_OVERRIDES:
        print(f"Optimizer Overrides: {OPTIMIZER_OVERRIDES}")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)

    log_path = "run.log"
    start_time = time.time()
    peak_vram = None

    with open(log_path, "w") as log_file:
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Kill the process group
            if hasattr(os, "killpg"):
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                time.sleep(5)
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                proc.kill()
            print(f"\nTIMEOUT: Training exceeded {timeout}s. Killed.")

    elapsed = time.time() - start_time

    # Get GPU memory
    peak_vram = get_gpu_memory()

    # Extract metrics from log
    metrics = extract_metrics(log_path)

    # Override with GPU memory if we got it
    if peak_vram is not None:
        metrics["peak_vram_mb"] = peak_vram

    # Print results in standardized format
    print()
    print("---")
    print(f"policy:           {POLICY_TYPE}")
    print(f"task:             {ENV_TASK}")
    print(f"success_rate:     {metrics['success_rate']:.2f}" if metrics["success_rate"] is not None else "success_rate:     N/A")
    print(f"avg_reward:       {metrics['avg_reward']:.3f}" if metrics["avg_reward"] is not None else "avg_reward:       N/A")
    print(f"final_loss:       {metrics['final_loss']:.4f}" if metrics["final_loss"] is not None else "final_loss:       N/A")
    print(f"training_sec:     {elapsed:.1f}")
    print(f"peak_vram_mb:     {metrics['peak_vram_mb']:.1f}" if metrics["peak_vram_mb"] is not None else "peak_vram_mb:     N/A")
    print(f"steps_completed:  {metrics['steps_completed']}")
    print(f"inference_fps:    {metrics['inference_fps']:.1f}" if metrics["inference_fps"] is not None else "inference_fps:    N/A")
    print(f"seed:             {SEED}")
    print("---")

    return metrics, elapsed


def main():
    parser = argparse.ArgumentParser(description="AutoResearch-MRL Training")
    parser.add_argument("--smoke-test", action="store_true", help="Quick 100-step verification run")
    args = parser.parse_args()

    metrics, elapsed = run_training(smoke_test=args.smoke_test)

    # Exit with error code if training crashed (no success_rate extracted)
    if metrics["success_rate"] is None:
        print("\nWARNING: No success_rate found in log. Training may have crashed.")
        print("Check run.log for details: tail -n 50 run.log")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
AutoResearch-MRL: Evaluation Script (READ-ONLY)
================================================
Standardized evaluation harness for trained policies.
The AI agent MUST NOT modify this file.

Usage:
    python evaluate.py --checkpoint outputs/current/checkpoints/050000/pretrained_model \
                       --env-type pusht --env-task PushT-v0 --n-episodes 50

    python evaluate.py --checkpoint outputs/current/checkpoints/latest/pretrained_model \
                       --env-type aloha --env-task AlohaTransferCube-v0

    python evaluate.py --list-tasks   # Show all available tasks
"""

import subprocess
import sys
import re
import os
import json
import time
import argparse
from pathlib import Path


# ============================================================
# TASK REGISTRY — All supported tasks and their configurations
# ============================================================

TASKS = {
    "PushT-v0": {
        "env_type": "pusht",
        "dataset": "lerobot/pusht",
        "tier": 1,
        "default_episodes": 50,
    },
    "AlohaTransferCube-v0": {
        "env_type": "aloha",
        "dataset": "lerobot/aloha_sim_transfer_cube_human",
        "tier": 2,
        "default_episodes": 50,
    },
    "AlohaInsertion-v0": {
        "env_type": "aloha",
        "dataset": "lerobot/aloha_sim_insertion_human",
        "tier": 2,
        "default_episodes": 50,
    },
    "libero_spatial": {
        "env_type": "libero",
        "dataset": "lerobot/libero_spatial",
        "tier": 3,
        "default_episodes": 50,
    },
    "libero_object": {
        "env_type": "libero",
        "dataset": "lerobot/libero_object",
        "tier": 3,
        "default_episodes": 50,
    },
    "libero_goal": {
        "env_type": "libero",
        "dataset": "lerobot/libero_goal",
        "tier": 3,
        "default_episodes": 50,
    },
}


def evaluate_checkpoint(checkpoint_path, env_type, env_task, n_episodes=50, save_videos=False):
    """
    Evaluate a trained policy checkpoint using lerobot-eval.

    Returns:
        dict with keys: success_rate, avg_reward, inference_fps
    """
    cmd = [
        sys.executable, "-m", "lerobot.scripts.lerobot_eval",
        f"--policy.path={checkpoint_path}",
        f"--env.type={env_type}",
        f"--env.task={env_task}",
        f"--eval.n_episodes={n_episodes}",
        f"--eval.batch_size={min(n_episodes, 50)}",
    ]

    if save_videos:
        video_dir = f"eval_videos/{Path(checkpoint_path).parent.name}_{env_task}"
        cmd.append(f"--output_dir={video_dir}")

    print(f"Evaluating: {checkpoint_path}")
    print(f"Task: {env_task} ({n_episodes} episodes)")
    print(f"Command: {' '.join(cmd)}")

    log_path = "eval.log"
    start_time = time.time()

    with open(log_path, "w") as log_file:
        result = subprocess.run(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            timeout=600,  # 10 minute timeout for evaluation
        )

    elapsed = time.time() - start_time

    # Parse evaluation results
    metrics = {
        "success_rate": 0.0,
        "avg_reward": 0.0,
        "inference_fps": 0.0,
        "eval_time_sec": elapsed,
    }

    with open(log_path, "r") as f:
        log_text = f.read()

    # Extract success rate
    success_matches = re.findall(r"pc_success[:\s]+([0-9.]+)", log_text)
    if success_matches:
        metrics["success_rate"] = float(success_matches[-1])

    # Extract average reward
    reward_matches = re.findall(r"avg_sum_reward[:\s]+([0-9.]+)", log_text)
    if reward_matches:
        metrics["avg_reward"] = float(reward_matches[-1])

    # Estimate inference FPS from eval time
    if elapsed > 0 and n_episodes > 0:
        metrics["inference_fps"] = n_episodes / elapsed

    # Print standardized results
    print()
    print("--- EVALUATION RESULTS ---")
    print(f"checkpoint:    {checkpoint_path}")
    print(f"task:          {env_task}")
    print(f"n_episodes:    {n_episodes}")
    print(f"success_rate:  {metrics['success_rate']:.2f}")
    print(f"avg_reward:    {metrics['avg_reward']:.3f}")
    print(f"eval_time_sec: {metrics['eval_time_sec']:.1f}")
    print(f"inference_fps: {metrics['inference_fps']:.1f}")
    print("-" * 30)

    return metrics


def find_best_checkpoint(output_dir):
    """Find the latest/best checkpoint in an output directory."""
    checkpoints_dir = Path(output_dir) / "checkpoints"

    if not checkpoints_dir.exists():
        return None

    # Check for 'latest' symlink
    latest = checkpoints_dir / "last" / "pretrained_model"
    if latest.exists():
        return str(latest)

    # Find highest-numbered checkpoint
    checkpoint_dirs = sorted(
        [d for d in checkpoints_dir.iterdir() if d.is_dir() and d.name.isdigit()],
        key=lambda d: int(d.name),
    )

    if checkpoint_dirs:
        pretrained = checkpoint_dirs[-1] / "pretrained_model"
        if pretrained.exists():
            return str(pretrained)

    return None


def list_tasks():
    """Print all available tasks."""
    print("Available tasks:")
    print("-" * 70)
    print(f"{'Task':<30} {'Env Type':<15} {'Tier':<6} {'Episodes':<10}")
    print("-" * 70)
    for task_id, info in TASKS.items():
        print(f"{task_id:<30} {info['env_type']:<15} {info['tier']:<6} {info['default_episodes']:<10}")
    print("-" * 70)


def main():
    parser = argparse.ArgumentParser(description="AutoResearch-MRL Evaluation")
    parser.add_argument("--checkpoint", type=str, help="Path to pretrained_model directory")
    parser.add_argument("--output-dir", type=str, help="Path to training output dir (auto-finds checkpoint)")
    parser.add_argument("--env-type", type=str, help="Environment type (pusht, aloha, libero)")
    parser.add_argument("--env-task", type=str, help="Task ID (PushT-v0, AlohaTransferCube-v0, etc.)")
    parser.add_argument("--n-episodes", type=int, default=50, help="Number of evaluation episodes")
    parser.add_argument("--save-videos", action="store_true", help="Save evaluation rollout videos")
    parser.add_argument("--list-tasks", action="store_true", help="List all available tasks")
    args = parser.parse_args()

    if args.list_tasks:
        list_tasks()
        return

    # Resolve checkpoint path
    checkpoint = args.checkpoint
    if checkpoint is None and args.output_dir:
        checkpoint = find_best_checkpoint(args.output_dir)
        if checkpoint is None:
            print(f"ERROR: No checkpoint found in {args.output_dir}")
            sys.exit(1)
        print(f"Found checkpoint: {checkpoint}")

    if checkpoint is None:
        print("ERROR: Provide --checkpoint or --output-dir")
        sys.exit(1)

    # Resolve env config
    env_type = args.env_type
    env_task = args.env_task

    if env_task and env_task in TASKS and env_type is None:
        env_type = TASKS[env_task]["env_type"]

    if env_type is None or env_task is None:
        print("ERROR: Provide --env-type and --env-task (or use --list-tasks to see options)")
        sys.exit(1)

    metrics = evaluate_checkpoint(
        checkpoint_path=checkpoint,
        env_type=env_type,
        env_task=env_task,
        n_episodes=args.n_episodes,
        save_videos=args.save_videos,
    )

    sys.exit(0 if metrics["success_rate"] > 0 else 1)


if __name__ == "__main__":
    main()

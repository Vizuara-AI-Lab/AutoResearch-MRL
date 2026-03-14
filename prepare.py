#!/usr/bin/env python3
"""
AutoResearch-MRL: Environment Preparation (READ-ONLY)
=====================================================
Setup and verification script for datasets, environments, and dependencies.
The AI agent MUST NOT modify this file.

Usage:
    python prepare.py --check      # Verify all dependencies
    python prepare.py --download   # Download all datasets
    python prepare.py --check-task PushT-v0  # Check specific task
"""

import subprocess
import sys
import os
import importlib
import argparse
from pathlib import Path


# ============================================================
# CONSTANTS — Do not modify
# ============================================================

REQUIRED_PACKAGES = [
    "torch",
    "lerobot",
    "gymnasium",
    "numpy",
    "pandas",
    "matplotlib",
]

DATASETS = {
    "lerobot/pusht": {"task": "PushT-v0", "tier": 1},
    "lerobot/aloha_sim_transfer_cube_human": {"task": "AlohaTransferCube-v0", "tier": 2},
    "lerobot/aloha_sim_insertion_human": {"task": "AlohaInsertion-v0", "tier": 2},
}

ENVIRONMENTS = {
    "pusht": {
        "package": "gym_pusht",
        "env_id": "gym_pusht/PushT-v0",
        "install_hint": "pip install gym-pusht",
    },
    "aloha": {
        "package": "gym_aloha",
        "env_id": "gym_aloha/AlohaTransferCube-v0",
        "install_hint": "pip install gym-aloha",
    },
    "libero": {
        "package": "libero",
        "env_id": None,  # LIBERO uses its own env creation
        "install_hint": "pip install libero",
    },
}

POLICIES = ["diffusion", "act", "vqbet", "tdmpc"]


# ============================================================
# CHECK FUNCTIONS
# ============================================================

def check_python():
    """Check Python version."""
    version = sys.version_info
    ok = version >= (3, 10)
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] Python {version.major}.{version.minor}.{version.micro} (need >= 3.10)")
    return ok


def check_cuda():
    """Check CUDA availability."""
    try:
        import torch
        available = torch.cuda.is_available()
        if available:
            device_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_mem / 1e9
            print(f"  [OK] CUDA available: {device_name} ({vram_gb:.1f} GB)")
        else:
            print("  [WARN] CUDA not available — training will be slow on CPU")
        return True  # Not a hard requirement
    except ImportError:
        print("  [FAIL] PyTorch not installed")
        return False


def check_packages():
    """Check required Python packages."""
    all_ok = True
    for pkg in REQUIRED_PACKAGES:
        try:
            mod = importlib.import_module(pkg)
            version = getattr(mod, "__version__", "unknown")
            print(f"  [OK] {pkg} ({version})")
        except ImportError:
            print(f"  [FAIL] {pkg} — not installed")
            all_ok = False
    return all_ok


def check_environments():
    """Check that simulation environments are available."""
    all_ok = True
    for env_name, env_info in ENVIRONMENTS.items():
        try:
            importlib.import_module(env_info["package"])
            print(f"  [OK] {env_name} environment ({env_info['package']})")
        except ImportError:
            print(f"  [WARN] {env_name} environment not available — {env_info['install_hint']}")
            # Not a hard failure — agent can skip tasks for unavailable envs
    return all_ok


def check_policies():
    """Check that policy implementations are available in LeRobot."""
    all_ok = True
    for policy in POLICIES:
        try:
            mod = importlib.import_module(f"lerobot.policies.{policy}")
            print(f"  [OK] Policy: {policy}")
        except ImportError:
            print(f"  [FAIL] Policy: {policy} — not found in LeRobot")
            all_ok = False
    return all_ok


def check_datasets():
    """Check if datasets are cached locally."""
    cache_dir = Path.home() / ".cache" / "huggingface" / "lerobot"
    all_ok = True
    for dataset_id, info in DATASETS.items():
        # Check if dataset directory exists in cache
        dataset_path = cache_dir / dataset_id.replace("/", "--")
        alt_path = cache_dir / dataset_id.split("/")[-1]

        if dataset_path.exists() or alt_path.exists():
            print(f"  [OK] {dataset_id} (cached)")
        else:
            print(f"  [MISS] {dataset_id} — not cached (will download on first use)")
            # Not a hard failure — LeRobot downloads automatically
    return all_ok


def check_disk_space():
    """Check available disk space."""
    import shutil
    total, used, free = shutil.disk_usage("/")
    free_gb = free / (1024 ** 3)
    status = "OK" if free_gb > 50 else "WARN"
    print(f"  [{status}] Disk space: {free_gb:.1f} GB free")
    return free_gb > 10  # Hard minimum: 10 GB


def check_all():
    """Run all checks."""
    print("=" * 60)
    print("AutoResearch-MRL Environment Check")
    print("=" * 60)

    results = {}

    print("\n1. Python Version")
    results["python"] = check_python()

    print("\n2. CUDA / GPU")
    results["cuda"] = check_cuda()

    print("\n3. Required Packages")
    results["packages"] = check_packages()

    print("\n4. Simulation Environments")
    results["environments"] = check_environments()

    print("\n5. Policy Implementations")
    results["policies"] = check_policies()

    print("\n6. Datasets")
    results["datasets"] = check_datasets()

    print("\n7. Disk Space")
    results["disk"] = check_disk_space()

    # Summary
    print("\n" + "=" * 60)
    all_ok = all(results.values())
    if all_ok:
        print("All checks passed. Ready to run experiments.")
    else:
        print("Some checks failed:")
        for name, ok in results.items():
            if not ok:
                print(f"  - {name}")
        print("\nFix the issues above before starting the experiment loop.")
    print("=" * 60)

    return all_ok


# ============================================================
# DOWNLOAD FUNCTIONS
# ============================================================

def download_datasets():
    """Pre-download all datasets used in the benchmark."""
    print("=" * 60)
    print("Downloading datasets...")
    print("=" * 60)

    for dataset_id, info in DATASETS.items():
        print(f"\nDownloading: {dataset_id} (Tier {info['tier']})")
        try:
            # Use LeRobot's dataset loading to trigger download
            cmd = [
                sys.executable, "-c",
                f"from lerobot.common.datasets.lerobot_dataset import LeRobotDataset; "
                f"ds = LeRobotDataset('{dataset_id}'); "
                f"print(f'  Episodes: {{ds.num_episodes}}, Frames: {{ds.num_frames}}')"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                print(f"  [OK] {dataset_id}")
                print(result.stdout.strip())
            else:
                print(f"  [FAIL] {dataset_id}")
                print(f"  Error: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            print(f"  [TIMEOUT] {dataset_id} — download took too long")

    print("\nDone.")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="AutoResearch-MRL Environment Preparation")
    parser.add_argument("--check", action="store_true", help="Run all environment checks")
    parser.add_argument("--download", action="store_true", help="Download all datasets")
    parser.add_argument("--check-task", type=str, help="Check a specific task by name")
    args = parser.parse_args()

    if args.check or (not args.download and not args.check_task):
        success = check_all()
        sys.exit(0 if success else 1)

    if args.download:
        download_datasets()

    if args.check_task:
        print(f"Checking task: {args.check_task}")
        # Find the task
        found = False
        for dataset_id, info in DATASETS.items():
            if info["task"] == args.check_task:
                found = True
                print(f"  Dataset: {dataset_id}")
                print(f"  Tier: {info['tier']}")
                break
        if not found:
            print(f"  Unknown task: {args.check_task}")
            print(f"  Available: {[info['task'] for info in DATASETS.values()]}")
            sys.exit(1)


if __name__ == "__main__":
    main()

#!/bin/bash
# ============================================================
# AutoResearch-MRL: RunPod / GPU Server Setup
# ============================================================
# Run this once on a fresh GPU instance.
# Usage: bash setup.sh
#
# Tested on: RunPod PyTorch 2.x template, Ubuntu 22.04, CUDA 12.x
# ============================================================

set -e  # Exit on any error

echo "============================================================"
echo "AutoResearch-MRL: Environment Setup"
echo "============================================================"

# ---- 1. System Dependencies ----
echo ""
echo "[1/7] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq git htop tmux libegl1-mesa-dev libgl1-mesa-glx > /dev/null 2>&1
echo "  Done."

# ---- 2. Clone Repo ----
echo ""
echo "[2/7] Cloning AutoResearch-MRL..."
REPO_DIR="/workspace/AutoResearch-MRL"
if [ -d "$REPO_DIR" ]; then
    echo "  Repo already exists at $REPO_DIR, pulling latest..."
    cd "$REPO_DIR" && git pull origin main
else
    git clone https://github.com/Vizuara-AI-Lab/AutoResearch-MRL.git "$REPO_DIR"
    cd "$REPO_DIR"
fi
echo "  Done."

# ---- 3. Python Environment ----
echo ""
echo "[3/7] Setting up Python environment..."
cd "$REPO_DIR"

# Use system Python (RunPod templates come with PyTorch pre-installed)
pip install --quiet --upgrade pip

# Install LeRobot from source for latest features
if [ ! -d "/workspace/lerobot" ]; then
    echo "  Cloning LeRobot..."
    git clone https://github.com/huggingface/lerobot.git /workspace/lerobot
fi
cd /workspace/lerobot
pip install --quiet -e ".[aloha,pusht]"

# Install additional dependencies
pip install --quiet gym-pusht gym-aloha
pip install --quiet pandas matplotlib seaborn scipy jupyter
pip install --quiet wandb  # Optional but useful for tracking

echo "  Done."

# ---- 4. Environment Variables ----
echo ""
echo "[4/7] Setting environment variables..."
export MUJOCO_GL=egl  # Headless rendering for MuJoCo
echo 'export MUJOCO_GL=egl' >> ~/.bashrc

# Disable wandb by default (agent can enable it)
export WANDB_MODE=disabled
echo 'export WANDB_MODE=disabled' >> ~/.bashrc

echo "  Done."

# ---- 5. Download Datasets ----
echo ""
echo "[5/7] Downloading datasets..."
cd "$REPO_DIR"

python -c "
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
import sys

datasets = [
    'lerobot/pusht',
    'lerobot/aloha_sim_transfer_cube_human',
    'lerobot/aloha_sim_insertion_human',
]

for ds_id in datasets:
    try:
        print(f'  Downloading {ds_id}...')
        ds = LeRobotDataset(ds_id)
        print(f'    OK: {ds.num_episodes} episodes, {ds.num_frames} frames')
    except Exception as e:
        print(f'    WARN: {ds_id} failed: {e}')
"
echo "  Done."

# ---- 6. Verify GPU ----
echo ""
echo "[6/7] Verifying GPU..."
python -c "
import torch
if torch.cuda.is_available():
    name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_mem / 1e9
    print(f'  GPU: {name} ({vram:.1f} GB VRAM)')
else:
    print('  WARNING: No CUDA GPU detected!')
"

# ---- 7. Smoke Test ----
echo ""
echo "[7/7] Running smoke test..."
cd "$REPO_DIR"
python train.py --smoke-test 2>&1 | tail -20

echo ""
echo "============================================================"
echo "Setup complete!"
echo ""
echo "To start the autonomous experiment loop:"
echo "  cd $REPO_DIR"
echo "  tmux new -s autoresearch"
echo "  python run_loop.py 2>&1 | tee autoresearch.log"
echo ""
echo "To monitor from another terminal:"
echo "  tmux attach -t autoresearch"
echo "  tail -f $REPO_DIR/autoresearch.log"
echo "============================================================"

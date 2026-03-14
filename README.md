# AutoResearch-MRL

**Autonomous Research in Manipulation Robot Learning**

An AI-driven research framework that autonomously benchmarks, optimizes, and compares robot learning policies across standardized manipulation tasks.

Inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) — the human writes the research program (`program.md`), and the AI agent runs experiments, analyzes results, and iterates autonomously.

## What This Does

An AI agent (Claude, GPT, etc.) runs in a loop:

1. **Trains** a robot learning policy on a manipulation task
2. **Evaluates** it in simulation (success rate over 50 episodes)
3. **Records** the result
4. **Keeps or discards** the change based on improvement
5. **Repeats** — overnight, unsupervised, for dozens of experiments

The result: a comprehensive benchmark comparing **Diffusion Policy**, **ACT**, **VQ-BeT**, and **TDMPC** across **PushT**, **ALOHA**, and **LIBERO** tasks, with ablation studies on data efficiency, observation modality, action chunking, and more.

## Policies Compared

| Policy | Type | Key Idea |
|--------|------|----------|
| Diffusion Policy | Imitation Learning | Denoise action trajectories via DDPM |
| ACT | Imitation Learning | Transformer + CVAE action chunking |
| VQ-BeT | Imitation Learning | VQ-VAE + autoregressive transformer |
| TDMPC | Model-Based RL | Latent dynamics + MPC planning |

Extended (stretch goals): Pi0, SmolVLA (VLA models)

## Tasks

| Task | Difficulty | Time Budget |
|------|-----------|-------------|
| PushT | Easy | 30 min |
| ALOHA Transfer Cube | Medium | 60 min |
| ALOHA Insertion | Hard | 60 min |
| LIBERO-Spatial | Medium | 90 min |

## Quick Start

```bash
# Clone and setup
git clone https://github.com/Vizuara-AI-Lab/AutoResearch-MRL.git
cd AutoResearch-MRL
pip install -e .

# Verify environment
python prepare.py --check

# Download datasets
python prepare.py --download

# Smoke test (60 seconds)
python train.py --smoke-test

# Full training run
python train.py
```

## Repository Structure

```
AutoResearch-MRL/
├── program.md          # THE meta-program — instructions for the AI agent
├── README.md           # This file
├── train.py            # Training script — the AI agent modifies this
├── evaluate.py         # Evaluation harness (read-only)
├── prepare.py          # Data & environment setup (read-only)
├── analysis.ipynb      # Results analysis notebook
├── pyproject.toml      # Dependencies
├── .gitignore          # Ignore patterns
├── reports/            # Generated research reports (by the agent)
└── outputs/            # Training checkpoints (gitignored)
```

### Who Edits What

| File | Editor | Purpose |
|------|--------|---------|
| `program.md` | **Human** | Research agenda, agent instructions |
| `train.py` | **AI Agent** | Experiment configuration |
| `evaluate.py` | Nobody | Standardized evaluation |
| `prepare.py` | Nobody | Environment setup |

## How It Works

The core idea from [Karpathy's autoresearch](https://github.com/karpathy/autoresearch):

> You're not touching the Python files like you normally would as a researcher. Instead, you are programming the `program.md` Markdown files that provide context to the AI agents.

The human's job is to write `program.md` — the meta-program that defines what experiments to run, what metrics to track, and what research questions to answer. The AI agent reads `program.md`, modifies `train.py`, and runs experiments in an autonomous loop.

### Experiment Tracking

- **Git is the experiment tracker.** Each experiment is a commit.
- Successful experiments advance the branch. Failed ones get reverted.
- `results.tsv` (gitignored) keeps the full log of all experiments including failures.
- `analysis.ipynb` reads `results.tsv` to generate plots and tables.

### Research Phases

1. **Baselines** — Run every policy on every task with defaults
2. **Optimization** — Tune hyperparameters per (policy, task) pair
3. **Ablations** — Controlled studies on data efficiency, modality, horizons, seeds
4. **Reporting** — Synthesize findings into a research report

## Built On

- [LeRobot](https://github.com/huggingface/lerobot) — Unified robot learning framework by HuggingFace
- [gym-pusht](https://github.com/huggingface/gym-pusht) — PushT environment
- [gym-aloha](https://github.com/huggingface/gym-aloha) — ALOHA simulation
- [LIBERO](https://github.com/Lifelong-Robot-Learning/LIBERO) — Multi-task manipulation benchmark

## Citation

If you use this benchmark in your research:

```bibtex
@misc{autoresearch-mrl,
  title={AutoResearch-MRL: Autonomous Benchmarking of Manipulation Robot Learning Policies},
  author={Vizuara AI Lab},
  year={2026},
  url={https://github.com/Vizuara-AI-Lab/AutoResearch-MRL}
}
```

## License

MIT

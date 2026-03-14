# AutoResearch-MRL

Autonomous research agent for benchmarking and improving **M**anipulation **R**obot **L**earning policies.

Inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch). Instead of manually running experiments, an AI agent autonomously trains, evaluates, and iterates on robot learning policies across standardized manipulation benchmarks. You are not touching the Python files like you normally would as a researcher. Instead, you are programming the `program.md` Markdown file that provides context to the AI agent and sets up your autonomous research org.

The research framework uses [LeRobot](https://github.com/huggingface/lerobot) as the unified training/evaluation backend and Git for experiment tracking.

---

## Scope

### Policies Under Study

| Policy | Type | Key Innovation | Paper |
|--------|------|---------------|-------|
| **Diffusion Policy** | Imitation Learning | DDPM-based action denoising, multimodal distributions | Chi et al., RSS 2023 |
| **ACT** | Imitation Learning | Transformer action chunking + CVAE latent plan | Zhao et al., RSS 2023 |
| **VQ-BeT** | Imitation Learning | VQ-VAE discretization + autoregressive GPT | Lee et al., ICRA 2024 |
| **TDMPC** | Model-Based RL | Latent dynamics + online MPC planning | Hansen et al., ICLR 2024 |
| **Pi0** | VLA | SigLIP + PaliGemma VLM + flow matching action expert | Black et al., 2024 |
| **SmolVLA** | VLA | Lightweight vision-language-action model | HuggingFace, 2025 |

**Core policies** (run on all tasks): Diffusion, ACT, VQ-BeT
**Extended policies** (run on select tasks, require more compute): TDMPC, Pi0, SmolVLA

### Tasks & Environments

| Task | Environment | Env ID | Action Dim | Obs | Tier | Time Budget |
|------|-------------|--------|-----------|-----|------|-------------|
| **PushT** | gym_pusht | `PushT-v0` | 2 | image + state | 1 | 30 min |
| **ALOHA Transfer Cube** | gym_aloha | `AlohaTransferCube-v0` | 14 | image + state | 2 | 60 min |
| **ALOHA Insertion** | gym_aloha | `AlohaInsertion-v0` | 14 | image + state | 2 | 60 min |
| **LIBERO-Spatial** | libero | `libero_spatial` | 7 | image + state | 3 | 90 min |
| **LIBERO-Object** | libero | `libero_object` | 7 | image + state | 3 | 90 min |
| **LIBERO-Goal** | libero | `libero_goal` | 7 | image + state | 3 | 90 min |

### Datasets

| Task | HuggingFace Dataset | Episodes | FPS |
|------|---------------------|----------|-----|
| PushT | `lerobot/pusht` | 206 | 10 |
| ALOHA Transfer | `lerobot/aloha_sim_transfer_cube_human` | 50 | 50 |
| ALOHA Insertion | `lerobot/aloha_sim_insertion_human` | 50 | 50 |
| LIBERO-Spatial | `lerobot/libero_spatial` | 500 (50×10) | 20 |
| LIBERO-Object | `lerobot/libero_object` | 500 (50×10) | 20 |
| LIBERO-Goal | `lerobot/libero_goal` | 500 (50×10) | 20 |

### Primary Metric

**Success rate** (%) over 50 evaluation episodes. **Higher is better.**

Secondary metrics (tracked but not used for keep/discard decisions):
- `avg_reward` — Mean cumulative reward per episode
- `final_loss` — Final training loss
- `training_min` — Wall-clock training time in minutes
- `peak_vram_gb` — Peak GPU memory usage
- `inference_fps` — Policy inference speed
- `steps_completed` — Actual training steps run

---

## Setup

One-time initialization (agent + human work together):

1. **Agree on a run tag.** Naming convention: `<date>` (e.g., `mar14`). The git branch will be `exp/<tag>`.

2. **Create the experiment branch.**
   ```bash
   git checkout -b exp/<tag>
   ```

3. **Read the in-scope files.** Read and understand in full:
   - `README.md` — Project overview
   - `program.md` — This file (your instructions)
   - `train.py` — Training script (the file you modify)
   - `evaluate.py` — Evaluation harness (read-only)
   - `prepare.py` — Data & environment setup (read-only)

4. **Verify environment.** Run:
   ```bash
   python prepare.py --check
   ```
   This checks: LeRobot installation, dataset availability, environment functionality. If anything is missing, tell the human and wait.

5. **Download data.** If datasets are not cached:
   ```bash
   python prepare.py --download
   ```

6. **Initialize `results.tsv`.** Create the file with just the header row:
   ```
   commit	policy	task	success_rate	avg_reward	vram_gb	training_min	steps	status	description
   ```

7. **Smoke test.** Run a 60-second training sanity check:
   ```bash
   python train.py --smoke-test
   ```
   This trains Diffusion Policy on PushT for 100 steps to verify everything works.

8. **Confirm and go.** This is the last human checkpoint. After this, the agent runs autonomously through all phases.

---

## File Permissions

| File | Who Edits | Purpose |
|------|-----------|---------|
| `program.md` | **The human** | Agent instructions — the meta-program |
| `train.py` | **The AI agent** | Training configuration & experiment logic |
| `evaluate.py` | Nobody (read-only) | Standardized evaluation harness |
| `prepare.py` | Nobody (read-only) | Dataset download, environment verification |
| `analysis.ipynb` | Either | Results analysis & visualization |
| `reports/*.md` | **The AI agent** | Generated research reports |

### CAN do
- Modify `train.py` — policy type, hyperparameters, training schedule, data augmentation, observation processing, anything in the configuration section
- Create files in `reports/` — analysis, figures, summaries
- Run training and evaluation commands
- Read any file in the repo or the LeRobot library source for reference
- Create/modify helper scripts if needed for analysis

### CANNOT do
- Modify `evaluate.py` or `prepare.py` (read-only infrastructure)
- Install new packages or add dependencies to `pyproject.toml`
- Modify LeRobot source code directly
- Skip or modify the evaluation protocol (50 episodes, standardized metric extraction)
- Commit `results.tsv` to git (it is gitignored)

---

## The Benchmark Matrix

The full matrix of (policy × task) experiments to run. Core experiments are required; extended experiments are stretch goals.

### Core Experiments (Required)

```
                    PushT    ALOHA-Transfer    ALOHA-Insertion    LIBERO-Spatial
Diffusion Policy     ✓            ✓                 ✓                 ✓
ACT                  ✓            ✓                 ✓                 ✓
VQ-BeT               ✓            ✓                 ✓                 ✓
```

### Extended Experiments (Stretch Goals)

```
                    PushT    ALOHA-Transfer    LIBERO-Spatial    LIBERO-Goal
TDMPC                ✓            ✓                 -                -
Pi0                  -            -                 ✓                ✓
SmolVLA              -            -                 ✓                ✓
```

**Priority:** Complete all core experiments before starting extended ones. Within core, prioritize by tier (PushT first → ALOHA → LIBERO).

---

## Rules of Engagement

### Time Budgets

| Tier | Tasks | Wall-Clock Budget | Recommended Steps | Batch Size |
|------|-------|-------------------|-------------------|------------|
| 1 | PushT | 30 minutes | 50,000 | 64 |
| 2 | ALOHA (Transfer, Insertion) | 60 minutes | 100,000 | 64 |
| 3 | LIBERO (Spatial, Object, Goal) | 90 minutes | 100,000 | 64 |

If a run exceeds **2× the time budget**, kill it and treat as a timeout failure.

### Simplicity Criterion

All else being equal, **simpler is better**. The goal is not just to maximize success rate — it is to find the simplest configuration that achieves high performance.

| Scenario | Verdict |
|----------|---------|
| +2% success rate from clean hyperparameter tuning | Keep |
| +0.5% from hacky data preprocessing trick | Discard (not worth the complexity) |
| Same performance with fewer hyperparameters / simpler arch | Keep (simplification win) |
| +5% from any change, regardless of complexity | Keep (significant improvement) |
| -1% but 2× faster training | Discuss in report (interesting tradeoff) |

### Evaluation Protocol

Every experiment is evaluated identically:
- **50 episodes** per evaluation
- Same random seeds for environment initialization
- Report success_rate as the primary metric
- Save evaluation videos for qualitative analysis (on key experiments)

### Seed Policy

Default seed: `1000`. For seed sensitivity studies (Phase 3), use: `1000, 2000, 3000, 4000, 5000`.

---

## Output Format

After each training run, `train.py` prints a standardized block:

```
---
policy:           diffusion
task:             PushT-v0
success_rate:     82.00
avg_reward:       0.876
final_loss:       0.0234
training_sec:     1823.4
peak_vram_mb:     12045.2
steps_completed:  50000
inference_fps:    45.2
seed:             1000
---
```

To extract the key metric:
```bash
grep "^success_rate:" run.log
```

To extract VRAM:
```bash
grep "^peak_vram_mb:" run.log
```

If neither grep returns anything, the run crashed. Use `tail -n 50 run.log` to see the error.

---

## Logging Results

Record **every** experiment in `results.tsv` (tab-separated, NOT comma-separated):

### Header

```
commit	policy	task	success_rate	avg_reward	vram_gb	training_min	steps	status	description
```

### Columns

| Column | Type | Description |
|--------|------|-------------|
| `commit` | string | Short git hash (7 chars) of the experiment commit |
| `policy` | string | Policy type: `diffusion`, `act`, `vqbet`, `tdmpc`, `pi0`, `smolvla` |
| `task` | string | Task ID: `PushT-v0`, `AlohaTransferCube-v0`, etc. |
| `success_rate` | float | Success rate percentage (0.00–100.00). Use `0.00` for crashes |
| `avg_reward` | float | Mean cumulative reward. Use `0.00` for crashes |
| `vram_gb` | float | Peak VRAM in GB, rounded to 0.1. Use `0.0` for crashes |
| `training_min` | float | Training time in minutes, rounded to 0.1 |
| `steps` | int | Actual steps completed. Use `0` for crashes |
| `status` | string | `keep`, `discard`, `crash`, or `baseline` |
| `description` | string | Short description of what was tried |

### Example

```
a1b2c3d	diffusion	PushT-v0	82.00	0.876	12.0	30.4	50000	baseline	default diffusion on pusht
e4f5g6h	diffusion	PushT-v0	85.00	0.901	12.0	30.2	50000	keep	lr=5e-5 (was 1e-4)
i7j8k9l	diffusion	PushT-v0	80.00	0.842	12.0	30.1	50000	discard	smaller unet dims (256,512)
m1n2o3p	act	PushT-v0	0.00	0.000	0.0	0.0	0	crash	OOM with batch_size=256
q4r5s6t	act	PushT-v0	76.00	0.812	8.5	28.7	50000	baseline	default act on pusht
```

**Important:** `results.tsv` is `.gitignore`'d. It stays local as the complete experiment log. The git branch history only contains winning commits.

---

## Phase 1: Baseline Sweep

**Goal:** Establish baseline performance for every core (policy, task) pair using default LeRobot hyperparameters.

### Procedure

For each (policy, task) pair in the core benchmark matrix:

1. Configure `train.py` with the policy and task, using default hyperparameters
2. `git commit -m "baseline: <policy> on <task>"`
3. Run: `python train.py > run.log 2>&1`
4. Extract metrics from `run.log`
5. Record in `results.tsv` with status `baseline`
6. **Always keep** baseline commits (never revert)

### Priority Order

Run in this order (fastest first, build up to harder tasks):

1. **Diffusion Policy on PushT** (30 min) — sanity check, well-known baseline
2. **ACT on PushT** (30 min)
3. **VQ-BeT on PushT** (30 min)
4. **Diffusion Policy on ALOHA Transfer** (60 min)
5. **ACT on ALOHA Transfer** (60 min)
6. **VQ-BeT on ALOHA Transfer** (60 min)
7. **Diffusion Policy on ALOHA Insertion** (60 min)
8. **ACT on ALOHA Insertion** (60 min)
9. **VQ-BeT on ALOHA Insertion** (60 min)
10. **Diffusion Policy on LIBERO-Spatial** (90 min)
11. **ACT on LIBERO-Spatial** (90 min)
12. **VQ-BeT on LIBERO-Spatial** (90 min)

### Completion Criteria

Phase 1 is complete when all 12 core baselines are recorded. Generate a summary:

```
reports/01_baselines.md
```

Include a table of all results, ranked by success rate per task. Note any surprises or failures.

---

## Phase 2: Optimization Loop

**Goal:** For each (policy, task) pair, improve success rate through systematic hyperparameter and architecture tuning.

### Procedure

For each (policy, task) pair, starting from its baseline:

```
current_best = baseline_success_rate
consecutive_discards = 0

WHILE consecutive_discards < 5:
    1. Propose a modification (see Experiment Ideas)
    2. Modify train.py
    3. git commit -m "opt: <policy>/<task> — <description>"
    4. python train.py > run.log 2>&1
    5. Extract success_rate
    6. IF success_rate > current_best:
         current_best = success_rate
         consecutive_discards = 0
         Record with status "keep"
       ELSE:
         git reset --hard HEAD~1
         consecutive_discards += 1
         Record with status "discard"
```

Stop optimizing a (policy, task) pair after **5 consecutive discards** (convergence signal). Move to the next pair.

### Experiment Ideas

Try these in roughly this priority order. Start with high-impact, low-risk changes.

**1. Learning Rate (highest impact, try first)**
- Sweep: `1e-5, 5e-5, 1e-4, 5e-4, 1e-3`
- This single parameter often accounts for >50% of performance variance

**2. Batch Size**
- Sweep: `32, 64, 128, 256`
- Larger batches smooth gradients but may need LR adjustment

**3. Observation Configuration**
- `n_obs_steps`: `1, 2, 4` (how much history the policy sees)
- Image resolution: `84, 128, 224, 384`
- Crop augmentation ratio: `0.8, 0.9, 0.95, 1.0`

**4. Action Configuration**
- `horizon` (prediction horizon): `8, 16, 32, 64`
- `n_action_steps` (execution horizon): `1, 4, 8, 16`
- These interact — try combinations

**5. Architecture (policy-specific)**

*Diffusion Policy:*
- U-Net channel dims: `(256, 512)`, `(256, 512, 1024)`, `(512, 1024, 2048)`
- Diffusion steps: `50, 100, 200`
- Noise schedule: `linear`, `squaredcos_cap_v2`
- FiLM conditioning: on/off
- Prediction type: `epsilon`, `sample`
- DDIM inference steps: `10, 20, 50`

*ACT:*
- Transformer depth: `4, 6, 8` encoder layers; `1, 4, 7` decoder layers
- Hidden dim: `256, 512, 768`
- Chunk size: `10, 50, 100`
- VAE: on/off
- Latent dim: `16, 32, 64`

*VQ-BeT:*
- Codebook size: `256, 512, 1024`
- GPT layers: `4, 6, 8`
- Action chunk size: `8, 16, 32`

**6. Training Tricks**
- Learning rate schedule: `cosine`, `linear`, `constant_with_warmup`
- Gradient clipping: `1.0, 5.0, 10.0, off`
- Weight decay: `0, 1e-4, 1e-2`
- EMA decay: `0.995, 0.999, 0.9999`

**7. Data Augmentation**
- Random crop: various ratios
- Color jitter: brightness, contrast, saturation
- Random erasing
- Gaussian noise on state observations

### Priority Within Phase 2

Optimize policies in this order (most promising first):
1. Best-performing policy on PushT
2. Best-performing policy on ALOHA Transfer
3. Remaining policies on PushT
4. Remaining policies on ALOHA Transfer
5. Move to ALOHA Insertion, then LIBERO

### Completion Criteria

Phase 2 is complete when all core (policy, task) pairs have converged (5 consecutive discards each). Generate:

```
reports/02_optimization.md
```

Include: best configs found, improvement over baseline, number of experiments per pair, key findings.

---

## Phase 3: Ablation Studies

**Goal:** Controlled experiments to answer specific research questions. Unlike Phase 2, **all results are kept** — every data point is informative. No discarding.

### Study 1: Data Efficiency

**Question:** Which policy degrades least gracefully when training data is reduced?

For each core (policy, task) pair, using the best config from Phase 2:
- Train with `10%, 25%, 50%, 100%` of demonstrations
- Use `--dataset.episodes` to select subsets
- 4 experiments per pair

**Output:** `reports/03a_data_efficiency.md` with plots of success_rate vs data fraction.

### Study 2: Observation Modality

**Question:** How much does each observation modality contribute?

For each (policy, task) pair that supports it:
- **State-only:** Remove image observations, keep proprioceptive state
- **Image-only:** Remove state observations, keep images
- **Image + State:** Both (default)
- 3 experiments per pair

**Output:** `reports/03b_observation_modality.md`

### Study 3: Action Chunking

**Question:** What is the optimal action horizon for each policy and task?

For Diffusion Policy and ACT on PushT and ALOHA Transfer:
- Vary `horizon`: `4, 8, 16, 32, 64`
- Vary `n_action_steps`: `1, 4, 8, 16`
- ~10 experiments per pair

**Output:** `reports/03c_action_chunking.md`

### Study 4: Seed Sensitivity

**Question:** How robust are the results to random initialization?

For best config per (policy, task) pair:
- Run 5 seeds: `1000, 2000, 3000, 4000, 5000`
- Report mean +/- std
- Flag any pair with std > 10% (unreliable)

**Output:** `reports/03d_seed_sensitivity.md`

### Study 5: Compute Scaling

**Question:** Which policy reaches acceptable performance fastest?

For each core (policy, task) pair:
- Track success_rate at intermediate checkpoints: `10k, 20k, 30k, 40k, 50k` steps
- Use `--eval_freq=10000` during training
- Plot learning curves

**Output:** `reports/03e_compute_scaling.md`

### Completion Criteria

Phase 3 is complete when all 5 studies are done. Generate an integrated report:

```
reports/03_ablations.md
```

---

## Phase 4: Analysis & Reporting

**Goal:** Synthesize all findings into a coherent research report.

### Final Deliverables

1. **`reports/final_report.md`** — The main research document:
   - Executive summary
   - Methodology
   - Baseline results table
   - Optimization findings
   - Ablation study results
   - Policy recommendations (which policy for which scenario)
   - Limitations and future work

2. **`reports/figures/`** — All generated plots:
   - `baseline_comparison.png` — Bar chart of all baselines
   - `optimization_progress.png` — Improvement over baselines
   - `data_efficiency.png` — Success rate vs data fraction curves
   - `learning_curves.png` — Training step vs success rate
   - `action_horizon_sweep.png` — Horizon ablation
   - `seed_sensitivity.png` — Box plots per (policy, task)

3. **`reports/best_configs.md`** — The best configuration found for each (policy, task) pair, ready to be copy-pasted for training.

Use `analysis.ipynb` to generate all figures from `results.tsv`.

---

## The Experiment Loop

This is the core autonomous loop that drives all phases:

```
LOOP FOREVER:
    1. Determine current phase and next experiment
       - Phase 1 incomplete? → Next unfinished baseline
       - Phase 2 incomplete? → Next optimization experiment
       - Phase 3 incomplete? → Next ablation experiment
       - Phase 4 incomplete? → Generate reports
       - All done? → Go back, try more creative experiments

    2. Configure train.py for the experiment

    3. git commit -m "<phase>: <policy>/<task> — <description>"

    4. Run: python train.py > run.log 2>&1
       (redirect ALL output to run.log — do NOT flood the context window)

    5. Read results:
       grep "^success_rate:\|^peak_vram_mb:\|^steps_completed:" run.log

    6. If grep is empty → CRASH:
       a. tail -n 50 run.log    (get the stack trace)
       b. If fixable (typo, import, OOM):
          - Fix the issue
          - Re-run (max 2 retries)
       c. If unfixable:
          - Log as crash in results.tsv
          - git reset --hard HEAD~1
          - Move on

    7. Record results in results.tsv (do NOT commit results.tsv)

    8. Decision:
       - Phase 1 (baselines): Always keep
       - Phase 2 (optimization): Keep if success_rate > current_best, else git reset
       - Phase 3 (ablations): Always keep

    9. Go to step 1
```

### NEVER STOP

Once the experiment loop has begun, **do NOT pause to ask the human if you should continue.** Do NOT ask "should I keep going?" The human might be asleep, away, or intentionally letting you run autonomously overnight.

You are the researcher. You are autonomous.

If you run out of ideas in the current phase:
- Advance to the next phase
- Re-read this `program.md` for missed experiment ideas
- Re-read the LeRobot policy source code for architectural details you might vary
- Try combining near-miss modifications from Phase 2
- Try more radical changes (different backbone, unusual hyperparameter ranges)
- Revisit discarded experiments with complementary modifications

The loop runs until the human interrupts you. Period.

**Expected throughput:**
- Tier 1 (PushT, 30 min): ~2 experiments/hour
- Tier 2 (ALOHA, 60 min): ~1 experiment/hour
- Tier 3 (LIBERO, 90 min): ~0.6 experiments/hour
- Overnight (12h, mixed tiers): ~15-20 experiments

### Timeout Handling

If a training run exceeds **2× the time budget** for its tier, kill it (`SIGTERM`, then `SIGKILL` after 30s). Log as crash with description "timeout — exceeded 2x budget". Common causes: OOM causing swap thrashing, compute-heavy architecture change.

### Crash Recovery

| Error Type | Action |
|-----------|--------|
| Import/syntax error | Fix immediately, re-run |
| OOM | Halve `batch_size`, retry once |
| NaN loss | Reduce LR by 10×, retry once |
| CUDA error | Log as crash, move on |
| Environment error | Log as crash, skip task, try next |
| Timeout | Log as crash, try simpler config |

After 3 consecutive crashes on the same (policy, task) pair, skip it and flag for human review in the report.

---

## Notes for the Agent

### Known Gotchas (from prior experimentation)

These are hard-won lessons from months of working with LeRobot. Save yourself hours of debugging:

1. **ACT delta_timestamps:** Do NOT include `observation.state` in delta_timestamps. Only `action` + image keys. ACT sets `observation_delta_indices = None`.

2. **Diffusion Policy delta_timestamps:** DO include `observation.state` with `observation_delta_indices` (e.g., `[-1, 0]`).

3. **Diffusion on ALOHA:** Default `crop_shape=[84,84]` destroys 480×640 images. Use `crop_shape=(440, 560)` with `crop_is_random=False`.

4. **Video decode errors** ("Could not push packet to decoder"): Corrupted dataset cache. Fix by deleting `~/.cache/huggingface/lerobot/lerobot/<dataset_name>`.

5. **MuJoCo rendering:** If running headless (server/Colab), set `MUJOCO_GL=egl` and install `libegl1-mesa-dev`.

6. **LIBERO environment:** Requires `libero` package. Check with `python -c "import libero"`.

7. **Large image inputs:** With ResNet50 + high-res images, VRAM usage can spike unexpectedly. Start with `resnet18` and `resize_shape=(128, 128)` for initial experiments.

### How to Read LeRobot Source

When you need to understand a policy's architecture or available hyperparameters:

```
# Policy config (all hyperparameters)
lerobot/src/lerobot/policies/<policy>/configuration_<policy>.py

# Policy model (architecture)
lerobot/src/lerobot/policies/<policy>/modeling_<policy>.py

# Training script
lerobot/src/lerobot/scripts/lerobot_train.py

# Evaluation script
lerobot/src/lerobot/scripts/lerobot_eval.py
```

### Experiment Naming Convention

Commit messages should follow this pattern:
```
<phase>: <policy>/<task> — <description>

Examples:
baseline: diffusion/pusht — default hyperparameters
opt: diffusion/pusht — lr=5e-5 (was 1e-4)
opt: act/aloha-transfer — chunk_size=50 (was 100)
ablation: diffusion/pusht — 25% data, seed=1000
ablation: act/pusht — state-only observations
```

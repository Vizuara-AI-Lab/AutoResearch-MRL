# AutoResearch-MRL: Live Results

> Last updated: **2026-03-15 15:40 UTC** | auto-generated every 5 min

## Summary

| Metric | Value |
|--------|-------|
| **Current Phase** | Phase 1: Baselines (7/9) |
| Total experiments | 40 |
| Baselines complete | 7 / 9 |
| Improvements kept | 0 |
| Discarded | 1 |
| Crashes | 32 |
| Total GPU time | 440 min (7.3 hrs) |

## Policy Comparison

![Baseline Comparison](reports/figures/baseline_comparison.png)

## Baseline Results

| Policy | Task | Success Rate | Avg Reward | VRAM (GB) | Time (min) | Steps |
|--------|------|:------------:|:----------:|:---------:|:----------:|:-----:|
| diffusion | PushT-v0 | 6.0% | 47.3 | 0.0 | 35 | 28405 |
| act | PushT-v0 | 0.0% | 25.8 | 0.0 | 35 | 16922 |
| vqbet | PushT-v0 | 0.0% | 1.9 | 0.0 | 35 | 25970 |
| diffusion | AlohaTransferCube-v0 | 2.0% | 29.4 | 0.0 | 65 | 10682 |
| act | AlohaTransferCube-v0 | 22.0% | 94.2 | 0.0 | 65 | 15213 |
| vqbet | AlohaTransferCube-v0 | 0.0% | 0.0 | 0.0 | 65 | 7570 |
| diffusion | AlohaInsertion-v0 | 0.0% | 6.3 | 0.0 | 65 | 11018 |

## Training Efficiency

![Training Efficiency](reports/figures/training_efficiency.png)

## Experiment Progress

![Experiment Progress](reports/figures/experiment_progress.png)

## Full Experiment Log

<details>
<summary>Click to expand all experiments</summary>

| # | Commit | Policy | Task | Success | Reward | Status | Description |
|---|--------|--------|------|:-------:|:------:|:------:|-------------|
| 1 | `c7275a1` | diffusion | PushT-v0 | 6.0% | 47.3 | baseline | default diffusion on PushT-v0 |
| 2 | `814f618` | act | PushT-v0 | 0.0% | 25.8 | baseline | default act on PushT-v0 |
| 3 | `5dcae14` | vqbet | PushT-v0 | 0.0% | 1.9 | baseline | default vqbet on PushT-v0 |
| 4 | `7fb27b8` | diffusion | AlohaTransferCube-v0 | 2.0% | 29.4 | baseline | default diffusion on AlohaTransferCube-v0 |
| 5 | `ee4f0ea` | act | AlohaTransferCube-v0 | 22.0% | 94.2 | baseline | default act on AlohaTransferCube-v0 |
| 6 | `5bf4180` | vqbet | AlohaTransferCube-v0 | 0.0% | 0.0 | baseline | default vqbet on AlohaTransferCube-v0 |
| 7 | `4083c68` | diffusion | AlohaInsertion-v0 | 0.0% | 6.3 | baseline | default diffusion on AlohaInsertion-v0 |
| 8 | `f0cd1ec` | act | AlohaInsertion-v0 | 4.0% | 116.0 | discard | default act on AlohaInsertion-v0 |
| 9 | `b9f8d1b` | diffusion | PushT-v0 | 0.0% | 0.0 | CRASH | data_efficiency 10% (20 episodes) |
| 10 | `ae1b3fe` | diffusion | PushT-v0 | 0.0% | 0.0 | CRASH | data_efficiency 25% (51 episodes) |
| 11 | `a3784a0` | diffusion | PushT-v0 | 0.0% | 0.0 | CRASH | data_efficiency 50% (103 episodes) |
| 12 | `c181b77` | diffusion | PushT-v0 | 0.0% | 0.0 | CRASH | data_efficiency 100% (206 episodes) |
| 13 | `faa51f6` | act | PushT-v0 | 0.0% | 0.0 | CRASH | data_efficiency 10% (20 episodes) |
| 14 | `fca5fbe` | act | PushT-v0 | 0.0% | 0.0 | CRASH | data_efficiency 25% (51 episodes) |
| 15 | `d60d984` | act | PushT-v0 | 0.0% | 0.0 | CRASH | data_efficiency 50% (103 episodes) |
| 16 | `dbae0d5` | act | PushT-v0 | 0.0% | 0.0 | CRASH | data_efficiency 100% (206 episodes) |
| 17 | `11dd80a` | vqbet | PushT-v0 | 0.0% | 0.0 | CRASH | data_efficiency 10% (20 episodes) |
| 18 | `6ce7061` | vqbet | PushT-v0 | 0.0% | 0.0 | CRASH | data_efficiency 25% (51 episodes) |
| 19 | `34211ff` | vqbet | PushT-v0 | 0.0% | 0.0 | CRASH | data_efficiency 50% (103 episodes) |
| 20 | `1744792` | vqbet | PushT-v0 | 0.0% | 0.0 | CRASH | data_efficiency 100% (206 episodes) |
| 21 | `36c3ae2` | diffusion | PushT-v0 | 0.0% | 0.0 | CRASH | seed_sensitivity seed=2000 |
| 22 | `51a6cdc` | diffusion | PushT-v0 | 0.0% | 0.0 | CRASH | seed_sensitivity seed=3000 |
| 23 | `50f62bb` | diffusion | PushT-v0 | 0.0% | 0.0 | CRASH | seed_sensitivity seed=4000 |
| 24 | `0613311` | diffusion | PushT-v0 | 0.0% | 0.0 | CRASH | seed_sensitivity seed=5000 |
| 25 | `2769c46` | act | PushT-v0 | 0.0% | 0.0 | CRASH | seed_sensitivity seed=2000 |
| 26 | `5ac84f6` | act | PushT-v0 | 0.0% | 0.0 | CRASH | seed_sensitivity seed=3000 |
| 27 | `87a676d` | act | PushT-v0 | 0.0% | 0.0 | CRASH | seed_sensitivity seed=4000 |
| 28 | `d6cc740` | act | PushT-v0 | 0.0% | 0.0 | CRASH | seed_sensitivity seed=5000 |
| 29 | `c696178` | vqbet | PushT-v0 | 0.0% | 0.0 | CRASH | seed_sensitivity seed=2000 |
| 30 | `80ce5de` | vqbet | PushT-v0 | 0.0% | 0.0 | CRASH | seed_sensitivity seed=3000 |
| 31 | `0f0ce2e` | vqbet | PushT-v0 | 0.0% | 0.0 | CRASH | seed_sensitivity seed=4000 |
| 32 | `41db9b5` | vqbet | PushT-v0 | 0.0% | 0.0 | CRASH | seed_sensitivity seed=5000 |
| 33 | `7349fee` | diffusion | PushT-v0 | 0.0% | 0.0 | CRASH | horizon_sweep horizon=4 n_action_steps=2 |
| 34 | `3e4b31f` | diffusion | PushT-v0 | 0.0% | 0.0 | CRASH | horizon_sweep horizon=8 n_action_steps=4 |
| 35 | `c046a2d` | diffusion | PushT-v0 | 0.0% | 0.0 | CRASH | horizon_sweep horizon=16 n_action_steps=8 |
| 36 | `f1a1ee9` | diffusion | PushT-v0 | 0.0% | 0.0 | CRASH | horizon_sweep horizon=32 n_action_steps=16 |
| 37 | `e5ce06f` | act | PushT-v0 | 0.0% | 0.0 | CRASH | horizon_sweep horizon=4 n_action_steps=2 |
| 38 | `c3f0cde` | act | PushT-v0 | 0.0% | 0.0 | CRASH | horizon_sweep horizon=8 n_action_steps=4 |
| 39 | `13471b9` | act | PushT-v0 | 0.0% | 0.0 | CRASH | horizon_sweep horizon=16 n_action_steps=8 |
| 40 | `f4e6736` | act | PushT-v0 | 0.0% | 0.0 | CRASH | horizon_sweep horizon=32 n_action_steps=16 |

</details>

---
*Generated automatically by [AutoResearch-MRL](program.md). Figures by [PaperBanana](https://github.com/vizuara/paperbanana).*
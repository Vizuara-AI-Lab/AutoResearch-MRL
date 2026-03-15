# AutoResearch-MRL: Live Results

> Last updated: **2026-03-15 16:08 UTC** | auto-generated every 5 min

## Summary

| Metric | Value |
|--------|-------|
| **Current Phase** | Phase 1: Baselines (8/9) |
| Total experiments | 8 |
| Baselines complete | 8 / 9 |
| Improvements kept | 0 |
| Discarded | 0 |
| Crashes | 0 |
| Total GPU time | 431 min (7.2 hrs) |

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
| act | AlohaInsertion-v0 | 4.0% | 116.0 | 0.0 | 65 | 15616 |

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
| 8 | `f0cd1ec` | act | AlohaInsertion-v0 | 4.0% | 116.0 | baseline | default act on AlohaInsertion-v0 |

</details>

---
*Generated automatically by [AutoResearch-MRL](program.md). Figures by [PaperBanana](https://github.com/vizuara/paperbanana).*
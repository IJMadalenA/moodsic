# Benchmark Summary

Composite score weights: accuracy=0.600, reward=0.400

Robustness formula: robust_score = comp_mean - 0.500*comp_std

## Recommendation

Recommended config: d7_l1000_e2_synthTrue_trainTrue (runs=2, robust_score=0.6750, comp_mean=0.6772, comp_std=0.0045, alpha=0.500).

## Robustness by Configuration

| config | runs | acc_mean | acc_std | reward_mean | reward_std | comp_mean | comp_std | robust_score | best_comp | worst_comp |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| d7_l1000_e2_synthTrue_trainTrue | 2 | 0.6055 | 0.0055 | 1.1393 | 0.0120 | 0.6772 | 0.0045 | 0.6750 | 0.6817 | 0.6727 |

## Runs

| file | timestamp | accuracy | Δaccuracy | trend_acc | mean_reward | Δmean_reward | trend_reward | comp_score | rank | config | samples | seed | auto_train | synthetic | test_days |
|---|---|---:|---:|---|---:|---:|---|---:|---:|---|---:|---:|---|---|---:|
| evaluation_benchmark_seed_222.json | 2026-04-15T00:04:49.098705 | 0.6110 | +0.0110 | UP | 1.1513 | +0.0241 | UP | 0.6817 | 1 | d7_l1000_e2_synthTrue_trainTrue | 1000 | 222 | True | True | 7 |
| evaluation_benchmark_seed_111.json | 2026-04-15T00:02:47.906514 | 0.6000 | N/A | N/A | 1.1273 | N/A | N/A | 0.6727 | 2 | d7_l1000_e2_synthTrue_trainTrue | 1000 | 111 | True | True | 7 |

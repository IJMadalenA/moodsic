"""Summarize recent evaluation benchmark JSON files into a comparison table."""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Build a summary table from recent evaluation benchmark JSON logs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--logs-dir",
            type=str,
            default="ml/logs",
            help="Directory containing evaluation_benchmark_*.json files",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maximum number of recent benchmark files to include",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="ml/logs/benchmark_summary.md",
            help="Output markdown file path",
        )
        parser.add_argument(
            "--csv-output",
            type=str,
            default="",
            help="Optional CSV output path (disabled when omitted)",
        )
        parser.add_argument(
            "--w-accuracy",
            type=float,
            default=0.7,
            help="Weight for accuracy in composite score",
        )
        parser.add_argument(
            "--w-reward",
            type=float,
            default=0.3,
            help="Weight for normalized reward in composite score",
        )
        parser.add_argument(
            "--robustness-alpha",
            type=float,
            default=0.5,
            help="Penalty factor in robust_score = comp_mean - alpha*comp_std",
        )

    def handle(self, *args, **options):
        logs_dir = Path(options["logs_dir"])
        limit = max(1, options["limit"])
        output_path = Path(options["output"])
        csv_output_raw = options.get("csv_output", "")
        csv_output_path = Path(csv_output_raw) if csv_output_raw else None
        w_accuracy = float(options["w_accuracy"])
        w_reward = float(options["w_reward"])
        robustness_alpha = float(options["robustness_alpha"])

        if w_accuracy < 0 or w_reward < 0:
            raise CommandError("Weights must be non-negative")
        if (w_accuracy + w_reward) <= 0:
            raise CommandError("At least one weight must be greater than zero")
        if robustness_alpha < 0:
            raise CommandError("robustness-alpha must be non-negative")

        # Normalize weights so users can pass either percentages or direct weights.
        total_weight = w_accuracy + w_reward
        w_accuracy = w_accuracy / total_weight
        w_reward = w_reward / total_weight

        if not logs_dir.exists():
            raise CommandError(f"Logs directory does not exist: {logs_dir}")

        files = sorted(
            logs_dir.glob("evaluation_benchmark_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]

        if not files:
            raise CommandError(
                f"No benchmark files found in {logs_dir} matching evaluation_benchmark_*.json"
            )

        rows: list[dict[str, Any]] = []
        for fpath in files:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)

            options_data = data.get("options", {})
            metrics = data.get("metrics", {})
            rows.append(
                {
                    "file": fpath.name,
                    "timestamp": data.get("timestamp", "N/A"),
                    "accuracy": metrics.get("accuracy", "N/A"),
                    "mean_reward": metrics.get("mean_reward_dataset", "N/A"),
                    "samples": metrics.get("total_samples", "N/A"),
                    "seed": options_data.get("seed", "N/A"),
                    "auto_train": options_data.get("auto_train", "N/A"),
                    "synthetic": options_data.get("with_synthetic_context", "N/A"),
                    "benchmark_episodes": options_data.get("benchmark_episodes", "N/A"),
                    "test_limit": options_data.get("test_limit", "N/A"),
                    "test_days": options_data.get("test_days", "N/A"),
                }
            )

        # Compute deltas against the previous (older) run in the sorted list.
        for i, row in enumerate(rows):
            prev = rows[i + 1] if i + 1 < len(rows) else None
            row["delta_accuracy"] = self._compute_delta(
                row.get("accuracy"), prev, "accuracy"
            )
            row["delta_mean_reward"] = self._compute_delta(
                row.get("mean_reward"), prev, "mean_reward"
            )
            row["trend_accuracy"] = self._trend_from_delta(row["delta_accuracy"])
            row["trend_mean_reward"] = self._trend_from_delta(row["delta_mean_reward"])
            row["composite_score"] = self._compute_composite_score(
                row.get("accuracy"), row.get("mean_reward"), w_accuracy, w_reward
            )

        scored = [r for r in rows if isinstance(r.get("composite_score"), (int, float))]
        scored_sorted = sorted(
            scored, key=lambda r: float(r["composite_score"]), reverse=True
        )
        rank_by_file = {r["file"]: idx + 1 for idx, r in enumerate(scored_sorted)}
        for row in rows:
            row["composite_rank"] = rank_by_file.get(row["file"], "N/A")
            row["config_key"] = self._build_config_key(row)

        table = self._build_markdown_table(rows)
        config_stats = self._compute_config_stats(rows, robustness_alpha)
        recommendation_text = self._build_recommendation_text(
            config_stats, robustness_alpha
        )
        config_table = self._build_config_markdown_table(config_stats)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as out:
            out.write("# Benchmark Summary\n\n")
            out.write(
                f"Composite score weights: accuracy={w_accuracy:.3f}, reward={w_reward:.3f}\n\n"
            )
            out.write(
                f"Robustness formula: robust_score = comp_mean - {robustness_alpha:.3f}*comp_std\n\n"
            )
            out.write("## Recommendation\n\n")
            out.write(recommendation_text + "\n\n")
            out.write("## Robustness by Configuration\n\n")
            out.write(config_table)
            out.write("\n\n## Runs\n\n")
            out.write(table)
            out.write("\n")

        if csv_output_path is not None:
            self._write_csv(rows, csv_output_path)

        self.stdout.write(self.style.SUCCESS(f"Summary written to {output_path}"))
        if csv_output_path is not None:
            self.stdout.write(
                self.style.SUCCESS(f"CSV summary written to {csv_output_path}")
            )
        self.stdout.write("\nRecommendation: " + recommendation_text)
        self.stdout.write("\n" + config_table)
        self.stdout.write("\n" + table)

    @staticmethod
    def _fmt_float(value: Any, digits: int = 4) -> str:
        if isinstance(value, (float, int)):
            return f"{float(value):.{digits}f}"
        return str(value)

    def _build_markdown_table(self, rows: list[dict[str, Any]]) -> str:
        header = (
            "| file | timestamp | accuracy | Δaccuracy | trend_acc | mean_reward | Δmean_reward | trend_reward | comp_score | rank | config | samples | seed | auto_train | synthetic | test_days |\n"
            "|---|---|---:|---:|---|---:|---:|---|---:|---:|---|---:|---:|---|---|---:|\n"
        )
        body_lines = []
        for row in rows:
            body_lines.append(
                "| {file} | {timestamp} | {accuracy} | {delta_accuracy} | {trend_accuracy} | {mean_reward} | {delta_mean_reward} | {trend_mean_reward} | {composite_score} | {composite_rank} | {config_key} | {samples} | {seed} | {auto_train} | {synthetic} | {test_days} |".format(
                    file=row["file"],
                    timestamp=row["timestamp"],
                    accuracy=self._fmt_float(row["accuracy"]),
                    delta_accuracy=row["delta_accuracy"],
                    trend_accuracy=row["trend_accuracy"],
                    mean_reward=self._fmt_float(row["mean_reward"]),
                    delta_mean_reward=row["delta_mean_reward"],
                    trend_mean_reward=row["trend_mean_reward"],
                    composite_score=self._fmt_float(row["composite_score"]),
                    composite_rank=row["composite_rank"],
                    config_key=row["config_key"],
                    samples=row["samples"],
                    seed=row["seed"],
                    auto_train=row["auto_train"],
                    synthetic=row["synthetic"],
                    test_days=row["test_days"],
                )
            )
        return header + "\n".join(body_lines)

    @staticmethod
    def _build_config_key(row: dict[str, Any]) -> str:
        return (
            f"d{row.get('test_days', 'N/A')}"
            f"_l{row.get('test_limit', 'N/A')}"
            f"_e{row.get('benchmark_episodes', 'N/A')}"
            f"_synth{row.get('synthetic', 'N/A')}"
            f"_train{row.get('auto_train', 'N/A')}"
        )

    def _compute_config_stats(
        self, rows: list[dict[str, Any]], robustness_alpha: float
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            key = str(row.get("config_key", "N/A"))
            grouped.setdefault(key, []).append(row)

        stats_rows: list[dict[str, Any]] = []
        for config_key, grouped_rows in grouped.items():
            accuracies = [
                float(r["accuracy"])
                for r in grouped_rows
                if isinstance(r.get("accuracy"), (int, float))
            ]
            rewards = [
                float(r["mean_reward"])
                for r in grouped_rows
                if isinstance(r.get("mean_reward"), (int, float))
            ]
            composites = [
                float(r["composite_score"])
                for r in grouped_rows
                if isinstance(r.get("composite_score"), (int, float))
            ]

            comp_mean = statistics.mean(composites) if composites else None
            comp_std = (
                statistics.pstdev(composites)
                if len(composites) > 1
                else 0.0
                if composites
                else None
            )
            robust_score = (
                (comp_mean - robustness_alpha * comp_std)
                if isinstance(comp_mean, float) and isinstance(comp_std, float)
                else None
            )

            stats_rows.append(
                {
                    "config_key": config_key,
                    "runs": len(grouped_rows),
                    "acc_mean": statistics.mean(accuracies) if accuracies else "N/A",
                    "acc_std": statistics.pstdev(accuracies)
                    if len(accuracies) > 1
                    else 0.0
                    if accuracies
                    else "N/A",
                    "reward_mean": statistics.mean(rewards) if rewards else "N/A",
                    "reward_std": statistics.pstdev(rewards)
                    if len(rewards) > 1
                    else 0.0
                    if rewards
                    else "N/A",
                    "comp_mean": comp_mean if comp_mean is not None else "N/A",
                    "comp_std": comp_std if comp_std is not None else "N/A",
                    "robust_score": robust_score if robust_score is not None else "N/A",
                    "best_comp": max(composites) if composites else "N/A",
                    "worst_comp": min(composites) if composites else "N/A",
                }
            )

        stats_rows.sort(
            key=lambda r: (
                float(r["robust_score"])
                if isinstance(r.get("robust_score"), (int, float))
                else float("-inf")
            ),
            reverse=True,
        )
        return stats_rows

    def _build_recommendation_text(
        self, config_stats: list[dict[str, Any]], robustness_alpha: float
    ) -> str:
        if not config_stats:
            return "No configuration statistics available."
        best = config_stats[0]
        if not isinstance(best.get("robust_score"), (int, float)):
            return "No recommended configuration (insufficient numeric data)."
        return (
            "Recommended config: {config} (runs={runs}, robust_score={robust}, comp_mean={comp_mean}, comp_std={comp_std}, alpha={alpha})."
        ).format(
            config=best["config_key"],
            runs=best["runs"],
            robust=self._fmt_float(best["robust_score"]),
            comp_mean=self._fmt_float(best["comp_mean"]),
            comp_std=self._fmt_float(best["comp_std"]),
            alpha=self._fmt_float(robustness_alpha, digits=3),
        )

    def _build_config_markdown_table(self, config_stats: list[dict[str, Any]]) -> str:
        header = (
            "| config | runs | acc_mean | acc_std | reward_mean | reward_std | comp_mean | comp_std | robust_score | best_comp | worst_comp |\n"
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
        )
        body_lines = []
        for row in config_stats:
            body_lines.append(
                "| {config_key} | {runs} | {acc_mean} | {acc_std} | {reward_mean} | {reward_std} | {comp_mean} | {comp_std} | {robust_score} | {best_comp} | {worst_comp} |".format(
                    config_key=row["config_key"],
                    runs=row["runs"],
                    acc_mean=self._fmt_float(row["acc_mean"]),
                    acc_std=self._fmt_float(row["acc_std"]),
                    reward_mean=self._fmt_float(row["reward_mean"]),
                    reward_std=self._fmt_float(row["reward_std"]),
                    comp_mean=self._fmt_float(row["comp_mean"]),
                    comp_std=self._fmt_float(row["comp_std"]),
                    robust_score=self._fmt_float(row["robust_score"]),
                    best_comp=self._fmt_float(row["best_comp"]),
                    worst_comp=self._fmt_float(row["worst_comp"]),
                )
            )
        return header + "\n".join(body_lines)

    def _compute_delta(
        self, current_value: Any, prev_row: dict[str, Any] | None, prev_key: str
    ) -> str:
        if prev_row is None:
            return "N/A"
        prev_value = prev_row.get(prev_key)
        if not isinstance(current_value, (int, float)) or not isinstance(
            prev_value, (int, float)
        ):
            return "N/A"
        delta = float(current_value) - float(prev_value)
        return f"{delta:+.4f}"

    @staticmethod
    def _trend_from_delta(delta_text: str) -> str:
        if delta_text == "N/A":
            return "N/A"
        try:
            value = float(delta_text)
        except ValueError:
            return "N/A"
        if value > 0.0001:
            return "UP"
        if value < -0.0001:
            return "DOWN"
        return "FLAT"

    @staticmethod
    def _compute_composite_score(
        accuracy: Any, mean_reward: Any, w_accuracy: float, w_reward: float
    ) -> Any:
        """Compute weighted score from accuracy and normalized reward.

        Reward is normalized from [-2, 2] into [0, 1].
        """
        if not isinstance(accuracy, (int, float)) or not isinstance(
            mean_reward, (int, float)
        ):
            return "N/A"
        normalized_reward = (float(mean_reward) + 2.0) / 4.0
        normalized_reward = max(0.0, min(1.0, normalized_reward))
        return w_accuracy * float(accuracy) + w_reward * normalized_reward

    @staticmethod
    def _write_csv(rows: list[dict[str, Any]], csv_output_path: Path) -> None:
        csv_output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "file",
            "timestamp",
            "accuracy",
            "delta_accuracy",
            "trend_accuracy",
            "mean_reward",
            "delta_mean_reward",
            "trend_mean_reward",
            "composite_score",
            "composite_rank",
            "config_key",
            "samples",
            "seed",
            "auto_train",
            "synthetic",
            "benchmark_episodes",
            "test_limit",
            "test_days",
        ]
        with open(csv_output_path, "w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "file": row["file"],
                        "timestamp": row["timestamp"],
                        "accuracy": Command._fmt_float(row["accuracy"]),
                        "delta_accuracy": row["delta_accuracy"],
                        "trend_accuracy": row["trend_accuracy"],
                        "mean_reward": Command._fmt_float(row["mean_reward"]),
                        "delta_mean_reward": row["delta_mean_reward"],
                        "trend_mean_reward": row["trend_mean_reward"],
                        "composite_score": Command._fmt_float(row["composite_score"]),
                        "composite_rank": row["composite_rank"],
                        "config_key": row["config_key"],
                        "samples": row["samples"],
                        "seed": row["seed"],
                        "auto_train": row["auto_train"],
                        "synthetic": row["synthetic"],
                        "benchmark_episodes": row["benchmark_episodes"],
                        "test_limit": row["test_limit"],
                        "test_days": row["test_days"],
                    }
                )

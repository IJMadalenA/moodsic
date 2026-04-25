"""Run a reproducible benchmark sweep (multi-seed) and generate weighted summaries."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Run benchmark sweep across seeds and build weighted summary reports."
    DEFAULTS = {
        "seeds": "101,202,303,404,505",
        "weights": "0.7:0.3,0.8:0.2,0.6:0.4",
        "base_dir": "ml/logs",
        "run_name": "",
        "summary_limit": 200,
        "test_days": 7,
        "test_limit": 1000,
        "benchmark_episodes": 5,
        "synthetic_users": 3,
        "synthetic_tracks": 30,
        "synthetic_interactions": 600,
        "synthetic_weather": 60,
        "synthetic_news": 120,
        "skip_runs": False,
        "robustness_alpha": 0.5,
        "alphas": "",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--seeds",
            type=str,
            default=self.DEFAULTS["seeds"],
            help="Comma-separated seeds for benchmark runs",
        )
        parser.add_argument(
            "--weights",
            type=str,
            default=self.DEFAULTS["weights"],
            help="Comma-separated weight pairs as w_acc:w_reward",
        )
        parser.add_argument(
            "--base-dir",
            type=str,
            default=self.DEFAULTS["base_dir"],
            help="Base directory where matrix run artifacts are written",
        )
        parser.add_argument(
            "--run-name",
            type=str,
            default=self.DEFAULTS["run_name"],
            help="Optional run name suffix (default: timestamp)",
        )
        parser.add_argument(
            "--summary-limit",
            type=int,
            default=self.DEFAULTS["summary_limit"],
            help="Maximum files read by benchmark_summary",
        )
        parser.add_argument("--test-days", type=int, default=self.DEFAULTS["test_days"])
        parser.add_argument(
            "--test-limit", type=int, default=self.DEFAULTS["test_limit"]
        )
        parser.add_argument(
            "--benchmark-episodes",
            type=int,
            default=self.DEFAULTS["benchmark_episodes"],
        )
        parser.add_argument(
            "--synthetic-users", type=int, default=self.DEFAULTS["synthetic_users"]
        )
        parser.add_argument(
            "--synthetic-tracks", type=int, default=self.DEFAULTS["synthetic_tracks"]
        )
        parser.add_argument(
            "--synthetic-interactions",
            type=int,
            default=self.DEFAULTS["synthetic_interactions"],
        )
        parser.add_argument(
            "--synthetic-weather", type=int, default=self.DEFAULTS["synthetic_weather"]
        )
        parser.add_argument(
            "--synthetic-news", type=int, default=self.DEFAULTS["synthetic_news"]
        )
        parser.add_argument(
            "--skip-runs",
            action="store_true",
            help="Skip evaluate_model runs and only regenerate summaries from existing JSON in run dir",
        )
        parser.add_argument(
            "--robustness-alpha",
            type=float,
            default=self.DEFAULTS["robustness_alpha"],
            help="Penalty factor in robust_score = comp_mean - alpha*comp_std",
        )
        parser.add_argument(
            "--alphas",
            type=str,
            default=self.DEFAULTS["alphas"],
            help="Optional comma-separated alpha sweep (overrides --robustness-alpha)",
        )
        parser.add_argument(
            "--config",
            type=str,
            default="",
            help="Optional JSON config file for reproducible matrix runs",
        )

    def handle(self, *args, **options):
        options = self._apply_config_file(options)

        seeds = self._parse_seeds(options["seeds"])
        weight_pairs = self._parse_weights(options["weights"])
        robustness_alpha = float(options["robustness_alpha"])
        if robustness_alpha < 0:
            raise CommandError("robustness-alpha must be non-negative")
        alpha_values = self._parse_alphas(options.get("alphas", ""), robustness_alpha)

        run_suffix = options["run_name"].strip() or timezone.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        run_dir = Path(options["base_dir"]) / f"benchmark_matrix_{run_suffix}"
        run_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.SUCCESS("\n[MATRIX] Benchmark matrix started"))
        self.stdout.write(f"   Run directory: {run_dir}")
        self.stdout.write(f"   Seeds: {seeds}")
        self.stdout.write(f"   Weight pairs: {weight_pairs}")
        self.stdout.write(f"   Robustness alpha(s): {alpha_values}")
        if options.get("config"):
            self.stdout.write(f"   Config: {options['config']}")

        if not options["skip_runs"]:
            for seed in seeds:
                output_json = run_dir / f"evaluation_benchmark_seed_{seed}.json"
                self.stdout.write(f"\n[RUN] seed={seed} -> {output_json.name}")
                self._run_evaluate_subprocess(
                    seed=seed,
                    output_json=output_json,
                    benchmark_episodes=options["benchmark_episodes"],
                    test_days=options["test_days"],
                    test_limit=options["test_limit"],
                    synthetic_users=options["synthetic_users"],
                    synthetic_tracks=options["synthetic_tracks"],
                    synthetic_interactions=options["synthetic_interactions"],
                    synthetic_weather=options["synthetic_weather"],
                    synthetic_news=options["synthetic_news"],
                )

        # Check if there are any benchmark files to process
        benchmark_files = list(run_dir.glob("evaluation_benchmark_*.json"))
        if not benchmark_files:
            self.stdout.write(
                self.style.WARNING(
                    f"\n[MATRIX] No benchmark files found in {run_dir}. Skipping summary generation."
                )
            )
            return

        generated_files: list[Path] = []
        alpha_winners: list[dict[str, Any]] = []

        for alpha in alpha_values:
            alpha_slug = self._alpha_slug(alpha)
            consolidated_rows: list[dict[str, Any]] = []
            for w_acc, w_reward in weight_pairs:
                slug = self._weight_slug(w_acc, w_reward)
                if len(alpha_values) == 1:
                    md_out = run_dir / f"benchmark_summary_{slug}.md"
                    csv_out = run_dir / f"benchmark_summary_{slug}.csv"
                else:
                    md_out = run_dir / f"benchmark_summary_{slug}_{alpha_slug}.md"
                    csv_out = run_dir / f"benchmark_summary_{slug}_{alpha_slug}.csv"

                self.stdout.write(
                    f"\n[SUMMARY] alpha={alpha:.3f} weights=({w_acc:.3f}, {w_reward:.3f})"
                )
                call_command(
                    "benchmark_summary",
                    logs_dir=str(run_dir),
                    limit=options["summary_limit"],
                    output=str(md_out),
                    csv_output=str(csv_out),
                    w_accuracy=w_acc,
                    w_reward=w_reward,
                    robustness_alpha=alpha,
                )
                generated_files.extend([md_out, csv_out])
                consolidated_rows.append(
                    self._load_weight_summary_row(
                        csv_path=csv_out,
                        w_acc=w_acc,
                        w_reward=w_reward,
                        robustness_alpha=alpha,
                    )
                )

            consolidated_rows.sort(
                key=lambda r: (
                    float(r["robust_score"])
                    if isinstance(r.get("robust_score"), (int, float))
                    else float("-inf")
                ),
                reverse=True,
            )
            for idx, row in enumerate(consolidated_rows, start=1):
                row["global_rank"] = idx

            if len(alpha_values) == 1:
                consolidated_md = run_dir / "benchmark_weights_summary.md"
                consolidated_csv = run_dir / "benchmark_weights_summary.csv"
            else:
                consolidated_md = run_dir / f"benchmark_weights_summary_{alpha_slug}.md"
                consolidated_csv = (
                    run_dir / f"benchmark_weights_summary_{alpha_slug}.csv"
                )

            self._write_consolidated_outputs(
                rows=consolidated_rows,
                md_path=consolidated_md,
                csv_path=consolidated_csv,
            )
            generated_files.extend([consolidated_md, consolidated_csv])

            winner = consolidated_rows[0] if consolidated_rows else None
            if winner is not None:
                alpha_winners.append(
                    {
                        "alpha": alpha,
                        "w_accuracy": winner["w_accuracy"],
                        "w_reward": winner["w_reward"],
                        "robust_score": winner["robust_score"],
                    }
                )

        if len(alpha_values) > 1:
            sensitivity_md = run_dir / "benchmark_alpha_sensitivity.md"
            sensitivity_csv = run_dir / "benchmark_alpha_sensitivity.csv"
            self._write_alpha_sensitivity(
                winners=alpha_winners,
                md_path=sensitivity_md,
                csv_path=sensitivity_csv,
            )
            generated_files.extend([sensitivity_md, sensitivity_csv])

        index_path = run_dir / "README.md"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("# Benchmark Matrix Run\n\n")
            f.write(f"Run directory: {run_dir}\n\n")
            f.write(f"Seeds: {seeds}\n\n")
            f.write("Weights:\n")
            for w_acc, w_reward in weight_pairs:
                f.write(f"- accuracy={w_acc:.3f}, reward={w_reward:.3f}\n")
            f.write(f"\nRobustness alpha(s): {alpha_values}\n")
            f.write("\nGenerated reports:\n")
            for item in generated_files:
                f.write(f"- {item.name}\n")

            winner = alpha_winners[0] if alpha_winners else None
            if winner is not None:
                f.write("\nGlobal winner:\n")
                f.write(
                    "- weights: accuracy={w_acc:.3f}, reward={w_reward:.3f} | robust_score={robust} | alpha={alpha:.3f}\n".format(
                        w_acc=float(winner["w_accuracy"]),
                        w_reward=float(winner["w_reward"]),
                        robust=self._fmt_float(winner["robust_score"]),
                        alpha=float(winner["alpha"]),
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Matrix run completed. Index: {index_path}")
        )
        if alpha_winners:
            winner = alpha_winners[0]
            self.stdout.write(
                "Global winner weights: accuracy={w_acc:.3f}, reward={w_reward:.3f} (robust_score={robust}, alpha={alpha:.3f})".format(
                    w_acc=float(winner["w_accuracy"]),
                    w_reward=float(winner["w_reward"]),
                    robust=self._fmt_float(winner["robust_score"]),
                    alpha=float(winner["alpha"]),
                )
            )

    @staticmethod
    def _parse_seeds(raw: Any) -> list[int]:
        if isinstance(raw, list):
            raw_items = [str(item) for item in raw]
        else:
            raw_items = str(raw).split(",")

        seeds: list[int] = []
        for part in raw_items:
            token = part.strip()
            if not token:
                continue
            try:
                seeds.append(int(token))
            except ValueError as exc:
                raise CommandError(f"Invalid seed: {token}") from exc
        if not seeds:
            raise CommandError("At least one seed is required")
        return seeds

    @staticmethod
    def _parse_weights(raw: Any) -> list[tuple[float, float]]:
        if isinstance(raw, list):
            tokens: list[str] = []
            for item in raw:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    tokens.append(f"{item[0]}:{item[1]}")
                else:
                    tokens.append(str(item))
        else:
            tokens = str(raw).split(",")

        pairs: list[tuple[float, float]] = []
        for part in tokens:
            token = part.strip()
            if not token:
                continue
            if ":" not in token:
                raise CommandError(
                    f"Invalid weight pair format: {token}. Expected w_acc:w_reward"
                )
            left, right = token.split(":", 1)
            try:
                w_acc = float(left.strip())
                w_reward = float(right.strip())
            except ValueError as exc:
                raise CommandError(f"Invalid weight pair values: {token}") from exc
            if w_acc < 0 or w_reward < 0 or (w_acc + w_reward) <= 0:
                raise CommandError(
                    f"Weight pair must be non-negative and sum > 0: {token}"
                )
            pairs.append((w_acc, w_reward))

        if not pairs:
            raise CommandError("At least one weight pair is required")
        return pairs

    @staticmethod
    def _parse_alphas(raw: Any, fallback_alpha: float) -> list[float]:
        if isinstance(raw, list):
            tokens = [str(item) for item in raw]
        else:
            text = str(raw)
            if not text.strip():
                return [fallback_alpha]
            tokens = text.split(",")

        if not tokens:
            return [fallback_alpha]

        alphas: list[float] = []
        for part in tokens:
            token = part.strip()
            if not token:
                continue
            try:
                value = float(token)
            except ValueError as exc:
                raise CommandError(f"Invalid alpha value: {token}") from exc
            if value < 0:
                raise CommandError(f"Alpha must be non-negative: {token}")
            alphas.append(value)

        if not alphas:
            raise CommandError("At least one alpha is required")
        return alphas

    def _apply_config_file(self, options: dict[str, Any]) -> dict[str, Any]:
        config_raw = str(options.get("config", "")).strip()
        if not config_raw:
            return options

        config_path = Path(config_raw)
        if not config_path.exists():
            raise CommandError(f"Config file does not exist: {config_path}")

        with open(config_path, encoding="utf-8") as f:
            try:
                config_data = json.load(f)
            except json.JSONDecodeError as exc:
                raise CommandError(f"Invalid JSON config: {config_path}") from exc

        if not isinstance(config_data, dict):
            raise CommandError("Config file must contain a JSON object")

        merged = dict(options)
        for key, default_value in self.DEFAULTS.items():
            if key in config_data and merged.get(key) == default_value:
                merged[key] = config_data[key]

        merged["config"] = str(config_path)
        return merged

    @staticmethod
    def _weight_slug(w_acc: float, w_reward: float) -> str:
        return f"wacc_{w_acc:.2f}_wrew_{w_reward:.2f}".replace(".", "p")

    @staticmethod
    def _alpha_slug(alpha: float) -> str:
        return f"alpha_{alpha:.2f}".replace(".", "p")

    def _run_evaluate_subprocess(
        self,
        *,
        seed: int,
        output_json: Path,
        benchmark_episodes: int,
        test_days: int,
        test_limit: int,
        synthetic_users: int,
        synthetic_tracks: int,
        synthetic_interactions: int,
        synthetic_weather: int,
        synthetic_news: int,
    ) -> None:
        command = [
            sys.executable,
            "manage.py",
            "evaluate_model",
            "--with-synthetic-context",
            "--auto-train",
            "--benchmark-episodes",
            str(benchmark_episodes),
            "--test-days",
            str(test_days),
            "--test-limit",
            str(test_limit),
            "--seed",
            str(seed),
            "--synthetic-users",
            str(synthetic_users),
            "--synthetic-tracks",
            str(synthetic_tracks),
            "--synthetic-interactions",
            str(synthetic_interactions),
            "--synthetic-weather",
            str(synthetic_weather),
            "--synthetic-news",
            str(synthetic_news),
            "--benchmark-output",
            str(output_json),
        ]

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
        )
        if result.stdout:
            self.stdout.write(result.stdout)
        if result.returncode != 0:
            if result.stderr:
                self.stderr.write(result.stderr)
            raise CommandError(
                f"evaluate_model failed for seed={seed} with code {result.returncode}"
            )

    def _load_weight_summary_row(
        self, csv_path: Path, w_acc: float, w_reward: float, robustness_alpha: float
    ) -> dict[str, Any]:
        with open(csv_path, encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            runs = list(reader)

        comp_scores = []
        for row in runs:
            token = str(row.get("composite_score", "")).strip()
            if not token or token == "N/A":
                continue
            try:
                comp_scores.append(float(token))
            except ValueError:
                continue

        if comp_scores:
            comp_mean = sum(comp_scores) / len(comp_scores)
            variance = sum((v - comp_mean) ** 2 for v in comp_scores) / len(comp_scores)
            comp_std = variance**0.5
            robust_score = comp_mean - robustness_alpha * comp_std
            best_comp = max(comp_scores)
            worst_comp = min(comp_scores)
        else:
            comp_mean = "N/A"
            comp_std = "N/A"
            robust_score = "N/A"
            best_comp = "N/A"
            worst_comp = "N/A"

        return {
            "w_accuracy": w_acc,
            "w_reward": w_reward,
            "robustness_alpha": robustness_alpha,
            "runs": len(runs),
            "comp_mean": comp_mean,
            "comp_std": comp_std,
            "robust_score": robust_score,
            "best_comp": best_comp,
            "worst_comp": worst_comp,
        }

    def _write_consolidated_outputs(
        self, rows: list[dict[str, Any]], md_path: Path, csv_path: Path
    ) -> None:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        header = (
            "| rank | w_accuracy | w_reward | runs | comp_mean | comp_std | robust_score | best_comp | worst_comp |\n"
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
        )
        body_lines = []
        for row in rows:
            body_lines.append(
                "| {rank} | {w_acc} | {w_reward} | {runs} | {comp_mean} | {comp_std} | {robust} | {best} | {worst} |".format(
                    rank=row.get("global_rank", "N/A"),
                    w_acc=self._fmt_float(row.get("w_accuracy")),
                    w_reward=self._fmt_float(row.get("w_reward")),
                    runs=row.get("runs", "N/A"),
                    comp_mean=self._fmt_float(row.get("comp_mean")),
                    comp_std=self._fmt_float(row.get("comp_std")),
                    robust=self._fmt_float(row.get("robust_score")),
                    best=self._fmt_float(row.get("best_comp")),
                    worst=self._fmt_float(row.get("worst_comp")),
                )
            )

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Benchmark Weights Summary\n\n")
            if rows:
                winner = rows[0]
                f.write(
                    "Global winner: accuracy={w_acc}, reward={w_reward}, robust_score={robust}, alpha={alpha}\n\n".format(
                        w_acc=self._fmt_float(winner.get("w_accuracy")),
                        w_reward=self._fmt_float(winner.get("w_reward")),
                        robust=self._fmt_float(winner.get("robust_score")),
                        alpha=self._fmt_float(winner.get("robustness_alpha"), digits=3),
                    )
                )
            else:
                f.write("Global winner: N/A\n\n")
            f.write(header)
            f.write("\n".join(body_lines))
            f.write("\n")

        fieldnames = [
            "global_rank",
            "w_accuracy",
            "w_reward",
            "runs",
            "comp_mean",
            "comp_std",
            "robust_score",
            "best_comp",
            "worst_comp",
        ]
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "global_rank": row.get("global_rank", "N/A"),
                        "w_accuracy": self._fmt_float(row.get("w_accuracy")),
                        "w_reward": self._fmt_float(row.get("w_reward")),
                        "runs": row.get("runs", "N/A"),
                        "comp_mean": self._fmt_float(row.get("comp_mean")),
                        "comp_std": self._fmt_float(row.get("comp_std")),
                        "robust_score": self._fmt_float(row.get("robust_score")),
                        "best_comp": self._fmt_float(row.get("best_comp")),
                        "worst_comp": self._fmt_float(row.get("worst_comp")),
                    }
                )

    @staticmethod
    def _fmt_float(value: Any, digits: int = 4) -> str:
        if isinstance(value, (float, int)):
            return f"{float(value):.{digits}f}"
        return str(value)

    def _write_alpha_sensitivity(
        self, winners: list[dict[str, Any]], md_path: Path, csv_path: Path
    ) -> None:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        winners_sorted = sorted(winners, key=lambda r: float(r["alpha"]))
        header = (
            "| alpha | winner_w_accuracy | winner_w_reward | robust_score |\n"
            "|---:|---:|---:|---:|\n"
        )
        lines = []
        for row in winners_sorted:
            lines.append(
                "| {alpha} | {w_acc} | {w_reward} | {robust} |".format(
                    alpha=self._fmt_float(row["alpha"], digits=3),
                    w_acc=self._fmt_float(row["w_accuracy"]),
                    w_reward=self._fmt_float(row["w_reward"]),
                    robust=self._fmt_float(row["robust_score"]),
                )
            )

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Alpha Sensitivity\n\n")
            f.write(header)
            f.write("\n".join(lines))
            f.write("\n")

        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "alpha",
                    "winner_w_accuracy",
                    "winner_w_reward",
                    "robust_score",
                ],
            )
            writer.writeheader()
            for row in winners_sorted:
                writer.writerow(
                    {
                        "alpha": self._fmt_float(row["alpha"], digits=3),
                        "winner_w_accuracy": self._fmt_float(row["w_accuracy"]),
                        "winner_w_reward": self._fmt_float(row["w_reward"]),
                        "robust_score": self._fmt_float(row["robust_score"]),
                    }
                )

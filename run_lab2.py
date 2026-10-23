"""Single-command Lab 2 runner: tests, benchmarks, and external-sort demo."""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from lab2.benchmarking import benchmark_suite
from lab2.datasets import generate_dataset, transaction_key
from lab2.external_sort import external_merge_sort
from lab2.reporting import create_report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("default", "quick", "large", "tests", "benchmark", "external", "report"), default="default")
    parser.add_argument("--size", type=int, default=None, help="benchmark item count (default depends on mode)")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--trials", type=int, default=None)
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--merge-fan-in", type=int, default=8)
    parser.add_argument("--records", action="store_true", help="benchmark transaction records")
    parser.add_argument("--report-csv", action="append", default=None,
                        help="CSV filename under --output-dir to include in report (repeatable); defaults to the two three-trial primary runs")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent
    if args.mode in {"default", "quick", "tests"}:
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-v"], cwd=root)
        if result.returncode: return result.returncode
        if args.mode == "tests": return 0
    if args.mode in {"default", "quick", "large", "benchmark"}:
        size = args.size if args.size is not None else {"quick": 300, "default": 1000, "large": 10_000}.get(args.mode, 1000)
        trials = args.trials if args.trials is not None else (1 if args.mode == "quick" else 3)
        path, rows = benchmark_suite(sizes=(size,), seed=args.seed, trials=trials,
                                     output_dir=args.output_dir, include_records=args.records)
        failures = sum(row["status"] != "ok" for row in rows)
        print(f"Benchmark CSV: {path} ({len(rows) - failures}/{len(rows)} successful rows)")
        if failures: return 1
        if args.mode in {"default", "quick"}:
            _external_demo(args)
        return 0
    if args.mode == "external":
        _external_demo(args)
    if args.mode == "report":
        csv_names = args.report_csv or [
            "benchmark_1000_seed2026_trials3.csv",
            "benchmark_3000_seed2026_trials3.csv",
        ]
        csvs = [Path(args.output_dir) / name for name in csv_names]
        missing = [str(path) for path in csvs if not path.is_file()]
        if missing:
            parser.error("report CSV file(s) missing: " + ", ".join(missing))
        import csv
        trial_counts = set()
        for csv_path in csvs:
            with csv_path.open(newline="", encoding="utf-8") as handle:
                trial_counts.update(int(row["trials"]) for row in csv.DictReader(handle))
        if len(trial_counts) != 1:
            parser.error(f"report CSVs have mixed trial counts: {sorted(trial_counts)}; choose a consistent set")
        path = create_report(csvs, root / "docs" / "Lab_2_Algorithmic_Engineering_Report.docx")
        print(f"Report: {path}")
    return 0


def _external_demo(args):
    output_dir = Path(args.output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    source, target = output_dir / "external_demo_input.jsonl", output_dir / "external_demo_sorted.jsonl"
    rows = generate_dataset(args.size or 2500, "random", seed=args.seed, records=True)
    source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    info = external_merge_sort(source, target, chunk_size=args.chunk_size,
                              merge_fan_in=args.merge_fan_in, temp_dir=output_dir,
                              key=transaction_key)
    print(f"External sort output: {target} ({info['records']} records, {info['merge_passes']} merge passes)")


if __name__ == "__main__":
    raise SystemExit(main())

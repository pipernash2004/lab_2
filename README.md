# Lab 2: Sorting Under Real-World Constraints

This project compares six in-memory sorting choices and demonstrates JSON Lines external merge sort. It uses Python's standard library only; tests use `unittest`. The DOCX report is generated from actual correctness-checked benchmark CSV files.

## Setup (Windows PowerShell)

```powershell
cd C:\Users\piper\OneDrive\Desktop\lab_2
python --version
```

Python 3.10 or newer is recommended. No install step is needed. `requirements.txt` records that the core has no dependencies; report generation also uses only the standard library.

## Run

Run tests only:

```powershell
python -m unittest discover -v
```

Run the default workflow (tests, 1,000-item benchmark with 3 trials, then 2,500-record external-sort demo):

```powershell
python run_lab2.py
```

Quick development workflow (300-item benchmark, one trial):

```powershell
python run_lab2.py --mode quick
```

Benchmark all five distributions, choosing size, seed, trial count, and output directory:

```powershell
python run_lab2.py --mode benchmark --size 3000 --seed 2026 --trials 3 --output-dir results
```

Use transaction-like records:

```powershell
python run_lab2.py --mode benchmark --size 1000 --records
```

Run a separate generated external-sort demonstration. Chunk size and merge fan-in control bounded memory and merge passes:

```powershell
python run_lab2.py --mode external --size 10000 --chunk-size 250 --merge-fan-in 8 --output-dir results
```

Regenerate the report after benchmark CSVs exist:

```powershell
python run_lab2.py --mode report --output-dir results
```

The default workflow creates `results/benchmark_1000_seed2026_trials3.csv`, external demo input/output JSONL files, and `docs/Lab_2_Algorithmic_Engineering_Report.docx`. The CSV contains one row per algorithm and distribution, timing units, median runtime, Python allocation peak, optional counters, and status. A failed correctness check is recorded as failed without a timing.

## Algorithms and conventions

All custom in-memory algorithms mutate and return the given list; the Timsort baseline calls `sorted()` and returns a new list. Every algorithm accepts an optional Python-style `key`. Transaction records use `(timestamp, amount, merchant)` as the common key. Merge Sort and Python Timsort are stable; Lomuto Quick Sort, Hoare Quick Sort, Heap Sort, and the hybrid are unstable. Lomuto chooses the last item; Hoare chooses the middle item. Ascending input is the explicit Lomuto adversary. The hybrid detects monotone runs, uses median-of-three pivots and insertion sort for small regions, then falls back to Heap Sort at its depth limit.

Nearly sorted means an ascending integer sequence with `max(1, n//100)` random pair swaps (zero swaps for empty data). Random input is drawn from a bounded domain to include duplicates. Adversarial data is ascending and targets deterministic last-element Lomuto partitioning.

## External sort and memory

Input and output are UTF-8 JSON Lines. The sorter holds one chunk of at most `chunk_size` decoded records during run generation, then up to `merge_fan_in` decoded stream heads during each merge. Each input stream has a 64 KiB text buffer and the output has another; advancing streams briefly adds a few records. Intermediate files are placed in a temporary directory and cleaned on success or failure. After each complete merge pass, consumed runs are removed, so the temporary directory holds at most roughly two generations, or about twice the serialized dataset size D, in addition to source and final output. Actual memory also depends on decoded Python objects, key tuples, serialization, sort workspace, file buffers, and operating-system caching.

With N records, M records fitting in memory, B records per disk block, and configured merge fan-in f, the implementation uses O((N/B) * (1 + log_f(N/M))) block transfers under sequential I/O and bounded-record assumptions. When f is Theta(M/B), this is the standard O((N/B) log_(M/B)(N/B)) bound (and assumes M >= 2B). Run generation additionally holds a decoded chunk and the hybrid's run-detection list or quicksort stack. Each merge stream has a 64 KiB text buffer; the output has another, plus a few transient decoded records during stream advancement. A completed pass deletes its input runs, so temporary runs peak at roughly two generations, each approximately the serialized data size D. For a purely illustrative average JSONL record size of 128 bytes, 100 million records would occupy about 12.8 GB per serialized copy; budget around 25.6 GB for two temporary generations, plus source, destination, and free-space headroom. Actual record sizes vary.

For a 512 MB process budget, estimate decoded object and sort-workspace use from representative records and measure process RSS for several chunk sizes on the target machine; leave headroom for the interpreter, key objects, a few transient records, and f merge buffers. Choose a conservative chunk size from that measurement, and choose f so `f * 64 KiB` plus decoded heap heads and output buffering stays within the remaining budget. These are sizing steps, not a claim of measured compliance: this project did not run 100 million records or measure/enforce an OS-level 512 MB process limit.

## Project structure

```text
lab2/
  algorithms.py       in-memory algorithms and counters
  datasets.py         reproducible inputs
  benchmarking.py     verification-first benchmark CSVs
  external_sort.py    bounded JSONL run generation and merge
  reporting.py        standard-library DOCX generation
tests/                unittest suite
results/              generated measurements and external-sort demonstration
docs/                  Word report
run_lab2.py            command-line entry point
```

## Troubleshooting

- If a large benchmark takes too long, the deterministic Lomuto cases are quadratic by design. Start with `--mode quick` or reduce `--size`.
- If an external sort uses too much memory, lower `--chunk-size` and/or `--merge-fan-in`; allow more temporary disk space.
- Run `python run_lab2.py --mode report` only after benchmark CSV files exist.
- Benchmark timings vary by machine and background load. Compare algorithms only within rows sharing the same input size, distribution, seed, and trial configuration.

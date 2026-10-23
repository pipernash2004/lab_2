# Lab 2 Sorting Project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete, tested Python project for comparing in-memory sorts and external merge sort, with measured CSV results and a Word report.

**Architecture:** Keep algorithms, data generation, benchmarking, external sorting, and CLI orchestration in separate standard-library modules. Tests exercise sorting contracts and external file behavior; report generation consumes actual CSV measurements and uses python-docx only when available.

**Tech Stack:** Python 3 standard library; `unittest`; optional `python-docx` for DOCX generation.

**Spec:** User-provided Lab 2 brief in pasted text.

## Global Constraints
- “Use Python 3 and the standard library wherever possible.”
- “Do not invent results.”
- “Never default to attempting to allocate 100 million Python records in memory.”
- Keep report claims limited to verified measurements and explain limitations.

## Review Focus
- Empty and duplicate-heavy input, including transaction ties: algorithm tests assert exact order and Merge Sort stability.
- Sorted/reverse/adversarial inputs with deterministic pivots: bounded quicksort tests and hybrid fallback counter.
- External sort with more runs than fan-in: multi-pass test verifies order and record preservation.
- Benchmark algorithm errors: harness records failures and omits invalid timings.
- DOCX dependency unavailable: report generation must state the limitation and keep a reviewable text report.

## File map
- `lab2/algorithms.py`: in-place in-memory algorithms and optional stats.
- `lab2/datasets.py`: reproducible integer and transaction distributions.
- `lab2/benchmarking.py`: verified timing, memory, CSV.
- `lab2/external_sort.py`: chunk runs and bounded k-way merge.
- `run_lab2.py`: test, benchmark, and external-sort CLI.
- `tests/`: unittest coverage for algorithm and external I/O behavior.
- `README.md`, `requirements.txt`, `docs/`: instructions and report.

## Tasks
1. Add algorithm contract tests, then implement six algorithms and introsort fallback instrumentation.
2. Add dataset tests and implement all five reproducible distributions and transaction keys.
3. Add external sorting integration tests including multipass fan-in, then implement safe run lifecycle and merging.
4. Implement benchmark verification, median timing, memory caveat, CSV, CLI commands; run manageable experiment.
5. Generate DOCX from verified CSV data with formal styles, tables, chart if tooling allows; document any unavailable capability.
6. Complete README and requirements, run full suite, benchmark, external demo, and final structure/content checks.

## Execution
The user explicitly approved the design and directed implementation, tests, benchmarking, report generation, and final verification. Execute inline in the current workspace.

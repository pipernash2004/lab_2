"""JSON Lines external merge sort with bounded input chunks and merge fan-in."""
import heapq
import json
import os
import tempfile
from pathlib import Path
from typing import Callable

from .algorithms import introsort


def _identity(value): return value


def _merge_group(paths, output, key):
    """Merge at most fan-in streams, keeping one decoded record per stream."""
    streams = []
    try:
        streams = [open(path, "r", encoding="utf-8", buffering=64 * 1024) for path in paths]
        heap = []
        serial = 0
        for index, stream in enumerate(streams):
            line = stream.readline()
            if line:
                record = json.loads(line)
                heapq.heappush(heap, (key(record), serial, index, record)); serial += 1
        with open(output, "w", encoding="utf-8", buffering=64 * 1024, newline="\n") as out:
            while heap:
                _, _, index, record = heapq.heappop(heap)
                out.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")
                line = streams[index].readline()
                if line:
                    record = json.loads(line)
                    heapq.heappush(heap, (key(record), serial, index, record)); serial += 1
    finally:
        for stream in streams: stream.close()


def external_merge_sort(input_path, output_path, *, chunk_size: int = 50_000,
                        merge_fan_in: int = 32, temp_dir=None,
                        key: Callable = _identity, sort_algorithm: Callable = introsort) -> dict:
    """Sort JSON Lines records externally.

    Each chunk holds at most ``chunk_size`` decoded objects. Intermediate runs
    use JSON serialization; a safe temp directory owns all intermediate data,
    removed on success or failure. Old runs are deleted after each complete
    merge pass, limiting temporary disk use to roughly two run sets at once.
    In the external-memory model with N records, M records of memory and B
    records per disk block, this configured f-way merge costs
    O((N/B) * (1 + log_f(N/M))) block transfers; when f is Theta(M/B), this
    is the familiar O((N/B) log_(M/B)(N/B)) bound. It assumes M >= 2B,
    sequential I/O, and bounded-size records. Python object/JSON buffers and
    storage device behavior are additional.
    """
    if chunk_size < 1: raise ValueError("chunk_size must be positive")
    if merge_fan_in < 2: raise ValueError("merge_fan_in must be at least 2")
    source, target = Path(input_path), Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    passes = 0
    with tempfile.TemporaryDirectory(prefix="lab2_external_", dir=temp_dir) as work:
        work_path = Path(work)
        runs = []
        chunk = []
        def flush():
            if not chunk: return
            sorted_chunk = sort_algorithm(chunk, key=key)
            # Support both in-place routines and non-mutating routines such as
            # Python's sorted/Timsort baseline.
            if sorted_chunk is not None:
                chunk[:] = sorted_chunk
            path = work_path / f"run_{len(runs):08d}.jsonl"
            with open(path, "w", encoding="utf-8", buffering=64 * 1024, newline="\n") as handle:
                for row in chunk: handle.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")
            runs.append(path); chunk.clear()
        with open(source, "r", encoding="utf-8", buffering=64 * 1024) as handle:
            for line in handle:
                if not line.strip(): continue
                chunk.append(json.loads(line))
                if len(chunk) >= chunk_size: flush()
        flush()
        initial_run_count = len(runs)
        if not runs:
            target.write_text("", encoding="utf-8")
            return {"records": 0, "initial_runs": 0, "merge_passes": 0}
        while len(runs) > 1:
            next_runs = []
            for group_index, offset in enumerate(range(0, len(runs), merge_fan_in)):
                group = runs[offset:offset + merge_fan_in]
                path = work_path / f"pass_{passes + 1}_{group_index:08d}.jsonl"
                _merge_group(group, path, key)
                next_runs.append(path)
            # Keep no stale sorted generations once the full pass succeeds.
            for old_run in runs:
                old_run.unlink()
            runs = next_runs
            passes += 1
        # Copy the final run to target to keep temporary ownership centralized.
        with open(runs[0], "rb") as source_run, open(target, "wb") as output:
            while data := source_run.read(1024 * 1024): output.write(data)
        with open(target, "rb") as sorted_file:
            record_count = sum(1 for _ in sorted_file)
        return {"records": record_count,
                "initial_runs": initial_run_count,
                "merge_passes": passes}

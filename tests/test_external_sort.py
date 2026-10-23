import json
import tempfile
import unittest
from pathlib import Path

from lab2.external_sort import external_merge_sort
from lab2.datasets import generate_dataset, transaction_key
from lab2.algorithms import timsort


class ExternalSortTests(unittest.TestCase):
    def test_external_sort_preserves_and_orders_records_across_multiple_passes(self):
        records = generate_dataset(73, "random", seed=9, records=True)
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / "input.jsonl", Path(tmp) / "output.jsonl"
            source.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
            summary = external_merge_sort(source, target, chunk_size=5, merge_fan_in=3,
                                          temp_dir=tmp, key=transaction_key)
            actual = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([transaction_key(r) for r in actual], sorted(transaction_key(r) for r in records))
            self.assertCountEqual([r["record_id"] for r in actual], [r["record_id"] for r in records])
            self.assertGreater(summary["merge_passes"], 1)
            self.assertEqual(summary["initial_runs"], 15)
            self.assertEqual(list(Path(tmp).glob("lab2_external_*")), [])

    def test_external_sort_empty_input_creates_empty_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / "in", Path(tmp) / "out"
            source.write_text("", encoding="utf-8")
            external_merge_sort(source, target, chunk_size=2, merge_fan_in=2, temp_dir=tmp)
            self.assertEqual(target.read_text(encoding="utf-8"), "")

    def test_external_sort_accepts_non_mutating_selected_sort(self):
        values = [9, 1, 8, 2, 7, 3, 6, 4, 5]
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / "in.jsonl", Path(tmp) / "out.jsonl"
            source.write_text("".join(json.dumps(value) + "\n" for value in values), encoding="utf-8")
            external_merge_sort(source, target, chunk_size=2, merge_fan_in=2,
                                temp_dir=tmp, sort_algorithm=timsort)
            actual = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(actual, sorted(values))


if __name__ == "__main__":
    unittest.main()

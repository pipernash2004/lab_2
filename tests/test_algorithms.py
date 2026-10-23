import unittest
import tempfile
from unittest.mock import patch

from lab2.algorithms import ALGORITHMS, SortStats, heap_sort, introsort, merge_sort, timsort
from lab2.algorithms import quick_sort_lomuto
from lab2.benchmarking import benchmark_suite
from lab2.datasets import adversarial_ints, generate_dataset, transaction_key


class SortingAlgorithmsTests(unittest.TestCase):
    def test_all_algorithms_handle_integer_edge_cases(self):
        cases = [[], [7], [3, -1, 3, 0, -8], list(range(40)), list(range(39, -1, -1))]
        for name, algorithm in ALGORITHMS.items():
            for values in cases:
                with self.subTest(algorithm=name, values=values[:5]):
                    result = algorithm(values.copy())
                    self.assertEqual(result, sorted(values))

    def test_all_algorithms_sort_transaction_records_by_shared_key(self):
        records = [
            {"timestamp": 4, "amount": 10, "merchant": "B", "id": 1},
            {"timestamp": 2, "amount": 90, "merchant": "A", "id": 2},
            {"timestamp": 4, "amount": 10, "merchant": "A", "id": 3},
        ]
        key = lambda row: (row["timestamp"], row["amount"], row["merchant"])
        for name, algorithm in ALGORITHMS.items():
            with self.subTest(algorithm=name):
                result = algorithm(records.copy(), key=key)
                self.assertEqual([key(x) for x in result], sorted(key(x) for x in records))
                self.assertCountEqual(result, records)

    def test_merge_sort_is_stable_for_equal_keys(self):
        rows = [{"k": 1, "i": i} for i in range(8)]
        self.assertEqual(merge_sort(rows, key=lambda row: row["k"]), rows)

    def test_stable_algorithms_preserve_order_of_duplicate_transaction_keys(self):
        rows = [
            {"timestamp": 2, "amount": 50, "merchant": "M", "id": 1},
            {"timestamp": 1, "amount": 20, "merchant": "A", "id": 2},
            {"timestamp": 2, "amount": 50, "merchant": "M", "id": 3},
        ]
        key = lambda row: (row["timestamp"], row["amount"], row["merchant"])
        for algorithm in (merge_sort, timsort):
            result = algorithm(rows.copy(), key=key)
            self.assertEqual([r["id"] for r in result if key(r) == key(rows[0])], [1, 3])

    def test_hybrid_activates_heap_fallback_at_depth_limit(self):
        stats = SortStats()
        values = generate_dataset(251, "random", seed=44)
        introsort(values, depth_limit=0, detect_runs=False, stats=stats)
        self.assertEqual(values, sorted(values))
        self.assertGreater(stats.fallbacks, 0)

    def test_hybrid_heap_fallback_sorts_nonzero_subrange(self):
        values = [99] + generate_dataset(80, "random", seed=145) + [-99]
        expected = sorted(values)
        introsort(values, insertion_threshold=1, depth_limit=1, detect_runs=False)
        self.assertEqual(values, expected)

    def test_hybrid_short_natural_runs_use_adaptive_merge(self):
        values = list(range(100))
        values[50], values[51] = values[51], values[50]
        stats = SortStats()
        introsort(values, stats=stats)
        self.assertEqual(values, sorted(values))
        self.assertEqual(stats.partitions, 0)

    def test_deterministic_lomuto_adversary_does_not_break_stack(self):
        values = adversarial_ints(1500, pivot="lomuto_last")
        stats = SortStats()
        self.assertEqual(ALGORITHMS["quick_lomuto"](values.copy(), stats=stats), sorted(values))
        self.assertEqual(stats.comparisons, len(values) * (len(values) - 1) // 2)

    def test_all_distributions_are_reproducible_and_ordered_correctly(self):
        for distribution in ("random", "sorted", "reverse", "nearly_sorted", "adversarial"):
            first = generate_dataset(80, distribution, seed=17)
            second = generate_dataset(80, distribution, seed=17)
            self.assertEqual(first, second)
            if distribution == "sorted":
                self.assertEqual(first, sorted(first))
            if distribution == "reverse":
                self.assertEqual(first, sorted(first, reverse=True))

    def test_generated_transaction_data_contains_distinct_records_with_duplicate_keys(self):
        records = generate_dataset(80, "random", seed=19, records=True)
        keys = [transaction_key(record) for record in records]
        self.assertLess(len(set(keys)), len(keys))
        self.assertEqual(len({record["record_id"] for record in records}), len(records))

    def test_benchmark_counters_are_single_run_and_timsort_unavailable_is_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, rows = benchmark_suite(sizes=(8,), seed=7, trials=2, output_dir=tmp)
        lomuto = next(row for row in rows if row["dataset"] == "random" and row["algorithm"] == "quick_lomuto")
        stats = SortStats()
        quick_sort_lomuto(generate_dataset(8, "random", seed=7), stats=stats)
        self.assertEqual(lomuto["comparisons"], stats.comparisons)
        timsort_row = next(row for row in rows if row["algorithm"] == "timsort_baseline")
        self.assertEqual(timsort_row["comparisons"], "")

    def test_benchmark_accepts_unstable_reordering_of_duplicate_transaction_keys(self):
        tied_records = [
            {"timestamp": 7, "amount": 25, "merchant": "Cafe", "id": identifier}
            for identifier in ("first", "second", "third", "fourth")
        ]
        with tempfile.TemporaryDirectory() as tmp:
            with patch("lab2.benchmarking.generate_dataset", return_value=tied_records):
                _, rows = benchmark_suite(sizes=(4,), seed=1, trials=1,
                                          output_dir=tmp, include_records=True)
        self.assertEqual(len(rows), 30)
        self.assertTrue(all(row["status"] == "ok" for row in rows), rows)


if __name__ == "__main__":
    unittest.main()

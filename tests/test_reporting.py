import csv
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from lab2.reporting import create_report


class ReportingTests(unittest.TestCase):
    def test_benchmark_table_distinguishes_integer_and_transaction_rows(self):
        fields = ["dataset", "algorithm", "input_size", "seed", "trials", "time_unit",
                  "median_seconds", "peak_python_bytes", "comparisons", "partitions",
                  "max_partition_depth", "fallbacks", "status", "message"]
        record = {"dataset": "random", "algorithm": "merge", "input_size": "10",
                  "seed": "2026", "trials": "3", "time_unit": "seconds",
                  "median_seconds": "0.000123456", "peak_python_bytes": "88",
                  "comparisons": "20", "partitions": "0", "max_partition_depth": "0",
                  "fallbacks": "0", "status": "ok", "message": ""}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_paths = []
            algorithms = ("merge", "quick_lomuto", "quick_hoare", "heap",
                          "timsort_baseline", "hybrid_introsort")
            datasets = ("random", "sorted", "reverse", "nearly_sorted", "adversarial")
            for filename in ("benchmark_10_seed2026_trials3.csv",
                             "benchmark_10_records_seed2026_trials3.csv"):
                path = root / filename
                with path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    for dataset in datasets:
                        for algorithm in algorithms:
                            writer.writerow(dict(record, dataset=dataset, algorithm=algorithm))
                csv_paths.append(path)
            output = create_report(csv_paths, root / "report.docx")
            with zipfile.ZipFile(output) as docx:
                document = ET.fromstring(docx.read("word/document.xml"))
                styles = docx.read("word/styles.xml")
            text = " ".join(node.text or "" for node in document.iter() if node.tag.endswith("}t"))
            tables = [node for node in document.iter() if node.tag.endswith("}tbl")]
            benchmark_table_text = " ".join(node.text or "" for node in tables[0].iter()
                                            if node.tag.endswith("}t"))
            self.assertIn("Input Type", benchmark_table_text)
            self.assertIn("Integer data", benchmark_table_text)
            self.assertIn("Transaction records", benchmark_table_text)
            self.assertIn("Input Type", text)
            self.assertIn("Integer data", text)
            self.assertIn("Transaction records", text)
            self.assertIn("0.000123456", text)
            self.assertEqual(len(tables), 3)
            self.assertIn("word/footer1.xml", docx.namelist())
            self.assertIn(b"Heading1", styles)
            self.assertIn(b"Times New Roman", styles)
            self.assertIn(b'w:sz w:val="24"', styles)
            self.assertIn(b'w:line="360"', styles)

    def test_selected_benchmark_csvs_produce_ninety_labeled_rows(self):
        root = Path(__file__).resolve().parents[1]
        csv_paths = [root / "results" / name for name in (
            "benchmark_1000_seed2026_trials3.csv",
            "benchmark_3000_seed2026_trials3.csv",
            "benchmark_1000_records_seed2026_trials3.csv",
        )]
        if not all(path.is_file() for path in csv_paths):
            self.skipTest("the selected benchmark CSVs are not present")
        with tempfile.TemporaryDirectory() as tmp:
            output = create_report(csv_paths, Path(tmp) / "selected-report.docx")
            with zipfile.ZipFile(output) as docx:
                document = ET.fromstring(docx.read("word/document.xml"))
                styles = docx.read("word/styles.xml")
                text = " ".join(node.text or "" for node in document.iter()
                                 if node.tag.endswith("}t"))
                tables = [node for node in document.iter() if node.tag.endswith("}tbl")]
                benchmark_rows = tables[0].findall("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr")
            self.assertEqual(len(benchmark_rows), 91)  # header plus 90 successful CSV rows
            input_type_counts = {}
            for row in benchmark_rows[1:]:
                first_cell = row.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc")
                label = "".join(node.text or "" for node in first_cell.iter()
                                if node.tag.endswith("}t"))
                input_type_counts[label] = input_type_counts.get(label, 0) + 1
            self.assertEqual(input_type_counts, {"Integer data": 60, "Transaction records": 30})
            for row in benchmark_rows:
                widths = [int(cell.find("./{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tcPr/{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tcW").attrib["{http://schemas.openxmlformats.org/wordprocessingml/2006/main}w"])
                          for cell in row.findall("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc")]
                self.assertLessEqual(sum(widths), 9360)
            self.assertIn("Integer data", text)
            self.assertIn("Transaction records", text)
            for path in csv_paths:
                self.assertIn(path.name, text)
            self.assertIn("3000", text)
            self.assertIn("2026", text)
            self.assertIn("trial counts represented: 3", text)
            self.assertIn("512 MB target is not proven", text)
            self.assertIn(b"Times New Roman", styles)
            self.assertIn(b'w:sz w:val="24"', styles)
            self.assertIn(b'w:line="360"', styles)


if __name__ == "__main__":
    unittest.main()

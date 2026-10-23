"""Create the report DOCX using only the standard-library ZIP/XML tools."""
import csv
import html
import platform
import statistics
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


def _paragraph(text, style=None):
    style_xml = f'<w:pStyle w:val="{style}"/>' if style else ""
    return f'<w:p><w:pPr>{style_xml}</w:pPr><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def _table(rows):
    xml = ['<w:tbl><w:tblPr><w:tblBorders>' + ''.join(
        f'<w:{edge} w:val="single" w:sz="4" w:space="0" w:color="777777"/>'
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV")) + '</w:tblBorders></w:tblPr>']
    for row in rows:
        xml.append('<w:tr>')
        for cell in row:
            xml.append('<w:tc><w:tcPr><w:tcW w:w="2400" w:type="dxa"/></w:tcPr>' + _paragraph(str(cell)) + '</w:tc>')
        xml.append('</w:tr>')
    xml.append('</w:tbl>')
    return ''.join(xml)


def _chart_svg(rows, destination):
    algorithms = list(dict.fromkeys(row["algorithm"] for row in rows if row["status"] == "ok"))
    medians = {name: statistics.median(float(r["median_seconds"]) for r in rows
                 if r["algorithm"] == name and r["status"] == "ok") for name in algorithms}
    maximum = max(medians.values()) or 1
    height = 330
    bars = []
    colors = ["#3b82f6", "#22c55e", "#f97316", "#a855f7", "#64748b", "#ef4444"]
    for index, name in enumerate(algorithms):
        y = 25 + index * 48
        width = max(2, 520 * medians[name] / maximum)
        bars.append(f'<text x="0" y="{y+17}" font-size="12">{html.escape(name)}</text>'
                    f'<rect x="150" y="{y}" width="{width:.1f}" height="25" fill="{colors[index%len(colors)]}"/>'
                    f'<text x="{155+width:.1f}" y="{y+17}" font-size="11">{medians[name]:.6f}s</text>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="760" height="{height}" viewBox="0 0 760 {height}"><rect width="100%" height="100%" fill="white"/><text x="0" y="15" font-size="12">Median across distributions, n={rows[0]["input_size"]}</text>{"".join(bars)}</svg>'
    destination.write_text(svg, encoding="utf-8")


def _document_xml(body):
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>{body}<w:sectPr><w:footerReference w:type="default" r:id="rIdFooter"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr></w:body></w:document>'''


def create_report(csv_paths, output_path):
    """Build a formal report containing actual timing tables for CSV inputs."""
    rows = []
    for path in csv_paths:
        with open(path, newline="", encoding="utf-8") as handle: rows.extend(csv.DictReader(handle))
    valid = [row for row in rows if row["status"] == "ok"]
    if not valid: raise ValueError("report requires at least one verified benchmark row")
    sizes = sorted({int(row["input_size"]) for row in valid})
    trial_counts = sorted({int(row["trials"]) for row in valid})
    largest_size = max(sizes)
    adversarial_rows = {row["algorithm"]: row for row in valid
                        if int(row["input_size"]) == largest_size
                        and row["dataset"] == "adversarial"}
    lomuto_row = adversarial_rows["quick_lomuto"]
    hoare_row = adversarial_rows["quick_hoare"]
    adversarial_observation = (
        f"At n={largest_size}, last-pivot Lomuto made {int(lomuto_row['comparisons']):,} comparisons "
        f"in {float(lomuto_row['median_seconds']):.6f} s on ascending adversarial input; "
        f"middle-pivot Hoare made {int(hoare_row['comparisons']):,} comparisons "
        f"in {float(hoare_row['median_seconds']):.6f} s on the same dataset. "
        "These are measurements from this run and machine, not general performance guarantees."
    )
    body = []
    body.append(_paragraph("Lab 2: Algorithmic Engineering", "Title"))
    body.append(_paragraph("Sorting Under Real-World Constraints", "Subtitle"))
    body.append(_paragraph("Student learning report | Generated from project benchmark CSV files"))
    sections = [
        ("1. Abstract", "This report implements and compares Merge Sort, two iterative Quick Sort partition schemes, Heap Sort, Python's Timsort baseline, an introsort-inspired adaptive hybrid, and JSON Lines external merge sort. The recorded results below come from correctness-checked benchmark runs generated on this machine. They are observations for the stated input sizes, not universal performance guarantees."),
        ("2. Introduction", "Sorting is a useful case study in algorithm engineering because asymptotic complexity, input structure, stability, memory use, and implementation overhead all affect practical choices."),
        ("3. Problem Definition and Requirements", "Each in-memory implementation accepts a list and optional key function. Transaction keys are lexicographic (timestamp, amount, merchant). Custom in-place algorithms mutate and return their list; Timsort returns a new list. Only Merge Sort and the built-in baseline promise stability."),
        ("4. Methodology and Experimental Environment", f"Python {__import__('sys').version.split()[0]} on {platform.platform()} ({platform.machine()}); processor model was not recorded. Random seed 2026; measured sizes {', '.join(map(str, sizes))}; trial counts represented in the imported CSV files: {', '.join(map(str, trial_counts))}. The results table contains {len(valid)} correct rows from all benchmark CSV files supplied to the report generator. Timing uses time.perf_counter and reports the median of the configured trials. Every output is compared with sorted() before timing is retained. Peak memory uses tracemalloc separately from timings, so it is Python allocation peak rather than process RSS or an enforced limit. Comparison and fallback counters describe one timed run. Rows with different sizes, distributions, or trial counts are not direct timing comparisons."),
        ("5. Algorithm Design and Correctness Reasoning", "Merge Sort repeatedly merges sorted runs; by induction each merged interval is ordered, and choosing the left run on equal keys preserves stability. Lomuto places values <= pivot before its final pivot position. Hoare scans from both ends, swapping out-of-place values until the indices cross; the returned split places values no greater than the pivot on the left and no smaller values on the right, and the iterative ranges [lo, split] and [split+1, hi] strictly shrink. Heap Sort maintains the max-heap property and moves each maximum into its final suffix position. Timsort delegates to Python's stable built-in sort. The hybrid either returns an ordered/low-run merge of individually sorted runs, or applies these partition and base-case algorithms; its heap fallback handles ranges when the depth budget is spent."),
        ("6. Complexity Analysis and Proofs", "Merge Sort satisfies T(n)=2T(n/2)+Theta(n), hence Theta(n log n) time and Theta(n) auxiliary storage. Heap Sort is Theta(n log n) in all cases with O(1) extra storage. Quick Sort satisfies T(n)=T(k)+T(n-k-1)+Theta(n): balanced splits give Theta(n log n), while repeated extreme splits give Theta(n^2). The iterative implementation avoids call-stack overflow, but does not remove the quadratic work."),
        ("7. Hybrid Algorithm Design", "The hybrid detects monotone natural runs in O(n), reversing strictly descending runs. If there is one run, or at most max(8, n//32) runs, it merges those runs and returns; this takes O(n log r) time for r runs. Otherwise it uses median-of-three pivots, insertion sort for partitions up to the configured threshold, and Heap Sort when a 2*floor(log2(n)) partition-depth budget is exhausted. Thus worst-case time remains O(n log n). The run-merge path uses O(n) auxiliary storage; the introsort path uses O(log n) stack storage. It is not stable as a whole because its partition path is not stable."),
        ("8. Adversarial Analysis and Defense", "Ascending input is adversarial to last-element Lomuto partitioning: each pivot is an endpoint, creating partitions of sizes 0 and n-1 and quadratic comparisons. " + adversarial_observation + " Hoare's middle pivot and the hybrid's run recognition avoid this particular failure mode; the hybrid also includes a tested heap fallback."),
        ("9. External Sorting and I/O Complexity", "The external sorter reads at most M records per chunk, sorts and serializes runs, then merges at most configured fan-in f streams while holding one head record/key per stream. With R=ceil(N/M) initial runs, it performs ceil(log_f R) merge passes. Under the standard external-memory model this gives O((N/B) * (1 + log_f(N/M))) block transfers; when f=Theta(M/B), it becomes the standard O((N/B) log_(M/B)(N/B)), assuming M >= 2B. The model assumes bounded fixed-size records and sequential block I/O. Each stream uses a 64 KiB text buffer and one decoded record/key, with a few transient records while advancing; merge output has a further 64 KiB buffer. Completed old runs are deleted after each pass, so temporary disk holds at most roughly two generations, approximately 2D for serialized input size D. For illustration only, if average JSONL size were 128 bytes, 100 million records would be about 12.8 GB per copy and about 25.6 GB for two temporary generations, before source, final output, and safety headroom. Python object headers, key objects, JSON encoding, varying record sizes, and OS cache affect real memory/disk needs."),
        ("10. Experimental Results", "Verified median times in seconds for every generated result row follow. Each line corresponds to a separately benchmarked input size and distribution."),
        ("11. Analysis and Decision Matrix", "For stability choose Merge Sort or the built-in baseline. For worst-case time with constant auxiliary storage choose Heap Sort. For an easy high-performance baseline use Python Timsort. For demonstrating partition schemes use Quick Sort, while avoiding deterministic endpoint pivots on ordered input. The hybrid is the adaptive educational option, with a worst-case fallback and additional run detection."),
        ("12. Limitations and Threats to Validity", "The benchmark uses small-to-moderate in-memory datasets and one local machine. Timings can vary with background work and hardware. tracemalloc excludes some native allocations and OS file cache. The 512 MB target is not proven: no peak process RSS measurement, memory limit, or 100-million-record run was performed. To configure such a run, measure representative decoded records and process RSS for several chunk sizes, include sort workspace and 64 KiB per merge stream plus output buffering, then reserve headroom within the 512 MB budget. External sorting was validated at manageable scale only."),
        ("13. Conclusion", "The experiment makes the trade-off visible: deterministic Lomuto quicksort is fast on ordinary random inputs at this scale, but its comparisons grow quadratically on ordered data. Merge and heap-based defenses provide predictable complexity; Timsort benefits from natural runs; external merge sort extends the approach to data larger than the selected in-memory chunk."),
        ("14. References", "Cormen, T. H., Leiserson, C. E., Rivest, R. L., and Stein, C. (2022). Introduction to Algorithms, 4th ed. MIT Press. ISBN 978-0-262-04630-5. https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/\nPhillips, J. M. (2013). Introduction to I/O Efficient Algorithms (External Memory Model). University of Utah lecture slides, August 30, 2013. https://users.cs.utah.edu/~jeffp/teaching/MCMD/IO-intro.pdf\nPython Software Foundation. Sorting Techniques. Python 3 documentation. https://docs.python.org/3/howto/sorting.html (accessed 2026-10-23)."),
        ("15. Appendix: Running the Project", "From PowerShell at the repository root: python -m unittest discover -v; python run_lab2.py; python run_lab2.py --mode quick; python run_lab2.py --mode benchmark --size 3000 --trials 3; python run_lab2.py --mode external --size 5000 --chunk-size 100 --merge-fan-in 8."),
    ]
    for title, text in sections:
        body.append(_paragraph(title, "Heading1"))
        for paragraph in text.split("\n"):
            body.append(_paragraph(paragraph))
        if title.startswith("10."):
            body.append(_table([["Size", "Dataset", "Algorithm", "Trials", "Median seconds", "Peak Python bytes"]] + [
                [r["input_size"], r["dataset"], r["algorithm"], r["trials"], r["median_seconds"], r["peak_python_bytes"]]
                for r in valid]))
            body.append(_paragraph("Adversarial comparison-count summary", "Heading2"))
            summary = []
            for size in sizes:
                summary.append([size] + [next(r["comparisons"] for r in valid if int(r["input_size"]) == size and r["dataset"] == "adversarial" and r["algorithm"] == alg)
                                          for alg in ("quick_lomuto", "quick_hoare", "hybrid_introsort")])
            body.append(_table([["Size", "Lomuto comparisons", "Hoare comparisons", "Hybrid comparisons"]] + summary))
        if title.startswith("11."):
            body.append(_table([
                ["Goal", "Suitable choice", "Trade-off / evidence"],
                ["Stable ordering", "Merge Sort or Timsort", "Preserves input order for equal keys; Merge Sort uses O(n) extra space."],
                ["Worst-case bound with O(1) auxiliary space", "Heap Sort", "O(n log n) worst case; unstable and often slower in these small runs."],
                ["General Python application", "Timsort baseline", "Stable built-in; measured as the practical reference, but Python runtime is not comparable to pure-Python loops."],
                ["Study partition schemes", "Hoare Quick Sort", "Middle pivot avoids the tested ascending endpoint-pivot adversary; worst case still O(n^2) for other inputs."],
                ["Educational adaptive hybrid", "Introsort-inspired hybrid", "Accepts low-count natural runs; otherwise uses insertion sort and tested Heap Sort fallback; O(n) space only on run-merge path."],
            ]))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as doc:
        doc.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>''')
        doc.writestr("_rels/.rels", '''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>''')
        doc.writestr("word/_rels/document.xml.rels", '''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>''')
        doc.writestr("word/styles.xml", '''<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:line="360" w:lineRule="auto" w:after="120"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:rPr><w:i/><w:sz w:val="28"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:rPr><w:b/><w:sz w:val="28"/></w:rPr><w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style></w:styles>''')
        doc.writestr("word/footer1.xml", '''<?xml version="1.0" encoding="UTF-8"?><w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:fldSimple w:instr="PAGE"><w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>''')
        doc.writestr("word/document.xml", _document_xml("".join(body)))
    return output_path

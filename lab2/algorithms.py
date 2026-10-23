"""In-memory sorting algorithms.

All functions mutate and return the supplied list (the Timsort baseline also
returns a new sorted list to match Python's ``sorted`` API). ``key`` follows
Python's key-function convention. Equal keys are ordered consistently but
only Merge Sort and Timsort promise stability. Custom algorithms use O(1),
O(n), or O(log n) auxiliary space as documented below.
"""
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")
K = TypeVar("K")
Key = Callable[[T], object]


@dataclass
class SortStats:
    comparisons: int = 0
    partitions: int = 0
    max_partition_depth: int = 0
    fallbacks: int = 0


def _key(key):
    return key if key is not None else (lambda value: value)


def merge_sort(items: list[T], key: Key | None = None, *, stats: SortStats | None = None) -> list[T]:
    """Stable bottom-up merge sort; O(n log n) time and O(n) auxiliary space."""
    key_fn = _key(key)
    n = len(items)
    if n < 2:
        return items
    source = list(items)
    target = [None] * n
    width = 1
    while width < n:
        for start in range(0, n, 2 * width):
            mid, end = min(start + width, n), min(start + 2 * width, n)
            left, right, out = start, mid, start
            while left < mid and right < end:
                if stats:
                    stats.comparisons += 1
                # Taking the left item on equality preserves input order.
                if key_fn(source[left]) <= key_fn(source[right]):
                    target[out] = source[left]; left += 1
                else:
                    target[out] = source[right]; right += 1
                out += 1
            while left < mid:
                target[out] = source[left]; left += 1; out += 1
            while right < end:
                target[out] = source[right]; right += 1; out += 1
        source, target = target, source
        width *= 2
    items[:] = source
    return items


def _lomuto_partition(a, lo, hi, key_fn, stats):
    pivot = key_fn(a[hi])
    boundary = lo
    for scan in range(lo, hi):
        if stats: stats.comparisons += 1
        if key_fn(a[scan]) <= pivot:
            a[boundary], a[scan] = a[scan], a[boundary]
            boundary += 1
    a[boundary], a[hi] = a[hi], a[boundary]
    if stats: stats.partitions += 1
    return boundary


def quick_sort_lomuto(items: list[T], key: Key | None = None, *, stats: SortStats | None = None) -> list[T]:
    """Iterative Lomuto quicksort, last-element pivot; O(n log n) average,
    O(n²) worst time, O(log n) pending stack when smaller side is processed
    immediately; unstable. Sorted/equal data is an adversary for this pivot.
    """
    key_fn = _key(key)
    stack = [(0, len(items) - 1, 1)] if len(items) > 1 else []
    while stack:
        lo, hi, depth = stack.pop()
        if stats: stats.max_partition_depth = max(stats.max_partition_depth, depth)
        while lo < hi:
            p = _lomuto_partition(items, lo, hi, key_fn, stats)
            left, right = (lo, p - 1), (p + 1, hi)
            small, large = (left, right) if left[1] - left[0] < right[1] - right[0] else (right, left)
            if large[0] < large[1]:
                stack.append((*large, depth + 1))
            lo, hi = small
            depth += 1
    return items


def _hoare_partition(a, lo, hi, key_fn, stats):
    pivot = key_fn(a[(lo + hi) // 2])
    i, j = lo - 1, hi + 1
    while True:
        i += 1
        while key_fn(a[i]) < pivot:
            if stats: stats.comparisons += 1
            i += 1
        if stats: stats.comparisons += 1
        j -= 1
        while key_fn(a[j]) > pivot:
            if stats: stats.comparisons += 1
            j -= 1
        if stats: stats.comparisons += 1
        if i >= j:
            if stats: stats.partitions += 1
            return j
        a[i], a[j] = a[j], a[i]


def quick_sort_hoare(items: list[T], key: Key | None = None, *, stats: SortStats | None = None) -> list[T]:
    """Iterative Hoare quicksort using middle element as pivot; average
    O(n log n), worst O(n²), O(log n) stack; unstable. Hoare returns a split
    index, so both ranges are [lo, split] and [split+1, hi].
    """
    key_fn = _key(key)
    stack = [(0, len(items) - 1, 1)] if len(items) > 1 else []
    while stack:
        lo, hi, depth = stack.pop()
        if stats: stats.max_partition_depth = max(stats.max_partition_depth, depth)
        while lo < hi:
            split = _hoare_partition(items, lo, hi, key_fn, stats)
            left, right = (lo, split), (split + 1, hi)
            small, large = (left, right) if left[1] - left[0] < right[1] - right[0] else (right, left)
            if large[0] < large[1]: stack.append((*large, depth + 1))
            lo, hi = small
            depth += 1
    return items


def _sift_down(a, start, end, key_fn, stats, base=0):
    root = start
    while base + 2 * (root - base) + 1 <= end:
        child = base + 2 * (root - base) + 1
        swap = root
        if stats: stats.comparisons += 1
        if key_fn(a[swap]) < key_fn(a[child]): swap = child
        if child + 1 <= end:
            if stats: stats.comparisons += 1
            if key_fn(a[swap]) < key_fn(a[child + 1]): swap = child + 1
        if swap == root: return
        a[root], a[swap] = a[swap], a[root]
        root = swap


def _heap_sort_range(a, lo, hi, key_fn, stats):
    n = hi - lo + 1
    for root in range(n // 2 - 1, -1, -1):
        _sift_down(a, lo + root, hi, key_fn, stats, base=lo)
    for end in range(hi, lo, -1):
        a[lo], a[end] = a[end], a[lo]
        _sift_down(a, lo, end - 1, key_fn, stats, base=lo)


def heap_sort(items: list[T], key: Key | None = None, *, stats: SortStats | None = None) -> list[T]:
    """In-place heap sort; O(n log n) time, O(1) auxiliary space; unstable."""
    if len(items) > 1: _heap_sort_range(items, 0, len(items) - 1, _key(key), stats)
    return items


def timsort(items: list[T], key: Key | None = None, *, stats: SortStats | None = None) -> list[T]:
    """Python's stable Timsort baseline, returning a new list; O(n log n)
    worst-case and O(n) worst-case auxiliary space (implementation dependent).
    """
    return sorted(items, key=key)


def _insertion_sort(a, lo, hi, key_fn, stats):
    for i in range(lo + 1, hi + 1):
        item, item_key, j = a[i], key_fn(a[i]), i - 1
        while j >= lo:
            if stats: stats.comparisons += 1
            if key_fn(a[j]) <= item_key: break
            a[j + 1] = a[j]; j -= 1
        a[j + 1] = item


def _median3(a, lo, hi, key_fn):
    mid = (lo + hi) // 2
    trio = [(key_fn(a[lo]), lo), (key_fn(a[mid]), mid), (key_fn(a[hi]), hi)]
    trio.sort(key=lambda pair: pair[0])
    return trio[1][1]


def _detect_runs(a, key_fn, stats=None):
    """Reverse strictly descending natural runs then merge adjacent runs.

    Fully merge only when there are at most max(8, n//32) runs. This avoids
    turning random data into a full merge sort before introsort. Run detection
    costs O(n), and merging r accepted runs costs O(n log r).
    """
    n = len(a)
    if n < 2: return
    runs = []
    start = 0
    while start < n:
        end = start + 1
        descending = end < n and key_fn(a[end]) < key_fn(a[start])
        if descending:
            while end < n and key_fn(a[end]) < key_fn(a[end - 1]):
                if stats: stats.comparisons += 1
                end += 1
            a[start:end] = reversed(a[start:end])
        else:
            while end < n and key_fn(a[end]) >= key_fn(a[end - 1]):
                if stats: stats.comparisons += 1
                end += 1
        runs.append((start, end)); start = end
    if len(runs) == 1: return True
    if len(runs) > max(8, n // 32): return False
    aux = list(a)
    while len(runs) > 1:
        next_runs = []
        for idx in range(0, len(runs), 2):
            if idx + 1 == len(runs): next_runs.append(runs[idx]); continue
            lo, mid = runs[idx][0], runs[idx][1]
            hi = runs[idx + 1][1]
            i, j, out = lo, mid, lo
            while i < mid and j < hi:
                if stats: stats.comparisons += 1
                if key_fn(a[i]) <= key_fn(a[j]): aux[out] = a[i]; i += 1
                else: aux[out] = a[j]; j += 1
                out += 1
            while i < mid: aux[out] = a[i]; i += 1; out += 1
            while j < hi: aux[out] = a[j]; j += 1; out += 1
            a[lo:hi] = aux[lo:hi]
            next_runs.append((lo, hi))
        runs = next_runs
    return True


def introsort(items: list[T], key: Key | None = None, *, insertion_threshold: int = 16,
              depth_limit: int | None = None, detect_runs: bool = True,
              stats: SortStats | None = None) -> list[T]:
    """Unstable introsort-inspired adaptive hybrid.

    Detects natural runs in O(n). Already ordered input and input with at most
    max(8, n//32) runs are merged adaptively in O(n log r) time. Otherwise,
    median-of-three quick partitions are used, insertion sort handles small
    ranges, and heapsort handles ranges that exhaust the 2*floor(log2(n))
    budget (or caller-supplied budget). Worst-case O(n log n); accepted run
    merging uses O(n) auxiliary space, otherwise partition stack is O(log n).
    """
    if insertion_threshold < 1: raise ValueError("insertion_threshold must be positive")
    n = len(items)
    if n < 2: return items
    key_fn = _key(key)
    if detect_runs and _detect_runs(items, key_fn, stats): return items
    limit = 2 * (n.bit_length() - 1) if depth_limit is None else depth_limit
    stack = [(0, n - 1, limit, 1)]
    while stack:
        lo, hi, remaining, depth = stack.pop()
        if stats: stats.max_partition_depth = max(stats.max_partition_depth, depth)
        if hi - lo + 1 <= insertion_threshold:
            _insertion_sort(items, lo, hi, key_fn, stats); continue
        if remaining <= 0:
            _heap_sort_range(items, lo, hi, key_fn, stats)
            if stats: stats.fallbacks += 1
            continue
        pivot_index = _median3(items, lo, hi, key_fn)
        items[pivot_index], items[hi] = items[hi], items[pivot_index]
        split = _lomuto_partition(items, lo, hi, key_fn, stats)
        if lo < split - 1: stack.append((lo, split - 1, remaining - 1, depth + 1))
        if split + 1 < hi: stack.append((split + 1, hi, remaining - 1, depth + 1))
    return items


ALGORITHMS = {
    "merge": merge_sort,
    "quick_lomuto": quick_sort_lomuto,
    "quick_hoare": quick_sort_hoare,
    "heap": heap_sort,
    "timsort_baseline": timsort,
    "hybrid_introsort": introsort,
}

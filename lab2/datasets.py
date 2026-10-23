"""Reproducible dataset factories used by tests and experiments."""
import random


def adversarial_ints(size: int, *, pivot: str = "lomuto_last") -> list[int]:
    """Generate ascending keys, a quadratic adversary for last-element Lomuto
    and first-element pivot strategies. Hoare's middle pivot handles it well.
    """
    if size < 0: raise ValueError("size must be non-negative")
    if pivot not in {"lomuto_last", "first"}: raise ValueError("unsupported pivot policy")
    return list(range(size))


def generate_dataset(size: int, distribution: str, *, seed: int = 0,
                     records: bool = False) -> list:
    """Create random, sorted, reverse, nearly-sorted, or Lomuto-adversarial data.

    Nearly sorted means shuffled integers with max(1, n//100) random pair
    swaps. Random keys use a bounded domain so duplicates are common.
    Record datasets contain transaction fields and use timestamp/amount/
    merchant as their common lexicographic sort key.
    """
    if size < 0: raise ValueError("size must be non-negative")
    rng = random.Random(seed)
    if distribution not in {"random", "sorted", "reverse", "nearly_sorted", "adversarial"}:
        raise ValueError(f"unknown distribution: {distribution}")
    if distribution == "adversarial":
        values = adversarial_ints(size)
    elif distribution == "random":
        values = [rng.randrange(max(1, size // 4)) for _ in range(size)]
    else:
        values = list(range(size))
        if distribution == "reverse": values.reverse()
        elif distribution == "nearly_sorted":
            for _ in range(max(1, size // 100) if size else 0):
                i, j = rng.randrange(size), rng.randrange(size)
                values[i], values[j] = values[j], values[i]
    if not records: return values
    merchants = ("Aster", "Birch", "Cedar", "Dahlia")
    return [{"timestamp": value, "amount": rng.randrange(1, 100_000),
             "merchant": merchants[rng.randrange(len(merchants))], "record_id": i}
            for i, value in enumerate(values)]


def transaction_key(record: dict) -> tuple:
    return record["timestamp"], record["amount"], record["merchant"]

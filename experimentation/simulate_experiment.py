"""Generate fictional checkout redesign data; these are not real customers."""

import argparse
from numbers import Integral
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from experimentation.sample_size import calculate_sample_size


CONTROL_PROBABILITY = 0.12
TREATMENT_PROBABILITY = 0.14
DEFAULT_SEED = 42
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent / "outputs" / "synthetic_checkout_experiment.csv"
)


def simulate_experiment(
    users_per_group: int | None = None,
    *,
    seed: int = DEFAULT_SEED,
) -> pd.DataFrame:
    """Return unique users with independent Bernoulli outcomes in equal arms.

    True generation probabilities are A=0.12 and B=0.14; observed rates will
    vary. The default count comes from Phase 1 (alpha=.05, power=.80).
    A local PCG64 generator draws all A outcomes first, then all B outcomes.
    Repeated calls with the same count, seed, and NumPy version reproduce
    the data and leave NumPy's global random state untouched.
    """
    if users_per_group is None:
        users_per_group = calculate_sample_size(
            CONTROL_PROBABILITY, TREATMENT_PROBABILITY,
        ).sample_size_per_group
    if (isinstance(users_per_group, bool)
            or not isinstance(users_per_group, Integral)
            or users_per_group <= 0):
        raise ValueError("users_per_group must be a positive integer.")
    if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
        raise ValueError("seed must be a non-negative integer.")

    count = int(users_per_group)
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    outcomes = np.concatenate([
        rng.binomial(1, CONTROL_PROBABILITY, size=count),
        rng.binomial(1, TREATMENT_PROBABILITY, size=count),
    ])
    return pd.DataFrame({
        "user_id": [f"synthetic_user_{i:06d}" for i in range(1, 2 * count + 1)],
        "variant": np.repeat(["A", "B"], count),
        "converted": outcomes,
    })


def main(argv: Sequence[str] | None = None) -> int:
    """Write synthetic user-level data to a CSV, overwriting the chosen file."""
    parser = argparse.ArgumentParser(
        description="Simulate a fictional e-commerce checkout A/B experiment.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--users-per-group", type=int, default=None,
                        help="Equal arm size; default uses the Phase 1 calculation")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help="PCG64 random seed")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Synthetic CSV output path")
    args = parser.parse_args(argv)
    try:
        data = simulate_experiment(args.users_per_group, seed=args.seed)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(args.output, index=False, encoding="utf-8", lineterminator="\n")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))

    print("SYNTHETIC DATA: fictional e-commerce checkout redesign experiment.")
    print(f"Users per group: {len(data) // 2}; total users: {len(data)}")
    print(f"True generation probabilities: A={CONTROL_PROBABILITY:.2f}, "
          f"B={TREATMENT_PROBABILITY:.2f} (not observed conversion rates)")
    print(f"Random generator: PCG64; seed: {args.seed}")
    print(f"Saved CSV: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

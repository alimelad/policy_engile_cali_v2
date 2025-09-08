# policy/rebates/flat_per_capita.py

def flat_per_capita_rebate(agi: float, hh_size: int, filing_status: str,
                           amount: float = 1700.0,
                           start_single: float = 50000.0,
                           start_mfj: float = 100000.0,
                           rate: float = 0.05) -> float:
    """
    Flat per-capita rebate:
      - Base = amount × household_size
      - Phase-out starts at:
          $50,000 for single/HOH
          $100,000 for MFJ
      - Tapers down at `rate` (default 5¢ per $1)
      - Floors at zero
    """
    base = amount * hh_size
    is_mfj = filing_status.lower() in {"mfj", "married_filing_jointly"}
    start = start_mfj if is_mfj else start_single

    if agi <= start:
        return base

    reduction = rate * (agi - start)
    return max(0.0, base - reduction)

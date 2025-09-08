# policy/rebates/poverty_times_vat.py

from policy.constants import poverty_threshold

def poverty_times_vat_rebate(agi: float, hh_size: int, vat_rate: float) -> float:
    """
    Poverty × VAT rebate:
      - Base = poverty_threshold(hh_size) × vat_rate
      - Full rebate for AGI ≤ 150% of poverty
      - Zero rebate for AGI ≥ 200% of poverty
      - Linear taper in between
    """
    base = poverty_threshold(hh_size) * float(vat_rate)
    start = 1.5 * poverty_threshold(hh_size)   # phase-out start
    end   = 2.0 * poverty_threshold(hh_size)   # phase-out end

    if agi <= start:
        return base
    if agi >= end:
        return 0.0

    # Linearly scale down between start and end
    frac = (end - agi) / (end - start)
    return max(0.0, base * frac)

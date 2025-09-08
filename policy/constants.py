# policy/constants.py

# Poverty thresholds for household sizes 1–7 (7 used for 7+)
POVERTY_THRESHOLDS = {
    1: 15650.0,
    2: 21150.0,
    3: 26650.0,
    4: 32150.0,
    5: 37650.0,
    6: 43150.0,
    7: 48650.0,  # use for 7 or more
}

def poverty_threshold(hh_size: int) -> float:
    """
    Return the poverty threshold for a household of given size.
    Caps at the 7+ value if hh_size >= 7.
    """
    return POVERTY_THRESHOLDS[7] if hh_size >= 7 else POVERTY_THRESHOLDS[hh_size]

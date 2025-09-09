# policy/vat_rebate.py
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Callable, Dict
# ----------------------------
#  constants
# ----------------------------
ALLOW_SINGLE  = {1:14580, 2:19720, 3:24860, 4:30000, 5:35140, 6:40280, 7:45420}
ALLOW_MARRIED = {2:29160, 3:34300, 4:39440, 5:44580, 6:49720, 7:54860}

THRESHOLDS  = {"single": 50_000.0, "mfj": 100_000.0}
PHASE_RANGE = {"single": 50_000.0, "mfj": 100_000.0}

assert THRESHOLDS["single"] + PHASE_RANGE["single"] == 100_000.0
assert THRESHOLDS["mfj"]    + PHASE_RANGE["mfj"]    == 200_000.0

# ----------------------------
# Flexible column detection
# ----------------------------
def _pick(cols: set[str], candidates: list[str], required=False) -> str | None:
    lower = {c.lower(): c for c in cols}
    for name in candidates:
        if name.lower() in lower:
            return lower[name.lower()]
    if required:
        raise KeyError(f"Required column not found; tried: {candidates}")
    return None

# ----------------------------
# Normalize arbitrary panels → simple household schema
# ----------------------------
def normalize_panel(df: pd.DataFrame) -> pd.DataFrame:
    """
    Output columns:
      household_id (optional),
      household_size (int),
      household_weight (float),
      is_married_couple (1 = MFJ-only, else 0),
      size_bucket (1..7, where 7 is 7+),
      household_agi (optional if present).
    """
    cols = set(df.columns)
    c_id   = _pick(cols, ["household_id","hh_id","hid"], required=False)
    c_size = _pick(cols, ["household_size","hh_size","household_members","family_size","HHSIZE"], required=True)
    c_wt   = _pick(cols, ["household_weight","weight","marsupwt","HHWT","hh_weight","asec_weight","cps_weight"], required=True)
    c_is_mar = _pick(cols, ["is_married_couple","married_couple","is_mfj_household"], required=False)
    c_mfj    = _pick(cols, ["mfj","is_mfj","filing_status_mfj"], required=False)
    c_single = _pick(cols, ["single","is_single","filing_status_single"], required=False)
    c_fs     = _pick(cols, ["filing_status","filingstatus","status"], required=False)
    c_agi    = _pick(cols, ["household_agi","hh_agi","agi_household","agi_hh","adjusted_gross_income","agi"], required=False)

    out = pd.DataFrame(index=df.index)
    if c_id is not None:
        out["household_id"] = df[c_id]

    out["household_size"]   = pd.to_numeric(df[c_size], errors="coerce")
    out["household_weight"] = pd.to_numeric(df[c_wt],   errors="coerce")

    # MFJ-only for married
    if c_is_mar is not None:
        out["is_married_couple"] = (pd.to_numeric(df[c_is_mar], errors="coerce").fillna(0) > 0).astype(int)
    elif c_mfj is not None:
        out["is_married_couple"] = (pd.to_numeric(df[c_mfj], errors="coerce").fillna(0) == 1).astype(int)
    elif c_fs is not None:
        fs = df[c_fs].astype(str).str.lower()
        is_mfj = (
            fs.str.contains("mfj")
            | fs.str.contains("joint")
            | (fs.str.contains("married") & ~fs.str.contains("separate") & ~fs.str.contains("mfs"))
        )
        out["is_married_couple"] = is_mfj.astype(int)
    elif c_single is not None:
        out["is_married_couple"] = (pd.to_numeric(df[c_single], errors="coerce").fillna(0) == 0).astype(int)
    else:
        raise KeyError("Need 'is_married_couple' or an MFJ indicator to classify households.")

    # Guard: MFJ households must be size>=2
    bad = (out["is_married_couple"] == 1) & (out["household_size"] < 2)
    if bad.any():
        out.loc[bad, "household_size"] = 2

    size_int = out["household_size"].fillna(1).astype(int)
    out["size_bucket"] = np.where(size_int >= 7, 7, np.maximum(1, size_int)).astype(int)

    if c_agi is not None:
        out["household_agi"] = pd.to_numeric(df[c_agi], errors="coerce")

    out = out.dropna(subset=["household_size","household_weight"]).copy()
    out["household_size"] = out["household_size"].astype(int)
    out["household_weight"] = out["household_weight"].astype(float)
    out["is_married_couple"] = out["is_married_couple"].astype(int)
    return out

# ----------------------------
# Allowance + phase-out
# ----------------------------
def _allow_single(n: int) -> float:
    return float(ALLOW_SINGLE.get(n, ALLOW_SINGLE[7]))

def _allow_married(n: int) -> float:
    return float(ALLOW_MARRIED.get(n if n >= 2 else 2, ALLOW_MARRIED[7]))

def compute_allowance(df: pd.DataFrame,
                      size_col: str = "size_bucket",
                      married_col: str = "is_married_couple",
                      out_col: str = "consumption_allowance") -> pd.DataFrame:
    sb = df[size_col].astype(int)
    is_m = df[married_col].astype(int) == 1
    allow = np.where(is_m, sb.map(_allow_married), sb.map(_allow_single))
    out = df.copy()
    out[out_col] = allow.astype(float)
    return out

def apply_phaseout(df: pd.DataFrame,
                   base_col: str = "consumption_allowance",
                   agi_col: str = "household_agi",
                   out_col: str = "rebate_after_phaseout") -> pd.DataFrame:
    if agi_col not in df.columns:
        raise KeyError("household_agi not found; attach/compute it before phaseout.")
    is_m = df["is_married_couple"].astype(int) == 1
    start = np.where(is_m, THRESHOLDS["mfj"],  THRESHOLDS["single"])
    width = np.where(is_m, PHASE_RANGE["mfj"], PHASE_RANGE["single"])
    excess = (df[agi_col].fillna(0).to_numpy() - start).clip(min=0)
    frac = (excess / width).clip(max=1)
    out = df.copy()
    out[out_col] = out[base_col].to_numpy() * (1 - frac)
    out["excess_over_threshold"] = excess
    return out

# ----------------------------
# Equivalized income & weighted quantiles
# ----------------------------
def equivalized_income(df: pd.DataFrame,
                       income_col: str = "household_agi",
                       size_col: str = "household_size",
                       method: str = "per_capita",
                       out_col: str = "equiv_income") -> pd.DataFrame:
    """
    method = 'per_capita' (agi / size)   [default]
           = 'sqrt'       (agi / sqrt(size))  — change if desired
    """
    inc = pd.to_numeric(df[income_col], errors="coerce").fillna(0.0)
    sz  = pd.to_numeric(df[size_col], errors="coerce").fillna(1.0).clip(lower=1.0)
    if method == "sqrt":
        eq = inc / np.sqrt(sz)
    else:
        eq = inc / sz
    out = df.copy()
    out[out_col] = eq.astype(float)
    return out

def _weighted_quantile(x: np.ndarray, w: np.ndarray, q: float) -> float:
    idx = np.argsort(x)
    xs, ws = x[idx], w[idx]
    c = np.cumsum(ws)
    if c[-1] <= 0:
        return float(np.nan)
    cutoff = q * c[-1]
    k = np.searchsorted(c, cutoff, side="left")
    k = min(max(k, 0), len(xs) - 1)
    return float(xs[k])

# ----------------------------
# Summaries and utilities
# ----------------------------
def households_by_size(df: pd.DataFrame) -> pd.DataFrame:
    tmp = df.copy()
    tmp["group"] = np.where(tmp["is_married_couple"] == 1, "Married Households", "Single Households")
    tmp["size_label"] = tmp["size_bucket"].map({1:"1",2:"2",3:"3",4:"4",5:"5",6:"6",7:"7 or more"})
    res = (tmp.groupby(["group","size_label"], as_index=False)["household_weight"].sum()
             .rename(columns={"household_weight":"hh_000s"}))
    res["hh_000s"] = res["hh_000s"] / 1_000
    order = {s:i for i,s in enumerate(["1","2","3","4","5","6","7 or more"])}
    res["__o"] = res["size_label"].map(order)
    return res.sort_values(["group","__o"]).drop(columns="__o")

def weighted_sum(x: pd.Series, w: pd.Series) -> float:
    return float((x.astype(float) * w.astype(float)).sum())

def add_weighted_deciles(df: pd.DataFrame, income_col: str, weight_col: str, label: str = "decile") -> pd.DataFrame:
    x = df[income_col].astype(float).to_numpy()
    w = df[weight_col].astype(float).to_numpy()
    if len(w) == 0 or np.sum(w) <= 0:
        df[label] = 1
        return df
    idx = np.argsort(x); xs = x[idx]; ws = w[idx]
    cw = np.cumsum(ws); total = cw[-1]
    cuts = [total*k/10 for k in range(1,10)]
    edges = [-np.inf]
    for c in cuts:
        i = np.searchsorted(cw, c, side="left")
        i = min(max(i, 0), len(xs)-1)
        edges.append(xs[i])
    edges.append(np.inf)
    df[label] = pd.cut(df[income_col].astype(float), bins=edges, labels=range(1,11), include_lowest=True)
    return df

def apply_income_tax_removal(df: pd.DataFrame, tax_cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in tax_cols:
        if c in out:
            out[c] = 0.0
    return out

def rebate_mtr_plus_one(df: pd.DataFrame, wages_col: str | None = None):
    """
    Rebate-only marginal response to +$1 AGI (proxying +$1 wages where wages>0).
    Returns (series_of_deltas, weighted_total_delta) using 'household_weight'.
    """
    if "household_agi" not in df:
        raise KeyError("household_agi missing for rebate MTR.")
    base = compute_allowance(df)
    base = apply_phaseout(base)
    cf = base.copy()
    if wages_col and (wages_col in cf):
        bump = cf[wages_col].fillna(0) > 0
        cf.loc[bump, "household_agi"] = cf.loc[bump, "household_agi"] + 1.0
    else:
        cf["household_agi"] = cf["household_agi"] + 1.0
    cf = compute_allowance(cf)
    cf = apply_phaseout(cf)
    d_rebate = cf["rebate_after_phaseout"] - base["rebate_after_phaseout"]
    weighted = float((d_rebate * base["household_weight"]).sum())
    return d_rebate, weighted

# --- 010 helpers ---

def wmean(series, weight):
    s = series.astype(float); w = weight.astype(float)
    tot = w.sum()
    return float((s * w).sum() / tot) if tot != 0 else float("nan")

def compute_after_tax_income(df: pd.DataFrame,
                             agi_col="household_agi",
                             fed_col="fed_income_tax",
                             state_col="ca_income_tax") -> pd.Series:
    # fed/state tax columns are NET of credits in our panel
    return df[agi_col].astype(float) - (df[fed_col].astype(float) + df[state_col].astype(float))

def mtr_plus_one_baseline(
    df: pd.DataFrame,
    compute_taxes_fn: Callable[[pd.DataFrame], pd.DataFrame],
    bump_on="employment_income",
    bump_amount=1.0,
    agi_col="household_agi",
    fed_col="fed_income_tax",
    state_col="ca_income_tax",
    weight_col="household_weight",
) -> pd.DataFrame:
    # Prepare base and bumped copies
    base = df.copy()
    base["__tax_base__"] = base[fed_col].astype(float) + base[state_col].astype(float)

    bump = base.copy()
    mask = bump[bump_on].astype(float) > 0
    bump.loc[mask, bump_on] = bump.loc[mask, bump_on].astype(float) + bump_amount
    bump.loc[mask, agi_col]  = bump.loc[mask, agi_col].astype(float)  + bump_amount

    # Recompute taxes on bumped DF 
    bumped_taxes = compute_taxes_fn(bump)  # must return fed_col, state_col aligned row-for-row
    for c in (fed_col, state_col):
        if c not in bumped_taxes.columns:
            raise KeyError(f"compute_taxes_fn must return '{c}'")
    bump[fed_col]  = bumped_taxes[fed_col].astype(float)
    bump[state_col] = bumped_taxes[state_col].astype(float)
    bump["__tax_bump__"] = bump[fed_col] + bump[state_col]

    out = base.copy()
    out["mtr_delta_tax"] = bump["__tax_bump__"].astype(float) - base["__tax_base__"].astype(float)
    return out

def decile_table(
    df: pd.DataFrame,
    group_col: str,
    cols: Dict[str, str],
    weight_col="household_weight",
) -> pd.DataFrame:
    rows = []
    for g, sub in df.groupby(group_col, sort=True):
        w = sub[weight_col].astype(float)
        row = {group_col: g, "pop_weight": float(w.sum())}
        for out_name, src in cols.items():
            s = sub[src].astype(float)
            if out_name.startswith("mean_"):
                row[out_name] = wmean(s, w)
            elif out_name.startswith("total_"):
                row[out_name] = float((s * w).sum())
        rows.append(row)
    return pd.DataFrame(rows)
# policy/baseline_taxes.py
from __future__ import annotations
import pandas as pd
import numpy as np
import yaml
from policyengine_us import Microsimulation

YEAR = 2024

def _load_colmap(path="../config/columns.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)

def _get_household_ids(sim: Microsimulation) -> tuple[pd.Series, pd.Series]:
    """
    Return (hh_ids_at_household, hh_ids_at_person) as Series with aligned labels.
    Prefer real household_id; fall back to household_index; finally size-expansion.
    """
    for var in ("household_id", "household_index"):
        try:
            hh_ids_hh = pd.Series(sim.calculate(var, map_to="household", period=YEAR, decode_enums=False))
            hh_ids_p  = pd.Series(sim.calculate(var, map_to="person",    period=YEAR, decode_enums=False))
            return hh_ids_hh, hh_ids_p
        except Exception:
            pass

    # Fallback: expand by household_size
    sizes = pd.Series(sim.calculate("household_size", map_to="household", period=YEAR, decode_enums=False)).astype(int)
    hh_ids_hh = pd.Series(np.arange(len(sizes), dtype=np.int64))
    hh_ids_p  = pd.Series(np.repeat(hh_ids_hh.to_numpy(), sizes.clip(lower=0).to_numpy()), dtype=np.int64)
    return hh_ids_hh, hh_ids_p

def run_baseline_taxes_2024(df_like: pd.DataFrame,
                            columns_yaml_path: str = "../config/columns.yaml") -> pd.DataFrame:
    """
    EXACT baseline recompute for household-level taxes after a +$1 wage bump,
    using *person-level* set_input so array lengths match the sim's person count.

    df_like: CA-only, AGI>=0 panel in Step-01 order. Must include 'employment_income'
             (already bumped by caller for HHs with wages>0).
    Returns: DataFrame aligned row-for-row with df_like:
             columns = ['fed_income_tax','ca_income_tax'] (floats, net of credits).
    """
    col_map = _load_colmap(columns_yaml_path)
    wages_var = col_map["wages"]

    # 1) Fresh simulation
    sim = Microsimulation()

    # 2) Step-01 mask (CA & non-negative AGI) to ensure ordering/length match
    state_code_hh = pd.Series(sim.calculate("state_code", map_to="household", period=YEAR, decode_enums=True))
    agi_hh        = pd.Series(sim.calculate(col_map["agi"], map_to="household", period=YEAR, decode_enums=False)).astype(float)
    mask_ca   = state_code_hh.astype(str).str.strip().str.upper().eq("CA")
    mask_agi  = (agi_hh >= 0.0)
    mask_keep = (mask_ca & mask_agi)

    n_sim_keep = int(mask_keep.sum())
    n_df       = int(len(df_like))
    if n_df != n_sim_keep:
        raise ValueError(
            "Row alignment mismatch: df_like rows != sim CA&AGI>=0 households.\n"
            f"df_like={n_df}, sim_keep={n_sim_keep}. Ensure df_like is CA-only, AGI>=0, Step-01 order."
        )

    # 3) IDs and baseline wages
    hh_ids_hh, hh_ids_p = _get_household_ids(sim)
    hh_ids_keep = hh_ids_hh[mask_keep].reset_index(drop=True)

    wages_hh_base = pd.Series(sim.calculate(wages_var, map_to="household", period=YEAR, decode_enums=False)).astype(float)
    wages_hh_keep = wages_hh_base[mask_keep].reset_index(drop=True)

    wages_p_base = pd.Series(sim.calculate(wages_var, map_to="person", period=YEAR, decode_enums=False)).astype(float)
    base_nonneg  = wages_p_base.clip(lower=0.0)

    # 4) Household deltas (target - baseline) from df_like
    target_hh = pd.to_numeric(df_like["employment_income"], errors="coerce").fillna(0.0).reset_index(drop=True)
    delta_hh  = (target_hh - wages_hh_keep).astype(float)

    # label deltas by household_id
    delta_by_hid = pd.Series(delta_hh.values, index=hh_ids_keep.values)

    # 5) Allocate to persons (proportional to baseline person wages; if all zero, assign to first person)
    sum_per_hh_on_person = base_nonneg.groupby(hh_ids_p).transform("sum")
    delta_hh_on_person   = hh_ids_p.map(delta_by_hid).astype(float).fillna(0.0)

    with np.errstate(divide="ignore", invalid="ignore"):
        delta_p = np.where(
            sum_per_hh_on_person.to_numpy() > 0.0,
            (base_nonneg.to_numpy() / np.where(sum_per_hh_on_person.to_numpy()==0.0, 1.0, sum_per_hh_on_person.to_numpy()))
            * delta_hh_on_person.to_numpy(),
            0.0
        )

    # If HH has zero baseline person wages but nonzero HH delta, put it on the first person in that HH
    sums_by_hh = base_nonneg.groupby(hh_ids_p).sum()
    zero_sum_hhs = [hid for hid, sm in sums_by_hh.items() if (sm == 0.0 and abs(delta_by_hid.get(hid, 0.0)) > 0.0)]
    if zero_sum_hhs:
        delta_p_series = pd.Series(delta_p)
        phid_vals = hh_ids_p.to_numpy()
        for hid in zero_sum_hhs:
            idx = np.where(phid_vals == hid)[0]
            if len(idx):
                delta_p_series.iloc[idx] = 0.0
                delta_p_series.iloc[idx[0]] = float(delta_by_hid.get(hid, 0.0))
        delta_p = delta_p_series.to_numpy()

    # 6) Apply person-level wages and recompute taxes
    wages_p_new = wages_p_base.to_numpy() + delta_p
    sim.set_input(wages_var, YEAR, wages_p_new)

    fed_all = pd.Series(sim.calculate(col_map["fed_tax"],   map_to="household", period=YEAR, decode_enums=False)).astype(float)
    sta_all = pd.Series(sim.calculate(col_map["state_tax"], map_to="household", period=YEAR, decode_enums=False)).astype(float)

    # Return CA & AGI>=0 slice in Step-01 order (row-for-row with df_like)
    return pd.DataFrame({
        "fed_income_tax": fed_all[mask_keep].reset_index(drop=True),
        "ca_income_tax":  sta_all[mask_keep].reset_index(drop=True),
    }).astype(float)

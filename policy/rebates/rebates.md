# Rebate Policy Modules

## Part A — What we’re doing

We implement two new rebate designs, both at the **household** level, as alternatives to the current VAT rebate:

1) **Poverty × VAT rebate**  
   Rebate = poverty threshold (by household size) × VAT rate.  
   Phase-out: begins at 150% of the poverty threshold, fully gone at 200%.  
   No marriage adjustment — only household size matters.

2) **Flat per-capita rebate**  
   Rebate = $1,700 × household size.  
   Phase-out thresholds: $50,000 AGI for singles/HOH, $100,000 for MFJ.  
   Phase-out slope: 5¢ per $1 of AGI above the threshold.  
   Floors at zero.

**Main outputs (from notebooks 07–08)**
- `outputs/rebates/poverty_times_vat/rebate_records.csv` — household-level rebates
- `outputs/rebates/poverty_times_vat/summary.csv` — totals & subgroup breakdowns
- `outputs/rebates/flat_per_capita/rebate_records.csv` — household-level rebates
- `outputs/rebates/flat_per_capita/summary.csv` — totals & subgroup breakdowns
- Plots (PNG) showing phase-out bands and decile distribution

---

## Part B — Inputs

- Panel from Step 01: `intermediate/ca_panel_2024.(parquet|csv)`  
  Must include: `household_agi`, `household_size`, `filing_status`, `household_weight`.

- Policy constants:
  - `policy/constants.py` — poverty thresholds (hardcoded 1–7+ values).
  - Config parameters:
    - `vat.rate`
    - `rebate.flat.amount = 1700`
    - `rebate.flat.phaseout.single_start = 50000`
    - `rebate.flat.phaseout.mfj_start = 100000`
    - `rebate.flat.phaseout.rate = 0.05`

---

## Part C — Methods

### C1. Poverty × VAT rebate
- For each household, compute base = `poverty_threshold(hh_size) × vat_rate`.
- If AGI ≤ 1.5×poverty → full base.
- If AGI ≥ 2.0×poverty → rebate = 0.
- In between: linearly interpolate.
- Aggregate totals with household weights; produce decile and status breakdowns.

### C2. Flat per-capita rebate
- For each household, compute base = `amount × hh_size`.
- Determine threshold:
  - Single/HOH → $50k
  - MFJ → $100k
- If AGI ≤ threshold → full base.
- If AGI > threshold → reduce by `rate × (AGI − threshold)`.
- Floors at zero.
- Aggregate totals and distribution the same way as above.

---

## Part D — Validation checks

- **Non-negativity**: no household gets a negative rebate.  
- **Monotonic taper**: rebates fall weakly as AGI rises.  
- **Phase-out boundaries**: exact values at 150%, 200% poverty (poverty × VAT) and at start + base/0.05 (flat).  
- **Totals consistency**: subgroup totals sum to the overall total.  
- **With-phase-out ≤ without-phase-out** for every group.

---

## Part E — Usage

Run the new notebooks:

- `07_poverty_times_vat_rebate.ipynb`  
  → saves household-level rebate records, summaries, and plots under `outputs/rebates/poverty_times_vat/`.

- `08_flat_per_capita_rebate.ipynb`  
  → saves analogous outputs under `outputs/rebates/flat_per_capita/`.

Both notebooks assume Step 01 panel and Step 02–06 calibrations have been run, and use the same logging/timing format.

---

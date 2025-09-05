# California VAT Rebate — 2024 Results (Household-level)

Scope: California households, calendar year 2024. We build a household panel from PolicyEngine’s household entity, exclude negative-AGI households, apply a uniform 11% downward deflator to household weights (Step 01), and group by equivalized income (AGI / household size). “Married Households” means MFJ-only, inferred from household spouse presence and Head-of-Household flags; “Single Households” covers all others (Single, MFS, HOH, Widow/er).

## Policy Scenario

- Replace: Individual income tax, corporate income tax, general & selective sales taxes, estate & gift tax (modeled here via income-tax removal; sales-tax dynamics handled off-model).
- Add: Per-household VAT rebate with phase-out by AGI.

### Consumption-allowance (poverty guideline) — constants used
Singles: 1→14,580; 2→19,720; 3→24,860; 4→30,000; 5→35,140; 6→40,280; 7+→45,420  
Married (MFJ): 2→29,160; 3→34,300; 4→39,440; 5→44,580; 6→49,720; 7+→54,860

Phase-out thresholds and bands (household-level):  
Singles: 50,000–100,000 • MFJ: 100,000–200,000

### Rebate formula
For household size n (capped at 7) and status S ∈ {Single, MFJ}:
- Base allowance A = table value for (S, n) above.
- excess = max(0, AGI − threshold_S)
- scale = max(0, 1 − excess / band_S)
- Rebate = A × scale

## Key 2024 Results

- Rebate totals:  
  No phase-out: $391,504,607,385  
  With phase-out: $283,828,897,363  
  Reduction from phase-out: $107,675,710,022

- Rebate-only MTR (+$1 wages experiment):  
  Population-weighted: 0.0754  
  Earnings-weighted: 0.1017

- Share of wages in phase-out bands:  
  Singles 50,000–100,000: 5.16%  
  MFJ 100,000–200,000: 21.72%

- MTR decomposition by status × size (see CSV for full table):  
  outputs/vat/mtr_slope_by_status_size_2024.csv

## Files

- Rebate totals: outputs/vat/rebate_cost_2024.csv  
- Rebate totals by decile: outputs/vat/rebate_cost_by_decile_2024.csv  
- Rebate totals by filing status: outputs/vat/rebate_cost_by_status_2024.csv  
- Rebate-only MTRs: outputs/vat/mtr_summary_2024.csv  
- Wage shares in phase-out bands: outputs/vat/wage_phaseout_shares_2024.csv  
- MTR slope and in-band shares by status × size: outputs/vat/mtr_slope_by_status_size_2024.csv  
- Distribution (baseline vs. no income tax + rebate): outputs/vat/distribution_2024.csv  
- Off-model VAT inputs: outputs/vat/sales_tax_inputs_2024.csv

## Method notes and assumptions

- Entity = household throughout; we exclude AGI < 0 households.  
- MFJ vs Single derived from household spouse presence (has_spouse / spouse_present / head_spouse_count) and HOH eligibility; we treat MFJ-only as “Married.”  
- Household weights are uniformly deflated by 11% in Step 01 to align overall size with external controls.  
- Grouping = equivalized income (AGI / household size) for deciles; includes Top 5% and Top 1% by the weighted distribution.  
- Phase-out bands are defined centrally in code (vat_rebate.py) and echoed here via Step 03 outputs.

Weighting note: Step 01 applied a uniform deflator of 0.89
to household weights (total 16,215,270 → 14,431,592).

# California VAT Rebate — 2024 Results (Household-level)

**Scope:** California households, calendar year 2024. We build a household panel from PolicyEngine’s household entity, exclude **negative AGI** households, and group by **equivalized income** (AGI / household size). *Married Households* means **MFJ-only**, inferred from household spouse presence and Head-of-Household flags; **Single Households** covers all others (Single, MFS, HOH, Widow/er).

## Policy Scenario

- **Replace**: Individual income tax, corporate income tax, general & selective sales taxes, estate & gift tax (modeled here via income-tax removal; sales-tax dynamics handled off-model).
- **Add**: Per-household VAT rebate with phase-out by AGI.

### Consumption-allowance (poverty guideline) — constants used
Singles: 1→14,580; 2→19,720; 3→24,860; 4→30,000; 5→35,140; 6→40,280; 7+→45,420  
Married (MFJ): 2→29,160; 3→34,300; 4→39,440; 5→44,580; 6→49,720; 7+→54,860

Phase-out thresholds: Single = 75,000; MFJ = 150,000  
Phase-out bands (width): Single = 50,000; MFJ = 100,000

### Rebate formula
For household size *n* (capped at 7) and status *S ∈ {Single, MFJ}*:
- **Base allowance A** = table value for (S, n) above.
- **excess** = max(0, AGI − threshold_S)
- **scale** = max(0, 1 − excess / band_S)
- **Rebate** = A × scale

## Key 2024 Results

- **Rebate totals**:  
  No phase-out: **$439,892,827,841**  
  With phase-out: **$345,335,469,784**  
  Reduction from phase-out: **$94,557,358,056**

- **Rebate-only MTR (+$1 wages experiment)**:  
  Population-weighted: **0.0294**  
  Earnings-weighted: **0.0855**

- **Share of wages in phase-out bands**:  
  Singles 75–125k: **4.63%**  
  MFJ 150–200k: **9.91%**

## Files

- Rebate totals: `outputs/vat/rebate_cost_2024.csv`  
- Rebate totals by decile: `outputs/vat/rebate_cost_by_decile_2024.csv`  
- Rebate totals by filing status: `outputs/vat/rebate_cost_by_status_2024.csv`  
- Rebate-only MTRs: `outputs/vat/mtr_summary_2024.csv`  
- Wage shares in phase-out bands: `outputs/vat/wage_phaseout_shares_2024.csv`  
- Distribution (baseline vs. no income tax + rebate): `outputs/vat/distribution_2024.csv`  
- Off-model VAT inputs: `outputs/vat/sales_tax_inputs_2024.csv`

## Method notes and assumptions

- Entity = **household** throughout; we exclude **AGI < 0** households.  
- **MFJ vs Single** derived from household spouse presence (`has_spouse` / `spouse_present` / `head_spouse_count`) and HOH eligibility; we treat MFJ-only as “Married.”  
- Grouping = **equivalized income** (AGI / household size) for deciles; we also report **Top 5%** and **Top 1%** by the weighted distribution.  
- Rebate constants are **hard-coded** per spec above.


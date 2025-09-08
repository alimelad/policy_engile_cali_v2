# Rebate Results — 2024 (Household-level)

This page summarizes outputs from:

- **07_poverty_times_vat_rebate.ipynb** → `outputs/rebates/poverty_times_vat/`
- **08_flat_per_capita_rebate.ipynb** → `outputs/rebates/flat_per_capita/`

## Poverty × VAT (2024)

- VAT rate: 0.1
- No phase-out total: $33,733,976,971
- With phase-out total: $12,508,775,845
- Reduction from phase-out: $21,225,201,127

Files:
- Records: `outputs/rebates/poverty_times_vat/rebate_records_2024.csv`
- Summary: `outputs/rebates/poverty_times_vat/summary_2024.csv`
- By decile: `outputs/rebates/poverty_times_vat/by_decile_2024.csv`
- By size: `outputs/rebates/poverty_times_vat/by_size_2024.csv`
- Plot: `outputs/rebates/poverty_times_vat/plots/deciles_2024.png`

## Flat per-capita (2024)

- Amount per person: $1,700
- Single start: $50,000
- MFJ start: $100,000
- Phase-out rate: 0.05
- No phase-out total: $59,234,433,120
- With phase-out total: $44,222,171,752
- Reduction from phase-out: $15,012,261,368

Files:
- Records: `outputs/rebates/flat_per_capita/rebate_records_2024.csv`
- Summary: `outputs/rebates/flat_per_capita/summary_2024.csv`
- By decile: `outputs/rebates/flat_per_capita/by_decile_2024.csv`
- By size: `outputs/rebates/flat_per_capita/by_size_2024.csv`
- By status: `outputs/rebates/flat_per_capita/by_status_2024.csv`
- Plot: `outputs/rebates/flat_per_capita/plots/deciles_2024.png`

## Notes

- All totals are **household-weighted**. Deciles are computed on **AGI per capita** (AGI ÷ household size).
- Both policies enforce **non-negativity** and **monotone phase-out** by construction.
- Phase-outs ensure **with-phase-out ≤ no-phase-out** totals by group and overall.

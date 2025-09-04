Thought for 36s
California VAT Rebate Analysis — Working Spec & Debug Prompt (2024)

Version: 2025-09-04
Repo: policyengine-us-ali-cali-v2
Branch (typical): feature/ca-vat-rebate-2024
Primary module: policy/vat_rebate.py
Primary notebooks (2024):

notebooks/00_repo_audit_and_config_2024.ipynb

notebooks/01_data_prep_ca_2024.ipynb

notebooks/02_rebate_costs_2024.ipynb

notebooks/03_mtr_labor_plus_one_2024.ipynb

notebooks/04_distribution_baseline_vs_noiit_rebate_2024.ipynb

notebooks/05_sales_tax_offmodel_inputs_2024.ipynb

notebooks/06_results_rollup_and_pr_2024.ipynb

Key outputs: outputs/vat/*.csv
Intermediate data: intermediate/*.csv (Parquet if available)
Config: config/columns.yaml

1) Project goal (what we’re trying to do)

Implement a California-only VAT rebate analysis that reproduces Kyle’s policy scenario using our PolicyEngine household microdata, then produce reproducible outputs and diagnostics for 2024 (with the option to extend to 2025 later). Specifically:

Replace: individual income tax, corporate income tax, general & selective sales taxes, estate & gift tax (in-model we remove income taxes; sales taxes are handled off-model via inputs).

Add: a per-household VAT rebate equal to a consumption allowance that phases out by AGI at the household level.

Produce totals and distributions that are consistent with our CA sample, weights, and grouping conventions.

Incorporate recent additions/requirements:

Exclude negative AGI households from the analysis universe.

Classify Married as MFJ-only using household spouse signals and Head-of-Household (HOH), not tax-unit filing status.

Use equivalized income (AGI / household size) for decile grouping.

Add Top 5% and Top 1% groups to the distribution table.

Include diagnostics for household size × status counts to sanity-check the allowance attachment.

2) Policy definition (constants and formulas)

Consumption-allowance (poverty guideline) — use verbatim

Singles (cap size ≥7 to 7):
ALLOW_SINGLE = {1:14580, 2:19720, 3:24860, 4:30000, 5:35140, 6:40280, 7:45420}

Married (MFJ):
ALLOW_MARRIED = {2:29160, 3:34300, 4:39440, 5:44580, 6:49720, 7:54860}

Phase-out (household level, based on household AGI):

Thresholds: THRESHOLDS = {single: 75_000, mfj: 150_000}

Band widths: PHASE_RANGE = {single: 50_000, mfj: 100_000}

Formulas (household i)
Let size_i be capped at 7; status_i ∈ {single, mfj}; A_i = allowance(size_i, status_i)
excess_i = max(0, AGI_i − threshold_status)
scale_i = max(0, 1 − excess_i / band_status)
Rebate_i = A_i × scale_i

3) Data and variable mapping

We build everything from the household entity via PolicyEngine’s Microsimulation.calculate(..., map_to="household"). We infer concrete variable names (because they differ across builds) and write them to config/columns.yaml.

Detected/required fields (household level):

AGI: e.g., adjusted_gross_income

Wages: e.g., employment_income

Household size: e.g., household_size

Weight: e.g., household_weight

Federal income tax: income_tax

CA income tax: ca_income_tax

Filing status: we do not trust tax-unit status; we derive MFJ vs Single using household spouse signals and HOH.

Spouse/HOH signals (household level, any that exist):

has_spouse, spouse_present, head_spouse_count (≥2 ⇒ couple),

head_of_household_eligible (⇒ treat as single).

California filter: state_code ∈ {"CA"} (fallbacks to state_name, state_abbr; FIPS 6 if needed).

Negative AGI exclusion: drop households with household_agi < 0.

4) Core module: policy/vat_rebate.py (what it provides)

normalize_panel(df) → returns a clean household schema with:

household_size, household_weight, is_married_couple (MFJ-only), size_bucket (1..7), optional household_agi

compute_allowance(df) → adds consumption_allowance using size_bucket + is_married_couple

apply_phaseout(df) → adds rebate_after_phaseout and excess_over_threshold using household_agi

households_by_size(df) → weighted table of households by size × status (for diagnostics)

weighted_sum(x, w); add_weighted_deciles(df, income_col, weight_col, label); helpers for basic math and grouping.

Important assumptions embedded in the module:

Married means MFJ-only (others including HOH/MFS => Single).

size_bucket caps at 7.

Rebate computation requires household_agi to be present.

Deciles are computed on equivalized income (AGI / size) in the notebooks.

5) Notebooks — what each one does, and where files land
00_repo_audit_and_config_2024.ipynb

Detects real column names from PolicyEngine for AGI, wages, size, weight, fed tax, state tax.

Writes config/columns.yaml with the resolved mapping.

Sanity-checks: CA sample size > 0, basic fields non-missing.

Writes:

config/columns.yaml

01_data_prep_ca_2024.ipynb

Loads mapping; pulls household arrays for 2024.

Filters to CA.

Derives filing_status: HOH ⇒ single; else spouse present ⇒ mfj; else single.

Builds is_married_couple (MFJ-only), size_bucket (cap 7), household_agi.

Excludes negative AGI households.

Computes consumption_allowance and rebate_after_phaseout (adds allowance_no_phaseout, allowance_phaseout for compatibility).

Prints household size × status weighted table (in thousands).

Saves the panel (Parquet; falls back to CSV if pyarrow/fastparquet is missing).

Writes:

intermediate/ca_panel_2024.parquet or intermediate/ca_panel_2024.csv

02_rebate_costs_2024.ipynb

Reads the panel, ensures allowance & phaseout present (recomputes if needed).

Statewide totals: no phase-out vs with phase-out.

By decile: uses equivalized income (AGI / size).

By filing status: sums by mfj vs single.

Writes:

outputs/vat/rebate_cost_2024.csv

outputs/vat/rebate_cost_by_decile_2024.csv

outputs/vat/rebate_cost_by_status_2024.csv

03_mtr_labor_plus_one_2024.ipynb

Rebate-only marginal tax rate from the phase-out:

For households with wages > 0, add +$1 to household_agi, recompute rebate, set MTR = −Δrebate.

Reports population-weighted and earnings-weighted average MTRs.

Wage shares in phase-out bands: Singles 75–125k; MFJ 150–200k.

Writes:

outputs/vat/mtr_summary_2024.csv

outputs/vat/wage_phaseout_shares_2024.csv

04_distribution_baseline_vs_noiit_rebate_2024.ipynb

Baseline burden: fed_income_tax + ca_income_tax.

Reform burden: − rebate_after_phaseout (income taxes removed; rebate added).

Groups by equivalized income deciles and adds Top 5% and Top 1%.

Outputs mean burdens, mean change, share of total change, population shares.

Writes:

outputs/vat/distribution_2024.csv

05_sales_tax_offmodel_inputs_2024.ipynb

Creates off-model inputs by decile:

Weighted households, AGI sum, wages sum,

consumption_allowance_sum, rebate_after_phaseout_sum (handy proxies).

Used for external VAT/sales tax incidence modeling.

Writes:

outputs/vat/sales_tax_inputs_2024.csv

06_results_rollup_and_pr_2024.ipynb

Confirms presence of all expected CSVs.

Prints a mini-dashboard: totals, MTRs, wage shares, distribution preview, off-model preview.

Writes documentation at docs/README_VAT.md.

Optional: creates a git branch and commit; prints PR title/body.

Writes:

docs/README_VAT.md

Optional git branch/commit: feature/ca-vat-rebate-2024

6) Expected columns on the panel (intermediate/ca_panel_2024.*)

At minimum:

state_code (or equivalent, normalized to “CA” for this sample)

household_size (integer; used for equivalization and size_bucket)

household_weight (float; used as universal weight)

household_agi (float; non-negative after exclusion)

employment_income (float; used for wage conditions in MTR)

fed_income_tax, ca_income_tax (baseline comparison)

filing_status (string: “mfj” / “single”, derived from spouse/HOH)

is_married_couple (0/1; MFJ-only)

size_bucket (1..7)

consumption_allowance, rebate_after_phaseout, excess_over_threshold

Compatibility aliases: allowance_no_phaseout, allowance_phaseout

7) Acceptance checks & invariants

CA sample present: len(panel) > 0 and state_code == "CA".

Negative AGI excluded: household_agi >= 0 for all rows.

Allowance sanity: consumption_allowance >= rebate_after_phaseout row-wise.

Totals add up: by-decile totals sum to statewide totals (both no-phase and phase).

Decile coverage: population shares across 10 deciles ≈ 100%.

MTR bounds: rebate-only MTRs are finite; shares in phase-out bands ∈ [0, 1].

Singles at sizes > 1: weighted table shows Singles present beyond size 1 (given HOH and non-MFJ).

8) Common failure modes and how to debug

Missing Parquet engine
Symptom: Parquet save/read errors.
Action: The notebooks already fall back to CSV; see intermediate/ca_panel_2024.csv.

No weight column for Step 02/03
Symptom: Missing required columns: ['weight'].
Action: We normalize from household_weight → weight at read time. Ensure this normalization code is present.

All filers show as Single or as MFJ only
Symptom: Filings skewed; singles not appearing at sizes > 1.
Action: Step 01 derives filing status from household spouse signals (has_spouse / spouse_present / head_spouse_count) and HOH. The code prints which spouse signal was used. Check those series for reasonable distributions.

Large rebate totals
Symptom: Statewide totals look too high.
Action:

Inspect household size × status weighted counts (Step 01 prints a table in thousands).

Check consumption_allowance distribution by size and status.

Confirm negative AGI exclusion happened (Step 01 prints excluded count).

Confirm decile totals sum to statewide totals (Step 02 has assertions).

Distribution table off
Symptom: Pop shares not summing to ~100.
Action: Ensure equiv_income = AGI / household_size and deciles were formed with weighted deciles. Verify household_size > 0 and weights > 0.

9) How to re-run (2024)

Run notebooks/00_repo_audit_and_config_2024.ipynb → writes config/columns.yaml.

Run notebooks/01_data_prep_ca_2024.ipynb → writes intermediate/ca_panel_2024.(parquet|csv).

Run notebooks/02_rebate_costs_2024.ipynb → writes outputs/vat/rebate_cost_*.csv.

Run notebooks/03_mtr_labor_plus_one_2024.ipynb → writes MTR and wage-shares CSVs.

Run notebooks/04_distribution_baseline_vs_noiit_rebate_2024.ipynb.

Run notebooks/05_sales_tax_offmodel_inputs_2024.ipynb.

Run notebooks/06_results_rollup_and_pr_2024.ipynb → writes docs and prepares commit/PR.

10) Prompts you can reuse with an AI assistant

“Open policy/vat_rebate.py. Verify that compute_allowance uses size_bucket and is_married_couple to pick from ALLOW_SINGLE/ALLOW_MARRIED, with size capped at 7.”

“In 01_data_prep_ca_2024.ipynb, print the weighted table of household size by status. Confirm Singles appear for sizes > 1 and the totals look reasonable.”

“In 02_rebate_costs_2024.ipynb, confirm that decile totals sum to statewide totals for both no-phase and phase-out and that all phase-out totals are ≤ no-phase totals.”

“In 03_mtr_labor_plus_one_2024.ipynb, recompute rebate-only MTRs and report both population- and earnings-weighted averages.”

“In 04_distribution_baseline_vs_noiit_rebate_2024.ipynb, ensure the Top 5% and Top 1% groups are formed from weighted percentiles of equivalized income.”

“In 05_sales_tax_offmodel_inputs_2024.ipynb, show decile rows and confirm no missing values in AGI, wages, or weights.”

11) Known limitations and to-do

The distribution treats “Married Households” as MFJ-only; MFS/HOH are treated as Singles. If you later need MFS/HOH as separate groups, we’ll need additional signals.

We model income-tax removal directly. Sales-tax interactions are off-model; we provide inputs (sales_tax_inputs_2024.csv) for external incidence/consumption modeling.

We rely on household-level AGI and spouse signals; if a build lacks these, update 01_data_prep_ca_2024.ipynb with alternative candidates.

Parquet is optional; install pyarrow or fastparquet for speed/size benefits.

File index (quick reference)

Module: policy/vat_rebate.py

Config: config/columns.yaml

Intermediates: intermediate/ca_panel_2024.parquet (or .csv)

Outputs:

outputs/vat/rebate_cost_2024.csv

outputs/vat/rebate_cost_by_decile_2024.csv

outputs/vat/rebate_cost_by_status_2024.csv

outputs/vat/mtr_summary_2024.csv

outputs/vat/wage_phaseout_shares_2024.csv

outputs/vat/distribution_2024.csv

outputs/vat/sales_tax_inputs_2024.csv

Docs: docs/README_VAT.md

Roll-up: notebooks/06_results_rollup_and_pr_2024.ipynb

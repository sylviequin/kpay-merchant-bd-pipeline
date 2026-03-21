# kpay-merchant-bd-pipeline

**KPay Ltd Australia — Merchant Business Development Data Pipeline**

End-to-end data cleaning, segmentation, and BD strategy framework built on a 200k-row Google Maps merchant scrape. Transforms raw, messy data into a clean, tiered outreach-ready dataset for the KPay Australia sales team.

---

## Project Overview

| Item | Detail |
|------|--------|
| **Dataset** | `Case_Study.csv` — 199,999 merchants scraped from Google Maps, NSW-heavy |
| **Final output** | 190,684 clean records (95.3% retained) |
| **Stack** | Python · pandas · reportlab · Jupyter |
| **Status** | Part 1 complete · Part 2–3 in progress |

---

## Repository Structure

```
kpay-merchant-bd-pipeline/
├── notebooks/
│   ├── Cleaning_process.ipynb      # Step-by-step cleaning walkthrough
│   └── Cleaning_script.ipynb       # Clean pipeline script version
├── scripts/
│   └── clean_kpay_pandas.py        # Standalone cleaning script
├── outputs/
│   ├── cleaned_Kpay_data.csv
│   ├── kpay_part1_qa_report.pdf
│   └── kpay_Qa_summary.json
├── docs/
│   ├── kpay_BD_Checklist.html
│   └── KPay_BD_Checklist_v4.md
├── .gitignore
└── README.md
```

---

## Data

`Case_Study.csv` is not tracked in this repository — 30MB exceeds the recommended per-file limit.

Place it in the project root before running the pipeline.

> **Source:** Internal KPay dataset — request access from the data team.

---

## Part 1 — Data Cleaning

Column-by-column cleaning using pandas. Each function is fully self-contained — cells can run independently in any order.

| Step | Column | Key Action |
|------|--------|------------|
| 1 | `phone` | Reconstruct scientific notation from `lead_key`; normalise all formats; flag foreign numbers |
| 2 | `state` | Normalise long-form names; infer from address text; exclude US/invalid codes |
| 3 | `suburb` | Extract from address using 7 regex patterns — 75,711 recovered from 105k blanks |
| 4 | `address` | Remove duplicated words (`Sydney Sydney NSW → Sydney NSW`) |
| 5 | `business_name` | Recover 9 blank names via address→name dict; strip pipe-route suffixes |
| 6 | `sector_level_1` | Merge 147 fragmented labels → 9 canonical values |
| 7 | `sector_level_2` | Fill blank with `'Other'` |
| 8 | `sector_level_3` | Merge duplicate labels via `_S3_MAP` |

**Manipulation phase:**

```python
reformed_df = df[df['address'] != ''].reset_index(drop=True)            # −54
reformed_df = reformed_df.drop_duplicates(subset='phone', keep='first') # −590
reformed_df = reformed_df[reformed_df['state'].isin(AU_STATES)]          # −8,671
# Final: 190,684 rows
```

---

## Part 2 — BD Segmentation

Tiering order: **Sector → Location → Data Completeness**

| Tier | Target Sectors | Approach |
|------|----------------|----------|
| Tier 1 | F&B · Beauty & Wellness · Retail · Professional Services | Senior BD reps — in-person walk-in |
| Tier 2 | Automotive · Suburban Retail | Phone + email sequence |
| Tier 3 | Others · Uncategorised · Regional NSW | Nurture / brand awareness |

---

## Part 3 — Dashboard (Tableau)

Five metrics: Lead Distribution by Tier · Contacts/Week · Outreach Split · Heatmap by Zone · Lead Core Distribution by Sector.

---

## Quickstart

```bash
git clone https://github.com/<your-username>/kpay-merchant-bd-pipeline.git
cd kpay-merchant-bd-pipeline
pip install pandas openpyxl reportlab

# Place Case_Study.csv in project root, then:
python scripts/clean_kpay_pandas.py
```

---

*Author: Quynh Huong Nguyen (Sylvie)· March 2026*

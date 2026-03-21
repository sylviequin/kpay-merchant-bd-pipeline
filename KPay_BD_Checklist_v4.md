# KPay Ltd Australia — Merchant BD Project Checklist v4
### Dataset: `Case_Study.csv` — 199,999 records · 10 columns · Google Maps scrape
### Status: Part 1 COMPLETE |  Part 2 Pending | Part 3 Pending

---

## Part 1: Data Cleaning & Enrichment  COMPLETE

> **Script:** `NOTEBOOD.ipynb` — pandas, column-by-column
> **Deliverables:** `kpay_merchants_cleaned.csv` · `kpay_part1_qa_report.pdf`

---

### 1.1 Data Load & Setup

- [x] Load raw CSV with `dtype=str, encoding="utf-8-sig"` → `merchant` (199,999 rows)
- [x] Copy to working `df = merchant.copy()` — original untouched
- [x] Add `qa_flags` and `exclude_reason` working columns
- [x] Confirm nulls per column: `suburb` (105,011), `sector_level_1/2` (37,770), `address` (54), `business_name` (9)

---

### 1.2 Data Cleaning Steps

### 1.2.a Reformatting & Correction (NOTEBOOD.ipynb cells)

#### Step 1 — `phone`
- [x] Reconstruct scientific notation (`6.113E+11`) from `lead_key` — **381 records**
- [x] Normalise `+61` prefix → local format (`04xx xxx xxx` / `(0x) xxxx xxxx`) — **79,230 records**
- [x] Normalise bare `61XXXXXXXXX` → local format — **8,634 records**
- [x] Flag foreign numbers (`+44`, `+27`, `+64`, `+1`) as `"foreign number"` — **6,876 records**
- [x] Format 1300/1800 freecall correctly — strip leading-zero artefact
- [x] Flag values: `ok` · `local number` · `normalised` · `reconstructed` · `foreign number`

#### Step 2 — `state`
- [x] Mark valid AU codes (`NSW/VIC/QLD/WA/SA/ACT/TAS/NT`) as `"valid"` — **190,485 records**
- [x] Normalise long-form names (`New South Wales` → `NSW`) as `"lowercase"` — **556 records**
- [x] Infer from address/suburb text as `"address inferred"` — **234 records**
- [x] Flag US/invalid codes as `"invalid"` — **623 records**
- [x] Flag unresolvable blanks as `"blank_unresolved"` — **8,101 records**
- [x] `INVALID_STATES` set covers: US states + `APAC`, `AMM`, `ATM`, `ATT`, `HOP`, `BPM`, `PTD`, `STE`, `NEX`, `BG`, `GD`, `AU`, `IGO`

#### Step 3 — `suburb`
- [x] Apply Title Case to existing values — **41,392 records**
- [x] Extract suburb from address using 7 ordered regex patterns — **75,711 recovered**
- [x] Flag unrecoverable blanks as `"blank_unresolved"` — **29,300 remaining**
- [x] 7 patterns cover: `, Suburb STATE`, `, Suburb, Long-Form State`, `, Suburb, STATE digit`, `Suburb STATE POSTCODE`, `Suburb,POSTCODE,STATE`, `Suburb,STATE,POSTCODE`, last-word-group before state (road-word filtered)

#### Step 4 — `address`
- [x] Fix duplicated words: `Sydney Sydney NSW` → `Sydney NSW` — **6,037 records**
- [x] Fix duplicated state codes: `NSW NSW` → `NSW`
- [x] Blank address returns `np.nan` (flag for drop in manipulation phase) — **54 records**

#### Step 5 — `business_name`
- [x] Identify 9 blank business name rows
- [x] Manually map `address → business_name` via `add_dict_name` dict:
  - [x] Domino's Pizza Edensor Park
  - [x] Hemlock Mall
  - [x] Parking Car Lot
  - [x] Bianchini's Eloura Beach
  - [x] JB Hi-Fi Macquarie
  - [x] Construction Building
  - [x] Warriewood Automotive Service PTY LTD
  - [x] Greater West Exercise Physiology (×2 rows — same address)
  - [x] Mr O Wholefoods
- [x] `df.loc[missing_name, 'business_name'] = df.loc[missing_mask, 'address'].map(add_dict_name)`
- [x] All 9 blanks resolved → **0 blank business names remaining**

#### Step 6 — `sector_level_1`
- [x] Merge 147 unique labels → 9 canonical values using `_S1_MAP` dict
- [x] Canonical taxonomy: `F&B` · `Retail` · `Beauty & Wellness` · `Professional Services` · `Automotive` · `Others` · `Nightlife` · `Florists` · `Uncategorised`
- [x] Blank → `"Uncategorised"` with `was_blank` flag — **37,770 records**
- [x] Merged values — **8,879 records**
- [x] **Result: 147 → 9 unique Sector L1 values**

#### Step 7 — `sector_level_2`
- [x] `df['sector_level_2'] = df['sector_level_2'].fillna('Other')` — simple fill
- [x] Blank/NaN → `'Other'`

#### Step 8 — `sector_level_3`
- [x] Apply `_S3_MAP` merge dict for duplicate L3 labels
- [x] Covers: Quick-Service / Takeaway · Medical & Dental · Spa & Massage · Beauty Salon / Barber · Gym / Fitness / Yoga · Fashion & Accessories · Bottle Shop / Liquor · Hotel / Motel / Accommodation · Automotive Services · Cafe & Dessert · Nail Salon · Grocery / Convenience Store · Physiotherapy & Allied Health · Bar / Pub / Nightlife
- [x] Blank L3 inherits parent sector context (L1+L2 = Others/Others → flagged for keyword triage)

---

### 1.2.b Data Manipulation Phase (`reformed_df = df.copy()`)

| Action | Rows Removed | Rationale |
|--------|-------------|-----------|
| Drop blank `address` | **54** | Uncontactable — no street info, suburb uninferable |
| Drop duplicate `phone` (`keep='first'`) | **590** | 590 phone numbers appearing on 1,180 rows → same number = noise |
| Filter `state` to `AU_STATES` only | **8,671** | Removes blank states, invalid codes, foreign locations |
| **Total removed** | **9,315** | **4.7% of input** |

- [x] `reformed_df[reformed_df['address'] != ''].reset_index(drop=True)` — drop 54 blank address rows
- [x] `reformed_df.drop_duplicates(subset='phone', keep='first').reset_index(drop=True)` — drop 590 duplicate phone rows
- [x] Diagnostic: `blank_view[['street','country']]` — confirmed blank-state rows are non-AU (Canada, NZ etc.)
- [x] `reformed_df[reformed_df['state'].isin(AU_STATES)].reset_index(drop=True)` — final AU filter
- [x] **Final clean dataset: 190,684 rows · 8 AU states confirmed**

#### Final Row Reconciliation

| Stage | Rows | Removed |
|-------|------|---------|
| Raw input | 199,999 | — |
| After drop blank address | 199,945 | −54 |
| After drop duplicate phone | 199,355 | −590 |
| After AU state filter | **190,684** | −8,671 |

#### Final Output
- [x] Export cleaned file as `cleaned_Kpay_dataset.csv`
- [x] Produce a **QA Summary Report**: rows removed, rows modified, rows flagged per issue type

---

### 1.2.c Data Quality Issues — Classification by DQ Dimension

> Three-layer framework applied to every issue found in `Case_Study.csv`:
> - **Syntactic DQ** — the value violates format or structural rules (wrong shape, wrong type)
> - **Semantic DQ** — the value is structurally valid but wrong in meaning or context
> - **Pragmatic DQ** — the value is technically correct but unusable or irrelevant for the intended business purpose

| # | Column | Issue | DQ Dimension | Definition | How Addressed |
|---|--------|-------|-------------|------------|---------------|
| 1 | `phone` | Scientific notation (`6.113E+11`) | **Syntactic** | Value stored as float notation instead of a string — unreadable as a contact number | Reconstructed from `lead_key` digit extraction |
| 2 | `phone` | Mixed formats (`+61`, `04xx`, `(0x)`, bare `61`) | **Syntactic** | Same information type in inconsistent structural formats across the column | Normalised to `04xx xxx xxx` / `(0x) xxxx xxxx` / `1300 xxx xxx` |
| 3 | `phone` | Foreign numbers (`+44`, `+27`, `+64`, `+1`) | **Pragmatic** | Valid number in correct country format but outside Australia — irrelevant for KPay AU BD outreach | Flagged `foreign number`; removed in AU state filter |
| 4 | `phone` | Duplicate phone shared by multiple business names | **Semantic** | Same number mapped to different businesses — phone-to-merchant relationship is ambiguous | `drop_duplicates(subset='phone', keep='first')` |
| 5 | `state` | US / invalid codes (`NY`, `CA`, `APAC`, `AMM`) | **Semantic** | Formatted correctly as short codes but refer to wrong geography — not Australian states | Excluded via `AU_STATES` filter |
| 6 | `state` | Long-form names (`New South Wales`, `Victoria`) | **Syntactic** | Semantically correct but inconsistent with the expected 2-letter code format | Normalised via `LONGFORM` dict → `NSW`, `VIC` etc. |
| 7 | `state` | Blank values (8,335) | **Semantic** | Missing state does not mean "no state" — scraper failure; the merchant has a location | Inferred from address text (234 recovered); remainder flagged |
| 8 | `suburb` | 105,011 blank values (52.5%) | **Pragmatic** | Syntactically absent but address often contains the suburb — extraction failure, not true missing data; reduces geographic routing utility | 7-pattern regex extraction from `address` → 75,711 recovered |
| 9 | `suburb` | All-lowercase values (`sydney`, `surry hills`) | **Syntactic** | Correct in content but violate Title Case convention — inconsistent casing breaks string matching | `.title()` applied across column |
| 10 | `address` | Duplicated words (`Sydney Sydney NSW`, `NSW NSW`) | **Syntactic** | Scraper concatenated the same token twice — internally inconsistent; fails address-validation APIs | Regex word-deduplication |
| 11 | `address` | 54 blank values | **Pragmatic** | Address-less merchant cannot be visited by field BD rep and suburb cannot be inferred | Dropped in manipulation phase |
| 12 | `business_name` | 9 blank values | **Pragmatic** | Nameless merchant cannot be pitched — BD reps cannot approach without knowing the name | Manually recovered via `address → name` mapping dict (9/9 resolved) |
| 13 | `business_name` | Pipe-appended route suffixes (`Name \| City to City`) | **Semantic** | Pipe suffix is a Google Maps description artefact — misrepresents business identity in CRM | `re.sub(r'\s*\|\s*.+$', '', n)` |
| 14 | `business_name` | Junk listings (hotlines, charities, bare phone numbers) | **Pragmatic** | Structurally valid strings but non-commercial entities that will never convert — wastes BD rep time | Excluded via `_JUNK_RE` + `_JUNK_EXACT` patterns |
| 15 | `sector_level_1` | 147 unique values for ~9 logical categories | **Syntactic** | Taxonomy is fragmented — same semantic category exists under multiple surface forms (`F&B`, `Food & Drink`, `Restaurants` etc.) | Merged to 9 canonical values via `_S1_MAP` |
| 16 | `sector_level_1` | 37,770 blank values (18.9%) | **Semantic** | Blank sector does not mean "no sector" — scraper returned no category; the merchant has an industry, it is simply unknown | Relabelled `Uncategorised`; flagged for keyword triage |
| 17 | `sector_level_2` | 91,005 values labelled `Others` (45.5%) | **Pragmatic** | Value is present and neutral, but provides no actionable BD segmentation signal — nearly half the column is uninformative | `fillna('Other')` for blanks; keyword triage recommended |

---

### 1.3 Data Enrichment — Proposed Additional Fields

> Based on 4 perspectives: Task · Action · Impact · Challenges

1. [ ] **Identify revenue band / merchant size**
   - **Task:** Estimate transaction volume or revenue band based on Google Maps signals
   - **Action:** Re-scrape Google Maps for review count + rating, keyed on `business_name` + `address`
   - **Impact:** Proxy for customer awareness and transaction count
   - **Challenges:** Requires Google Places API access and budget for 190k record queries

2. [ ] **Customer willingness × merchant sector payment needs**
   - **Situation:** F&B and Retail move fast, high volume — payment friction directly costs them revenue. Traditional sectors (trades, NGOs) have lower digital expectations and higher switching resistance.
   - **Task:** Score each canonical Sector L1 on a 1–5 digital payment demand scale
   - **Action:** Map sector to score lookup table — F&B = 5, Beauty = 4, Retail = 4, Professional Services = 3, Automotive = 2
   - **Impact:** Lead quality hinges on two axes — how digital the sector already is and how frequently customers transact
   - **Challenges:** Score is opinionated; requires validation against KPay's historical conversion data

3. [ ] **Competitor payment method intelligence**
   - **Task:** Understand payment methods used by merchants and research competitor landscape
   - **Action:** Collect via job descriptions, business website footer badges, or in-person walk-in observation
   - **Impact:** Quantifies switching opportunity and sharpens pitch
   - **Challenges:** Transport cost for in-person; ~60% of small AU merchants have no website

---

## Part 2: Sales Canvassing Strategy  PENDING

### 2.1 Merchant Tiering and Segmentation
> Segmentation order: **Sector → Location → Phone + Address (valid)**

**Input:** `reformed_df` — 190,684 rows · 8 AU states · 9 Sector L1 values

**Segmentation rules:**
- Based on Sector L1: `sector_level_1` + `sector_level_2` (F&B, Retail, Beauty & Wellness, Professional Services, Others)
- Based on Geographic Routing:
  - [x] Cluster Tier 1 merchants by suburb (Sydney CBD, Parramatta, Surry Hills, Pyrmont, Ryde, Port Macquarie)
  - [x] Build suburb-level heatmap: calculate merchant density
  - [x] Prioritise high-density inner Sydney suburbs for initial sprint
  - [x] Size proxy: sector + suburb (CBD = high traffic)

| Tier | Sectors | Value | Approach |
|------|---------|-------|----------|
| **Tier 1** | Beauty & Wellness + F&B (Cafe, Restaurant), Retail (high turnover), Professional Services, fully-recovered address/state/suburb, premium suburb | **High Value** | Senior BD reps — in-person walk-in |
| **Tier 2** | Automotive, suburban, phone covered | **Medium** | Phone + email sequence |
| **Tier 3** | Others, regional NSW, Uncategorised | **Low / Long-term** | Brand awareness / nurture campaign |

- [ ] Append `bd_tier` column (1 / 2 / 3) to `reformed_df`
- [ ] Run keyword classifier on `business_name` + `sector_level_3` to promote Others/Uncategorised into Tier 1/2
- [ ] Geocode Tier 1 records by suburb for field rep routing
- [ ] Suppress existing KPay merchants before CRM export
- [ ] Flag `E Pay Australia` for competitor intelligence visit

---

### 2.2 Concrete, Actionable Canvassing Strategy

**a. Territory Mapping**

| Zone | Suburbs | Priority |
|------|---------|----------|
| Zone 1 — Sydney CBD + Inner | Sydney, Surry Hills, Darlinghurst, Pyrmont, Ultimo, Waterloo | Tier 1 pilot — Week 1–2 |
| Zone 2 — Western Sydney | Parramatta, Seven Hills, Wentworthville, Ryde | Tier 1–2 expansion — Week 3–4 |
| Zone 3 — North / East | Lane Cove, Rozelle, Alexandria | Tier 2 — Week 3–4 |
| Zone 4 — Regional NSW | Port Macquarie, Kurri Kurri, Lakesland… | Tier 3 — nurture / lower priority |

**b. Cadence Outreach**
- Tier 1: 2–3 touchpoints/week (call, email, in-person walk-in)
- Tier 2: 1–2 touchpoints/week (phone call, email sequence)
- Tier 3: Nurture campaign (email drip, marketing awareness, sample)

**c. Messaging by Segment**

| Sector | Key Message | Pain Point |
|--------|-------------|------------|
| F&B (Cafe, Restaurant, Catering) | Speed of service, POS integration, table ordering | Slow checkout at peak hour |
| Retail (Electronics, Fashion, Specialty) | Inventory reporting, multi-outlet management | Manual reconciliation, no real-time visibility |
| Professional Services (Medical, Real Estate, Automotive) | Invoicing, recurring payments | Late payments, manual follow-up |
| Beauty & Wellness | Appointment + payment integration | Booking-to-payment gap, no-show losses |

- [ ] Build sector-specific script for each of the 4 message tracks
- [ ] Load tiered, zoned dataset into CRM: `bd_tier` · `zone` · `suburb` · `sector_level_1` · `assigned_rep` · `outreach_status` · `contact_date`
- [ ] Week 2 debrief gate: if Contact → Meeting rate < 15%, revise script before Zone 2 expansion

---

## Part 3: Performance Dashboard PENDING

> **Purpose:** Give the sales manager a single view to track canvassing performance — by tier, by rep, by territory, and by sector.
> **Requirement:** Connected to live CRM data.

### 3.1 Key Metrics

| # | Metric | Visual | Keep Track |
|---|--------|--------|------------|
| a | **Lead Distribution by Tier** | Stacked bar | If Tier 3 dominates contacted column → reps wasting effort; if Tier 2/3 sign rate exceeds Tier 1 → recalibrate tier model |
| b | **Contacts / Week by Tier** | Line + target overlay | Tier 1 must hit outreach KPI before Tier 2 is prioritised |
| c | **Outreach Split** | % stacked bar (weekly) | Should skew Tier 1 in Weeks 1–2; broadens only after Zone 1 gate (>60% contact rate) is cleared |
| d | **Heatmap by Zone / Suburb** | Dot plot on Sydney metro map | Zone boundaries with merchant density dot plot — dot size = lead count, dot colour = signed rate |
| e | **Lead Core Distribution by Sector / Suburb** | Donut + cross-tab | Others + Uncategorised should be optimal minority of active Tier 1/2 outreach; Zone 1 should represent majority of Tier 1 contacts in Weeks 1–2 |

---

### 3.2 Dashboard Design Checklist
> Tool: **Tableau**

**a. Lead Distribution by Tier (Stacked Bar)**
- [ ] Build stacked bar: total leads by Tier 1 / 2 / 3 (volume count + % of total)
- [ ] Add second stacked bar: contacted leads by tier — compare to volume split
- [ ] Add signed % annotation per tier bar to surface conversion delta visually

**b. Contacts / Week by Tier (Line + Target)**
- [ ] Build weekly contacts line chart split by Tier 1 / 2 / 3
- [ ] Overlay Tier 1 target line (KPI_1) and Tier 2 target (KPI_2)
- [ ] Colour Tier 1 line red when below target, green when on track

**c. Outreach Split (Weekly % Stacked Bar)**
- [ ] Build weekly % stacked bar: proportion of contacts that are Tier 1 vs Tier 2 vs Tier 3
- [ ] Add Zone 1 gate indicator — visual lock on Tier 2/3 bars until Zone 1 Contact Rate > 60%
- [ ] Add week-on-week trend arrow to show if Tier 1 share is growing or shrinking

**d. Heatmap by Zone / Suburb (Dot Plot)**
- [ ] Geocode all Tier 1 + Tier 2 records by suburb centroid
- [ ] Build Sydney metro map overlay: dot size = lead count, dot colour = signed rate
- [ ] Draw Zone 1/2/3/4 boundary overlays on map
- [ ] Add filter toggle: view by total leads / contacted / signed

**e. Lead Core Distribution by Sector / Suburb (Donut + Cross-tab)**
- [ ] Build Sector L1 donut chart filtered to Tier 1 + Tier 2 only (exclude Tier 3)
- [ ] Flag Others + Uncategorised slice — highlight if combined exceeds optimal % of Tier 1/2 (triage not complete)
- [ ] Build Sector × Zone cross-tab heatmap: cell colour = contact rate, cell value = signed count
- [ ] Add Zone 1 share callout: "Zone 1 = X% of Tier 1 contacts this week" — target majority in Weeks 1–2

---

### 3.3 Supporting Steps

- [ ] Connect `reformed_df` + CRM live outreach updates as data source
- [ ] Data incompleteness handling — flag records missing phone / suburb / address before dashboard push
- [ ] Ranking leaderboard: rank result of each key metric per rep and per zone
- [ ] Present dashboard prototype to sales manager for feedback
- [ ] Schedule monthly data re-enrichment to keep merchant records current

---

## Deliverables

| File | Description | Output |
|------|-------------|--------|
| `Cleaning_process.ipynb` | Full cleaning pipeline notebook | 190,684 rows · 12 cols |
| `Cleaning_script.ipynb` | Full cleaning pipeline script | 190,684 rows · 12 cols |
| `cleaned_Kpay_data.csv` | Final clean merchant dataset | `reformed_df` export |
| `kpay_BD_Checklist.html` | Full project checklist (this document) | HTML |
| `kpay_Qa_summary.json` | QA summary with per-step counts and distributions | JSON |

---

*Dataset: `Case_Study.csv` · Input: 199,999 rows · Final: 190,684 rows (95.3% retained)*
*Checklist v4 — Part 1 complete · March 2026*

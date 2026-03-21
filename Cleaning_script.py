# import necessary lib 
import pandas as pd
import numpy as np 
import re

# ── Paths — adjust to environment 
raw_dataset   = "Case Study.csv"

# -------------
# step 0 — LOAD
# -------------
merchant = pd.read_csv(raw_dataset, dtype=str, encoding="utf-8-sig")

# Protect the original data
df = merchant.copy()

df["qa_flags"]       = "" # Notice actions after dealing
df["exclude_reason"] = ""

print("dataframe:",df)

# -------------
# Step 1: PHONE 
# create a note for each handling, convert the correct format 
# -------------
        # Transfrom all phone to digits:
def _digits(s: str) -> str: 
    return re.sub(r"\D", "", s)
        # Format as AU mobile phone (following the stardard rules):
def _fmt_au(local: str) -> str:
    d = _digits(local)
    if len(d) == 10 and d.startswith("04"):
        return f"{d[:4]} {d[4:7]} {d[7:]}"
    if len(d) == 10 and d[0] == "0":
        return f"({d[:2]}) {d[2:6]} {d[6:]}"
    if len(d) == 10 and (d.startswith("1300") or d.startswith("1800")):
        return f"{d[:4]} {d[4:7]} {d[7:]}"
    return local

def _from_lead_key(lk: str):
    d = re.sub(r"^L_", "", lk)
    if not d.isdigit():
        return None
    local = "0" + d[2:] if (d.startswith("61") and len(d) >= 10) else d
    if local.startswith("01300") or local.startswith("01800"):
        local = local[1:]   # drop leading-zero artefact on freecall numbers
    return local

def clean_phone(phone, lead_key):
    # Inline NaN guard — no external helper needed
    p  = "" if pd.isna(phone)    else str(phone).strip()
    lk = "" if pd.isna(lead_key) else str(lead_key).strip()

    if "E+" in p or "e+" in p:                          # scientific notation
        local = _from_lead_key(lk)
        return (_fmt_au(local), "reconstructed") if local else (p, "unresolvable")
    if p.startswith("+") and not p.startswith("+61"):   # foreign number
        return (p, "foreign number")
    if p.startswith("+61"):                             # +61 → local
        return (_fmt_au("0" + _digits(p)[2:]), "local number")
    d = _digits(p)
    if d.startswith("+61") and len(d) == 11:             # bare 61XXXXXXXXX
        return (_fmt_au("0" + d[2:]), "normalised")
    return (_fmt_au(p), "ok")

results      = df.apply(lambda r: clean_phone(r["phone"], r["lead_key"]), axis=1)
df["phone"]   = results.map(lambda x: x[0])
flags         = results.map(lambda x: x[1])

df.loc[flags == "foreign", "exclude_reason"] = "foreign_phone"
non_ok = flags != "ok"
df.loc[non_ok, "qa_flags"] += flags[non_ok].map("|phone:{}".format).str.lstrip("|")

# -------------
# STEP 2: STATE
# mapping state with given address (Australia-based location), otherwise keep blank for foreign location
# -------------
AU_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "ACT", "TAS", "NT"}

LONGFORM = {
    "new south wales": "NSW",  "victoria": "VIC",
    "queensland": "QLD",       "western australia": "WA",
    "south australia": "SA",   "australian capital territory": "ACT",
    "tasmania": "TAS",         "northern territory": "NT",
    "sydney, nsw": "NSW",
}

INVALID_STATES = {
    "KY","NY","CA","FL","NC","TX","OR","MA","GA","CT","PA","OH","MD","AZ","VT",
    "SC","IL","MI","TN","CO","ME","KS","UT","IN","RI","ID","ND","NJ","NH","AL",
    "WI","NV","OK","SD","HI","MN","MO","NM","DC","WV","VA","MT","DE","APAC",
    "HOP","AMM","ATM","ATT","LOT","BPM","PTD","STE","NEX","BG","GD","AU","IGO",
}

def clean_state(state, address, suburb):
    s   = "" if pd.isna(state)   else str(state).strip()
    adr = "" if pd.isna(address) else str(address).strip()
    sub = "" if pd.isna(suburb)  else str(suburb).strip()

    if s in AU_STATES:
        return s, "valid"
    if s.lower() in LONGFORM:
        return LONGFORM[s.lower()], "lowercase"
    if s in INVALID_STATES:
        return s, "invalid"
    if not s:
        # Try to infer from address / suburb text
        text = (adr + " " + sub).upper()
        for st in AU_STATES:
            if re.search(r"\b" + st + r"\b", text):
                return st, "address inferred"
        for long, short in LONGFORM.items():
            if long in (adr + " " + sub).lower():
                return short, "address inferred"
        return "", "blank_unresolved"
    return s, "unknown"

results      = df.apply(lambda r: clean_state(r["state"], r["address"], r["suburb"]), axis=1)
df["state"]   = results.map(lambda x: x[0])
flags         = results.map(lambda x: x[1])

df.loc[(flags == "invalid") & (df["exclude_reason"] == ""), "exclude_reason"] = "non_au_state"
need_flag = flags.isin(["invalid", "blank_unresolved", "address inferredd", "lowercase"])
df.loc[need_flag, "qa_flags"] += flags[need_flag].map("|state:{}".format).str.lstrip("|")

# -------------
# STEP 3: SUBURB
# -------------
_ROAD_WORDS = {
    "road","rd","street","st","ave","avenue","lane","ln","dr","drive",
    "blvd","boulevard","way","close","court","place","pl","crescent","cres","parade",
}

def clean_suburb(suburb, address):
    s   = "" if pd.isna(suburb)  else str(suburb).strip()
    adr = "" if pd.isna(address) else str(address).strip()

    # Already has a value — just ensure Title Case
    if s:
        return s.title(), ("cased" if s != s.title() else "ok")

    # Try to extract from address using 7 ordered regex patterns
    patterns = [
        r",\s+([A-Za-z][A-Za-z\s\-\'\.]{2,30}?)\s+(NSW|VIC|QLD|WA|SA|ACT|TAS|NT)\b",
        r",\s+([A-Za-z][A-Za-z\s\-\'\.]{2,30}?),\s+(New South Wales|Victoria|Queensland|Western Australia|South Australia|Australian Capital Territory|Tasmania|Northern Territory)",
        r",\s+([A-Za-z][A-Za-z\s\-\'\.]{2,30}?),\s*(NSW|VIC|QLD|WA|SA|ACT|TAS|NT)[,\s\d]",
        r"\s+([A-Za-z][A-Za-z\s\-\'\.]{2,25}?),?\s*(NSW|VIC|QLD|WA|SA|ACT|TAS|NT)\s+\d{4}",
        r",\s*([A-Za-z][A-Za-z\s\-\'\.]{2,30}?),\s*\d{4},\s*(NSW|VIC|QLD|WA|SA|ACT|TAS|NT)",
        r",\s*([A-Za-z][A-Za-z\s\-\'\.]{2,30}?),\s*(NSW|VIC|QLD|WA|SA|ACT|TAS|NT),\s*\d{4}",
    ]
    for pat in patterns:
        m = re.search(pat, adr)
        if m:
            candidate = m.group(1).strip().split(",")[-1].strip()
            if len(candidate) > 2 and not re.search(r"\d", candidate):
                return candidate.title(), "extracted"

    # Last-resort: last 1-3 words before the state abbreviation
    clean_adr = adr.rstrip(", Australia").strip()
    m = re.search(
        r"\b([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\s+(NSW|VIC|QLD|WA|SA|ACT|TAS|NT)\s*$",
        clean_adr,
    )
    if m:
        candidate = m.group(1).strip()
        words = candidate.lower().split()
        if (not any(w in _ROAD_WORDS for w in words)
                and not re.search(r"\d", candidate)
                and len(candidate) > 2):
            return candidate.title(), "extracted"

    return "", "blank_unresolved"

results       = df.apply(lambda r: clean_suburb(r["suburb"], r["address"]), axis=1)
df["suburb"]   = results.map(lambda x: x[0])
flags          = results.map(lambda x: x[1])

need_flag = flags.isin(["extracted", "blank_unresolved"])
df.loc[need_flag, "qa_flags"] += flags[need_flag].map("|suburb:{}".format).str.lstrip("|")

# -------------
# STEP 5: ADDRESS
# reformatting
# -------------
def clean_address(addr):
    a = "" if pd.isna(addr) else str(addr).strip()

    if not a:
        return a, np.nan
    cleaned = re.sub(r"\b([A-Za-z]{4,})\s+\1\b", r"\1", a, flags=re.I)  # dup words
    cleaned = re.sub(r"\b(NSW|VIC|QLD|WA|SA|ACT|TAS|NT)\s+\1\b", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip().strip(",").strip()
    return (cleaned, "fixed") if cleaned != a else (a, "ok")

results      = df["address"].map(clean_address)
df["address"] = results.map(lambda x: x[0])
flags         = results.map(lambda x: x[1])

# -------------
# STEP 6: BUSINESS NAME
# Manually entered the value based on the given address` to maximize the value feature
# -------------
# 0: For ['address'] which hold 54 missing value (<1% of total values) -> `Dropna` method to delete 54 rows of value -> the rest columns is 199,945 rows --OR-- mapping with business name to enrich data
missing_mask = df['address'].isna()
missing_row = df[missing_mask][['business_name','address', 'suburb','state']]
missing_row
# 1: Recall missing data for business_name and address
missing_name = df['business_name'].isna()
# 2: Manually mapping business name with given address
add_dict_name = {
    'Shop 4 207-215 Edensor Road Edensor Park, Greenfield Park, New South Wales 2176 Australia' : 'Domina"s Pizaa Edersor Park',
    'Hemlock St,, Marsden Park Marsden Park, New South Wales 2765'                              : 'Hemlock mall',
    '41/47 Shepherds Dr, Cherrybrook, Hornsby, New South Wales 2126 Australia'                  :'Parking car lot',
    '80 Mitchell Rd, Cronulla, New South Wales 2230 Australia'                                  :'Bianchini"s Eloura Beach',
    'Shop 449, Level 4 Macquarie Centre, Macquarie Park, Ryde, New South Wales 2112 Australia'  :'JB Hi-Fi macquarie',
    '220 Annerley Road, Brisbane, Queensland 4102 Australia'                                    :'Construction Building',
    'Factory 8/3 Apollo St, Warriewood NSW 2102, Australia'                                     :'Warriewood automotive service PTY LTD',
    '30/74 Mileham St, South Windsor NSW 2756, Australia'                                       :'Greater West Exercise Physiology',
    'Hervey Range Rd, Cessnock, New South Wales 4817 Australia'                                 :'Mr O Wholefoods'
}
# 3. Fill missing values using the map
df.loc[missing_name, 'business_name'] = (
            df.loc[missing_mask, 'address']
                .map(add_dict_name)
)

# -------------
# STEP 6: SECTOR_LEVEL_1
# -------------
#check sector_level_: categoriese each unique value that might be duplicated meaning
'''
Example: Catergorised sector into 5 major field + 2 fixed fields (Nightlight and Frorist) ~ 147 unique values -> merged into 9 major categories 
> F&B: Food & Beverage (row 322), Food & Drink, Food and Dining...
> Retail: "Retail Shopping","Stores","Retail Store","Retail Stores",...
> Beauty & Wellness
> Professtional Service
> Automotive
> Nightlight
'''
df['sector_level_1'].unique().shape #check unique value (147)
mask_sector_1 = df['sector_level_1'] == 'others' # replace na (37,770) by 'others'
missing_sector = df[mask_sector_1][['sector_level_1','sector_level_2','sector_level_3']]
missing_sector
df['sector_level_1'].unique().shape
# df['sector_level_1']
_S1_MAP = {
    **{k: "F&B" for k in [
        "Food & Drink","Restaurants","Restaurant","Restaurants & Bistros",
        "Food & Beverage","Food & Beverages","Food and Beverage","Food and Beverages",
        "Food and Beverage Retail","Food Retailers","Foods","Food","Food & Dining",
        "Food and Dining","Food and Drink","Food Services","Food Service",
        "Food &/or General Stores","Cafes","Coffee","Grocery & Food","Grocery Stores",
        "Groceries","Grocery","Food & Beverage Retailing","Seafood","Fruit & Vegetables",
        "Desserts & Sweets","Beverage","Ice Cream","Snack Foods","catering",
        "Eating and Drinking",
    ]},
    **{k: "Retail" for k in [
        "Retail Shopping","Stores","Retail Store","Retail Stores","Retail Trade",
        "Retailers","Shopping","Shops & Stores","Clothing","Fashion",
        "Fashion & Accessories","Fashion Accessories","Fashion & Clothing",
        "Fashion & Beauty","Clothing & Accessories","Clothing & Apparel",
        "Women's Clothing","Apparel","Apparel & Accessories","Sportswear","Footwear",
        "Alterations & Services","Tailors","Fashion Jewellery","Jewelry","Furniture",
        "Furniture & Supplies","Furniture Stores","Home & Furniture","Electronics",
        "Electronics & Gadgets","Electronics Repair","Electrical Appliances",
        "Household Appliances","Kitchen Appliances","Kitchen Equipment",
        "Computer Hardware","Computers","Computers & Electronics","Technology",
        "Telephones & Accessories","Audio Equipment","Video & DVD Equipment",
        "Radios & Hi-Fi","Office Products","Office Equipment",
        "Office Supplies & Services","Stationery","Glassware & Earthenware",
        "China & Glass Decoration","Gifts & Novelty","Gifts & Novelties","Toys",
        "Toys & Games","Games","Games & Toys","Games & Accessories","Hobbies",
        "Hobbies & Crafts","Crafts","Art Supplies","Party Supplies","Baby Products",
        "Books","Bicycles","Sporting Goods","Sports Club","Markets","Tobacco Products",
        "Equipment & Products","Cleaning Equipment & Supplies","Printers","Floor Mats",
        "Musical Instruments & Gear","Watches",
    ]},
    **{k: "Beauty & Wellness" for k in [
        "Hair & Beauty","Beauty Salons","Beauty & Personal Care","Health & Beauty",
        "Health and Beauty","Beauty & Spa","Beauty & Spas","Beauty",
        "Beauty Salon Supplies","Hairdressers","Hair Salons","Hairdressing Supplies",
        "Massage","Cosmetics & Personal Care","Perfumes & Fragrances","Tattooist",
        "Body Piercing","Physiotherapy","Pharmacy",
    ]},
    **{k: "Professional Services" for k in [
        "Professional Service","Repair Services","Laundries,Services",
        "Laundry & Dry Cleaning",
    ]},
    **{k: "Automotive" for k in [
        "Automotive Parts","Automotive Parts & Accessories","Automotive Accessories",
        "Automotive Products","Automotive Repair","Automotive Repair & Services",
        "Car Accessories","Tyres","Gas Station","Vehicle Rental",
    ]},
}
 
def clean_sector_l1(val):
    v = "" if pd.isna(val) else str(val).strip()
    if not v:         return "others", "others"
    if v in _S1_MAP:  return _S1_MAP[v], "merged"
    return v, "ok"
 
results                = df["sector_level_1"].map(clean_sector_l1)
df["sector_level_1"]   = results.map(lambda x: x[0])
flags                  = results.map(lambda x: x[1])
 
df.loc[flags == "others", "qa_flags"] += "|sector:others"
df["qa_flags"] = df["qa_flags"].str.lstrip("|")

# -------------
# STEP 7: SECTOR_LEVEL 2 
# -------------
df[df.sector_level_2.isnull()]
df['sector_level_2'] = df['sector_level_2'].fillna('Other')

# -------------
# STEP 8: SECTOR_LEVEL_3
# -------------
#check sector_level_3: categoriese each unique value that might be duplicated meaning
'''
Goals: Keep the specific value and check for missing value
Clearly seen that for those missing in sector level 1,2 will lead to missing value in sector level 3 (6,846 values) -> run keyword-based sub-classification using `business_name` and `sector_level_3` to reduce vague tagging
Result: From raw dataset, 'other' in L1 and L2 -> only missing value hold ->> after cleaning, 
'''
df['sector_level_3'].unique().shape  #check unique value (147)
mask_sector_2 = df['sector_level_2'].isnull() # replace na (37,770) by 'others'
missing_sector_2 = df[mask_sector_2][['business_name','sector_level_1','sector_level_2','sector_level_3']]
missing_sector_2
# BEFORE CLEANING:
mask_sector_3 = merchant['sector_level_3'].isnull() # replace na (37,770) by 'others'
mask_sector_3 = (merchant['sector_level_1'] == 'Others') & (merchant['sector_level_2'] == 'Others')
missing_sector_3 = merchant[mask_sector_3][['sector_level_1','sector_level_2','sector_level_3']]
missing_sector_3 #['sector_level_3'].unique().shape
# AFTER CLEANING:
df_sector_3 = (df['sector_level_1'] == 'Others') & (df['sector_level_2'] == 'Others')  # replace na (37,770) by 'others'
df_sector_3 = df[df_sector_3][['sector_level_1','sector_level_2','sector_level_3']]
df_sector_3
# df['sector_level_3'].value_counts()
_S3_MAP = {
    **{k: "Quick-Service / Takeaway" for k in [
        "Takeaways","Take Away Food, Pizza, Fish & Chips Shops",
        "Take Away","Fast Food","Fast-Food Restaurants",
    ]},
    **{k: "Medical & Dental" for k in [
        "Medical Center","Dental","Dentist","Doctors",
        "General Practitioners (GP) & Family Doctors",
    ]},
    **{k: "Physiotherapy & Allied Health" for k in [
        "Physiotherapists","Physiotherapy","Allied Health","Sports Medicine",
    ]},
    **{k: "Spa & Massage" for k in [
        "Massage Therapists","Thai Massage","Remedial Massage",
    ]},
    **{k: "Bar / Pub / Nightlife" for k in [
        "Bar","Pub","Nightclub","Night Club","Cocktail Bar",
    ]},
    **{k: "Beauty Salon / Barber" for k in [
        "Hair Salon","Hair Salons","Hairdresser","Hairdressers","Barbershop","Barbers",
    ]},
    **{k: "Nail Salon"                    for k in ["Nail Salons","Nails"]},
    **{k: "Grocery / Convenience Store"   for k in [
        "Supermarket","Supermarkets","Convenience Store","Convenience Stores","Mini Mart",
    ]},
    **{k: "Cafe & Dessert"                for k in ["Cafe","Coffee Shop","Coffee House","Bakery"]},
    **{k: "Gym / Fitness / Yoga"          for k in [
        "Fitness Centre","Fitness Center","Yoga","Yoga Studio",
        "Pilates","Pilates Studio","Gym",
    ]},
    **{k: "Fashion & Accessories"         for k in [
        "Clothing Stores","Clothing Store","Clothes",
        "Men's Clothing","Women's Clothing",
        "Shoes","Shoe Store","Shoe Shops",
        "Jewellery","Jewellery Store","Jewelry Store",
    ]},
    **{k: "Bottle Shop / Liquor"          for k in ["Liquor Store","Liquor","Bottle Shop","BWS"]},
    **{k: "Hotel / Motel / Accommodation" for k in [
        "Motel","Hotel","Accommodation","Hostel","Bed & Breakfast",
    ]},
    **{k: "Automotive Services"           for k in [
        "Mechanic","Car Mechanic","Auto Repair","Car Service",
        "Car Wash","Petrol Station","Service Station",
    ]},
}
 
_OOS_L3 = {"Religious / Community / NGO", "Government / Utility Services"}
 
def clean_sector_l3(val):
    v = "" if pd.isna(val) else str(val).strip()
    if not v:         return "Others", "was_blank"
    if v in _S3_MAP:  return _S3_MAP[v], "merged"
    return v, "ok"
 
results                = df["sector_level_3"].map(clean_sector_l3)
df["sector_level_3"]   = results.map(lambda x: x[0])
flags                  = results.map(lambda x: x[1])
 
df.loc[df["sector_level_3"].isin(_OOS_L3) & (df["exclude_reason"] == ""),
       "exclude_reason"] = "out_of_scope_sector"

# -------------
# STEP 9: DATA CLEANING
# -------------
reformed_df = df.copy()
# For ['address'] which hold 54 blank cells (<1% of total values) -> `Dropna` method to delete 54 rows of value -> the rest columns is 199,945 rows
blank_cell = reformed_df.address == ""
reformed_df = reformed_df[reformed_df['address'] != ""].reset_index(drop=True)
# Report
print(f'Rows after dropping blank address: {len(reformed_df):,}')
print(f'Rows which hold blank address: {len(reformed_df[blank_cell]):,}')
print(f'Blank addresses remaining: {(reformed_df["address"] == "").sum()}')

# Remove Dupplicate phone (Frequency >= 2): drop
    # Diagnostic — see duplicate phone scale
tmp = reformed_df['phone'].value_counts().to_frame().reset_index()
tmp[tmp['count']>1].shape
print(f' Total duplicate phone groups : {tmp[tmp["count"] > 1].shape[0]:,}')
print(f'Total rows affected    : {tmp[tmp["count"] > 1]["count"].sum():,}')

# Drop duplicates — keep first occurrence, remove the rest, retains one representative record per phone number and drops the 590 phone number repeated across 1,180 rows, leaving 199,355 clean, unique-phone merchants ready for BD outreach
reformed_df = (reformed_df
               .drop_duplicates(subset='phone', keep='first')
               .reset_index(drop=True))
print(f'Rows after dedup : {len(reformed_df):,}')

# Location not based in Au
blank_state = reformed_df.state == ""
blank_view = reformed_df[blank_state]
blank_view
blank_view['address'].value_counts()
# # # Extract country name to visibly double check
blank_view[['street','country']] = (blank_view['address']
                                        .str.extract("(?P<Address>.*\d+[\w+?|\s]\s?\w+\s+\w+),?\s(?P<Suburb>.*$)")
                                        .apply(lambda x: x.str.title()))
# Report: Convert to a list of country: clealy state that the merchant is not located in Aus but in Canada, Newzealand, etc
print(f'Blank state rows         : {len(blank_view):,}')
print(f'Unique country values    : {blank_view["country"].nunique()}')
print(blank_view['country'].value_counts().head(15).to_string())

# inValid Au state filter count: remove any state are not in valid AU state
reformed_df = reformed_df[reformed_df['state'].isin(AU_STATES)].reset_index(drop=True)
print(f'\nRows after invalid state removal : {len(reformed_df):,}')
print(f'States remaining : {sorted(reformed_df["state"].unique())}')
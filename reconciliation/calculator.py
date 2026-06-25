"""
Reconciliation Calculator
Applies per-location formula to produce all rows of the statement.

Balance b/f logic (all locations):
  - Balance b/f             = prior month Debtors c/f
  - Balance b/f after adj   = open.pdf system opening total
  - Adjustments (1)         = Balance b/f (after adj) - Balance b/f
"""

LOCATION_NAMES = {
    "male":        "MALE'",
    "hulhumale":   "HULHUMALE'",
    "thilafushi":  "THILAFUSHI",
    "gulhi_falhu": "GULHI FALHU",
}


def calculate(location: str, f: dict) -> dict:
    name = LOCATION_NAMES.get(location, location.upper())

    # Balance b/f = prior month c/f (user confirmed in review step)
    elec_bf   = f.get("elec_bf", 0.0)
    misc_bf   = f.get("misc_bf", 0.0)

    # Balance b/f (after adjustment) = open.pdf total
    # For Male': parser returns elec_bfadj from open.pdf
    # For Hulhumale': open.pdf IS the prior c/f so bfadj = bf, adj1 = 0
    elec_bfadj = f.get("elec_bfadj", elec_bf)
    misc_bfadj = f.get("misc_bfadj", misc_bf)

    # Adjustments (1) = Balance b/f after adj - Balance b/f
    elec_adj1 = elec_bfadj - elec_bf
    misc_adj1 = misc_bfadj - misc_bf

    elec_sales    = f.get("elec_sales", 0.0)
    misc_sales    = f.get("misc_sales", 0.0)
    elec_credits  = f.get("elec_credits", 0.0)
    misc_credits  = f.get("misc_credits", 0.0)
    elec_discount = f.get("elec_discount", 0.0)
    misc_discount = f.get("misc_discount", 0.0)

    elec_sub1 = elec_bfadj + elec_sales
    misc_sub1 = misc_bfadj + misc_sales
    elec_sub2 = elec_sub1 + elec_credits + elec_discount
    misc_sub2 = misc_sub1 + misc_credits + misc_discount

    elec_collection = f.get("elec_collection", 0.0)
    misc_collection = f.get("misc_collection", 0.0)

    elec_close_system = f.get("elec_close_system", 0.0)
    misc_close_system = f.get("misc_close_system", 0.0)

    # Adjustments (2) = system c/f - calculated c/f
    elec_calc = elec_sub2 - elec_collection
    misc_calc = misc_sub2 - misc_collection
    elec_adj2 = elec_close_system - elec_calc
    misc_adj2 = misc_close_system - misc_calc

    elec_cf = elec_calc + elec_adj2  # = elec_close_system
    misc_cf = misc_calc + misc_adj2  # = misc_close_system

    return {
        "location_name": name,
        "rows": [
            {"label": "Balance b/f",                    "elec": elec_bf,         "misc": misc_bf},
            {"label": "Adjustments",                    "elec": elec_adj1,       "misc": misc_adj1},
            {"label": "Balance b/f (after adjustment)", "elec": elec_bfadj,      "misc": misc_bfadj,  "bold": True},
            {"label": "Total Sales/Additional Revenue*","elec": elec_sales,      "misc": misc_sales},
            {"label": "",                               "elec": elec_sub1,       "misc": misc_sub1,   "subtotal": True},
            {"label": "Credits / Fine",                 "elec": elec_credits,    "misc": misc_credits},
            {"label": "Discount",                       "elec": elec_discount,   "misc": misc_discount},
            {"label": "",                               "elec": elec_sub2,       "misc": misc_sub2,   "subtotal": True},
            {"label": "Collection for the month",       "elec": -elec_collection,"misc": -misc_collection},
            {"label": "Adjustments (2)",                "elec": elec_adj2,       "misc": misc_adj2},
            {"label": "Debtors Balance c/f",            "elec": elec_cf,         "misc": misc_cf,     "final": True},
        ],
        "elec_cf": elec_cf,
        "misc_cf": misc_cf,
    }

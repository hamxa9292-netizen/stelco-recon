"""
Reconciliation Calculator

Logic:
  - Balance b/f             = prior month c/f (elec_bf)
  - Balance b/f after adj   = open.pdf total (elec_bfadj)
  - Adjustments (1)         = elec_bfadj - elec_bf
  - Debtors Balance c/f     = close.pdf total (elec_close_system)
  - Adjustments (2)         = close.pdf total - calculated c/f
                            = automatically correct sign (positive or negative)
"""

LOCATION_NAMES = {
    "male":        "MALE'",
    "hulhumale":   "HULHUMALE'",
    "thilafushi":  "THILAFUSHI",
    "gulhi_falhu": "GULHI FALHU",
}


def calculate(location: str, f: dict) -> dict:
    name = LOCATION_NAMES.get(location, location.upper())

    elec_bf    = f.get("elec_bf",    0.0)
    misc_bf    = f.get("misc_bf",    0.0)
    elec_bfadj = f.get("elec_bfadj", elec_bf)
    misc_bfadj = f.get("misc_bfadj", misc_bf)

    # Adjustments (1) = b/f after adj - b/f
    elec_adj1 = elec_bfadj - elec_bf
    misc_adj1 = misc_bfadj - misc_bf

    elec_sales    = f.get("elec_sales",    0.0)
    misc_sales    = f.get("misc_sales",    0.0)
    elec_credits  = f.get("elec_credits",  0.0)
    misc_credits  = f.get("misc_credits",  0.0)
    elec_discount = f.get("elec_discount", 0.0)
    misc_discount = f.get("misc_discount", 0.0)

    elec_sub1 = elec_bfadj + elec_sales
    misc_sub1 = misc_bfadj + misc_sales
    elec_sub2 = elec_sub1 + elec_credits + elec_discount
    misc_sub2 = misc_sub1 + misc_credits + misc_discount

    elec_collection = f.get("elec_collection", 0.0)
    misc_collection = f.get("misc_collection", 0.0)

    # Calculated c/f before adj(2)
    elec_calc = elec_sub2 - elec_collection
    misc_calc = misc_sub2 - misc_collection

    # c/f = close.pdf total
    elec_cf = f.get("elec_close_system", 0.0)
    misc_cf = f.get("misc_close_system", 0.0)

    # Adjustments (2) = c/f - calculated  →  correct sign automatically
    elec_adj2 = elec_cf - elec_calc
    misc_adj2 = misc_cf - misc_calc

    return {
        "location_name": name,
        "rows": [
            {"label": "Balance b/f",                    "elec": elec_bf,         "misc": misc_bf},
            {"label": "Adjustments",                    "elec": elec_adj1,       "misc": misc_adj1},
            {"label": "Balance b/f (after adjustment)", "elec": elec_bfadj,      "misc": misc_bfadj,   "bold": True},
            {"label": "Total Sales/Additional Revenue*","elec": elec_sales,      "misc": misc_sales},
            {"label": "",                               "elec": elec_sub1,       "misc": misc_sub1,    "subtotal": True},
            {"label": "Credits / Fine",                 "elec": elec_credits,    "misc": misc_credits},
            {"label": "Discount",                       "elec": elec_discount,   "misc": misc_discount},
            {"label": "",                               "elec": elec_sub2,       "misc": misc_sub2,    "subtotal": True},
            {"label": "Collection for the month",       "elec": -elec_collection,"misc": -misc_collection},
            {"label": "Adjustments (2)",                "elec": elec_adj2,       "misc": misc_adj2},
            {"label": "Debtors Balance c/f",            "elec": elec_cf,         "misc": misc_cf,      "final": True},
        ],
        "elec_cf": elec_cf,
        "misc_cf": misc_cf,
    }

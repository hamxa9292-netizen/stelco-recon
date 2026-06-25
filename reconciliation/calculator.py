"""
Reconciliation Calculator
Applies per-location formula to produce all rows of the statement.
"""

LOCATION_NAMES = {
    "male":        "MALE'",
    "hulhumale":   "HULHUMALE'",
    "thilafushi":  "THILAFUSHI",
    "gulhi_falhu": "GULHI FALHU",
}


def calculate(location: str, f: dict) -> dict:
    """
    Given extracted/reviewed figures (f), compute all reconciliation rows.
    Returns a result dict ready for the docx generator.
    """
    name = LOCATION_NAMES.get(location, location.upper())

    elec_bf   = f["elec_bf"]
    misc_bf   = f["misc_bf"]

    # Adjustment (1): difference between b/f (prior month c/f) and system opening
    # For Male': open.pdf may differ from the prior c/f due to late postings
    # For Hulhumale': usually 0
    elec_adj1 = f.get("elec_adj1", 0.0)
    misc_adj1 = f.get("misc_adj1", 0.0)

    elec_bfadj = elec_bf + elec_adj1
    misc_bfadj = misc_bf + misc_adj1

    elec_sales = f["elec_sales"]
    misc_sales = f["misc_sales"]

    elec_sub1  = elec_bfadj + elec_sales
    misc_sub1  = misc_bfadj + misc_sales

    elec_credits = f.get("elec_credits", 0.0)
    misc_credits = f.get("misc_credits", 0.0)
    elec_discount = f.get("elec_discount", 0.0)
    misc_discount = f.get("misc_discount", 0.0)

    elec_sub2  = elec_sub1 + elec_credits + elec_discount
    misc_sub2  = misc_sub1 + misc_credits + misc_discount

    elec_collection = f["elec_collection"]
    misc_collection = f["misc_collection"]

    # Adjustment (2): residual to make c/f tie to system
    elec_close_system = f["elec_close_system"]
    misc_close_system = f["misc_close_system"]

    elec_calc = elec_sub2 - elec_collection
    misc_calc = misc_sub2 - misc_collection

    elec_adj2 = elec_close_system - elec_calc
    misc_adj2 = misc_close_system - misc_calc

    elec_cf = elec_calc + elec_adj2   # = elec_close_system
    misc_cf = misc_calc + misc_adj2   # = misc_close_system

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

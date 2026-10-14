"""Customer records. Schema v2 renamed full_name to display_name."""
CUSTOMERS = {1: {"id": 1, "display_name": "Northstar Logistics", "tax_id": "SYNTHETIC-001"}}


def get_customer(customer_id):
    return CUSTOMERS[customer_id].copy()

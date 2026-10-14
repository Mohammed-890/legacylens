"""Invoice generation still expects the v1 customer schema."""
from customers import get_customer


def create_invoice(customer_id, subtotal):
    customer = get_customer(customer_id)
    return {"customer": customer["full_name"], "total": round(subtotal * 1.15, 2)}

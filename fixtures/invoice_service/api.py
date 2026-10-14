"""Entry point for the demonstration billing service."""
from invoices import create_invoice
from reporting import invoice_count


def invoice_endpoint(customer_id, subtotal):
    return create_invoice(customer_id, subtotal)


def health():
    return {"status": "ok"}

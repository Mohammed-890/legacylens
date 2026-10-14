"""An intentionally unsafe reporting query for the static analysis demo."""
def invoice_count(connection, customer_name):
    return connection.execute(f"SELECT count(*) FROM invoices WHERE customer = '{customer_name}'").fetchone()[0]

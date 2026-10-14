# Incident INC-042 · Invoice creation fails after migration

Symptom: invoice_endpoint(1, 100) raises KeyError: 'full_name'.
Change: customer schema v2 renamed full_name to display_name.
The customer service now returns display_name; the invoice service still reads full_name.
Investigate the producer in customers.py and consumer in invoices.py.
Fix the consumer, then verify invoice names, totals and unknown-customer behaviour.
This is a deliberately seeded training incident, not a real customer outage.

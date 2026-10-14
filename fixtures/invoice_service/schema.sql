-- Customer schema v2. All data in this project is synthetic.
CREATE TABLE customers (id INTEGER PRIMARY KEY, display_name TEXT, tax_id TEXT);
CREATE TABLE invoices (id INTEGER PRIMARY KEY, customer TEXT, total NUMERIC);

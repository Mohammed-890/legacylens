import unittest
from api import invoice_endpoint
from customers import get_customer


class InvoiceTests(unittest.TestCase):
    def test_customer_name(self):
        self.assertEqual(invoice_endpoint(1, 100)['customer'], 'Northstar Logistics')

    def test_total(self):
        self.assertEqual(invoice_endpoint(1, 100)['total'], 115)

    def test_zero_total(self):
        self.assertEqual(invoice_endpoint(1, 0)['total'], 0)

    def test_unknown_customer(self):
        with self.assertRaises(KeyError):
            invoice_endpoint(999, 100)

    def test_customer_copy(self):
        copy = get_customer(1)
        copy['display_name'] = 'Changed'
        self.assertEqual(get_customer(1)['display_name'], 'Northstar Logistics')


if __name__ == '__main__':
    unittest.main()

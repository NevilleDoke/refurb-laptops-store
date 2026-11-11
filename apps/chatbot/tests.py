from django.test import SimpleTestCase

from .selectors import _extract_ram, _extract_price, _extract_storage, _extract_screen


class SelectorParsingTests(SimpleTestCase):
    """Tests for the pure parsing helpers used by the chat bot matcher."""

    def test_extract_price(self):
        self.assertEqual(_extract_price("gaming laptop under 50000"), (None, 50000))
        self.assertEqual(_extract_price("below ₹45000"), (None, 45000))
        self.assertEqual(_extract_price("budget 30000 to 60000"), (30000, 60000))
        self.assertEqual(_extract_price("above 40000"), (40000, None))
        self.assertEqual(_extract_price("i need a laptop"), (None, None))

    def test_extract_ram(self):
        self.assertEqual(_extract_ram("8gb ram"), [8])
        self.assertEqual(_extract_ram("16 gb"), [16])
        self.assertEqual(_extract_ram("8gb and 16gb"), [8, 16])
        self.assertEqual(_extract_ram("no ram mentioned"), [])

    def test_extract_storage(self):
        self.assertEqual(_extract_storage("512gb ssd"), [512])
        self.assertEqual(_extract_storage("1tb nvme"), [1024])
        self.assertEqual(_extract_storage("256gb hdd"), [256])
        self.assertEqual(_extract_storage("none"), [])

    def test_extract_screen(self):
        self.assertEqual(_extract_screen("15.6 inch laptop"), [15.6])
        self.assertEqual(_extract_screen("14in"), [14])
        self.assertEqual(_extract_screen("no screen"), [])

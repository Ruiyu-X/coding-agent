import unittest

from calculator import add, subtract


class CalculatorTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_subtract(self):
        self.assertEqual(subtract(7, 4), 3)


if __name__ == "__main__":
    unittest.main()

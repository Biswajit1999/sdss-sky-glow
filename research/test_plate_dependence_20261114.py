import math
import unittest
from plate_dependence_20261114 import design_effect, leave_one_cluster_out

class PlateTests(unittest.TestCase):
    def test_independent(self):
        self.assertEqual(design_effect([3, 7], 0)["effective_n"], 10)
    def test_perfect_cluster(self):
        self.assertEqual(design_effect([5, 5], 1)["effective_n"], 2)
    def test_unbalanced(self):
        self.assertAlmostEqual(design_effect([1, 3], 1)["design_effect"], 2.5)
    def test_single_plate_rejected(self):
        with self.assertRaises(ValueError): leave_one_cluster_out([1, 2], ["A", "A"])
    def test_deletion(self):
        self.assertEqual(leave_one_cluster_out([1, 3, 8], ["A", "A", "B"]), {"A": 8, "B": 2})
    def test_bad_rho(self):
        with self.assertRaises(ValueError): design_effect([5], float("nan"))

if __name__ == "__main__":
    unittest.main()

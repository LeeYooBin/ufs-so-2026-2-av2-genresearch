import importlib.util
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('run_benchmarks',ROOT/'scripts/run_benchmarks.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class BenchmarkTests(unittest.TestCase):
    def test_matrix_covers_all_cases_and_three_factors(self):
        configs=module.matrix()
        self.assertEqual({c['case'] for c in configs},{'C1','C2','C3','C4','C5','C6'})
        self.assertEqual({c['consumers'] for c in configs if c['case']=='C3'},{1,2,4})
        self.assertEqual({c['documents'] for c in configs if c['case']=='C1'},{120,1200})
        self.assertEqual({c['cache_capacity'] for c in configs if c['case']=='C4'},{2,8})

if __name__=='__main__':unittest.main()

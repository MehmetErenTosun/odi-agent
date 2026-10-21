import unittest
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "odi_agent"
# schema_map tek kaynak; seed.py ve schema.sql sahte ODI'nin kendisi olduğu için hariç.
ALLOWED = {"schema_map.py", "seed.py"}


class SchemaMapTest(unittest.TestCase):
    def test_odi_names_only_in_schema_map(self):
        modules = [p for p in PACKAGE_DIR.glob("*.py") if p.name not in ALLOWED]
        self.assertTrue(modules)
        for path in modules:
            with self.subTest(module=path.name):
                self.assertNotIn("SNP_", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

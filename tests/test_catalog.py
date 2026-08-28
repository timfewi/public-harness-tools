from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_catalog import parse_frontmatter, validate_catalog  # noqa: E402


class CatalogValidationTests(unittest.TestCase):
    def test_complete_catalog_is_valid(self) -> None:
        errors, count = validate_catalog()
        self.assertEqual(count, 18)
        self.assertEqual(errors, [])

    def test_immediately_duplicated_frontmatter_is_rejected(self) -> None:
        text = """---
name: example-skill
description: Use for an example; not for another workflow.
---

---
name: example-skill
description: Use for an example; not for another workflow.
---

# Example
"""
        _, errors = parse_frontmatter(text, Path("SKILL.md"))
        self.assertTrue(
            any(
                "second frontmatter-like block" in error
                or "exactly two frontmatter delimiters" in error
                for error in errors
            )
        )

    def test_extra_frontmatter_key_is_rejected(self) -> None:
        text = """---
name: example-skill
description: Use for an example; not for another workflow.
license: MIT
---

# Example
"""
        _, errors = parse_frontmatter(text, Path("SKILL.md"))
        self.assertTrue(any("frontmatter keys must be exactly" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from hymn_splitter.imaging import _line_gap
from hymn_splitter.service import apply_build_options


class LineSpacingTest(unittest.TestCase):
    def test_spacing_modes_increase_in_order(self) -> None:
        compact = _line_gap({"options": {"line_spacing": "compact"}}, 1000)
        normal = _line_gap({"options": {"line_spacing": "normal"}}, 1000)
        relaxed = _line_gap({"options": {"line_spacing": "relaxed"}}, 1000)
        self.assertLess(compact, normal)
        self.assertLess(normal, relaxed)

    def test_build_options_normalize_unknown_spacing(self) -> None:
        config = apply_build_options(
            {},
            line_spacing="unexpected",
        )
        self.assertEqual(config["options"]["line_spacing"], "normal")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from hymn_splitter.staff_layout import (
    _is_note_row,
    _pair_staves,
    _reslice_rows,
    _slice_rows,
)


def _row(center: int, *, top: int, bottom: int, square: float) -> dict:
    return {
        "center": center,
        "top": top,
        "bottom": bottom,
        "count": 6,
        "square_ratio": square,
        "median_aspect": 1.0,
    }


class PairStavesTest(unittest.TestCase):
    def test_grand_staff_systems_are_paired_by_gap_clustering(self) -> None:
        staves = [
            (259, 329),
            (634, 701),
            (782, 846),
            (1163, 1227),
            (1324, 1387),
            (1743, 1792),
            (1897, 1941),
            (2137, 2204),
        ]
        pairs = _pair_staves(staves)
        self.assertEqual(
            pairs,
            [
                ((259, 329), (634, 701)),
                ((782, 846), (1163, 1227)),
                ((1324, 1387), (1743, 1792)),
                ((1897, 1941), (2137, 2204)),
            ],
        )

    def test_even_gaps_pair_consecutive_staves(self) -> None:
        staves = [(0, 10), (120, 130), (240, 250), (360, 370)]
        self.assertEqual(
            _pair_staves(staves),
            [
                ((0, 10), None),
                ((120, 130), None),
                ((240, 250), None),
                ((360, 370), None),
            ],
        )


class RowClassificationTest(unittest.TestCase):
    def test_jianpu_and_chords_are_note_rows(self) -> None:
        self.assertTrue(_is_note_row(_row(300, top=280, bottom=320, square=0.0)))
        self.assertTrue(_is_note_row(_row(300, top=280, bottom=320, square=0.4)))
        self.assertFalse(_is_note_row(_row(300, top=280, bottom=320, square=0.9)))


class SliceRowsTest(unittest.TestCase):
    def test_rows_split_at_quiet_valleys_without_overlap(self) -> None:
        profile = [0] * 400
        for center, half in ((100, 20), (200, 20), (300, 20)):
            for y in range(center - half, center + half + 1):
                profile[y] = 500
        rows = [
            _row(100, top=80, bottom=120, square=0.9),
            _row(200, top=180, bottom=220, square=0.9),
            _row(300, top=280, bottom=320, square=0.9),
        ]
        slices = _slice_rows(
            rows,
            profile=profile,
            pitch=100.0,
            image_height=400,
        )
        self.assertEqual(len(slices), 3)
        self.assertEqual(slices[0][1], slices[1][0])
        self.assertEqual(slices[1][1], slices[2][0])
        self.assertEqual(slices[0][1], 150)

    def test_reslice_splits_a_merged_block_evenly(self) -> None:
        self.assertEqual(
            _reslice_rows([[100, 180]], count=2),
            [[100, 140], [140, 180]],
        )


if __name__ == "__main__":
    unittest.main()

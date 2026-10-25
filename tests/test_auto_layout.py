from __future__ import annotations

import unittest

from hymn_splitter.auto_layout import (
    _drop_leading_staff_run,
    _partition_verse_groups,
)


def _group(*sizes: int) -> list[list[dict[str, int]]]:
    return [[{"top": index} for index in range(size)] for size in sizes]


class PartitionVerseGroupsTest(unittest.TestCase):
    def test_short_group_in_the_middle_stays_with_verses(self) -> None:
        groups = _group(4, 4, 2, 4)
        main, remaining = _partition_verse_groups(groups, first_count=4)
        self.assertEqual(len(main), 4)
        self.assertEqual(remaining, [])

    def test_tail_groups_are_kept_as_chorus(self) -> None:
        groups = _group(4, 4, 2, 2)
        main, remaining = _partition_verse_groups(groups, first_count=4)
        self.assertEqual(len(main), 2)
        self.assertEqual(len(remaining), 2)

    def test_single_irregular_group_before_tail_is_not_chorus(self) -> None:
        groups = _group(3, 3, 1, 3)
        main, remaining = _partition_verse_groups(groups, first_count=3)
        self.assertEqual(len(main), 4)
        self.assertEqual(remaining, [])


class DropLeadingStaffRunTest(unittest.TestCase):
    def test_keeps_legitimate_low_tall_lyric_edge(self) -> None:
        group = [
            {"top": 2658, "bottom": 2778, "height": 121, "coverage": 0.384, "tall_columns": 20},
            {"top": 2815, "bottom": 2931, "height": 117, "coverage": 0.364, "tall_columns": 100},
            {"top": 2962, "bottom": 3082, "height": 121, "coverage": 0.372, "tall_columns": 101},
            {"top": 3114, "bottom": 3234, "height": 121, "coverage": 0.394, "tall_columns": 19},
        ]
        self.assertEqual(len(_drop_leading_staff_run(group)), 4)

    def test_removes_a_note_staff_that_touched_the_first_lyric(self) -> None:
        group = [
            {"top": 1012, "bottom": 1094, "height": 83, "coverage": 0.491, "tall_columns": 29},
            {"top": 1155, "bottom": 1232, "height": 78, "coverage": 0.553, "tall_columns": 137},
            {"top": 1253, "bottom": 1329, "height": 77, "coverage": 0.557, "tall_columns": 139},
        ]
        self.assertEqual(len(_drop_leading_staff_run(group)), 2)


if __name__ == "__main__":
    unittest.main()

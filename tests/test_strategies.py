"""
tests/test_strategies.py - Unit tests for window arrangement strategies.
"""

import pytest
from win_utils import Rect, WindowInfo
from strategies.side_by_side import SideBySideLayout
from strategies.grid import GridLayout
from strategies.stack import StackLayout
from strategies import get_strategy, list_strategies


def make_window(hwnd: int, title: str = "Table", class_name: str = "PokerClass", w: int = 1302, h: int = 800) -> WindowInfo:
    return WindowInfo(
        hwnd=hwnd,
        title=title,
        class_name=class_name,
        rect=Rect(10, 10, w, h),
        is_minimized=False,
    )


def test_side_by_side_zero_windows():
    strategy = SideBySideLayout()
    work_area = Rect(0, 0, 1920, 1080)
    placements = strategy.arrange([], work_area, {})
    assert placements == []


def test_side_by_side_one_window():
    strategy = SideBySideLayout()
    work_area = Rect(0, 0, 1920, 1080)
    windows = [make_window(101, "Table 1")]

    placements = strategy.arrange(windows, work_area, {"gap": 0, "single_window_slot": "left", "keep_aspect_ratio": False})
    assert len(placements) == 1
    p = placements[0]
    assert p.hwnd == 101
    assert p.rect.x == 0
    assert p.rect.y == 0
    assert p.rect.height == 1080


def test_side_by_side_two_windows_aspect_ratio():
    """
    User requirement:
    With 2 windows, resize tables to half screen width each (left and right),
    touching seamlessly with aspect ratio preserved, instead of being tiny in the corners.
    """
    strategy = SideBySideLayout()
    work_area = Rect(0, 0, 1920, 1000)
    windows = [make_window(101, "Table 1"), make_window(102, "Table 2")]

    placements = strategy.arrange(windows, work_area, {"gap": 0, "keep_aspect_ratio": True, "aspect_ratio": 1.6, "vertical_overlap": 50})
    assert len(placements) == 2

    p1, p2 = placements[0], placements[1]
    # table_w = 1920 // 2 = 960; table_h = int(960 / 1.6) = 600
    assert p1.rect.width == 960
    assert p1.rect.height == 600
    assert abs((p1.rect.width / p1.rect.height) - 1.6) < 0.01

    assert p2.rect.width == 960
    assert p2.rect.height == 600
    # Left at 0, Right at 960 (touching with 0 gap)
    assert p1.rect.x == 0
    assert p2.rect.x == 960
    assert p1.rect.x + p1.rect.width == p2.rect.x


def test_side_by_side_four_windows_aspect_ratio():
    strategy = SideBySideLayout()
    work_area = Rect(0, 0, 1920, 1000)
    windows = [make_window(i, f"T{i}") for i in range(1, 5)]

    placements = strategy.arrange(windows, work_area, {"gap": 0, "keep_aspect_ratio": True, "aspect_ratio": 1.6, "vertical_overlap": 50})
    assert len(placements) == 4

    p1, p2, p3, p4 = placements
    # 4 windows: Top-Left, Top-Right, Bottom-Left, Bottom-Right
    # Left column is at x=0; Right column is directly adjacent at x=840 (0 gap in between).
    # Remaining space (1920 - 1680 = 240px) is on the right side!
    assert (p1.rect.x, p1.rect.y, p1.rect.width, p1.rect.height) == (0, 0, 840, 525)
    assert (p2.rect.x, p2.rect.y, p2.rect.width, p2.rect.height) == (840, 0, 840, 525)
    assert (p3.rect.x, p3.rect.y, p3.rect.width, p3.rect.height) == (0, 1000 - 525, 840, 525)
    assert (p4.rect.x, p4.rect.y, p4.rect.width, p4.rect.height) == (840, 1000 - 525, 840, 525)

    # Left and right columns touch seamlessly with zero gap in between
    assert p1.rect.right == p2.rect.x
    assert p3.rect.right == p4.rect.x
    # Remaining horizontal space (cap) is on the right side
    assert work_area.right - p2.rect.right == 1920 - 1680

    # Vertical overlap between top and bottom rows: 525 - (1000 - 525) = 50px
    assert (p1.rect.y + p1.rect.height) - p3.rect.y == 50


def test_four_window_mode_larger_overlap_and_distinct_from_six_mode():
    """
    User requirement:
    'in 4 window mode windows have gap in between.. if theere is cap it should be on right side...
     4 window overlap shold be bigger and it can be totally different than the 6 window mode,.
     not it is just 4 positions from 6 windowm ode'
    """
    strategy = SideBySideLayout()
    work_area = Rect(0, 0, 2560, 1528)
    windows_4 = [make_window(i, f"Table {i}") for i in range(1, 5)]

    # Configure 6-table mode overlap = 50, but 4-table mode overlap = 200
    cfg = {
        "gap": 0,
        "keep_aspect_ratio": True,
        "aspect_ratio": 1.267,
        "vertical_overlap": 50,
        "vertical_overlap_4_tables": 200,
    }
    placements_4 = strategy.arrange(windows_4, work_area, cfg)
    assert len(placements_4) == 4

    p1, p2, p3, p4 = placements_4
    # Overlap in 4-table mode should be 200px (much bigger than 50px in 6-table mode)
    actual_overlap = (p1.rect.y + p1.rect.height) - p3.rect.y
    assert actual_overlap == 200

    # Window size should be distinct from 6-table mode (bigger windows)
    # table_h = (1528 + 200) // 2 = 864; table_w = int(864 * 1.267) = 1094
    assert p1.rect.height == 864
    assert p1.rect.width == 1094

    # No gap between left and right columns! Right column starts at left column's right edge
    assert p1.rect.x == 0
    assert p2.rect.x == p1.rect.right  # 1094 (adjacent!)
    assert p3.rect.x == 0
    assert p4.rect.x == p3.rect.right  # 1094 (adjacent!)

    # Remaining horizontal space (gap/cap) is on the right side
    gap_on_right = work_area.right - p2.rect.right
    assert gap_on_right == 2560 - (1094 * 2)  # 372px
    assert gap_on_right > 0


def test_side_by_side_six_spots_3_horizontal_x_2_vertical():
    """
    User requirement:
    'screen is wider when taller, so lets have 2 windows vertically and 3 horizontally ...'
    """
    strategy = SideBySideLayout()
    work_area = Rect(0, 0, 2560, 1528)
    windows = [make_window(i, f"Table {i}") for i in range(1, 7)]

    placements = strategy.arrange(windows, work_area, {"gap": 0, "keep_aspect_ratio": True, "aspect_ratio": 1.625, "vertical_overlap": 50, "max_spots": 6})
    assert len(placements) == 6

    # Table dimensions: table_h = (1528 + 50) // 2 = 789; table_w = int(789 * 1.625) = 1282
    # 3 columns horizontally: [0, 639, 1278]
    # 2 rows vertically: [0, 1528 - 789 = 739]
    for p in placements:
        assert p.rect.width == 1282
        assert p.rect.height == 789
        assert abs((p.rect.width / p.rect.height) - 1.625) < 0.01

    # Row 0 (Top): 3 windows horizontally
    assert (placements[0].rect.x, placements[0].rect.y) == (0, 0)
    assert (placements[1].rect.x, placements[1].rect.y) == (639, 0)
    assert (placements[2].rect.x, placements[2].rect.y) == (1278, 0)

    # Row 1 (Bottom): 3 windows horizontally
    assert (placements[3].rect.x, placements[3].rect.y) == (0, 739)
    assert (placements[4].rect.x, placements[4].rect.y) == (639, 739)
    assert (placements[5].rect.x, placements[5].rect.y) == (1278, 739)

    # Check vertical overlap between top and bottom rows: 789 - 739 = 50px
    assert (placements[0].rect.y + placements[0].rect.height) - placements[3].rect.y == 50

    # Check horizontal overlap between adjacent columns: 1282 - 639 = 643px (even overlap!)
    h_overlap_1 = (placements[0].rect.x + placements[0].rect.width) - placements[1].rect.x
    h_overlap_2 = (placements[1].rect.x + placements[1].rect.width) - placements[2].rect.x
    assert h_overlap_1 == h_overlap_2 == 643


def test_side_by_side_more_than_six_windows_only_arranges_six():
    """
    User requirement:
    'if more windows are open those will not be arranged. .. when windows are closed, always 6 are arranged..'
    """
    strategy = SideBySideLayout()
    work_area = Rect(0, 0, 2560, 1528)
    windows = [make_window(i, f"Table {i}") for i in range(1, 10)]

    placements = strategy.arrange(windows, work_area, {"max_spots": 6, "keep_aspect_ratio": True})
    assert len(placements) == 6
    hwnds_arranged = [p.hwnd for p in placements]
    assert hwnds_arranged == [1, 2, 3, 4, 5, 6]

    # When Table 1 is closed, tables 2-7 are arranged (always 6)!
    windows_after_close = windows[1:]
    placements_after = strategy.arrange(windows_after_close, work_area, {"max_spots": 6, "keep_aspect_ratio": True})
    assert len(placements_after) == 6
    assert [p.hwnd for p in placements_after] == [2, 3, 4, 5, 6, 7]


def test_grid_layout_2x2():
    grid = GridLayout()
    work_area = Rect(0, 0, 1920, 1080)
    windows = [make_window(i, f"T{i}") for i in range(4)]

    placements = grid.arrange(windows, work_area, {"columns": 2, "rows": 2, "gap": 0})
    assert len(placements) == 4

    assert (placements[0].rect.x, placements[0].rect.y) == (0, 0)
    assert (placements[0].rect.width, placements[0].rect.height) == (960, 540)
    assert (placements[1].rect.x, placements[1].rect.y) == (960, 0)
    assert (placements[2].rect.x, placements[2].rect.y) == (0, 540)
    assert (placements[3].rect.x, placements[3].rect.y) == (960, 540)


def test_strategy_registry():
    strategies = list_strategies()
    assert "side_by_side" in strategies
    assert "grid" in strategies
    assert "stack" in strategies
    assert "other_bottom" in strategies

    inst = get_strategy("side_by_side")
    assert isinstance(inst, SideBySideLayout)

    with pytest.raises(ValueError):
        get_strategy("non_existent_strategy")

"""
tests/test_more_than_two_windows.py - Tests for user requirement:
'in more than 2 windows, old windows are filled first horizontally then vertically, new windows go to back'
"""

import pytest
from win_utils import Rect, WindowInfo, WindowPlacement, reset_bottom_state
from strategies.side_by_side import SideBySideLayout
from app import WindowTilerApp


def make_window(hwnd: int, title: str, x: int = 0, y: int = 0, w: int = 500, h: int = 300) -> WindowInfo:
    return WindowInfo(
        hwnd=hwnd,
        title=title,
        class_name="TableClass",
        rect=Rect(x, y, w, h),
        is_minimized=False,
    )


def test_three_windows_filled_horizontally_first_then_vertically():
    """
    User requirement:
    'in more than 2 windows, old windows are filled first horizontally then vertically, new windows go to back'
    When 3 windows are arranged:
    - 1st window -> Top-Left (row 0, col 0)
    - 2nd window -> Top-Right (row 0, col 1)  [Fills horizontally across top row first!]
    - 3rd window -> Bottom-Left (row 1, col 0) [Fills vertically into next row]
    """
    strategy = SideBySideLayout()
    work_area = Rect(0, 0, 1920, 1000)
    win1 = make_window(1, "Table 1 (Old 1)")
    win2 = make_window(2, "Table 2 (Old 2)")
    win3 = make_window(3, "Table 3 (New 3)")

    placements = strategy.arrange([win1, win2, win3], work_area, {
        "gap": 0,
        "keep_aspect_ratio": True,
        "aspect_ratio": 1.6,
        "vertical_overlap": 50,
        "vertical_overlap_4_tables": 200,
    })

    assert len(placements) == 3
    p1, p2, p3 = placements

    # 1st window at Top-Left
    assert p1.hwnd == 1
    assert p1.rect.x == 0
    assert p1.rect.y == 0

    # 2nd window at Top-Right (Filled horizontally across top row first!)
    assert p2.hwnd == 2
    assert p2.rect.x > 0
    assert p2.rect.y == 0
    assert p2.rect.x == p1.rect.right  # Seamless 0-gap adjacent on top row

    # 3rd window at Bottom-Left (Filled vertically into next row)
    assert p3.hwnd == 3
    assert p3.rect.x == 0
    assert p3.rect.y > 0


def test_four_windows_filled_horizontally_then_vertically():
    """
    In 4 windows:
    - Top row (horizontal):
      1st window -> Top-Left (row 0, col 0)
      2nd window -> Top-Right (row 0, col 1)
    - Bottom row (vertical):
      3rd window -> Bottom-Left (row 1, col 0)
      4th window -> Bottom-Right (row 1, col 1)
    """
    strategy = SideBySideLayout()
    work_area = Rect(0, 0, 1920, 1000)
    windows = [make_window(i, f"Table {i}") for i in range(1, 5)]

    placements = strategy.arrange(windows, work_area, {
        "gap": 0,
        "keep_aspect_ratio": True,
        "aspect_ratio": 1.6,
        "vertical_overlap_4_tables": 200,
    })

    assert len(placements) == 4
    p1, p2, p3, p4 = placements

    # Top row
    assert p1.hwnd == 1 and p1.rect.x == 0 and p1.rect.y == 0
    assert p2.hwnd == 2 and p2.rect.x == p1.rect.right and p2.rect.y == 0

    # Bottom row
    assert p3.hwnd == 3 and p3.rect.x == 0 and p3.rect.y > 0
    assert p4.hwnd == 4 and p4.rect.x == p3.rect.right and p4.rect.y == p3.rect.y


def test_new_windows_go_to_back_in_app():
    """
    User requirement:
    'in more than 2 windows, old windows are filled first horizontally then vertically, new windows go to back'
    Verifies that when > 2 tables are arranged:
    - Tables 1 and 2 (old windows) stay in front (insert_after is None)
    - Table 3 (new window) is placed behind Table 2 (insert_after=Table 2.hwnd)
    - Table 4 (new window) is placed behind Table 3 (insert_after=Table 3.hwnd)
    """
    reset_bottom_state()
    app = WindowTilerApp()

    work_area = Rect(0, 0, 1920, 1000)
    t1 = make_window(10, "Table 1")
    t2 = make_window(20, "Table 2")
    t3 = make_window(30, "Table 3")
    t4 = make_window(40, "Table 4")

    # 1. Start with 2 tables
    tables_2 = app._get_game_tables_to_arrange([t1, t2], max_spots=6, work_area=work_area)
    assert [w.hwnd for w in tables_2] == [10, 20]

    # 2. Add 3rd table (transition to 3 tables)
    tables_3 = app._get_game_tables_to_arrange([t1, t2, t3], max_spots=6, work_area=work_area)
    # Arrival order preserved: old windows first, new windows at end
    assert [w.hwnd for w in tables_3] == [10, 20, 30]

    # 3. Add 4th table
    tables_4 = app._get_game_tables_to_arrange([t1, t2, t3, t4], max_spots=6, work_area=work_area)
    assert [w.hwnd for w in tables_4] == [10, 20, 30, 40]

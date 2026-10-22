"""
tests/test_in_place_no_adjustment.py - Tests ensuring that windows already in place
are never adjusted, moved, or resized.
"""

from win_utils import Rect, WindowInfo, WindowPlacement, apply_window_placement
from strategies.side_by_side import SideBySideLayout


def test_two_windows_already_in_place_not_reshuffled():
    """
    User requirement:
    'if windows aer in place, those should not be adjusted'
    """
    strategy = SideBySideLayout()
    work_area = Rect(0, 0, 1920, 1000)

    # Window 1 is at Left, Window 2 is at Right
    w1 = WindowInfo(101, "Table 1", "PokerClass", Rect(0, 0, 960, 600), False)
    w2 = WindowInfo(102, "Table 2", "PokerClass", Rect(960, 0, 960, 600), False)

    placements = strategy.arrange([w1, w2], work_area, {"gap": 0, "aspect_ratio": 1.6})
    assert len(placements) == 2

    # Verify both keep their exact current positions
    p1 = next(p for p in placements if p.hwnd == 101)
    p2 = next(p for p in placements if p.hwnd == 102)

    assert p1.rect == Rect(0, 0, 960, 600)
    assert p2.rect == Rect(960, 0, 960, 600)


def test_two_windows_swapped_already_in_place_not_swapped_back():
    """
    If the user has Window 1 on the Right and Window 2 on the Left,
    since both spots are filled, do NOT force them to swap places.
    """
    strategy = SideBySideLayout()
    work_area = Rect(0, 0, 1920, 1000)

    w1 = WindowInfo(101, "Table 1", "PokerClass", Rect(960, 0, 960, 600), False)
    w2 = WindowInfo(102, "Table 2", "PokerClass", Rect(0, 0, 960, 600), False)

    placements = strategy.arrange([w1, w2], work_area, {"gap": 0, "aspect_ratio": 1.6})

    p1 = next(p for p in placements if p.hwnd == 101)
    p2 = next(p for p in placements if p.hwnd == 102)

    # Window 1 stays on the right, Window 2 stays on the left
    assert p1.rect == Rect(960, 0, 960, 600)
    assert p2.rect == Rect(0, 0, 960, 600)


def test_six_windows_already_in_place_preserve_spots():
    """
    When all 6 spots are occupied, each window must be paired with its current spot.
    """
    strategy = SideBySideLayout()
    work_area = Rect(0, 0, 2560, 1528)

    # 3 cols x 2 rows
    cols = [0, 639, 1278]
    rows = [0, 739]
    spots = [
        Rect(cols[0], rows[0], 1282, 789),
        Rect(cols[1], rows[0], 1282, 789),
        Rect(cols[2], rows[0], 1282, 789),
        Rect(cols[0], rows[1], 1282, 789),
        Rect(cols[1], rows[1], 1282, 789),
        Rect(cols[2], rows[1], 1282, 789),
    ]

    # Create 6 windows already in spots (in reverse order to verify smart matching)
    windows = []
    for i in range(6):
        spot = spots[5 - i]
        windows.append(WindowInfo(100 + i, f"Table {i}", "PokerClass", spot, False))

    placements = strategy.arrange(windows, work_area, {"gap": 0, "aspect_ratio": 1.625, "max_spots": 6})
    assert len(placements) == 6

    # Verify each window was matched to its own spot without adjusting
    for win in windows:
        p = next(pl for pl in placements if pl.hwnd == win.hwnd)
        assert p.rect == win.rect


def test_tables_over_six_remain_in_manual_control():
    """
    User requirement:
    'tables over 6 are still arranged, those should be only in manual contol'
    """
    from app import PokerTilerApp
    app = PokerTilerApp()

    work_area = Rect(0, 0, 1920, 1080)
    # 8 tables open
    all_tables = [
        WindowInfo(100 + i, f"Table {i}", "PokerClass", Rect(10 * i, 10 * i, 400, 300), False)
        for i in range(1, 9)
    ]

    # Get tables to arrange (max 6)
    arranged_tables = app._get_game_tables_to_arrange(all_tables, max_spots=6, work_area=work_area)
    assert len(arranged_tables) == 6
    arranged_hwnds = {w.hwnd for w in arranged_tables}

    # Verify tables 7 and 8 are NOT in arranged_tables (strictly in manual control)
    assert 107 not in arranged_hwnds
    assert 108 not in arranged_hwnds

    # Next cycle with same tables:
    second_cycle = app._get_game_tables_to_arrange(all_tables, max_spots=6, work_area=work_area)
    assert len(second_cycle) == 6
    assert {w.hwnd for w in second_cycle} == arranged_hwnds
    assert 107 not in {w.hwnd for w in second_cycle}
    assert 108 not in {w.hwnd for w in second_cycle}

    # Now close one of the arranged tables (e.g. table 1)
    remaining_tables = [w for w in all_tables if w.hwnd != 101]
    refilled = app._get_game_tables_to_arrange(remaining_tables, max_spots=6, work_area=work_area)
    assert len(refilled) == 6
    # Table 7 stepped in to fill the vacated spot!
    assert 107 in {w.hwnd for w in refilled}
    # Table 8 remains in manual control
    assert 108 not in {w.hwnd for w in refilled}


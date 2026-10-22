"""
tests/test_reuse_window_slots.py - Tests for 'reuse window slots' configuration.

Verifies:
  - Default (empty) ignores overflow windows.
  - "last" / "last slot" places all overflow windows into the last slot.
  - "recycle" places 1st overflow into 1st slot, 2nd into 2nd slot, etc.
  - Works with side_by_side, custom, and grid strategies.
  - Config key variations ("reuse window slots", "reuse_window_slots", "reuse_slots").
"""

import pytest
from win_utils import Rect, WindowInfo, WindowPlacement
from strategies.base import normalize_reuse_mode, ArrangementStrategy
from strategies.side_by_side import SideBySideLayout
from strategies.custom_layout import CustomLayout
from strategies.grid import GridLayout


def make_test_windows(count: int, width: int = 400, height: int = 300) -> list[WindowInfo]:
    """Helper to create dummy WindowInfo objects."""
    return [
        WindowInfo(
            hwnd=1000 + i,
            title=f"Table {i + 1} - Hold'em",
            rect=Rect(100 + i * 20, 100 + i * 20, width, height),
            class_name="PokerTableClass",
            is_minimized=False,
        )
        for i in range(count)
    ]


# ------------------------------------------------------------------------------
# 1. Normalization tests
# ------------------------------------------------------------------------------

def test_normalize_reuse_mode():
    # Empty / default cases
    assert normalize_reuse_mode("") == ""
    assert normalize_reuse_mode(None) == ""
    assert normalize_reuse_mode("ignore") == ""
    assert normalize_reuse_mode("none") == ""
    assert normalize_reuse_mode("empty") == ""

    # "last" / "last slot" variations
    assert normalize_reuse_mode("last") == "last"
    assert normalize_reuse_mode("last slot") == "last"
    assert normalize_reuse_mode("last_slot") == "last"
    assert normalize_reuse_mode("LAST") == "last"
    assert normalize_reuse_mode("Last Slot") == "last"

    # "recycle" variations
    assert normalize_reuse_mode("recycle") == "recycle"
    assert normalize_reuse_mode("RECYCLE") == "recycle"
    assert normalize_reuse_mode("repeat") == "recycle"
    assert normalize_reuse_mode("cycle") == "recycle"
    assert normalize_reuse_mode("loop") == "recycle"


# ------------------------------------------------------------------------------
# 2. Side-by-Side Strategy with Reuse Window Slots
# ------------------------------------------------------------------------------

def test_side_by_side_default_ignores_overflow_windows():
    """Default (empty) ignores windows beyond 6 spots."""
    strat = SideBySideLayout()
    windows = make_test_windows(8)
    work_area = Rect(0, 0, 1920, 1080)
    config = {"max_spots": 6, "reuse_window_slots": ""}

    placements = strat.arrange(windows, work_area, config)
    # Only 6 windows are arranged
    assert len(placements) == 6
    hwnds = [p.hwnd for p in placements]
    assert 1006 not in hwnds
    assert 1007 not in hwnds


def test_side_by_side_last_slot_places_all_overflow_to_last_slot():
    """'last' or 'last slot' sends all overflow windows to the last slot (spot 5)."""
    strat = SideBySideLayout()
    windows = make_test_windows(8)
    work_area = Rect(0, 0, 1920, 1080)

    for mode in ("last", "last slot", "LAST_SLOT"):
        config = {"max_spots": 6, "reuse_window_slots": mode}
        placements = strat.arrange(windows, work_area, config)

        # All 8 windows must be arranged
        assert len(placements) == 8

        # Last spot is the placement of window 6 (index 5)
        last_slot_rect = placements[5].rect

        # Windows 6 and 7 (hwnds 1006 and 1007) are overflow and must go to last_slot_rect
        p6 = next(p for p in placements if p.hwnd == 1006)
        p7 = next(p for p in placements if p.hwnd == 1007)

        assert p6.rect.x == last_slot_rect.x
        assert p6.rect.y == last_slot_rect.y
        assert p6.rect.width == last_slot_rect.width
        assert p6.rect.height == last_slot_rect.height

        assert p7.rect.x == last_slot_rect.x
        assert p7.rect.y == last_slot_rect.y


def test_side_by_side_recycle_slots_in_order():
    """'recycle' puts 1st overflow to 1st slot, 2nd to 2nd slot, etc."""
    strat = SideBySideLayout()
    windows = make_test_windows(9)  # 6 base + 3 overflow
    work_area = Rect(0, 0, 1920, 1080)
    config = {"max_spots": 6, "reuse_window_slots": "recycle"}

    placements = strat.arrange(windows, work_area, config)
    assert len(placements) == 9

    slot_0_rect = placements[0].rect
    slot_1_rect = placements[1].rect
    slot_2_rect = placements[2].rect

    # 1st overflow (hwnd 1006) -> slot 0
    p6 = next(p for p in placements if p.hwnd == 1006)
    assert p6.rect.x == slot_0_rect.x
    assert p6.rect.y == slot_0_rect.y

    # 2nd overflow (hwnd 1007) -> slot 1
    p7 = next(p for p in placements if p.hwnd == 1007)
    assert p7.rect.x == slot_1_rect.x
    assert p7.rect.y == slot_1_rect.y

    # 3rd overflow (hwnd 1008) -> slot 2
    p8 = next(p for p in placements if p.hwnd == 1008)
    assert p8.rect.x == slot_2_rect.x
    assert p8.rect.y == slot_2_rect.y


# ------------------------------------------------------------------------------
# 3. Custom Layout Strategy with Reuse Window Slots
# ------------------------------------------------------------------------------

def test_custom_layout_default_ignores_windows_without_a_box(tmp_path):
    """Custom layout default ignores windows that exceed available boxes."""
    layout_file = tmp_path / "custom_3_slots.json"
    layout_file.write_text(
        '{"slots": ['
        '{"x": 0, "y": 0, "width": 640, "height": 480},'
        '{"x": 640, "y": 0, "width": 640, "height": 480},'
        '{"x": 1280, "y": 0, "width": 640, "height": 480}'
        ']}',
        encoding="utf-8",
    )

    strat = CustomLayout()
    windows = make_test_windows(5)  # 5 windows, only 3 boxes
    work_area = Rect(0, 0, 1920, 1080)
    config = {
        "layout_name": str(layout_file),
        "reuse_window_slots": "",
    }

    placements = strat.arrange(windows, work_area, config)
    assert len(placements) == 3


def test_custom_layout_last_slot_places_overflow_to_last_box(tmp_path):
    """Custom layout 'last' sends all overflow windows to the last defined box."""
    layout_file = tmp_path / "custom_3_slots.json"
    layout_file.write_text(
        '{"slots": ['
        '{"x": 0, "y": 0, "width": 640, "height": 480},'
        '{"x": 640, "y": 0, "width": 640, "height": 480},'
        '{"x": 1280, "y": 0, "width": 640, "height": 480}'
        ']}',
        encoding="utf-8",
    )

    strat = CustomLayout()
    windows = make_test_windows(5)  # 5 windows, 3 boxes -> 2 overflow
    work_area = Rect(0, 0, 1920, 1080)
    config = {
        "layout_name": str(layout_file),
        "reuse_window_slots": "last",
    }

    placements = strat.arrange(windows, work_area, config)
    assert len(placements) == 5

    box_2_rect = placements[2].rect  # 3rd slot (index 2)
    p3 = next(p for p in placements if p.hwnd == 1003)
    p4 = next(p for p in placements if p.hwnd == 1004)

    assert p3.rect.x == box_2_rect.x
    assert p3.rect.y == box_2_rect.y
    assert p4.rect.x == box_2_rect.x
    assert p4.rect.y == box_2_rect.y


def test_custom_layout_recycle_slots(tmp_path):
    """Custom layout 'recycle' cycles overflow windows back to slot 0, slot 1, etc."""
    layout_file = tmp_path / "custom_3_slots.json"
    layout_file.write_text(
        '{"slots": ['
        '{"x": 0, "y": 0, "width": 640, "height": 480},'
        '{"x": 640, "y": 0, "width": 640, "height": 480},'
        '{"x": 1280, "y": 0, "width": 640, "height": 480}'
        ']}',
        encoding="utf-8",
    )

    strat = CustomLayout()
    windows = make_test_windows(5)  # 3 base + 2 overflow
    work_area = Rect(0, 0, 1920, 1080)
    config = {
        "layout_name": str(layout_file),
        "reuse window slots": "recycle",  # test space-separated key
    }

    placements = strat.arrange(windows, work_area, config)
    assert len(placements) == 5

    box_0 = placements[0].rect
    box_1 = placements[1].rect

    # 1st overflow (hwnd 1003) -> box 0
    p3 = next(p for p in placements if p.hwnd == 1003)
    assert p3.rect.x == box_0.x
    assert p3.rect.y == box_0.y

    # 2nd overflow (hwnd 1004) -> box 1
    p4 = next(p for p in placements if p.hwnd == 1004)
    assert p4.rect.x == box_1.x
    assert p4.rect.y == box_1.y


# ------------------------------------------------------------------------------
# 4. Grid Layout Strategy with Reuse Window Slots
# ------------------------------------------------------------------------------

def test_grid_layout_recycle_slots():
    """Grid layout 2x2 with 6 windows: 4 base + 2 overflow recycled."""
    strat = GridLayout()
    windows = make_test_windows(6)
    work_area = Rect(0, 0, 1920, 1080)
    config = {
        "columns": 2,
        "rows": 2,
        "reuse_window_slots": "recycle",
    }

    placements = strat.arrange(windows, work_area, config)
    assert len(placements) == 6

    # Base cells:
    # Cell 0: col 0, row 0
    # Cell 1: col 1, row 0
    # Overflow window 4 -> Cell 0
    # Overflow window 5 -> Cell 1
    cell_0 = placements[0].rect
    cell_1 = placements[1].rect

    p4 = next(p for p in placements if p.hwnd == 1004)
    p5 = next(p for p in placements if p.hwnd == 1005)

    assert p4.rect.x == cell_0.x
    assert p4.rect.y == cell_0.y
    assert p5.rect.x == cell_1.x
    assert p5.rect.y == cell_1.y


# ------------------------------------------------------------------------------
# 5. App Integration Tests with Reuse Window Slots
# ------------------------------------------------------------------------------

def test_app_integration_with_reuse_slots(monkeypatch):
    """
    Verifies that PokerTilerApp passes all matched tables when reuse_window_slots is configured,
    and only max_spots tables when reuse_window_slots is empty.
    """
    from app import PokerTilerApp
    import win_utils

    app = PokerTilerApp()
    app.config["game_windows"]["reuse_window_slots"] = "last"
    app.config["game_windows"]["strategy"] = "side_by_side"
    app.game_strategy = SideBySideLayout()
    app.game_strategy_name = "side_by_side"

    test_windows = make_test_windows(8)
    monkeypatch.setattr(win_utils, "get_all_top_level_windows", lambda: test_windows)
    monkeypatch.setattr(win_utils, "is_placement_needed", lambda *args, **kwargs: True)

    placements_made = []
    monkeypatch.setattr(
        win_utils,
        "apply_window_placement",
        lambda p, **kwargs: placements_made.append(p) or True,
    )

    moved = app.arrange_windows(verbose=False)
    # With reuse_window_slots: 'last', all 8 tables should be arranged!
    assert moved == 8
    assert len(placements_made) == 8

    # Now change reuse_window_slots back to empty
    app.config["game_windows"]["reuse_window_slots"] = ""
    app.arranged_game_hwnds = []
    placements_made.clear()

    moved_empty = app.arrange_windows(verbose=False)
    # Only 6 tables should be arranged
    assert moved_empty == 6
    assert len(placements_made) == 6

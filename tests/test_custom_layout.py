"""
tests/test_custom_layout.py - Tests for custom slot-based layouts loaded from layouts/ directory.
Verifies:
  - Top-left alignment and aspect ratio preservation inside bounding boxes.
  - Windows without a box remain in manual control (never arranged).
  - Multi-monitor slot offset support.
  - File-based loading from layouts/ directory.
"""

from unittest.mock import patch
import pytest

from win_utils import Rect, WindowInfo, MonitorInfo
from strategies.custom_layout import CustomLayout
from strategies import get_strategy


def test_custom_layout_fits_box_top_left_width_constrained():
    """
    User requirement:
    'windows will go tho specified slots , to top left corner and resized so that it fits to the box without changing aspect ratio'
    """
    strategy = CustomLayout()
    work_area = Rect(0, 0, 1920, 1080)

    # Mock a layout with a single 800x600 box at (100, 50)
    mock_slots = [Rect(100, 50, 800, 600)]

    windows = [
        WindowInfo(1, "Table 1", "PokerClass", Rect(0, 0, 400, 300), False)
    ]

    with patch.object(strategy, "get_slots", return_value=mock_slots):
        placements = strategy.arrange(
            windows,
            work_area,
            {"keep_aspect_ratio": True, "aspect_ratio": 1.6},
        )

    assert len(placements) == 1
    p = placements[0]
    # Width = 800 -> Height = 800 / 1.6 = 500 (fits inside 600)
    assert p.rect.width == 800
    assert p.rect.height == 500
    # Must be aligned to top-left corner of the box
    assert p.rect.x == 100
    assert p.rect.y == 50
    # Aspect ratio preserved
    assert abs((p.rect.width / p.rect.height) - 1.6) < 0.01


def test_custom_layout_fits_box_top_left_height_constrained():
    """
    When the box is wider than the table's aspect ratio allows,
    the table height fills the box height, and width is scaled down,
    staying anchored at the top-left corner.
    """
    strategy = CustomLayout()
    work_area = Rect(0, 0, 1920, 1080)

    # Wide / short box: 800x400 at (200, 150)
    mock_slots = [Rect(200, 150, 800, 400)]

    windows = [
        WindowInfo(1, "Table 1", "PokerClass", Rect(0, 0, 400, 300), False)
    ]

    with patch.object(strategy, "get_slots", return_value=mock_slots):
        placements = strategy.arrange(
            windows,
            work_area,
            {"keep_aspect_ratio": True, "aspect_ratio": 1.6},
        )

    assert len(placements) == 1
    p = placements[0]
    # Height = 400 -> Width = 400 * 1.6 = 640 (fits inside 800)
    assert p.rect.width == 640
    assert p.rect.height == 400
    # Top-left corner
    assert p.rect.x == 200
    assert p.rect.y == 150
    assert abs((p.rect.width / p.rect.height) - 1.6) < 0.01


def test_windows_without_a_box_remain_unarranged():
    """
    User requirement:
    'windows that do not have a box, are manually controller...'
    """
    strategy = CustomLayout()
    work_area = Rect(0, 0, 1920, 1080)

    # Layout with only 2 boxes
    mock_slots = [
        Rect(0, 0, 800, 500),
        Rect(850, 0, 800, 500),
    ]

    # 4 windows open
    windows = [
        WindowInfo(101, "Table 1", "PokerClass", Rect(0, 0, 400, 300), False),
        WindowInfo(102, "Table 2", "PokerClass", Rect(0, 0, 400, 300), False),
        WindowInfo(103, "Table 3", "PokerClass", Rect(0, 0, 400, 300), False),
        WindowInfo(104, "Table 4", "PokerClass", Rect(0, 0, 400, 300), False),
    ]

    with patch.object(strategy, "get_slots", return_value=mock_slots):
        # max_spots matches slot count (2)
        assert strategy.get_max_spots({}) == 2

        placements = strategy.arrange(
            windows,
            work_area,
            {"keep_aspect_ratio": True, "aspect_ratio": 1.6},
        )

    # Exactly 2 windows arranged; Tables 3 and 4 have NO box and are NOT in placements!
    assert len(placements) == 2
    arranged_hwnds = {p.hwnd for p in placements}
    assert 103 not in arranged_hwnds
    assert 104 not in arranged_hwnds


def test_multi_monitor_support_with_monitor_index():
    """
    User requirement:
    'layout can use multiple monitors, see that it is supported..'
    """
    strategy = CustomLayout()

    # Mock 2 monitors: Monitor 0 at (0, 0, 1920, 1080) and Monitor 1 at (1920, 0, 1920, 1080)
    mock_monitors = [
        MonitorInfo(0, "\\\\.\\DISPLAY1", True, Rect(0, 0, 1920, 1080), Rect(0, 0, 1920, 1040)),
        MonitorInfo(1, "\\\\.\\DISPLAY2", False, Rect(1920, 0, 1920, 1080), Rect(1920, 0, 1920, 1040)),
    ]

    layout_data = {
        "name": "multi_mon_test",
        "slots": [
            {"monitor": 0, "x": 10, "y": 20, "width": 800, "height": 500},
            {"monitor": 1, "x": 30, "y": 40, "width": 900, "height": 550},
        ],
    }

    with patch("strategies.custom_layout.win_utils.get_all_monitors", return_value=mock_monitors), \
         patch("strategies.custom_layout.load_layout_file", return_value=(layout_data, None)):

        slots = strategy.get_slots({"layout_name": "multi_mon_test"})

    assert len(slots) == 2
    # Monitor 0: 0 + 10 = 10, 0 + 20 = 20
    assert (slots[0].x, slots[0].y, slots[0].width, slots[0].height) == (10, 20, 800, 500)
    # Monitor 1: 1920 + 30 = 1950, 0 + 40 = 40
    assert (slots[1].x, slots[1].y, slots[1].width, slots[1].height) == (1950, 40, 900, 550)


def test_strategy_registration_and_layout_name_resolution():
    """
    Verify 'custom' is registered in the strategy registry, and layout names
    in layouts/ resolve to CustomLayout automatically.
    """
    strat = get_strategy("custom")
    assert isinstance(strat, CustomLayout)

    # 'testlayout' is a file in layouts/
    strat2 = get_strategy("testlayout")
    assert isinstance(strat2, CustomLayout)

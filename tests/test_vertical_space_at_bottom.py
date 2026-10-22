"""
tests/test_vertical_space_at_bottom.py - Tests ensuring that when aspect ratio leaves
vertical space, the empty space is placed at the bottom of the screen, never in the middle.
"""

from win_utils import Rect, WindowInfo
from strategies.side_by_side import SideBySideLayout


def test_vertical_space_placed_at_bottom_four_windows():
    """
    User requirement:
    'if the aspect ratio is so that there is spece between windows vertically,
     the space should be at the bottom not like this'
    """
    strategy = SideBySideLayout()
    # Tall display: 1920x1400
    work_area = Rect(0, 0, 1920, 1400)
    windows = [
        WindowInfo(i, f"T{i}", "PokerClass", Rect(0, 0, 960, 500), False)
        for i in range(1, 5)
    ]

    # Aspect ratio 1.6: table_w = 960 -> table_h = 600
    # 2 rows with vertical overlap 50px:
    # Row 0: y = 0, height = 600 (occupies [0, 600])
    # Row 1: y = 600 - 50 = 550, height = 600 (occupies [550, 1150])
    # Overlap between rows: exactly 50px (NO vertical gap in the middle!)
    # Remaining space: 1400 - 1150 = 250px at the bottom!
    placements = strategy.arrange(
        windows,
        work_area,
        {"gap": 0, "keep_aspect_ratio": True, "aspect_ratio": 1.6, "vertical_overlap": 50},
    )
    assert len(placements) == 4

    p1, p2, p3, p4 = placements
    # Row 0 top-left and top-right
    assert p1.rect.y == 0
    assert p2.rect.y == 0

    # Row 1 bottom-left and bottom-right
    # Must NOT be pushed down to work_area.height - table_h (1400 - 600 = 800)
    # which would leave a 200px gap in the middle!
    assert p3.rect.y == 550
    assert p4.rect.y == 550

    # Verify overlap in the middle
    assert (p1.rect.y + p1.rect.height) - p3.rect.y == 50

    # Verify all remaining empty space is at the bottom
    bottom_of_row1 = p3.rect.y + p3.rect.height  # 1150
    space_at_bottom = work_area.bottom - bottom_of_row1  # 250
    assert space_at_bottom == 250
    assert space_at_bottom > 0


def test_vertical_space_placed_at_bottom_six_windows():
    strategy = SideBySideLayout()
    # High-res tall display: 2560x1800
    work_area = Rect(0, 0, 2560, 1800)
    windows = [
        WindowInfo(i, f"Table {i}", "PokerClass", Rect(0, 0, 800, 500), False)
        for i in range(1, 7)
    ]

    # table_h = (1800 + 50) // 2 = 925
    # table_w = int(925 * 1.625) = 1503
    # Since 3 columns need to fit 2560 with overlap, let's test fixed aspect ratio
    placements = strategy.arrange(
        windows,
        work_area,
        {"gap": 0, "keep_aspect_ratio": True, "aspect_ratio": 1.625, "vertical_overlap": 50, "max_spots": 6},
    )
    assert len(placements) == 6

    # Row 0 windows are at y = 0
    for i in range(3):
        assert placements[i].rect.y == 0

    table_h = placements[0].rect.height
    expected_row1_y = table_h - 50

    # Row 1 windows must be at expected_row1_y touching Row 0 with 50px overlap
    for i in range(3, 6):
        assert placements[i].rect.y == expected_row1_y

    # Space is at the bottom
    bottom_of_row1 = expected_row1_y + table_h
    assert work_area.bottom >= bottom_of_row1

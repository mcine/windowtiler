"""
tests/test_two_windows_stability.py - Regression test verifying that 2 tables are large
and that auxiliary windows (lobbies) never balloon or cause game tables to shrink over time.
"""

from app import PokerTilerApp
from win_utils import Rect, WindowInfo, WindowPlacement
from strategies.side_by_side import SideBySideLayout
from strategies.other_bottom import OtherBottomLayout


def test_two_tables_aspect_ratio_and_resizing():
    """
    User requirement:
    'with 2 windows the game windwos are getting smaller all the time and lobby is growing. ...
     also the game tables are at sidet, but really small... apps should resize them but keep the aspect ratio'
    """
    side_by_side = SideBySideLayout()
    work_area = Rect(0, 0, 1920, 800)  # 1920x1080 display with 280px reserved for lobby

    tables = [
        WindowInfo(1, "Table 1", "PokerClass", Rect(10, 10, 400, 300), False),
        WindowInfo(2, "Table 2", "PokerClass", Rect(50, 50, 400, 300), False),
    ]

    cfg = {"gap": 0, "keep_aspect_ratio": True, "aspect_ratio": 1.625}
    placements = side_by_side.arrange(tables, work_area, cfg)
    assert len(placements) == 2

    p1, p2 = placements[0], placements[1]
    # Each table should be resized to half screen width: 1920 // 2 = 960
    assert p1.rect.width == 960
    # Height should preserve aspect ratio: 960 / 1.625 = 590
    assert p1.rect.height == 590
    assert p2.rect.width == 960
    assert p2.rect.height == 590

    # Left and Right positions
    assert p1.rect.x == 0
    assert p2.rect.x == 960
    # Tables must touch seamlessly with 0 gap
    assert p1.rect.x + p1.rect.width == p2.rect.x


def test_two_tables_zero_gap_when_height_constrained():
    """
    User requirement:
    'there is still cap between 2 windows configuration.'
    Ensures that even when height constraints reduce table width (e.g. aspect ratio 1.35 on 1707x663 area),
    the two tables touch seamlessly with 0 gap between them (p1.rect.x + p1.rect.width == p2.rect.x).
    """
    side_by_side = SideBySideLayout()
    work_area = Rect(0, 0, 1707, 663)

    tables = [
        WindowInfo(1, "Table 1", "PokerClass", Rect(10, 10, 666, 494), False),
        WindowInfo(2, "Table 2", "PokerClass", Rect(50, 50, 666, 494), False),
    ]

    cfg = {"gap": 0, "keep_aspect_ratio": True, "aspect_ratio": "auto"}
    placements = side_by_side.arrange(tables, work_area, cfg)
    assert len(placements) == 2

    p1, p2 = placements[0], placements[1]
    # Tables must touch seamlessly with 0 gap
    assert p1.rect.x + p1.rect.width == p2.rect.x
    # Tables must fill the whole screen width (from 0 to work_area.right)
    assert p1.rect.x == 0
    assert p2.rect.right == work_area.right


def test_two_tables_fill_whole_screen_width():
    """
    User requirement:
    '2 window version should fill the whole screen widht, now there is a cap'
    Verifies that on a 2560x1528 (or 2560x1150) display, the 2 tables divide the entire
    screen width in half (1280px each) with 0 gap, completely filling the screen width.
    """
    side_by_side = SideBySideLayout()
    work_area = Rect(0, 0, 2560, 1150)

    tables = [
        WindowInfo(1, "Table 1", "PokerClass", Rect(0, 0, 1000, 789), False),
        WindowInfo(2, "Table 2", "PokerClass", Rect(1000, 0, 1000, 789), False),
    ]

    cfg = {"gap": 0, "keep_aspect_ratio": True, "aspect_ratio": "auto"}
    placements = side_by_side.arrange(tables, work_area, cfg)
    assert len(placements) == 2

    p1, p2 = placements[0], placements[1]
    # Both tables must have width 1280 (half of 2560)
    assert p1.rect.width == 1280
    assert p2.rect.width == 1280
    # Left at 0, Right at 1280
    assert p1.rect.x == 0
    assert p2.rect.x == 1280
    # Left touches right with 0 gap
    assert p1.rect.right == p2.rect.x
    # Right edge touches screen right edge (2560) - completely filling screen width
    assert p2.rect.right == work_area.right


def test_lobby_size_stability_across_cycles():
    """
    Simulate multiple layout cycles to ensure the lobby height never grows,
    preventing the game tables work area from shrinking.
    """
    app = PokerTilerApp()
    initial_lobby_rect = Rect(x=0, y=800, width=460, height=220)
    work_area = Rect(0, 0, 1920, 1080)

    curr_rect = initial_lobby_rect
    for cycle in range(10):
        lobby = WindowInfo(hwnd=999, title="PokerStars Main Lobby", class_name="LobbyClass", rect=curr_rect, is_minimized=False)
        game_area, bottom_area, send_bottom = app.split_work_areas(
            work_area,
            matched_other=[lobby],
            game_window_count=2,
        )

        other_placements = app.other_strategy.arrange([lobby], bottom_area, {"resize": False, "gap": 0})
        assert len(other_placements) == 1
        p = other_placements[0]

        # Verify allow_resize is strictly False
        assert p.allow_resize is False
        # Height must remain exactly 220
        assert p.rect.height == 220
        assert p.rect.width == 460
        # Bottom area height must stay constant at 220
        assert bottom_area.height == 220
        # Game area height must stay constant at 1080 - 220 = 860
        assert game_area.height == 860

        # Update rect for next cycle
        curr_rect = p.rect

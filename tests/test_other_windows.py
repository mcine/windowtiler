"""
tests/test_other_windows.py - Tests for auxiliary 'other poker windows' arranged at bottom.
"""

from win_utils import Rect, WindowInfo
from strategies.other_bottom import OtherBottomLayout
from app import WindowTilerApp, PokerTilerApp


def make_win(hwnd: int, title: str = "Lobby", w: int = 500, h: int = 400) -> WindowInfo:
    return WindowInfo(
        hwnd=hwnd,
        title=title,
        class_name="LobbyClass",
        rect=Rect(50, 50, w, h),
        is_minimized=False,
    )


def test_other_bottom_single_window_not_resized():
    """
    User requirement:
    'main lobby was at bottom, but it should not be resized'
    """
    layout = OtherBottomLayout()
    work_area = Rect(0, 0, 1920, 1080)
    # Lobby window has original size 600x450
    windows = [make_win(1, "Main Lobby", w=600, h=450)]

    placements = layout.arrange(windows, work_area, {"resize": False, "gap": 2})
    assert len(placements) == 1
    p = placements[0]
    assert p.hwnd == 1
    # Width and height MUST BE PRESERVED
    assert p.rect.width == 600
    assert p.rect.height == 450
    # Position MUST BE AT THE BOTTOM
    assert p.rect.x == 0
    assert p.rect.y == 1080 - 450  # 630
    assert p.allow_resize is False


def test_other_bottom_multiple_windows_not_resized():
    layout = OtherBottomLayout()
    work_area = Rect(0, 0, 1920, 1080)
    windows = [
        make_win(1, "Lobby", w=500, h=400),
        make_win(2, "Cashier", w=400, h=350),
    ]

    gap = 10
    placements = layout.arrange(windows, work_area, {"resize": False, "gap": gap})
    assert len(placements) == 2

    p1, p2 = placements[0], placements[1]
    # First window
    assert p1.rect.width == 500
    assert p1.rect.height == 400
    assert p1.rect.x == 0
    assert p1.rect.y == 1080 - 400
    assert p1.allow_resize is False

    # Second window side-by-side
    assert p2.rect.width == 400
    assert p2.rect.height == 350
    assert p2.rect.x == 500 + 10  # 510
    assert p2.rect.y == 1080 - 350
    assert p2.allow_resize is False


def test_screen_split_with_unresized_other_windows():
    app = WindowTilerApp()
    work_area = Rect(0, 0, 1920, 1000)
    lobby = make_win(1, "Lobby", w=800, h=300)

    # Case A: When <= 2 game tables are open:
    # Lobby is visible at bottom (height 300), game tables take upper portion (700)
    game_area, bottom_area, send_bottom = app.split_work_areas(
        work_area, matched_other=[lobby], game_window_count=2
    )
    assert bottom_area.height == 300
    assert bottom_area.y == 1000 - 300  # 700
    assert game_area.y == 0
    assert game_area.height == 1000 - 300  # 700
    assert send_bottom is False

    # Case B: When > 2 game tables are open (e.g. 3 or 4 tables):
    # Game tables take the WHOLE screen (height 1000), lobby stays in background (send_bottom=True)
    game_area_4, bottom_area_4, send_bottom_4 = app.split_work_areas(
        work_area, matched_other=[lobby], game_window_count=4
    )
    assert game_area_4.height == 1000  # FULL SCREEN!
    assert game_area_4.y == 0
    assert send_bottom_4 is True

    # Case C: When no other windows exist: game tables get full screen
    game_area_full, bottom_area_empty, send_bottom_0 = app.split_work_areas(
        work_area, matched_other=[], game_window_count=1
    )
    assert game_area_full.height == 1000
    assert bottom_area_empty.height == 0


def test_other_bottom_placement_allow_resize_is_false():
    """
    Verify that placements generated for other windows explicitly have allow_resize=False
    so Win32 applies SWP_NOSIZE and prevents window ballooning or size drift.
    """
    layout = OtherBottomLayout()
    work_area = Rect(0, 0, 1920, 1080)
    windows = [make_win(1, "Lobby", w=500, h=400)]

    placements = layout.arrange(windows, work_area, {"resize": False, "gap": 0})
    assert len(placements) == 1
    assert placements[0].allow_resize is False


def test_second_other_window_placed_next_to_first_window():
    """
    User requirement:
    'second other window goes missing, it should go to bottom next to first one'
    Guarantees that:
    1. Second auxiliary window goes to bottom directly next to first one when it fits.
    2. Zero gap / configured gap is maintained.
    3. Both are bottom-aligned at work_area.bottom.
    4. Size is untouched (allow_resize=False).
    """
    layout = OtherBottomLayout()
    work_area = Rect(0, 0, 2560, 534)
    win1 = make_win(1, "PokerStars Main Lobby", w=692, h=378)
    win2 = make_win(2, "Cashier", w=800, h=450)

    # 0 gap configuration
    placements = layout.arrange([win1, win2], work_area, {"resize": False, "gap": 0})
    assert len(placements) == 2

    p1, p2 = placements[0], placements[1]
    # First window at bottom left
    assert p1.rect.x == 0
    assert p1.rect.width == 692
    assert p1.rect.height == 378
    assert p1.rect.bottom == 534
    assert p1.allow_resize is False

    # Second window directly next to first one at the bottom
    assert p2.rect.x == p1.rect.right  # 692
    assert p2.rect.width == 800
    assert p2.rect.height == 450
    assert p2.rect.bottom == 534
    assert p2.allow_resize is False
    assert p2.rect.right <= work_area.right


def test_second_other_window_does_not_go_off_screen_to_right():
    """
    User requirements:
    1. 'for other windows only chaneg position, do not resize etc'
    2. 'SECOND other window went off screen to right'
    When second window is wide (e.g. Pokeri:Rangeja - notes with width=2404, height=1163)
    on a 2560 display:
    - Placing it at win1.x + win1.w would push it to x=692, right=3096 (536px off-screen!).
    - It must NOT be resized (allow_resize=False, natural 2404x1163 size preserved).
    - Its position must be adjusted so that it remains fully on screen (right edge <= work_area.right).
    - It is placed at x=2560 - 2404 = 156, right=2560.
    - Zero pixels spill off screen to the right!
    """
    layout = OtherBottomLayout()
    work_area = Rect(0, 0, 2560, 534)
    win1 = make_win(1, "PokerStars Main Lobby", w=692, h=378)
    win2 = make_win(2, "Pokeri:Rangeja - notes", w=2404, h=1163)

    placements = layout.arrange([win1, win2], work_area, {"resize": False, "gap": 0})
    assert len(placements) == 2

    p1, p2 = placements[0], placements[1]

    # First window keeps natural size and is positioned at bottom
    assert p1.rect.x == 0
    assert p1.rect.width == 692
    assert p1.rect.height == 378
    assert p1.rect.bottom == 534
    assert p1.allow_resize is False

    # Second window:
    # 1. Natural dimensions strictly preserved (never resized)
    assert p2.rect.width == 2404
    assert p2.rect.height == 1163
    assert p2.allow_resize is False
    # 2. Bottom-aligned at work_area.bottom
    assert p2.rect.bottom == 534
    # 3. MUST NOT GO OFF SCREEN TO RIGHT!
    assert p2.rect.right <= work_area.right
    assert p2.rect.right == 2560
    assert p2.rect.x == 2560 - 2404  # 156
    assert p2.rect.x >= work_area.x

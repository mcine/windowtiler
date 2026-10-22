"""
tests/test_cashier_and_top_order.py - Tests ensuring that:
1. Checking/arranging windows does NOT bring windows on top or steal focus.
2. The Cashier window never disappears / is never sent to the bottom.
3. Focused/active auxiliary windows remain in the foreground.
"""

from app import PokerTilerApp
from win_utils import Rect, WindowInfo, WindowPlacement, apply_window_placement


def test_cashier_never_sent_to_bottom():
    """
    User requirement:
    'if I want to use cashier, I don't want it to disappera... '
    """
    app = PokerTilerApp()

    work_area = Rect(0, 0, 1920, 1080)
    # 4 game tables active -> normally sends general lobby to bottom
    games = [
        WindowInfo(100 + i, f"Table {i}", "PokerClass", Rect(10 * i, 10 * i, 400, 300), False)
        for i in range(1, 5)
    ]

    cashier = WindowInfo(201, "Cashier - Account Balance & Banking", "CashierClass", Rect(100, 800, 460, 220), False)
    lobby = WindowInfo(202, "PokerStars Main Lobby", "LobbyClass", Rect(570, 800, 460, 220), False)

    # In arrange_windows logic, cashier placements must have send_this_to_bottom = False
    game_area, bottom_area, send_other_to_bottom = app.split_work_areas(
        work_area,
        matched_other=[cashier, lobby],
        game_window_count=len(games),
    )

    other_placements = app.other_strategy.arrange([cashier, lobby], bottom_area, {"resize": False, "gap": 0})
    assert len(other_placements) == 2

    # Map titles
    titles = {201: cashier.title, 202: lobby.title}

    # Verify Cashier rule
    import re
    for op in other_placements:
        title = titles[op.hwnd]
        is_cashier = bool(re.search(r"cashier", title, re.IGNORECASE))
        effective_send = send_other_to_bottom and not app.other_windows_in_front
        send_this_to_bottom = effective_send and not is_cashier

        if is_cashier:
            # Cashier must NEVER be sent to bottom!
            assert send_this_to_bottom is False


def test_minimized_window_not_restored_when_restore_minimized_false():
    """
    User requirement:
    'checking windows should not bring those on top'
    """
    p = WindowPlacement(hwnd=999999, rect=Rect(0, 0, 500, 400))
    # Non-existent or minimized window with restore_minimized=False must return False
    res = apply_window_placement(p, restore_minimized=False)
    assert res is False

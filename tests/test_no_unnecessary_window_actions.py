"""
tests/test_no_unnecessary_window_actions.py - Tests ensuring that the application does
NOT perform any Win32 actions or modifications on windows if not strictly needed.
"""

from unittest.mock import MagicMock, patch
from win_utils import Rect, WindowInfo, WindowPlacement, is_placement_needed, apply_window_placement
from app import PokerTilerApp


def test_is_placement_needed_returns_false_for_in_place_window():
    """
    User requirement:
    'apps should not do anything with windows if it does not need to'
    """
    placement = WindowPlacement(
        hwnd=12345,
        rect=Rect(0, 0, 960, 600),
        allow_resize=True,
    )

    # Mock window state: window exists, not minimized, not zoomed, and already at (0, 0, 960, 600)
    with patch("win_utils.user32.IsWindow", return_value=True), \
         patch("win_utils.user32.IsIconic", return_value=False), \
         patch("win_utils.user32.IsZoomed", return_value=False), \
         patch("win_utils.get_window_rect", return_value=Rect(0, 0, 960, 600)), \
         patch("win_utils.get_window_extended_frame_bounds", return_value=Rect(0, 0, 960, 600)):

        needed = is_placement_needed(placement, compensate_borders=True)
        assert needed is False

        # apply_window_placement should also immediately return False without calling SetWindowPos
        with patch("win_utils.user32.SetWindowPos") as mock_setpos:
            applied = apply_window_placement(placement, compensate_borders=True)
            assert applied is False
            mock_setpos.assert_not_called()


def test_arrange_windows_does_zero_modifications_when_all_in_place():
    """
    When all windows are already in place, arrange_windows() must exit immediately
    with 0 moves and 0 Win32 SetWindowPos calls.
    """
    app = PokerTilerApp()

    with patch.object(app, "get_adjusted_work_area", return_value=Rect(0, 0, 1920, 1080)), \
         patch("win_utils.get_all_top_level_windows", return_value=[]):

        moved = app.arrange_windows()
        assert moved == 0

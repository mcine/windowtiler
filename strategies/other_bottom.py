"""
strategies/other_bottom.py - Layout strategy for 'other poker windows' at the bottom of the screen.

Arranges auxiliary windows (main lobbies, cashiers, tournament lobbies, HUD, notes)
side-by-side along the bottom edge of the monitor work area.
Preserves their original window dimensions (allow_resize=False) without resizing,
changing only their positions (x, y) so windows are placed along the bottom without
ever extending off-screen to the right.
"""

from typing import Any, Dict, List
from win_utils import Rect, WindowInfo, WindowPlacement
from strategies.base import ArrangementStrategy


class OtherBottomLayout(ArrangementStrategy):
    """
    Arranges other/auxiliary poker windows side-by-side along the bottom of the screen.
    Preserves original window dimensions (resize=False, allow_resize=False), strictly
    changing only position (x, y) unless resize is explicitly requested in config.
    Guarantees that windows never spill off-screen to the right by anchoring to the right
    screen edge when necessary.
    """

    name: str = "other_bottom"
    description: str = "Positions auxiliary windows side-by-side along the bottom edge"

    def arrange(
        self,
        windows: List[WindowInfo],
        work_area: Rect,
        config: Dict[str, Any],
    ) -> List[WindowPlacement]:
        if not windows:
            return []

        gap = int(config.get("gap", 2))
        should_resize = bool(config.get("resize", False))
        alignment = str(config.get("alignment", "left")).lower()

        placements: List[WindowPlacement] = []
        n = len(windows)

        if not should_resize:
            # Strictly change position only (x, y); do not resize under any circumstance
            total_gaps = gap * (n - 1)
            total_windows_w = sum(win.rect.width for win in windows) + total_gaps

            if alignment == "right":
                curr_x = max(work_area.x, work_area.right - total_windows_w)
            elif alignment == "center":
                curr_x = work_area.x + max(0, (work_area.width - total_windows_w) // 2)
            else:  # 'left' default
                curr_x = work_area.x

            for win in windows:
                w = win.rect.width
                h = win.rect.height

                # Ensure window never spills off-screen to the right.
                # If placing at curr_x would push it past the right edge of the work area,
                # anchor its right edge to work_area.right while strictly preserving width.
                if curr_x + w > work_area.right:
                    x = max(work_area.x, work_area.right - w)
                else:
                    x = curr_x

                # Bottom-aligned to work area bottom
                y = work_area.bottom - h

                placements.append(
                    WindowPlacement(
                        hwnd=win.hwnd,
                        rect=Rect(x=x, y=y, width=w, height=h),
                        allow_resize=False,
                    )
                )
                curr_x = x + w + gap

            return placements

        # If resize is explicitly set to True
        total_w = work_area.width
        h = work_area.height
        base_x = work_area.x
        base_y = work_area.y

        total_gaps = gap * (n - 1)
        col_w = max(100, (total_w - total_gaps) // n)

        for i, win in enumerate(windows):
            x = base_x + i * (col_w + gap)
            w = col_w if i < n - 1 else (total_w - (x - base_x))
            placements.append(
                WindowPlacement(
                    hwnd=win.hwnd,
                    rect=Rect(x=x, y=base_y, width=w, height=h),
                    allow_resize=True,
                )
            )

        return placements

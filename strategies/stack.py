"""
strategies/stack.py - Stacked / Cascading arrangement strategy.
"""

from typing import Any, Dict, List
from win_utils import Rect, WindowInfo, WindowPlacement
from strategies.base import ArrangementStrategy


class StackLayout(ArrangementStrategy):
    """
    Arranges windows in a stacked or cascading layout with configurable offsets.
    Useful for multi-tabling in a single focal area.
    """

    name: str = "stack"
    description: str = "Stacks windows at the same position or cascaded with offset"

    def arrange(
        self,
        windows: List[WindowInfo],
        work_area: Rect,
        config: Dict[str, Any],
    ) -> List[WindowPlacement]:
        if not windows:
            return []

        offset_x = int(config.get("offset_x", 30))
        offset_y = int(config.get("offset_y", 30))
        width_ratio = float(config.get("width_ratio", 0.8))
        height_ratio = float(config.get("height_ratio", 0.8))

        target_w = int(work_area.width * width_ratio)
        target_h = int(work_area.height * height_ratio)

        placements: List[WindowPlacement] = []
        for i, win in enumerate(windows):
            x = work_area.x + i * offset_x
            y = work_area.y + i * offset_y

            # Keep within work area boundaries
            if x + target_w > work_area.right:
                x = work_area.x
            if y + target_h > work_area.bottom:
                y = work_area.y

            placements.append(WindowPlacement(hwnd=win.hwnd, rect=Rect(x=x, y=y, width=target_w, height=target_h)))

        return placements

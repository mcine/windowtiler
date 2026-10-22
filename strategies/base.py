"""
strategies/base.py - Base class for poker window arranging strategies.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from win_utils import Rect, WindowInfo, WindowPlacement


def normalize_reuse_mode(val: Any) -> str:
    """
    Normalizes 'reuse window slots' configuration values:
      - "" (empty, default): ignore overflow windows
      - "last": all overflow windows go to last slot ("last", "last slot", "last_slot")
      - "recycle": puts 1st overflow in 1st slot, 2nd in 2nd slot, etc. ("recycle", "repeat", "cycle")
    """
    if not val:
        return ""
    s = str(val).strip().lower()
    if s in ("last", "last slot", "last_slot", "lastslot"):
        return "last"
    if s in ("recycle", "repeat", "cycle", "loop"):
        return "recycle"
    return ""


class ArrangementStrategy(ABC):
    """
    Abstract base class for all window arranging strategies.
    To add a new arranging method:
      1. Subclass ArrangementStrategy
      2. Decorate with @register_strategy("your_layout_name")
      3. Implement the arrange() method
      4. In config.yaml, set strategy: "your_layout_name"
    """

    name: str = "base"
    description: str = "Base layout strategy"

    @abstractmethod
    def arrange(
        self,
        windows: List[WindowInfo],
        work_area: Rect,
        config: Dict[str, Any],
    ) -> List[WindowPlacement]:
        """
        Calculates the target placement (x, y, width, height) for each window.
        """
        raise NotImplementedError

    def get_max_spots(self, config: Dict[str, Any]) -> int:
        """
        Returns the maximum number of windows this strategy arranges on screen.
        Tables beyond this count remain unarranged in manual control.
        """
        return int(config.get("max_spots", 6))

    @classmethod
    def get_reuse_mode(cls, config: Dict[str, Any]) -> str:
        """
        Resolves normalized reuse mode from config keys ('reuse_window_slots', 'reuse window slots', etc.).
        """
        val = (
            config.get("reuse_window_slots")
            if "reuse_window_slots" in config
            else config.get("reuse window slots")
            if "reuse window slots" in config
            else config.get("reuse_slots")
            if "reuse_slots" in config
            else config.get("reuse slots")
            if "reuse slots" in config
            else config.get("overflow_handling")
            if "overflow_handling" in config
            else config.get("overflow")
            if "overflow" in config
            else ""
        )
        return normalize_reuse_mode(val)

    @classmethod
    def assign_windows_to_spots(
        cls,
        windows: List[WindowInfo],
        spots: List[Rect],
        reuse_mode: str = "",
    ) -> List[WindowPlacement]:
        """
        Assigns windows to target spots:
        1. Windows already in or near a spot (within 30px) keep that spot and are NOT adjusted.
        2. Remaining unplaced windows fill remaining available spots in natural spot order.
        3. Overflow windows (more windows than spots) are handled according to reuse_mode:
           - "" (empty, default): overflow windows are ignored (not assigned).
           - "last" / "last slot": all overflow windows go to the last slot (spots[-1]).
           - "recycle": 1st overflow goes to 1st slot, 2nd to 2nd slot, etc. (spots[of_idx % len(spots)]).
        """
        if not windows or not spots:
            return []

        placements_map: Dict[int, Rect] = {}
        paired_windows = set()
        paired_spots = set()

        # Pass 1: Windows already in place (within 30px position & size)
        for w_idx, win in enumerate(windows):
            best_spot_idx = None
            best_dist = float("inf")
            for s_idx, spot in enumerate(spots):
                if s_idx in paired_spots:
                    continue
                dist = (
                    abs(win.rect.x - spot.x)
                    + abs(win.rect.y - spot.y)
                    + abs(win.rect.width - spot.width)
                    + abs(win.rect.height - spot.height)
                )
                if dist <= 30 and dist < best_dist:
                    best_dist = dist
                    best_spot_idx = s_idx

            if best_spot_idx is not None:
                paired_windows.add(w_idx)
                paired_spots.add(best_spot_idx)
                placements_map[win.hwnd] = spots[best_spot_idx]

        # Pass 2: Remaining windows (not yet placed) fill remaining spots in order
        remaining_wins = [w for i, w in enumerate(windows) if i not in paired_windows]
        remaining_spot_indices = [j for j in range(len(spots)) if j not in paired_spots]

        num_to_fill = min(len(remaining_wins), len(remaining_spot_indices))
        for idx in range(num_to_fill):
            win = remaining_wins[idx]
            s_idx = remaining_spot_indices[idx]
            placements_map[win.hwnd] = spots[s_idx]

        # Pass 3: Overflow windows handling
        overflow_wins = remaining_wins[num_to_fill:]
        if overflow_wins:
            norm_mode = normalize_reuse_mode(reuse_mode)
            if norm_mode == "last":
                # All overflow windows go to last slot
                last_spot = spots[-1]
                for win in overflow_wins:
                    placements_map[win.hwnd] = last_spot
            elif norm_mode == "recycle":
                # Put 1st overflow to 1st slot, 2nd to 2nd slot, etc.
                num_spots = len(spots)
                for of_idx, win in enumerate(overflow_wins):
                    target_spot_idx = of_idx % num_spots
                    placements_map[win.hwnd] = spots[target_spot_idx]
            else:
                # Default empty: ignores overflow windows
                pass

        # Return placements in original window order
        return [WindowPlacement(hwnd=w.hwnd, rect=placements_map[w.hwnd]) for w in windows if w.hwnd in placements_map]

    @staticmethod
    def _resolve_aspect_ratio(windows: List[WindowInfo], cfg_ratio: Any) -> float:
        """Determines the target aspect ratio (width / height) for poker windows."""
        if cfg_ratio not in ("auto", "", None):
            try:
                val = float(cfg_ratio)
                if val > 0:
                    return val
            except (ValueError, TypeError):
                pass

        for w in windows:
            if w.rect.height > 0:
                measured = w.rect.width / w.rect.height
                if 1.1 <= measured <= 2.2:
                    return measured

        return 1.625

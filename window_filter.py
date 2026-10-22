"""
window_filter.py - Filters windows matching poker criteria based on configuration.
Supports simple human-configurable string lists as well as regular expression patterns.
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Union
from win_utils import WindowInfo


class WindowFilter:
    """
    Filters windows matching criteria against window titles and class names.
    Supports:
      - Human-friendly string lists: if any string in the list is part of the title or class name,
        the window is matched (or excluded).
      - Regex pattern strings: backward compatible with existing regex configurations.
    """

    def __init__(
        self,
        title_pattern: Union[str, List[str]] = "",
        class_pattern: Union[str, List[str]] = "",
        exclude_title_pattern: Union[str, List[str]] = "",
        exclude_class_pattern: Union[str, List[str]] = "",
        case_sensitive: bool = False,
    ):
        self.case_sensitive = case_sensitive
        flags = 0 if case_sensitive else re.IGNORECASE

        # Title inclusion & exclusion
        self.title_substrings, self.title_regex = self._parse_pattern(title_pattern, flags)
        self.exclude_title_substrings, self.exclude_title_regex = self._parse_pattern(exclude_title_pattern, flags)

        # Class inclusion & exclusion
        self.class_substrings, self.class_regex = self._parse_pattern(class_pattern, flags)
        self.exclude_class_substrings, self.exclude_class_regex = self._parse_pattern(exclude_class_pattern, flags)

    @staticmethod
    def _parse_pattern(
        val: Any,
        flags: int,
    ) -> Tuple[List[str], Optional[re.Pattern]]:
        """
        Parses a filter value which can be:
          - A list of simple strings (e.g. ['Hold\'em', 'Omaha', 'Tournament', 'Table'])
          - A string (compiled as regex, falling back to literal substring)
          - Empty / None
        Returns (list_of_substrings, compiled_regex).
        """
        if not val:
            return [], None

        if isinstance(val, (list, tuple, set)):
            substrings = [str(item).strip() for item in val if str(item).strip()]
            return substrings, None

        if isinstance(val, str):
            s = val.strip()
            if not s:
                return [], None
            try:
                compiled = re.compile(s, flags)
                return [], compiled
            except re.error:
                return [s], None

        return [], None

    def _matches_item(
        self,
        text: str,
        substrings: List[str],
        regex: Optional[re.Pattern],
    ) -> bool:
        """Checks if text contains any substring or matches the compiled regex."""
        if not text:
            return False

        if substrings:
            if self.case_sensitive:
                return any(sub in text for sub in substrings)
            else:
                text_lower = text.lower()
                return any(sub.lower() in text_lower for sub in substrings)

        if regex:
            return bool(regex.search(text))

        return False

    @classmethod
    def from_config(cls, filter_cfg: Dict[str, Any]) -> "WindowFilter":
        """Builds a WindowFilter instance from the configuration dictionary."""
        # 1. Title inclusion: 'titles', 'title_keywords', 'title_pattern'
        titles = filter_cfg.get("titles")
        if titles is None:
            titles = filter_cfg.get("title_keywords", filter_cfg.get("title_pattern", []))

        # 2. Title/general exclusion: 'exclude', 'exclude_titles', 'exclude_title_keywords', 'exclude_title_pattern'
        exclude_titles = filter_cfg.get("exclude")
        if exclude_titles is None:
            exclude_titles = filter_cfg.get("exclude_titles")
        if exclude_titles is None:
            exclude_titles = filter_cfg.get("exclude_title_keywords", filter_cfg.get("exclude_title_pattern", []))

        # 3. Class inclusion: 'classes', 'class_pattern', 'class_names', 'class_list'
        classes = filter_cfg.get("classes")
        if classes is None:
            classes = filter_cfg.get("class_pattern", filter_cfg.get("class_names", filter_cfg.get("class_list", [])))

        # 4. Class exclusion: 'exclude_classes', 'exclude_class_pattern', 'exclude_class_names', 'exclude_class_list'
        exclude_classes = filter_cfg.get("exclude_classes")
        if exclude_classes is None:
            exclude_classes = filter_cfg.get("exclude_class_pattern", filter_cfg.get("exclude_class_names", filter_cfg.get("exclude_class_list", [])))

        return cls(
            title_pattern=titles,
            class_pattern=classes,
            exclude_title_pattern=exclude_titles,
            exclude_class_pattern=exclude_classes,
            case_sensitive=bool(filter_cfg.get("case_sensitive", False)),
        )

    def matches(self, window: WindowInfo) -> bool:
        """Determines if a window matches the filter criteria."""
        # 1. Exclude checks first
        if self._matches_item(window.title, self.exclude_title_substrings, self.exclude_title_regex):
            return False

        if self._matches_item(window.class_name, self.exclude_class_substrings, self.exclude_class_regex):
            return False

        # If general exclude strings were provided and no separate exclude_classes was specified,
        # allow general exclude strings to match window.class_name as well
        if not (self.exclude_class_substrings or self.exclude_class_regex):
            if self._matches_item(window.class_name, self.exclude_title_substrings, None):
                return False

        # 2. Inclusion checks
        has_title_criteria = bool(self.title_substrings or self.title_regex)
        has_class_criteria = bool(self.class_substrings or self.class_regex)

        # If neither title nor class criteria is given, match nothing by default
        if not has_title_criteria and not has_class_criteria:
            return False

        if has_title_criteria and not self._matches_item(window.title, self.title_substrings, self.title_regex):
            return False

        if has_class_criteria and not self._matches_item(window.class_name, self.class_substrings, self.class_regex):
            return False

        return True

    def filter(self, windows: List[WindowInfo], sort_by: str = "hwnd") -> List[WindowInfo]:
        """
        Filters a list of windows, keeping only matching ones.
        Optionally sorts them by 'hwnd', 'title', or 'position' (left-to-right).
        """
        matched = [w for w in windows if self.matches(w)]

        if sort_by == "title":
            matched.sort(key=lambda w: w.title.lower())
        elif sort_by == "position":
            matched.sort(key=lambda w: (w.rect.x, w.rect.y))
        else:  # default 'hwnd' gives stable ordering
            matched.sort(key=lambda w: w.hwnd)

        return matched

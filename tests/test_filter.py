"""
tests/test_filter.py - Unit tests for window identification filter.
"""

from win_utils import Rect, WindowInfo
from window_filter import WindowFilter


def make_win(hwnd: int, title: str, class_name: str = "DummyClass") -> WindowInfo:
    return WindowInfo(
        hwnd=hwnd,
        title=title,
        class_name=class_name,
        rect=Rect(0, 0, 100, 100),
        is_minimized=False,
    )


def test_filter_matches_title_regex():
    wf = WindowFilter(title_pattern=r"Hold'em|Omaha")
    assert wf.matches(make_win(1, "Table 1 - $1/$2 NL Hold'em"))
    assert wf.matches(make_win(2, "Omaha PL 6-max"))
    assert not wf.matches(make_win(3, "Google Chrome"))


def test_filter_matches_class_name():
    wf = WindowFilter(class_pattern=r"PokerStarsTableFrame")
    assert wf.matches(make_win(1, "Anything", "PokerStarsTableFrame"))
    assert not wf.matches(make_win(2, "Anything", "Chrome_WidgetWin_1"))


def test_filter_exclude_patterns():
    wf = WindowFilter(
        title_pattern=r"PokerStars",
        exclude_title_pattern=r"Lobby|Cashier",
    )
    assert wf.matches(make_win(1, "PokerStars - Table 42"))
    # Excluded
    assert not wf.matches(make_win(2, "PokerStars Lobby"))
    assert not wf.matches(make_win(3, "PokerStars Cashier"))


def test_filter_sorting():
    wf = WindowFilter(title_pattern=r"Table")
    wins = [
        make_win(30, "Table Charlie"),
        make_win(10, "Table Alpha"),
        make_win(20, "Table Bravo"),
    ]

    by_hwnd = wf.filter(wins, sort_by="hwnd")
    assert [w.hwnd for w in by_hwnd] == [10, 20, 30]

    by_title = wf.filter(wins, sort_by="title")
    assert [w.title for w in by_title] == ["Table Alpha", "Table Bravo", "Table Charlie"]


def test_filter_matches_human_friendly_string_list():
    """
    User requirement:
    'simplify this "title_pattern: ".*(Hold'em|Omaha|Tournament|NLH \\d+|Table.*-).*|.*\\bTable\\b.*""
     .. it is not human configurable.. list that contains string that if those are part of a title,
     it is counted as game window... exclude should work the same'
    """
    wf = WindowFilter(
        title_pattern=["Hold'em", "Omaha", "Tournament", "Table", "NLH"],
        exclude_title_pattern=["Lobby", "Cashier", "Tournament Lobby"],
    )

    # Inclusion matching (substring match)
    assert wf.matches(make_win(1, "Table 1 - $1/$2 NL Hold'em"))
    assert wf.matches(make_win(2, "Omaha PL 6-max"))
    assert wf.matches(make_win(3, "500/1000 NLH Deepstack"))
    assert wf.matches(make_win(4, "Daily Tournament #123"))
    assert wf.matches(make_win(5, "Table #402"))

    # Non-matching
    assert not wf.matches(make_win(6, "Google Chrome"))
    assert not wf.matches(make_win(7, "Visual Studio Code"))

    # Exclusion matching (substring match)
    assert not wf.matches(make_win(8, "PokerStars Main Lobby"))
    assert not wf.matches(make_win(9, "Cashier - Deposits & Withdrawals"))
    assert not wf.matches(make_win(10, "Tournament Lobby - Event #42"))


def test_filter_from_config_with_titles_and_exclude_titles():
    """Verify WindowFilter.from_config supports 'titles' and 'exclude_titles' keys."""
    cfg = {
        "titles": ["Hold'em", "Omaha", "Table"],
        "exclude_titles": ["Lobby", "Cashier"],
    }
    wf = WindowFilter.from_config(cfg)

    assert wf.matches(make_win(1, "Table 1 - Hold'em"))
    assert wf.matches(make_win(2, "Omaha Table"))
    assert not wf.matches(make_win(3, "Hold'em Lobby"))
    assert not wf.matches(make_win(4, "Cashier Window"))
    assert not wf.matches(make_win(5, "Unrelated Window"))


def test_filter_class_pattern_and_exclude_as_lists():
    """
    User requirement:
    'change class_pattern and exclude to this list configuration'
    Verifies that:
    - 'classes' or 'class_pattern' accepts a list of class name strings.
    - 'exclude' or 'exclude_titles' accepts a list of excluded title strings.
    - 'exclude_classes' or 'exclude_class_pattern' accepts a list of excluded class name strings.
    """
    cfg = {
        "titles": ["Table", "Hold'em"],
        "exclude": ["Lobby", "Cashier"],
        "classes": ["PokerStarsTableFrame"],
        "exclude_classes": ["CabinetWClass", "Chrome_WidgetWin_1", "Progman"],
    }
    wf = WindowFilter.from_config(cfg)

    # Valid game table with matching title and matching class
    assert wf.matches(make_win(1, "Table #1 - $1/$2 Hold'em", "PokerStarsTableFrame"))

    # Matching title but excluded class
    assert not wf.matches(make_win(2, "Table #1 - $1/$2 Hold'em", "Chrome_WidgetWin_1"))
    assert not wf.matches(make_win(3, "Table #1 - $1/$2 Hold'em", "CabinetWClass"))

    # Matching class but excluded title
    assert not wf.matches(make_win(4, "PokerStars Table Lobby", "PokerStarsTableFrame"))

    # Non-matching class
    assert not wf.matches(make_win(5, "Table #1 - $1/$2 Hold'em", "DifferentWindowClass"))


def test_filter_class_pattern_and_exclude_class_pattern_keys_with_lists():
    """Verifies that class_pattern and exclude_class_pattern work directly with list values."""
    cfg = {
        "titles": ["Hold'em"],
        "class_pattern": ["PokerStarsTableFrame", "GGTableFrame"],
        "exclude": ["Lobby"],
        "exclude_class_pattern": ["CabinetWClass", "Chrome_WidgetWin_1"],
    }
    wf = WindowFilter.from_config(cfg)

    assert wf.matches(make_win(1, "NL Hold'em $5/$10", "PokerStarsTableFrame"))
    assert wf.matches(make_win(2, "NL Hold'em $5/$10", "GGTableFrame"))
    assert not wf.matches(make_win(3, "NL Hold'em $5/$10", "Chrome_WidgetWin_1"))
    assert not wf.matches(make_win(4, "NL Hold'em Lobby", "PokerStarsTableFrame"))


def test_filter_general_exclude_matches_class_when_no_exclude_classes_specified():
    """If someone puts a class name directly in general 'exclude', it excludes matching classes."""
    cfg = {
        "titles": ["Table"],
        "exclude": ["Lobby", "CabinetWClass"],
    }
    wf = WindowFilter.from_config(cfg)

    assert wf.matches(make_win(1, "Table #1", "AnyNormalClass"))
    assert not wf.matches(make_win(2, "Table #1", "CabinetWClass"))
    assert not wf.matches(make_win(3, "Table Lobby", "AnyNormalClass"))

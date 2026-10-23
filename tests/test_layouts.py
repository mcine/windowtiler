"""
tests/test_layouts.py - Unit tests for Layout saving, loading, listing, and launcher integration.
"""

import json
from pathlib import Path
import tempfile
import pytest

from test_window_launcher import (
    get_layout_dir,
    find_layout_file,
    list_layouts,
    save_layout_file,
    load_layout_file,
    delete_layout_file,
    TestWindowLauncher,
)


@pytest.fixture
def temp_layout_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


def test_save_and_load_layout_json(temp_layout_dir):
    data = {
        "name": "test_3_tables",
        "game_count": 3,
        "other_count": 1,
        "game_windows": [
            {"title": "Table 1", "subtitle": "NLH", "color": "#111", "geometry": "400x300+10+10"},
            {"title": "Table 2", "subtitle": "PLO", "color": "#222", "geometry": "400x300+50+50"},
            {"title": "Table 3", "subtitle": "MTT", "color": "#333", "geometry": "400x300+90+90"},
        ],
        "other_windows": [
            {"title": "Main Lobby", "subtitle": "Lobby", "color": "#444", "geometry": "500x200+10+500"}
        ],
    }

    saved_file = save_layout_file("test_3_tables", data, temp_layout_dir)
    assert saved_file.is_file()
    assert saved_file.name == "test_3_tables.json"

    loaded_data, loaded_path = load_layout_file("test_3_tables", temp_layout_dir)
    assert loaded_path == saved_file
    assert loaded_data["name"] == "test_3_tables"
    assert loaded_data["game_count"] == 3
    assert len(loaded_data["game_windows"]) == 3
    assert loaded_data["game_windows"][0]["title"] == "Table 1"
    assert len(loaded_data["other_windows"]) == 1


def test_list_and_delete_layouts(temp_layout_dir):
    save_layout_file("layout_a", {"name": "layout_a"}, temp_layout_dir)
    save_layout_file("layout_b", {"name": "layout_b"}, temp_layout_dir)
    save_layout_file("layout_c.yaml", {"name": "layout_c"}, temp_layout_dir)

    layouts = list_layouts(temp_layout_dir)
    assert "layout_a" in layouts
    assert "layout_b" in layouts
    assert "layout_c" in layouts

    # Delete layout_b
    deleted = delete_layout_file("layout_b", temp_layout_dir)
    assert deleted is True

    remaining = list_layouts(temp_layout_dir)
    assert "layout_b" not in remaining
    assert "layout_a" in remaining

    # Deleting non-existent returns False
    assert delete_layout_file("non_existent", temp_layout_dir) is False


def test_find_layout_file_with_extensions(temp_layout_dir):
    save_layout_file("alpha.json", {"name": "alpha"}, temp_layout_dir)

    # Find by exact name
    p1 = find_layout_file("alpha.json", temp_layout_dir)
    assert p1 is not None and p1.name == "alpha.json"

    # Find without extension
    p2 = find_layout_file("alpha", temp_layout_dir)
    assert p2 is not None and p2.name == "alpha.json"

    # Non-existent
    assert find_layout_file("does_not_exist", temp_layout_dir) is None


def test_load_non_existent_layout_raises(temp_layout_dir):
    with pytest.raises(FileNotFoundError):
        load_layout_file("missing_layout", temp_layout_dir)


def test_default_project_layouts_exist():
    """Verify that default preset layouts are in place and valid."""
    default_dir = get_layout_dir()
    available = list_layouts(default_dir)
    assert "testlayout" in available

    for name in ("testlayout",):
        data, path = load_layout_file(name, default_dir)
        slots = data.get("slots") or data.get("game_windows")
        assert len(slots) > 0
        # Verify slots contain only x, y, width, height (no title, subtitle, color, or geometry)
        for s in slots:
            assert "x" in s and "y" in s and "width" in s and "height" in s
            assert "title" not in s
            assert "subtitle" not in s
            assert "color" not in s
            assert "geometry" not in s


def test_launcher_save_and_load_integration(temp_layout_dir):
    """
    Test that TestWindowLauncher saves only slots (no titles, subtitles, geometry, or color)
    and can accurately restore windows from slot coordinates.
    """
    launcher = TestWindowLauncher(
        initial_games=2,
        initial_others=1,
        layout_dir=str(temp_layout_dir),
    )
    launcher.root.withdraw()  # Hide UI during testing

    try:
        assert len(launcher.game_windows) == 2
        assert len(launcher.other_windows) == 1

        # Add one more game table
        launcher.add_game_window()
        assert len(launcher.game_windows) == 3

        # Save layout
        saved_path = launcher.save_layout("integration_test_layout")
        assert saved_path is not None
        assert saved_path.is_file()

        # Verify saved layout structure contains ONLY slots, no title/subtitle/color/geometry
        saved_json = json.loads(saved_path.read_text(encoding="utf-8"))
        assert "slots" in saved_json
        assert len(saved_json["slots"]) == 3
        for slot in saved_json["slots"]:
            assert set(slot.keys()).issubset({"x", "y", "width", "height", "monitor"})
            assert "title" not in slot
            assert "subtitle" not in slot
            assert "color" not in slot
            assert "geometry" not in slot

        # Change table count
        launcher.set_game_count(1)
        assert len(launcher.game_windows) == 1

        # Load back saved layout - window tool automatically generates names, subtitles, and colors
        success = launcher.load_layout("integration_test_layout")
        assert success is True
        assert len(launcher.game_windows) == 3
        assert len(launcher.other_windows) == 1

        # Delete saved layout
        del_success = launcher.delete_layout("integration_test_layout")
        assert del_success is True
        assert not saved_path.exists()
    finally:
        launcher.close_all_windows()
        launcher.root.destroy()

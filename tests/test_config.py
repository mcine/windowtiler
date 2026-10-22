"""
tests/test_config.py - Tests configuration loading and file modification monitoring.
"""

import os
import time
import tempfile
import yaml
from config_manager import ConfigManager, DEFAULT_CONFIG


def test_default_config_creation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = os.path.join(tmp_dir, "config.yaml")
        cm = ConfigManager(config_path=config_path)

        cfg = cm.load()
        assert os.path.exists(config_path)
        assert cfg["game_windows"]["strategy"] == "default"
        assert "game_windows" in cfg
        assert "other_windows" in cfg
        assert "rng" in cfg
        assert "runtime" in cfg
        assert cm.check_interval == 10.0


def test_config_hot_reload_on_file_change():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = os.path.join(tmp_dir, "config.yaml")
        reloaded_events = []

        cm = ConfigManager(
            config_path=config_path,
            on_change_callback=lambda new_cfg: reloaded_events.append(new_cfg),
            check_interval=0.01,  # Short interval for testing
        )
        cm.load()

        # Modify config file
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {
                    "game_windows": {"strategy": "grid", "filter": {"title_pattern": "MyPoker"}},
                    "rng": {"default_threshold": 60},
                },
                f,
            )

        time.sleep(0.05)

        updated = cm.check_for_updates(force=True)
        assert updated is not None
        assert updated["game_windows"]["strategy"] == "grid"
        assert updated["game_windows"]["filter"]["title_pattern"] == "MyPoker"
        assert updated["rng"]["default_threshold"] == 60
        assert len(reloaded_events) == 1


def test_invalid_syntax_does_not_crash():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = os.path.join(tmp_dir, "config.yaml")
        cm = ConfigManager(config_path=config_path, check_interval=0.01)
        initial_cfg = cm.load()

        # Write invalid YAML syntax
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("filter: [unbalanced brackets: {")

        time.sleep(0.05)
        res = cm.check_for_updates(force=True)
        assert res is None
        assert cm.current["game_windows"]["strategy"] == initial_cfg["game_windows"]["strategy"]

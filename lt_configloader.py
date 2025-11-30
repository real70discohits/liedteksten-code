""" (helper) Configuration classes for reading settings from json. """

from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import commentjson  # in plaats van json: Ondersteunt // en /* */ comments


@dataclass
class Condition:
    """Dada."""
    liedId: int
    showMeasures: Optional[bool]
    showChords: Optional[bool]
    showTabs: Optional[bool]
    tabOrientation: Optional[str]

@dataclass
class Action:
    """Dada."""
    adjustMargins: Optional[str]
    adjustFontsize: Optional[int]

@dataclass
class ConfigItem:
    """Dada."""
    description: Optional[str]
    condition: Condition
    action: Action

class ConfigLoader:
    """Configuration loader for song-specific settings."""

    @staticmethod
    def load_from_file(filepath: str | Path) -> list[ConfigItem]:
        """Load JSON configuration and parse to ConfigItem objects.

        Args:
            filepath: Path to the configuration file

        Returns:
            List of ConfigItem objects

        Raises:
            FileNotFoundError: If the file doesn't exist
            Various exceptions for invalid JSON or config structure
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = commentjson.load(f)

        config_items = []
        for item in data:
            try:
                description = item.get('description')  # Geeft None als veld ontbreekt
                condition = Condition(**item['condition'])
                action = Action(**item['action'])
            except (KeyError, TypeError) as e:
                print("Exception probable cause(s): in lt-config.jsonc "
                    "each entry must declare all fields, such as "
                    "adjustMargins and adjustFontsize. You cannot omit them: "
                    "instead simply assign null as value. Or have you "
                    "changed code without updating the config or vice versa?")
                raise

            config_items.append(ConfigItem(
                description=description, condition=condition, action=action))

        return config_items

    @staticmethod
    def load_from_file_optional(filepath: str | Path) -> list[ConfigItem]:
        """Load JSON configuration, returning empty list if file doesn't exist.

        Args:
            filepath: Path to the configuration file

        Returns:
            List of ConfigItem objects, or empty list if file doesn't exist
        """
        if not Path(filepath).exists():
            return []

        return ConfigLoader.load_from_file(filepath)


def get_config(configs: list[ConfigItem], lied_id: int,
            show_measures: bool, show_chords: bool,
            show_tabs: bool, tab_orientation: str) -> Optional[ConfigItem]:
    """Lookup configuration for a song and parameters.
    
    Returns the FIRST matching configuration from the list.
    Configured 'None' values act as wildcards (match any value).
    Order matters: place more specific configurations earlier in the list.
    """
    return next((config for config in configs if
                config.condition.liedId == lied_id
                and (config.condition.showMeasures == show_measures
                    or config.condition.showMeasures is None)
                and (config.condition.showChords == show_chords
                    or config.condition.showChords is None)
                and (config.condition.showTabs == show_tabs
                    or config.condition.showTabs is None)
                and (config.condition.tabOrientation == tab_orientation
                    or config.condition.tabOrientation is None)
            ), None)

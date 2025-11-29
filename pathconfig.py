"""Path configuration loader for liedteksten scripts.

This module provides functionality to load and validate path configurations
from a JSON configuration file. It supports both relative and absolute paths.
"""

import json
import sys
from pathlib import Path
from typing import Optional


class PathConfig:
    """Container for path configuration settings."""

    def __init__(self, input_folder: str, output_folder: str, audio_output_folder: str,
                 soundfont_path: Optional[str] = None):
        """Initialize PathConfig with folder paths.

        Args:
            input_folder: Path to input folder (relative or absolute)
            output_folder: Path to output folder (relative or absolute)
            audio_output_folder: Path to audio output folder (relative or absolute)
            soundfont_path: Path to soundfont file (optional, relative or absolute)
        """
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.audio_output_folder = audio_output_folder
        self.soundfont_path = soundfont_path

    def __repr__(self) -> str:
        """Return string representation of configuration."""
        return (f"PathConfig(input_folder='{self.input_folder}', "
                f"output_folder='{self.output_folder}', "
                f"audio_output_folder='{self.audio_output_folder}', "
                f"soundfont_path='{self.soundfont_path}')")


def _load_jsonc(filepath: Path) -> dict:
    """Load a JSON file with comments (.jsonc).

    Args:
        filepath: Path to the JSONC file

    Returns:
        Parsed JSON data as dictionary

    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove single-line comments
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        # Find comment position (but not inside strings)
        in_string = False
        escape_next = False
        comment_pos = -1

        for i, char in enumerate(line):
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string

            if not in_string and line[i:i+2] == '//':
                comment_pos = i
                break

        if comment_pos >= 0:
            cleaned_lines.append(line[:comment_pos].rstrip())
        else:
            cleaned_lines.append(line)

    cleaned_content = '\n'.join(cleaned_lines)

    # Remove multi-line comments
    while '/*' in cleaned_content:
        start = cleaned_content.find('/*')
        end = cleaned_content.find('*/', start)
        if end == -1:
            break
        cleaned_content = cleaned_content[:start] + cleaned_content[end+2:]

    return json.loads(cleaned_content)


def load_path_config(config_file: Optional[Path] = None) -> PathConfig:
    """Load path configuration from JSONC file.

    Args:
        config_file: Path to configuration file. If None, uses 'paths.jsonc'
                     in the same directory as this module.

    Returns:
        PathConfig object with loaded settings

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        json.JSONDecodeError: If configuration file contains invalid JSON
        KeyError: If required configuration keys are missing
        SystemExit: If configuration validation fails
    """
    if config_file is None:
        # Use paths.jsonc in the same directory as this module
        config_file = Path(__file__).parent / "paths.jsonc"

    try:
        data = _load_jsonc(config_file)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print(f"   Please create a 'paths.jsonc' configuration file.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in configuration file: {e}")
        sys.exit(1)

    # Extract required fields
    try:
        input_folder = data['input_folder']
        output_folder = data['output_folder']
        audio_output_folder = data['audio_output_folder']
    except KeyError as e:
        print(f"❌ Error: Missing required field in configuration: {e}")
        print(f"   Required fields: input_folder, output_folder, audio_output_folder")
        sys.exit(1)

    # Extract optional fields
    soundfont_path = data.get('soundfont_path', None)

    return PathConfig(input_folder, output_folder, audio_output_folder, soundfont_path)


def resolve_path(base_path: str, config_dir: Path) -> Path:
    """Resolve a path (relative or absolute) from configuration.

    Args:
        base_path: Path string from configuration (relative or absolute)
        config_dir: Directory containing the configuration file

    Returns:
        Resolved absolute Path object
    """
    path = Path(base_path)

    # If path is already absolute, return it
    if path.is_absolute():
        return path

    # Otherwise, resolve relative to config directory
    return (config_dir / path).resolve()


def validate_folder_exists(folder_path: Path, folder_name: str) -> bool:
    """Validate that a folder exists and is accessible.

    Args:
        folder_path: Path to validate
        folder_name: Name of the folder (for error messages)

    Returns:
        True if folder exists and is accessible

    Prints error message and returns False if validation fails.
    """
    if not folder_path.exists():
        print(f"❌ Error: {folder_name} does not exist: {folder_path}")
        return False

    if not folder_path.is_dir():
        print(f"❌ Error: {folder_name} is not a directory: {folder_path}")
        return False

    # Check if we can access the folder
    try:
        # Try to list directory contents to verify access
        list(folder_path.iterdir())
    except PermissionError:
        print(f"❌ Error: No access to {folder_name}: {folder_path}")
        return False

    return True


def validate_file_exists(file_path: Path, file_description: str) -> bool:
    """Validate that a file exists and is accessible.

    Args:
        file_path: Path to validate
        file_description: Description of the file (for error messages)

    Returns:
        True if file exists and is accessible

    Prints error message and returns False if validation fails.
    """
    if not file_path.exists():
        print(f"❌ Error: {file_description} does not exist: {file_path}")
        return False

    if not file_path.is_file():
        print(f"❌ Error: {file_description} is not a file: {file_path}")
        return False

    # Check if we can read the file
    try:
        with open(file_path, 'r', encoding='utf-8'):
            pass
    except PermissionError:
        print(f"❌ Error: No access to {file_description}: {file_path}")
        return False
    except Exception as e:
        print(f"❌ Error: Cannot read {file_description}: {e}")
        return False

    return True


def ensure_folder_writable(folder_path: Path, folder_name: str) -> bool:
    """Ensure a folder exists and is writable.

    Creates the folder if it doesn't exist. Validates write access.

    Args:
        folder_path: Path to validate/create
        folder_name: Name of the folder (for error messages)

    Returns:
        True if folder is writable

    Prints error message and returns False if validation fails.
    """
    # Create folder if it doesn't exist
    if not folder_path.exists():
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created {folder_name}: {folder_path}")
        except PermissionError:
            print(f"❌ Error: No permission to create {folder_name}: {folder_path}")
            return False
        except Exception as e:
            print(f"❌ Error: Cannot create {folder_name}: {e}")
            return False

    # Validate it's a directory
    if not folder_path.is_dir():
        print(f"❌ Error: {folder_name} exists but is not a directory: {folder_path}")
        return False

    # Check write access by attempting to create a temporary file
    try:
        test_file = folder_path / ".write_test"
        test_file.touch()
        test_file.unlink()
    except PermissionError:
        print(f"❌ Error: No write access to {folder_name}: {folder_path}")
        return False
    except Exception as e:
        print(f"❌ Error: Cannot write to {folder_name}: {e}")
        return False

    return True

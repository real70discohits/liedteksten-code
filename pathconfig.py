"""Path configuration loader for liedteksten scripts.

This module provides functionality to load and validate path configurations
from a JSON configuration file. It supports both relative and absolute paths.
"""

import commentjson
import os
import sys
from pathlib import Path
from typing import Optional


# Environment variable that overrides which paths config file is loaded.
# Used by the test harness to redirect all paths to a throwaway sandbox,
# but it is a general-purpose seam (e.g. for multiple path profiles) and
# carries no test-specific semantics.
ENV_PATHS_CONFIG = "LT_PATHS_CONFIG"


class PathConfig:
    """Container for path configuration settings."""

    def __init__(self, input_folder: str, build_folder: str, distributie_folder: str,
                audio_output_folder: str, soundfont_path: Optional[str] = None, pdrive_folder: Optional[str] = None):
        """Initialize PathConfig with folder paths.

        Args:
            input_folder: Path to input folder (relative or absolute)
            build_folder: Path to build folder for intermediate files (relative or absolute)
            distributie_folder: Path to distribution folder for final PDFs (relative or absolute)
            audio_output_folder: Path to audio output folder (relative or absolute)
            soundfont_path: Path to soundfont file (optional, relative or absolute)
            pdrive_folder: Path to local Proton Drive folder (optional, relative or absolute)
        """
        self.input_folder = input_folder
        self.build_folder = build_folder
        self.distributie_folder = distributie_folder
        self.audio_output_folder = audio_output_folder
        self.soundfont_path = soundfont_path
        self.pdrive_folder = pdrive_folder

    def __repr__(self) -> str:
        """Return string representation of configuration."""
        return (f"PathConfig(input_folder='{self.input_folder}', "
                f"build_folder='{self.build_folder}', "
                f"distributie_folder='{self.distributie_folder}', "
                f"audio_output_folder='{self.audio_output_folder}', "
                f"soundfont_path='{self.soundfont_path}', "
                f"pdrive_folder='{self.pdrive_folder}')")


def load_jsonc(filepath: Path) -> dict:
    """Load a JSON file with comments (.jsonc).

    Uses the commentjson library to support // and /* */ comments.

    Args:
        filepath: Path to the JSONC file

    Returns:
        Parsed JSON data as dictionary

    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        commentjson.JSONDecodeError: If the file contains invalid JSON
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        return commentjson.load(f)


def _find_repo_root(start_dir: Path) -> Optional[Path]:
    """Walk upward from start_dir and return the closest ancestor with a .git entry.

    Uses .exists() rather than .is_dir() so that git submodules and worktrees
    are also detected: there .git is a *file* (a pointer to the real gitdir),
    not a directory.
    """
    candidate = start_dir
    while candidate != candidate.parent:      # stop at filesystem root
        if (candidate / ".git").exists():
            return candidate
        candidate = candidate.parent
    return None


def resolve_config_file(config_file: Optional[Path] = None) -> Path:
    """Determine which paths config file to load.

    Resolution order:
    1. Explicit ``config_file`` argument (if provided).
    2. ``LT_PATHS_CONFIG`` environment variable.
    3. ``paths.jsonc`` in the parent of the *nearest* git repository —
        for a submodule layout this is the root of the outer (songs)
        repository, where the config is expected to live.

    Exits with a clear, actionable error if no config file can be found.
    """
    # 1. Explicit argument
    if config_file is not None:
        return Path(config_file)

    # 2. Environment variable (persistent, recommended for non-standard setups)
    env_value = os.environ.get(ENV_PATHS_CONFIG)
    if env_value:
        env_config = Path(env_value)
        if env_config.exists():
            return env_config
        print(f"❌ Error: Configuration file from environment variable not found.")
        print(f"   {ENV_PATHS_CONFIG}={env_value}")
        print(f"   But the file does not exist at that location.")
        print(f"   Fix the value or unset the variable and let the script resolve "
                f"the config automatically.")
        sys.exit(1)

    # 3. Parent of the nearest git repository
    module_dir = Path(__file__).parent
    repo_root = _find_repo_root(module_dir)

    if repo_root is not None:
        expected_dir = repo_root.parent
        expected_config = expected_dir / "paths.jsonc"

        if expected_config.exists():
            return expected_config

        print(f"❌ Error: No configuration file found.")
        print(f"   Nearest git repository root : {repo_root}")
        print(f"   Expected config location   : {expected_config}")
        print()
        print(f"   Fix:")
        print(f"   1. Place 'paths.jsonc' in: {expected_dir}")
        print(f"      (a template can be found in 'paths.jsonc.example')")
        print(f"   2. Or set the environment variable {ENV_PATHS_CONFIG} to the "
                f"full path of your config file.")
        sys.exit(1)

    # 4. No git repo found at all
    print(f"❌ Error: No configuration file found and no git repository detected "
            f"above {module_dir}.")
    print(f"   Fix: set the environment variable {ENV_PATHS_CONFIG} to the full "
            f"path of your paths.jsonc.")
    sys.exit(1)

def load_path_config(config_file: Optional[Path] = None) -> PathConfig:
    """Load path configuration from JSONC file.

    Args:
        config_file: Path to configuration file. If None, falls back to the
                    resolution logic in resolve_config_file().

    Returns:
        PathConfig object with loaded settings

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        json.JSONDecodeError: If configuration file contains invalid JSON
        KeyError: If required configuration keys are missing
        SystemExit: If configuration validation fails
    """
    config_file = resolve_config_file(config_file)

    try:
        data = load_jsonc(config_file)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print(f"   Please create a 'paths.jsonc' configuration file.")
        sys.exit(1)
    except (commentjson.JSONLibraryException, ValueError) as e:
        print(f"❌ Error: Invalid JSON in configuration file: {e}")
        sys.exit(1)

    # Extract required fields
    try:
        input_folder = data['input_folder']
        build_folder = data['build_folder']
        distributie_folder = data['distributie_folder']
        audio_output_folder = data['audio_output_folder']
        
    except KeyError as e:
        print(f"❌ Error: Missing required field in configuration: {e}")
        print(f"   Required fields: input_folder, build_folder, distributie_folder, audio_output_folder, pdrive_folder")
        sys.exit(1)

    # Extract optional fields
    soundfont_path = data.get('soundfont_path', None)
    pdrive_folder = data.get('pdrive_folder', None)

    return PathConfig(input_folder, build_folder, distributie_folder, audio_output_folder, soundfont_path, pdrive_folder)


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


class ResolvedPaths:
    """Container for resolved and validated paths.

    This class encapsulates all path resolution and provides convenience
    methods for validation. Use load_and_resolve_paths() to create instances.
    """

    def __init__(self, config: PathConfig, config_dir: Path):
        """Initialize ResolvedPaths with configuration.

        Args:
            config: PathConfig object with raw path strings
            config_dir: Directory containing the configuration file
        """
        self.config = config
        self.config_dir = config_dir

        # Resolve all paths
        self.input_folder = resolve_path(config.input_folder, config_dir)
        self.build_folder = resolve_path(config.build_folder, config_dir)
        self.distributie_folder = resolve_path(config.distributie_folder, config_dir)
        self.audio_output_folder = resolve_path(config.audio_output_folder, config_dir)
        
        # Resolve optional paths
        self.soundfont_path = None
        if config.soundfont_path:
            self.soundfont_path = resolve_path(config.soundfont_path, config_dir)

        if config.pdrive_folder:
            self.pdrive_folder = resolve_path(config.pdrive_folder, config_dir)


    def validate_input_folder(self) -> bool:
        """Validate that input folder exists and is accessible.

        Returns:
            True if validation succeeds, False otherwise
        """
        return validate_folder_exists(self.input_folder, "Input folder")

    def ensure_output_folders(self) -> bool:
        """Ensure output folders exist and are writable.

        Creates folders if they don't exist and validates write access.

        Returns:
            True if all validations succeed, False otherwise
        """
        return (ensure_folder_writable(self.build_folder, "Build folder") and
                ensure_folder_writable(self.distributie_folder, "Distribution folder") and
                ensure_folder_writable(self.audio_output_folder, "Audio output folder"))

    def __repr__(self) -> str:
        """Return string representation of resolved paths."""
        return (f"ResolvedPaths(input_folder={self.input_folder}, "
                f"build_folder={self.build_folder}, "
                f"distributie_folder={self.distributie_folder}, "
                f"audio_output_folder={self.audio_output_folder}, "
                f"soundfont_path={self.soundfont_path}, "
                f"pdrive_folder={self.pdrive_folder})")


def load_and_resolve_paths(songtitle) -> ResolvedPaths:
    """Load configuration and resolve all paths.

    Convenience function for script main() functions. Loads the path
    configuration and creates a ResolvedPaths object with all paths
    resolved relative to the configuration directory.

    Returns:
        ResolvedPaths object with all paths resolved

    Example:
        paths = load_and_resolve_paths()
        if not paths.validate_input_folder():
            sys.exit(1)
        song_folder = paths.input_folder / songtitle
    """
    config_file = resolve_config_file()
    config = load_path_config(config_file)
    config.build_folder = config.build_folder + '/' + songtitle
    config.distributie_folder = config.distributie_folder + '/' + songtitle
    config_dir = config_file.parent
    return ResolvedPaths(config, config_dir)

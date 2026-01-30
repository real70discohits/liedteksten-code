"""
API-specific module for lt-generate functionality.
Provides functions to compile .tex files in a Docker container environment.
"""

import os
import sys
import io
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass

# Import config loader
from lt_configloader import ConfigLoader, get_config


@dataclass
class CompileResult:
    """Result of a compilation operation."""
    success: bool
    pdf_files: List[Path]
    log_files: List[Path]
    console_output: str
    error_message: Optional[str] = None


def extract_song_title_from_filename(filename: str) -> str:
    """
    Extract song title from .tex filename.
    Example: "Such A Beauty (6).tex" -> "Such A Beauty (6)"
    """
    if filename.endswith('.tex'):
        return filename[:-4]
    return filename


def is_structuur_file(filename: str) -> bool:
    """
    Check if filename indicates a structuur document.
    Convention: filename ends with " structuur.tex"
    """
    return filename.endswith(" structuur.tex")


def create_temp_structure(song_title: str, tex_content: str,
                        config_content: Optional[str] = None,
                        sty_content: Optional[str] = None) -> Tuple[Path, Path, Path]:
    """
    Create temporary directory structure for compilation.

    Returns: (temp_root, input_folder, output_folder)
    """
    temp_root = Path(tempfile.mkdtemp(prefix="ltgen_"))

    input_folder = temp_root / "input"
    song_folder = input_folder / song_title
    output_folder = temp_root / "output"

    song_folder.mkdir(parents=True, exist_ok=True)
    output_folder.mkdir(parents=True, exist_ok=True)

    # Write .tex file
    tex_file = song_folder / f"{song_title}.tex"
    with open(tex_file, 'w', encoding='utf-8') as f:
        f.write(tex_content)

    # Write config if provided
    if config_content:
        config_file = song_folder / "lt-config.jsonc"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)

    # Write custom .sty if provided
    if sty_content:
        sty_file = temp_root / "liedbasis.sty"
        with open(sty_file, 'w', encoding='utf-8') as f:
            f.write(sty_content)

    return temp_root, input_folder, output_folder


def compile_tex_simple(song_title: str, input_folder: Path, output_folder: Path,
                        cleanup: bool = True, debug: bool = False) -> bool:
    """
    Simple compilation for structuur files.
    Compiles .tex file twice for proper references.
    """
    tex_file = input_folder / song_title / f"{song_title}.tex"
    if not tex_file.exists():
        print(f"❌ Error: {tex_file} does not exist")
        return False

    output_name = song_title

    # Set TEXINPUTS to include input folder
    tex_input_dir = os.path.abspath(input_folder)
    env = os.environ.copy()
    env['TEXINPUTS'] = f'{tex_input_dir}//;' + env.get('TEXINPUTS', '')

    # Compile twice for references
    for _ in range(2):
        result = subprocess.run(
            [
                'pdflatex',
                '-interaction=nonstopmode',
                f'-output-directory={output_folder}',
                f'-jobname={output_name}',
                str(tex_file)
            ],
            capture_output=not debug,
            text=True,
            check=False,
            env=env
        )

        if result.returncode != 0:
            print("❌ LaTeX compilation failed")
            if result.stderr:
                print(result.stderr)
            if result.stdout:
                print(result.stdout)
            return False

    # Cleanup auxiliary files
    if cleanup:
        for ext in ['.aux', '.log', '.out', '.toc']:
            aux_file = output_folder / f"{output_name}{ext}"
            if aux_file.exists():
                aux_file.unlink()

    print(f"✅ Success: {output_name}.pdf")
    return True


def compile_tex_variant(song_title: str, input_folder: Path, output_folder: Path,
                        show_measures: bool = False, show_chords: bool = False,
                        show_tabs: bool = False, tab_orientation: str = 'left',
                        cleanup: bool = True, large_print: bool = False, 
                        debug: bool = False) -> int:
    """
    Compile a single variant of a liedtekst.
    Returns number of PDFs generated (can be > 1 due to transpositions).

    This is adapted from compile_tex_file() in lt-generate.py
    """
    # Import transpose function from lt-generate
    from lt_generate import transpose, maak_opsomming

    tex_file = input_folder / song_title / f"{song_title}.tex"
    if not tex_file.exists():
        print(f"❌ Error: {tex_file} does not exist")
        return 0

    # Load song-specific configuration
    song_folder = input_folder / song_title
    lt_config_file = song_folder / "lt-config.jsonc"
    configurations = ConfigLoader.load_from_file_optional(lt_config_file)

    # Read .tex file
    with open(tex_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract metadata
    title_match = re.search(r'\\newcommand{\\liedTitel}{(.*?)}', content)
    id_match = re.search(r'\\newcommand{\\liedId}{(.*?)}', content)
    key_match = re.search(r'\\newcommand{\\sleutel}{(.*?)}', content)
    transpositions_match = re.search(r'\\newcommand{\\transpositions}{(.*?)}', content)

    if not title_match or not id_match:
        print(f"⚠️  Skipping {song_title}: metadata not found")
        return 0

    song_title_from_tex = title_match.group(1)
    song_id = int(id_match.group(1))

    # Parse transpositions
    additional_transpositions = []
    if transpositions_match:
        trans_str = transpositions_match.group(1)
        additional_transpositions = [int(x) for x in re.findall(r'-?\d+', trans_str) if x != '0']

    transpositions = [0] + additional_transpositions

    print(f"\n📝 Compiling {len(transpositions)} transposition(s) for {song_title}")

    success_count = 0

    # Set TEXINPUTS
    tex_input_dir = os.path.abspath(input_folder)
    env = os.environ.copy()
    env['TEXINPUTS'] = f'{tex_input_dir}//;' + env.get('TEXINPUTS', '')

    for transposition in transpositions:
        # Build output filename
        parts = [song_title_from_tex, f"({song_id})"]

        if transposition != 0:
            if key_match:
                chord = transpose(key_match.group(1), transposition)
                parts.append(f"in {chord}")
            parts.append(f'transp({transposition:+d})')

        output_name = " ".join(parts)
        output_name = re.sub(r'[^\w\-\s()]', '', output_name)

        _measurestext = 'maatnummers' if show_measures else ''
        _chordstext = 'akkoorden' if show_chords else ''
        _gittabtext = 'gitaargrepen' if show_tabs else ''
        output_name = output_name + maak_opsomming([_measurestext, _chordstext, _gittabtext])

        print(f"   Generating: {output_name}.pdf")

        # Build pdflatex arguments
        _showmeasures = 'true' if show_measures else 'false'
        _showchords = 'true' if show_chords else 'false'
        _showtabs = 'true' if show_tabs else 'false'
        _large_print = '\\def\\largePrint{}' if large_print else ''

        # Get configuration
        _set_margins = ""
        _set_fontsize = ""
        lied_config = get_config(configurations, song_id,
                                show_measures, show_chords,
                                show_tabs, tab_orientation,
                                large_print)

        if lied_config:
            print(f"   Applying configuration: {lied_config.description}")
            if lied_config.action.adjustMargins:
                _set_margins = f"\\def\\setMargins{{{lied_config.action.adjustMargins}}}"
            if lied_config.action.adjustFontsize:
                _set_fontsize = f"\\def\\setFontsize{{{lied_config.action.adjustFontsize}}}"

        # Construct pdflatex arguments
        pdflatex_args = (f""
                    f"{_set_margins}"
                    f"{_set_fontsize}"
                    f"{_large_print}"
                    f"\\def\\showMeasures{{{_showmeasures}}}"
                    f"\\def\\showChords{{{_showchords}}}"
                    f"\\def\\showTabs{{{_showtabs}}}"
                    f"\\def\\guitarTabOrientation{{{tab_orientation}}}"
                    f"\\def\\transpose{{{transposition}}}"
                    f"\\input{{{song_title}}}")

        # Compile twice
        original_cleanup = cleanup
        for i in range(2):
            result = subprocess.run(
                [
                    'pdflatex',
                    '-interaction=nonstopmode',
                    f'-output-directory={output_folder}',
                    f'-jobname={output_name}',
                    pdflatex_args
                ],
                capture_output=not debug,
                text=True,
                check=False,
                env=env
            )

            if result.returncode == 0:
                # First pass: keep aux files; second pass: cleanup
                cleanup = False if i == 0 else original_cleanup

                if i == 1:
                    print(f"✅ Success: {output_name}.pdf")
                    success_count += 1

                if cleanup:
                    for ext in ['.aux', '.log', '.out', '.toc']:
                        aux_file = output_folder / f"{output_name}{ext}"
                        if aux_file.exists():
                            aux_file.unlink()
            else:
                print(f"❌ Failed: {song_title}")
                if result.stderr:
                    print(result.stderr)
                break

    return success_count


def compile_liedtekst_variants(song_title: str, input_folder: Path, output_folder: Path,
                                only: int = 0, tab_orientation: str = 'left',
                                cleanup: bool = True, large_print=False, debug: bool = False) -> int:
    """
    Compile liedtekst with specified variants.
    Returns: number of successfully compiled PDFs
    """
    # Helper to check if variant has config
    def has_config_for_variant(variant_num):
        song_folder = input_folder / song_title
        lt_config_file = song_folder / "lt-config.jsonc"
        configurations = ConfigLoader.load_from_file_optional(lt_config_file)

        if not configurations:
            return False

        # Get song_id
        tex_file = song_folder / f"{song_title}.tex"
        with open(tex_file, 'r', encoding='utf-8') as f:
            content = f.read()
        id_match = re.search(r'\\newcommand{\\liedId}{(.*?)}', content)
        if not id_match:
            return False
        song_id = int(id_match.group(1))

        # Map variant to parameters
        variant_params = {
            1: (False, False, False),
            2: (True, False, False),
            3: (False, True, False),
            4: (True, True, False),
            5: (True, True, True),
        }
        show_measures, show_chords, show_tabs = variant_params[variant_num]

        config = get_config(configurations, song_id, show_measures,
                        show_chords, show_tabs, tab_orientation, large_print)
        return config is not None

    # Helper to decide if variant should be generated
    def should_generate_variant(variant_num):
        if only == 0:
            return True
        elif only == -1:
            return has_config_for_variant(variant_num)
        elif only == variant_num:
            return True
        else:
            return False

    success = 0

    # Variant 1: text only
    if should_generate_variant(1):
        success += compile_tex_variant(song_title, input_folder, output_folder,
                                        cleanup=cleanup, large_print=large_print, debug=debug)

    # Variant 2: text + measures
    if should_generate_variant(2):
        success += compile_tex_variant(song_title, input_folder, output_folder,
                                        show_measures=True, cleanup=cleanup, large_print=large_print, debug=debug)

    # Variant 3: text + chords
    if should_generate_variant(3):
        success += compile_tex_variant(song_title, input_folder, output_folder,
                                        show_chords=True, cleanup=cleanup, large_print=large_print, debug=debug)

    # Variant 4: text + measures + chords
    if should_generate_variant(4):
        success += compile_tex_variant(song_title, input_folder, output_folder,
                                        show_measures=True, show_chords=True,
                                        cleanup=cleanup, large_print=large_print, debug=debug)

    # Variant 5: text + measures + chords + tabs
    if should_generate_variant(5):
        success += compile_tex_variant(song_title, input_folder, output_folder,
                                        show_measures=True, show_chords=True,
                                        show_tabs=True, tab_orientation=tab_orientation,
                                        cleanup=cleanup, large_print=large_print, debug=debug)

    return success


def compile_for_api(
    tex_filename: str,
    tex_content: str,
    config_content: Optional[str] = None,
    sty_content: Optional[str] = None,
    only: int = 0,
    tab_orientation: str = 'left',
    large_print: bool = False,
) -> CompileResult:
    """
    Compile a .tex file for the API.

    Args:
        tex_filename: Original filename (e.g., "Such A Beauty (6).tex")
        tex_content: Content of the .tex file
        config_content: Optional lt-config.jsonc content
        sty_content: Optional custom liedbasis.sty content
        only: Which variant to generate (0=all, -1=configured only, 1-5=specific)
        tab_orientation: Guitar tab orientation (left/right/traditional)
        large_print: optimize output for readability: bold and sans serif font

    Returns:
        CompileResult with success status, PDF files, logs, and console output
    """
    song_title = extract_song_title_from_filename(tex_filename)
    is_structuur = is_structuur_file(tex_filename)

    # Create temp structure
    temp_root, input_folder, output_folder = create_temp_structure(
        song_title, tex_content, config_content, sty_content
    )

    # Capture console output
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    console_buffer = io.StringIO()

    try:
        # Redirect stdout/stderr
        sys.stdout = console_buffer
        sys.stderr = console_buffer

        # Set up environment for custom .sty
        if sty_content:
            env = os.environ.copy()
            env['TEXINPUTS'] = f'{temp_root}//;' + env.get('TEXINPUTS', '')
            os.environ.update(env)

        if is_structuur:
            success = compile_tex_simple(
                song_title, input_folder, output_folder,
                cleanup=True, debug=False
            )
            success_count = 1 if success else 0
        else:
            success_count = compile_liedtekst_variants(
                song_title, input_folder, output_folder,
                only=only, tab_orientation=tab_orientation,
                cleanup=True, large_print=large_print, debug=False
            )

        # Get console output
        console_output = console_buffer.getvalue()

        # Collect generated PDFs and logs
        pdf_files = list(output_folder.glob("*.pdf"))
        log_files = list(output_folder.glob("*.log"))

        if success_count > 0 and pdf_files:
            return CompileResult(
                success=True,
                pdf_files=pdf_files,
                log_files=log_files,
                console_output=console_output
            )
        else:
            return CompileResult(
                success=False,
                pdf_files=[],
                log_files=log_files,
                console_output=console_output,
                error_message="Compilation failed - see logs and console output"
            )

    except Exception as e:
        console_output = console_buffer.getvalue()
        return CompileResult(
            success=False,
            pdf_files=[],
            log_files=list(output_folder.glob("*.log")) if output_folder.exists() else [],
            console_output=console_output,
            error_message=f"Exception during compilation: {str(e)}"
        )

    finally:
        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr


# Config cache management
CACHE_DIR = Path("/app/cache/configs")


def get_cached_config(song_title: str) -> Optional[str]:
    """Get cached config for a song. Returns content as string, or None."""
    config_file = CACHE_DIR / f"{song_title}.jsonc"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def save_config_to_cache(song_title: str, config_content: str) -> None:
    """Save config to cache for a song."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    config_file = CACHE_DIR / f"{song_title}.jsonc"
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)


def delete_cached_config(song_title: str) -> bool:
    """Delete cached config. Returns True if deleted, False if not found."""
    config_file = CACHE_DIR / f"{song_title}.jsonc"
    if config_file.exists():
        config_file.unlink()
        return True
    return False


def list_cached_configs() -> List[str]:
    """List all cached song titles."""
    if not CACHE_DIR.exists():
        return []

    configs = []
    for config_file in CACHE_DIR.glob("*.jsonc"):
        configs.append(config_file.stem)

    return configs

"""Constants used throughout the liedteksten codebase.

This module contains shared constants to avoid magic strings and improve maintainability.
"""

# NWC Staff Names
STAFF_NAME_BASS = "Bass"
STAFF_NAME_ZANG = "Zang"

# File Extensions
EXT_NWCTXT = ".nwctxt"
EXT_TEX = ".tex"
EXT_JSONC = ".jsonc"
EXT_PDF = ".pdf"
EXT_TXT = ".txt"

# Folder Names
FOLDER_NWC = "nwc"

# NWC Element Prefixes
NWC_PREFIX_ADDSTAFF = "|AddStaff|"
NWC_PREFIX_STAFF_PROPERTIES = "|StaffProperties|"
NWC_PREFIX_STAFF_INSTRUMENT = "|StaffInstrument|"
NWC_PREFIX_CLEF = "|Clef|"
NWC_PREFIX_TIMESIG = "|TimeSig|"
NWC_PREFIX_TEMPO = "|Tempo|"
NWC_PREFIX_BAR = "|Bar|"
NWC_PREFIX_NOTE = "|Note|"
NWC_PREFIX_REST = "|Rest|"
NWC_PREFIX_TEXT = "|Text|"
NWC_PREFIX_LYRIC1 = "|Lyric1|"

# NWC Markers
NWC_END_MARKER = "!NoteWorthyComposer-End"
NWC_MARKER_LIEDSTART = "liedstart"

# Configuration Files
CONFIG_PATHS = "paths.jsonc"
CONFIG_LT = "lt-config.jsonc"

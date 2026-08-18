"""Constants used throughout the liedteksten codebase.

This module contains shared constants to avoid magic strings and improve maintainability.
"""

# NWC Staff Names
STAFF_NAME_BASS = "Bass"
STAFF_NAME_RITME = "Ritme"
STAFF_NAME_ZANG = "Zang"
STAFF_NAME_BASE_DRUM = "Basedrum"
STAFF_NAME_SNARE_DRUM = "Snare"
STAFF_NAME_HI_HAT = "HiHat"
STAFF_NAME_CRASH_CYMBAL = "Crash"
STAFF_NAME_RIDE_CYMBAL = "Ride"
STAFF_NAME_TOM_1 = "Tom1"
STAFF_NAME_TOM_2 = "Tom2"
STAFF_NAME_FLOOR_TOM = "FloorTom"
STAFF_NAME_DRUMS = "Drums"


# Staff names that pad-staffs.py leaves alone (not padded to match the Bass).
# Add staff names here to exclude them from measure-padding.
PAD_STAFFS_IGNORED_STAFFS = [STAFF_NAME_RITME, STAFF_NAME_DRUMS]


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
NWC_PREFIX_BAR = "|Bar"
NWC_PREFIX_NOTE = "|Note|"
NWC_PREFIX_REST = "|Rest|"
NWC_PREFIX_TEXT = "|Text|"
NWC_PREFIX_LYRIC1 = "|Lyric1|"

# NWC Markers
NWC_END_MARKER = "!NoteWorthyComposer-End"
NWC_MARKER_LIEDSTART = "liedstart"

# NWC beatbase names
NWC_BEAT_BASE_EIGHTH = "Eighth"       # example: |Tempo|Base:Eighth|Tempo:320|Pos:8
NWC_BEAT_BASE_QUARTER = "Quarter"     # not in file because this is the default
NWC_BEAT_BASE_QUARTER_DOTTED = "Quarter Dotted"    
NWC_BEAT_BASE_HALF = "Half"

# NWC note/rest duration names
NWC_DUR_WHOLE = "Whole"
NWC_DUR_HALF = "Half"
NWC_DUR_QUARTER = "4th"
NWC_DUR_EIGHTH = "8th"
NWC_DUR_SIXTEENTH = "16th"
NWC_DUR_THIRTYSECOND = "32nd"


# Configuration Files
CONFIG_PATHS = "paths.jsonc"
CONFIG_LT = "lt-config.jsonc"

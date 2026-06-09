"""UTF-8 safe console output.

The scripts print status with emoji (✅, ❌, ...). On Windows the default
stdout/stderr encoding is cp1252 whenever output is *not* an interactive
console - e.g. when it is redirected to a file or captured by another process
(such as a test runner). Printing an emoji then raises ``UnicodeEncodeError``
and crashes the script, even though it works fine in a normal terminal.

Calling :func:`enable_utf8_console` once at the start of a script's ``main()``
switches stdout/stderr to UTF-8 so the same output works everywhere.
"""

import sys


def enable_utf8_console() -> None:
    """Reconfigure stdout/stderr to UTF-8 if possible.

    Safe to call unconditionally: it is a no-op when the stream is already
    UTF-8, and silently does nothing for streams that cannot be reconfigured
    (e.g. an in-memory capture buffer without a ``reconfigure`` method).
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            # Stream is detached/closed or refuses reconfiguration; leave as-is.
            pass

# Troubleshooting

## lt-upload.ps1

**error:** `File or folder not found`

**fix:** try the upload manually: it may indicate the issue or even solve it.

## lt-generate.py

**error:** `ModuleNotFoundError: No module named 'commentjson'`

**fix:** probably you didn't initialize your .venv (git bash):

```bash
python -m venv .venv
source .venv/Scripts/activate
```

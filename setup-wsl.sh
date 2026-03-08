#!/bin/bash
#
# WSL Setup Script for lt-gen FastAPI development
# This script mirrors the Docker container environment for local debugging
#
#   NOTE: March 2026: script ging fout in stap 7: install venv.
#   handmatig opgelost en de rest handmatig uitgevoerd.
#   Let daarbij op: "which pip" moet een subpath van liedteksten teruggeven, niet /usr/bin/...
#   Als het toch /usr/bin/.. is moet je venv opnieuw installeren:
#        deactivate
#        rm -rf .venv-wsl
#        python3 -m venv .venv-wsl
#        source .venv-wsl/bin/activate
#
#
# Usage:
#   1. Open WSL terminal (let op: niet docker wsl!)
#   2. cd /mnt/c/Persoonlijk/liedteksten/lt-code
#   3. chmod +x setup-wsl.sh
#   4. ./setup-wsl.sh
#

set -e  # Exit on error

echo "=== WSL Setup for lt-gen FastAPI ==="
echo ""

# 1. Install system dependencies
echo "[1/9] Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y wget perl fontconfig

# 2. Install TinyTeX
echo ""
echo "[2/9] Installing TinyTeX..."
if [ -d "$HOME/.TinyTeX" ]; then
    echo "TinyTeX already installed, skipping..."
else
    wget -qO- "https://yihui.org/tinytex/install-bin-unix.sh" | sh
fi

# 3. Add TinyTeX to PATH
echo ""
echo "[3/9] Configuring PATH..."
if ! grep -q "TinyTeX" ~/.bashrc; then
    echo 'export PATH="$HOME/.TinyTeX/bin/x86_64-linux:$PATH"' >> ~/.bashrc
    echo "Added TinyTeX to ~/.bashrc"
else
    echo "TinyTeX already in ~/.bashrc"
fi
export PATH="$HOME/.TinyTeX/bin/x86_64-linux:$PATH"

# 4. Install LaTeX packages (matching Dockerfile)
echo ""
echo "[4/9] Installing LaTeX packages (this may take a while)..."
tlmgr install \
    collection-latex \
    collection-fontsrecommended \
    collection-latexrecommended

tlmgr install \
    pgf \
    tikz-cd \
    currfile \
    lastpage \
    savesym \
    anyfontsize \
    xstring \
    setspace

tlmgr install \
    # sk 6/3/2026: gchords is voorlopig vervangen door lokale kopie met wijzigingen ivm barré functionaliteit.
    # gchords \
    leadsheets \
    translations \
    musixtex \
    musixtex-fonts \
    musixguit \
    xcolor \
    etoolbox \
    metafont

tlmgr install \
    l3kernel \
    l3packages \
    l3experimental

tlmgr install \
    babel \
    babel-dutch \
    babel-english

# 5. Update LaTeX caches
echo ""
echo "[5/9] Updating LaTeX caches..."
mktexlsr
fmtutil-sys --all 2>/dev/null || fmtutil --all
updmap-sys 2>/dev/null || updmap

# 6. Install liedbasis.sty + gchordsz.sty
echo ""
echo "[6/9] Installing liedbasis.sty and gchordsz.sty..."
mkdir -p "$HOME/.TinyTeX/texmf-dist/tex/latex/local"
cp services/lt-gen/liedbasis.sty "$HOME/.TinyTeX/texmf-dist/tex/latex/local/"
cp services/lt-gen/gchordsz.sty "$HOME/.TinyTeX/texmf-dist/tex/latex/local/"
mktexlsr

# 7. Create /app directory structure (mirrors Docker container paths)
echo ""
echo "[7/9] Creating /app directory structure..."
sudo mkdir -p /app/cache/configs
sudo chown -R "$USER":"$USER" /app

# 8. Create Python virtual environment
echo ""
echo "[8/9] Setting up Python virtual environment..."
if [ -d ".venv-wsl" ]; then
    echo "Virtual environment .venv-wsl already exists"
else
    python3 -m venv .venv-wsl
fi
source .venv-wsl/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 9. Done
echo ""
echo "[9/9] Setup complete!"
echo ""
echo "=== Next steps ==="
echo ""
echo "1. Activate the virtual environment:"
echo "   source .venv-wsl/bin/activate"
echo ""
echo "2. Start the FastAPI server:"
echo "   cd services/lt-gen/app"
echo "   uvicorn main:app --reload --port 8000"
echo ""
echo "3. Open in browser:"
echo "   http://localhost:8000/docs"
echo ""
echo "4. For VS Code debugging:"
echo "   code ."
echo "   (Then install Python extension in WSL)"
echo ""

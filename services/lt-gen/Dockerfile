# Multi-stage build for security and size optimization

# Stage 1: Build stage - install TinyTeX and dependencies
FROM python:3.11-slim AS builder

# Install dependencies needed for TinyTeX installation
RUN apt-get update && apt-get install -y \
    wget \
    perl \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Install TinyTeX
WORKDIR /tmp
RUN wget -qO- "https://yihui.org/tinytex/install-bin-unix.sh" | sh

# Add TinyTeX to PATH for this stage
ENV PATH="/root/.TinyTeX/bin/x86_64-linux:${PATH}"

# Install LaTeX packages needed for liedbasis.sty and dependencies
# Core collections (provide: ifthen, graphicx, xparse, geometry, fancyhdr, etc.)
RUN tlmgr install \
    collection-latex \
    collection-fontsrecommended \
    collection-latexrecommended \
    && tlmgr path add

# Additional packages for liedbasis.sty
RUN tlmgr install \
    pgf \
    tikz-cd \
    currfile \
    lastpage \
    savesym \
    anyfontsize \
    xstring \
    && tlmgr path add

# Music-related packages
RUN tlmgr install \
    gchords \
    leadsheets \
    translations \
    musixtex \
    musixtex-fonts \
    musixguit \
    xcolor \
    etoolbox \
    metafont \
    && mktexlsr \
    && fmtutil-sys --all \
    && updmap-sys \
    && tlmgr path add

# L3 packages (for leadsheets)
RUN tlmgr install \
    l3kernel \
    l3packages \
    l3experimental \
    && tlmgr path add

# Copy requirements file and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
COPY liedbasis.sty /tmp/liedbasis.sty
RUN pip install --no-cache-dir --user -r /tmp/requirements.txt




#################################################################
#
# ======================   R U N T I M E   ======================      
#
#################################################################




# Stage 2: Runtime stage - minimal and hardened
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r pdfgen && useradd -r -g pdfgen -u 1001 pdfgen

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    fontconfig \
    perl \
    && rm -rf /var/lib/apt/lists/*

# Copy TinyTeX from builder
COPY --from=builder /root/.TinyTeX /home/pdfgen/.TinyTeX

# Copy Python packages from builder
COPY --from=builder /root/.local /home/pdfgen/.local

# Set up directory structure with proper permissions
RUN mkdir -p /app /app/cache/configs /tmp/tex-work /tmp/pdf-output && \
    chown -R pdfgen:pdfgen /app /tmp/tex-work /tmp/pdf-output /home/pdfgen

# Copy application code
COPY --chown=pdfgen:pdfgen app/ /app/

COPY --from=builder /tmp/liedbasis.sty /tmp/liedbasis.sty

# Install liedbasis.sty to LaTeX tree (as root, before switching user)
RUN cp /tmp/liedbasis.sty /home/pdfgen/.TinyTeX/texmf-dist/tex/latex/local/ 2>/dev/null || \
    mkdir -p /home/pdfgen/.TinyTeX/texmf-dist/tex/latex/local && \
    cp /tmp/liedbasis.sty /home/pdfgen/.TinyTeX/texmf-dist/tex/latex/local/ && \
    chown -R pdfgen:pdfgen /home/pdfgen/.TinyTeX/texmf-dist/tex/latex/local

# Set environment variables
ENV PATH="/home/pdfgen/.TinyTeX/bin/x86_64-linux:/home/pdfgen/.local/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER pdfgen

WORKDIR /app

# Expose port for API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# [oud] Run with limited shell-escape (security)
# CMD ["python", "main.py"]

# -----------------------------------------------------------------
# 2j – Start de FastAPI‑app met Uvicorn
# -----------------------------------------------------------------
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
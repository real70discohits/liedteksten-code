# --------------------------------------------------------------
# 1️⃣ BUILDER STAGE – install native deps + Python packages
# --------------------------------------------------------------
FROM python:3.11-slim-bookworm AS builder
ENV DEBIAN_FRONTEND=noninteractive

# -----------------------------------------------------------------
# 1a – 32‑bit arch + basis‑deps (ca‑certificates, gnupg2, wget …)
# -----------------------------------------------------------------
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        gnupg2 \
        wget \
        perl \
        fontconfig \
        # audio‑related runtime libs (needed by ffmpeg / fluidsynth)
        libasound2 \
        libasound2-plugins \
        libpulse0 && \
    rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------
# 1b – Wine repository (Debian‑specific) + install Wine
# -----------------------------------------------------------------
RUN wget -qO- https://dl.winehq.org/wine-builds/winehq.key | \
    gpg --dearmor -o /etc/apt/trusted.gpg.d/winehq.gpg && \
    echo "deb https://dl.winehq.org/wine-builds/debian/ bookworm main" > \
    /etc/apt/sources.list.d/winehq.list

# -----------------------------------------------------------------
# 1c – Optioneel Xvfb (via build‑arg) + Wine (stable)
# -----------------------------------------------------------------
ARG ENABLE_XVFB=true
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        winehq-stable \
        ffmpeg \
        fluidsynth \
        $(if [ "$ENABLE_XVFB" = "true" ]; then echo "xvfb"; fi) && \
    rm -rf /var/lib/apt/lists/*

# ---- Maak een Wine‑prefix (isolated Windows‑omgeving) ----
ENV WINEPREFIX=/wineprefix
RUN mkdir -p $WINEPREFIX && \
    wineboot --init   # initialiseert de prefix (creates C:\ drive etc.)

# ---- Kopieer de Windows‑installers in de builder image ----
COPY installers/setup_nwc21.exe /tmp/setup_nwc21.exe
COPY installers/nwcupd_from_v2.1_to_2.75a.exe /tmp/nwcupd_from_v2.1_to_2.75a.exe

# ---- Voer de installers uit (bij voorkeur in silent‑mode) ----
# Veel Windows‑installers hebben een “/S”, “/silent”, “/quiet” of “/qn” switch.
# Pas de switch aan op basis van de documentatie van de installer (sk: tested on ubuntu)
RUN wine "/tmp/setup_nwc21.exe" /S || \
    { echo "Installer setup_nwc21 failed – try a different silent flag"; exit 1; }
RUN wine "/tmp/nwcupd_from_v2.1_to_2.75a.exe" /S || \
    { echo "Installer nwcupd_from_v2.1_to_2.75a.exe failed – try a different silent flag"; exit 1; }


# Na de installatie liggen de bestanden vermoedelijk onder:
#   $WINEPREFIX/drive_c/Program Files (x86)/Noteworthy Software/NoteWorthy Composer 2/
#   Merk op dat 'Worthy' in het 1e geval hoofd- en het 2e geval kleine letter is.
# We laten ze in de image staan; later kopiëren we ze naar de runtime‑stage.

# -----------------------------------------------------------------
# 1d – Python dependencies (FastAPI, uvicorn, requests, etc.)
# -----------------------------------------------------------------
WORKDIR /tmp
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------
# 1e – (optioneel) SoundFont – kan later worden toegevoegd
# -----------------------------------------------------------------
# Als je nu al een soundfont in de repo hebt, kopieer je die hier:
COPY soundfonts/FluidR3_GM_GS.sf2 /opt/soundfonts/
ENV FLUIDSYNTH_SOUNDFONT=/opt/soundfonts/FluidR3_GM_GS.sf2
# (Voor nu laten we het leeg; je kunt later een volume mount gebruiken.)



#################################################################
#
# ======================   R U N T I M E   ======================      
#
#################################################################



# --------------------------------------------------------------
# 2️⃣ RUNTIME STAGE – zo klein mogelijk, alleen wat nodig is
# --------------------------------------------------------------
FROM python:3.11-slim-bookworm
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8

# -----------------------------------------------------------------
# 2a – Niet‑root gebruiker (username: api)
# -----------------------------------------------------------------
RUN groupadd -r api && useradd -r -g api -u 1001 api

# ---------- Maak een gedeelde Wine‑prefix ----------
ENV WINEPREFIX=/wineprefix
RUN mkdir -p $WINEPREFIX && \
    chown -R api:api $WINEPREFIX

# -----------------------------------------------------------------
# 2b – Runtime‑only native deps (fontconfig + audio libs)
# -----------------------------------------------------------------
RUN dpkg --add-architecture i386 && \
        apt-get update && apt-get install -y --no-install-recommends \
        fontconfig \
        libasound2:i386 \
        libasound2-plugins:i386 \
        libpulse0:i386 \
        libc6:i386 \
        libglib2.0-0:i386 \
        libgtk-3-0:i386 \
        libgdk-pixbuf2.0-0:i386 \
        libx11-6:i386 \
        libxext6:i386 \
        libxrender1:i386 \
        libfreetype6:i386 \
        libstdc++6:i386 \
        # if needed, temporary apt-file & sudo:
        # apt-file \  
        # sudo \
        ffmpeg \
        fluidsynth \
        xvfb \
    && rm -rf /var/lib/apt/lists/*


# ---------- Kopieer **alle** Wine‑binaries & libraries ----------
# 2c (a) Executables (wine, wine64, etc.)
# COPY --from=builder /usr/bin/wine*            /usr/bin/
# 1. De wine‑executables (wine, wine64, …) – ze zitten onder /opt/wine-stable/bin
COPY --from=builder /opt/wine-stable/bin/ /opt/wine-stable/bin/

# # 2c (b) Complete library trees (recursief!)
# De volledige library‑boom (incl. ntdll.so, dlls, …)
COPY --from=builder /opt/wine-stable/lib/ /opt/wine-stable/lib/

# Eventueel share‑data (icons, mime‑info) – niet strikt nodig voor CLI‑tools
COPY --from=builder /opt/wine-stable/share/ /opt/wine-stable/share/

# # (optioneel, als het bestaat)
# COPY --from=builder /usr/lib/wine/            /usr/lib/wine/

# ---------- Maak Wine‑config‑dir ----------
RUN mkdir -p /etc/wine

# ---------- Laat de dynamische linker de nieuwe libs zien ----------
# Voeg /opt/wine-stable/lib aan de library‑search‑path
# ENV LD_LIBRARY_PATH="/opt/wine-stable/lib:${LD_LIBRARY_PATH}"
RUN ldconfig

# ---------- Voeg wine‑bin‑pad toe aan $PATH ----------
ENV PATH="/opt/wine-stable/bin:${PATH}"

# ---------- (optioneel) Xvfb ----------
ARG ENABLE_XVFB=true
RUN if [ "$ENABLE_XVFB" = "true" ]; then \
        apt-get update && apt-get install -y --no-install-recommends xvfb && \
        rm -rf /var/lib/apt/lists/*; \
    fi

# ---------- Suppress noisy Wine output ----------
ENV WINEDEBUG=-all
ENV WINEDLLOVERRIDES=explorer,winebth=
# (optioneel) als je Xvfb wilt gebruiken: Xvfb will listen on :99 when started
# ENV DISPLAY=:99   

# Maak een schrijfbare cache‑map voor de api‑gebruiker
RUN mkdir -p /home/api/.cache/fontconfig && \
    chown -R api:api /home/api/.cache

# ---------- 2e – Maak de map (optioneel, maar netjes) ----------
RUN mkdir -p /opt/soundfonts
COPY --from=builder /opt/soundfonts/FluidR3_GM_GS.sf2 /opt/soundfonts/
ENV FLUIDSYNTH_SOUNDFONT=/opt/soundfonts/FluidR3_GM_GS.sf2

# -----------------------------------------------------------------
# Kopieer Python‑omgeving (site‑packages + scripts)
# -----------------------------------------------------------------
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# ---------- 2️⃣ Kopieer de Noteworthy‑installatie ----------
# Escape spaces and parentheses with backslashes
COPY --from=builder \
    ["wineprefix/drive_c/Program Files/Noteworthy Software/NoteWorthy Composer 2/", "/opt/noteworthy/"]

# (optioneel) maak de map zichtbaar voor Wine
ENV WINEPATH="/opt/noteworthy"

# -----------------------------------------------------------------
# 2f – Kopieer applicatiecode
# -----------------------------------------------------------------
WORKDIR /app
COPY app/ /app/
RUN chown -R api:api /app /opt/soundfonts /opt/noteworthy

# -----------------------------------------------------------------
# 2h – Niet‑root gebruiker activeren
# -----------------------------------------------------------------
USER api

# -----------------------------------------------------------------
# 2g – Environment
# -----------------------------------------------------------------
ENV PATH="/usr/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# -----------------------------------------------------------------
# 2i – Expose en health‑check (zelfde als in je andere API)
# -----------------------------------------------------------------
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# -----------------------------------------------------------------
# 2j – Start de FastAPI‑app met Uvicorn
# -----------------------------------------------------------------
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
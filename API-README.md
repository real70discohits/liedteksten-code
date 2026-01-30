# Liedteksten PDF Generation API

Docker-gebaseerde API voor het genereren van PDF's uit LaTeX liedteksten.

## Overzicht

Deze API stelt je in staat om LaTeX liedteksten (.tex files) te uploaden en gecompileerde PDF's terug te ontvangen. De API ondersteunt:

- Meerdere PDF varianten (met/zonder maatnummers, akkoorden, gitaargrepen)
- Transposities
- Song-specifieke configuraties (marges, fontsize)
- Custom LaTeX style packages
- Config caching voor hergebruik

## Gebouwd project

### Wat is er aangepast

1. **Dockerfile**
   - LaTeX packages toegevoegd voor liedbasis.sty (tikz, gchords, leadsheets, etc.)
   - Cache directory structuur gemaakt
   - liedbasis.sty geïnstalleerd in LaTeX tree

2. **requirements.txt**
   - commentjson toegevoegd voor .jsonc parsing

3. **Nieuwe modules**
   - `lt_generate_api.py` - API-specifieke compile functies
   - Gekopieerde modules: `lt_configloader.py`, `pathconfig.py`, `lt-generate.py`

4. **main.py**
   - Volledig herschreven met nieuwe endpoints
   - ZIP response voor meerdere PDFs
   - Config cache management

## Bouwen van de Docker image

```bash
docker build -t liedteksten-api .
```

## Draaien van de container

```bash
docker run -p 8000:8000 liedteksten-api
```

De API is nu beschikbaar op `http://localhost:8000`

## API Endpoints

### 1. Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "liedteksten-pdf-api"
}
```

### 2. Compile .tex naar PDF

```bash
POST /compile
```

**Parameters:**
- `tex_file` (file, required): De .tex file om te compileren
- `config_file` (file, optional): lt-config.jsonc voor layout aanpassingen
- `sty_file` (file, optional): Custom liedbasis.sty
- `only` (int, optional): Welke variant genereren
  - `0` (default): Alle varianten
  - `-1`: Alleen varianten met config
  - `1-5`: Specifieke variant
    - 1 = alleen tekst
    - 2 = tekst + maatnummers
    - 3 = tekst + akkoorden
    - 4 = tekst + maatnummers + akkoorden
    - 5 = alles (tekst + maatnummers + akkoorden + gitaargrepen)
- `tab_orientation` (string, optional): `left`, `right`, of `traditional` (default: `left`)
- `large_print` (bool, optional): default `false`. For optimized readability of PDF's (large, bold).

**Response:** ZIP file met:
- Bij succes: Alle PDFs + `console.log`
- Bij fout: `error.txt` + LaTeX `.log` files + `console.log`

De API suggereert automatisch een filename met timestamp: `{liedtitel}_{YYYYMMDD_HHMMSS}.zip`

**Input filename conventies:**
- Liedtekst: `Such A Beauty (6).tex`
- Structuur: `Such A Beauty (6) structuur.tex`

**Voorbeelden:**

```bash
# Basis: upload alleen .tex, genereer alle varianten
# De API suggereert automatisch: "Such A Beauty (6)_20260102_153045.zip"
# Assumes current dir contains file Such A Beauty (6).tex.
curl -X POST http://localhost:8000/compile \
  -F "tex_file=@Such A Beauty (6).tex" \
  -OJ

# Pad opgeven is mogelijk met curl, bv dit relatieve pad (let op de quotes
# ivm de spaties in de foldernaam)
curl -X POST http://localhost:8000/compile \
  -F 'tex_file=@"Such A Beauty (6)/Such A Beauty (6).tex"' \
  -OJ

# Of gebruik -o om zelf een naam te kiezen:
curl -X POST http://localhost:8000/compile \
  -F "tex_file=@Such A Beauty (6).tex" \
  -o output.zip

# Met config en specifieke variant
curl -X POST http://localhost:8000/compile \
  -F "tex_file=@Such A Beauty (6).tex" \
  -F "config_file=@lt-config.jsonc" \
  -F "only=5" \
  -OJ

# Met custom .sty
curl -X POST http://localhost:8000/compile \
  -F "tex_file=@Such A Beauty (6).tex" \
  -F "sty_file=@my-liedbasis.sty" \
  -OJ

# Alleen varianten met config, tab orientation right
curl -X POST http://localhost:8000/compile \
  -F "tex_file=@Such A Beauty (6).tex" \
  -F "only=-1" \
  -F "tab_orientation=right" \
  -OJ

# Voor optimized readability
curl -X POST http://localhost:8000/compile \
  -F "tex_file=@Such A Beauty (6).tex" \
  -F "only=1" \
  -F "large_print=true" \
  -OJ
```

**Note over curl opties:**
- `-OJ`: Gebruikt de door de server gesuggereerde filename (met timestamp)
- `-o bestandsnaam.zip`: Gebruik je eigen filename
- In de browser wordt automatisch de door de server gesuggereerde filename gebruikt

### 3. Config Management

#### Haal gecachte config op

```bash
GET /config/{song_title}
```

Voorbeeld:
```bash
curl http://localhost:8000/config/Such%20A%20Beauty%20%286%29
```

#### Upload/update config

```bash
POST /config/{song_title}
```

Voorbeeld:
```bash
curl -X POST http://localhost:8000/config/Such%20A%20Beauty%20%286%29 \
  -F "config_file=@lt-config.jsonc"
```

#### Verwijder config

```bash
DELETE /config/{song_title}
```

Voorbeeld:
```bash
curl -X DELETE http://localhost:8000/config/Such%20A%20Beauty%20%286%29
```

#### Lijst alle gecachte configs

```bash
GET /configs
```

Voorbeeld:
```bash
curl http://localhost:8000/configs
```

## Workflows

### Workflow 1: Snelle compile met config

Upload .tex + config in één request:

```bash
curl -X POST http://localhost:8000/compile \
  -F "tex_file=@Such A Beauty (6).tex" \
  -F "config_file=@lt-config.jsonc" \
  -OJ
```

De config wordt automatisch gecached voor toekomstige requests.

### Workflow 2: Pre-cache configs

Upload eerst alle configs:

```bash
curl -X POST http://localhost:8000/config/Such%20A%20Beauty%20(6) \
  -F "config_file=@lt-config.jsonc"
```

Dan kun je later alleen .tex uploaden:

```bash
curl -X POST http://localhost:8000/compile \
  -F "tex_file=@Such A Beauty (6).tex" \
  -OJ
```

### Workflow 3: Structuur PDF

Upload een structuur .tex file (gegenereerd door nwc-concat.py):

```bash
curl -X POST http://localhost:8000/compile \
  -F "tex_file=@Such A Beauty (6) structuur.tex" \
  -OJ
```

## Testen lokaal (zonder Docker)

Als je de code lokaal wilt testen zonder Docker:

```bash
# Installeer dependencies
pip install -r requirements.txt

# Start de API
cd app
python main.py
```

De API draait dan op `http://localhost:8000`

**Let op:** Voor lokaal testen moet pdflatex beschikbaar zijn in je PATH.

## Interactive API documentatie

FastAPI genereert automatisch interactive documentatie:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Bestandslimieten

- .tex files: max 10 MB
- .jsonc config files: max 1 MB
- .sty files: max 5 MB

## Folder structuur in container

```
/app/
  main.py                    # API endpoints
  lt_generate_api.py         # Compile functies
  lt-generate.py             # Originele module (import)
  lt_configloader.py         # Config loader
  pathconfig.py              # Path utilities
  liedbasis.sty             # Standaard LaTeX package
  cache/
    configs/                 # Gecachte lt-config.jsonc files
```

## Deployment naar Scaleway (of andere cloud)

Voor persistente config cache heb je een volume mount nodig:

```bash
docker run -p 8000:8000 \
  -v /path/to/configs:/app/cache/configs \
  liedteksten-api
```

Dit zorgt ervoor dat configs bewaard blijven tussen container restarts.

## Troubleshooting

### LaTeX compilation errors

Als de compilatie faalt, download de ZIP en check:
- `error.txt` voor algemene error info
- `console.log` voor volledige console output
- `*.log` files voor LaTeX specifieke errors

### Missing LaTeX packages

Als er een LaTeX package ontbreekt, voeg het toe aan de Dockerfile:

```dockerfile
RUN tlmgr install \
    ...
    your-missing-package \
    && tlmgr path add
```

Rebuild de image.

## Veiligheid

- Container draait als non-root user (`pdfgen`)
- File size limits voorkomen resource exhaustion
- Temporary directories worden opgeschoond na gebruik
- Geen shell-escape in pdflatex (veilig tegen code injection)

## Bekende beperkingen

- Oude ZIP files in `/tmp/pdf-output` worden niet automatisch opgeschoond
  - Voor productie: implementeer een cleanup background task
- Config cache is niet persistent zonder volume mount
- Geen rate limiting (voeg dit toe in productie)

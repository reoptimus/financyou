# ---------------------------------------------------------------------------
# Image FinancYou - construction multi-etages.
# Etage 1 (builder) : compile et installe les dependances dans un venv isole.
# Etage 2 (runtime) : image mince, sans chaine de compilation, utilisateur
#                     non privilegie, ne recevant que le venv et le code utile.
# ---------------------------------------------------------------------------

# =========================== Etage 1 : construction ========================
FROM python:3.12-slim AS builder

# Le venv est autonome : il sera recopie tel quel dans l'etage d'execution.
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Chaine de compilation necessaire uniquement ici (numpy/scipy sans roue).
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        gfortran \
        libopenblas-dev \
        liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv "$VIRTUAL_ENV" && pip install --upgrade pip setuptools wheel

WORKDIR /build

# Les dependances sont installees avant le code source : la couche est mise en
# cache tant que requirements.txt ne change pas.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Installation du paquet FinancYou lui-meme (dependances deja resolues).
COPY pyproject.toml MANIFEST.in README.md LICENSE ./
COPY investment_calculator/ ./investment_calculator/
COPY time_series_slicer/ ./time_series_slicer/
RUN pip install --no-deps .

# ============================ Etage 2 : execution ==========================
FROM python:3.12-slim AS runtime

LABEL maintainer="FinancYou Team" \
      org.opencontainers.image.title="FinancYou" \
      org.opencontainers.image.description="FinancYou - planification financiere et optimisation de portefeuille" \
      org.opencontainers.image.source="https://github.com/reoptimus/financyou" \
      org.opencontainers.image.licenses="MIT"

# Bibliotheques d'execution seules : pas de compilateur dans l'image finale.
# curl est requis par le healthcheck Streamlit.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libopenblas0 \
        liblapack3 \
    && rm -rf /var/lib/apt/lists/*

# Utilisateur non privilegie cree explicitement (UID/GID fixes).
RUN groupadd --gid 10001 financyou \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin financyou

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Recuperation du venv construit a l'etage precedent.
COPY --from=builder --chown=financyou:financyou /opt/venv /opt/venv

WORKDIR /app

# COPY selectif : uniquement ce qui est necessaire a l'execution de l'UI.
# Ni .git, ni legacy/, ni outputs/, ni tests/ (voir .dockerignore).
COPY --chown=financyou:financyou web_ui/ ./web_ui/
COPY --chown=financyou:financyou examples/input_files/ ./examples/input_files/

# Repertoire de sortie inscriptible par l'utilisateur non-root.
RUN mkdir -p /app/outputs && chown -R financyou:financyou /app

EXPOSE 8501

# Sonde de sante Streamlit (inchangee).
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# L'utilisateur non-root s'applique avant le CMD.
USER financyou

CMD ["streamlit", "run", "web_ui/app_enhanced.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]

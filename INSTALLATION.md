# FinancYou Installation Guide

Complete installation instructions for FinancYou financial planning system.

## Package Overview

| Item | Value |
|---|---|
| Distribution name (PyPI / `pip install`) | **`financyou`** |
| Version | **0.2.0** |
| Importable packages | `investment_calculator`, `time_series_slicer` |
| Minimum Python | **3.11** |
| Build backend | setuptools (PEP 621, `pyproject.toml`) |
| Repository | https://github.com/reoptimus/financyou |

> The distribution used to be published as `time_series_slicer`. It is now
> `financyou`. **The importable module names are unchanged** — existing code
> such as `from investment_calculator.modules import optimizer` keeps working.
> `setup.py` has been removed; all metadata lives in `pyproject.toml`.

### Extras

| Extra | Installs | Use it for |
|---|---|---|
| *(none)* | pandas, numpy, scipy, openpyxl, matplotlib | Core financial engine only |
| `web` | streamlit, plotly | Streamlit dashboard |
| `dev` | pytest, pytest-cov, ruff, mypy, type stubs | Tests, lint, type checking |

## Table of Contents
- [Quick Start (Local)](#quick-start-local)
- [Docker Installation (Recommended)](#docker-installation-recommended)
- [Manual Installation](#manual-installation)
- [Troubleshooting](#troubleshooting)

---

## Quick Start (Local)

### Prerequisites
- Python **3.11 or higher**
- pip package manager

### Install Dependencies

```bash
# Clone or navigate to the project directory
cd financyou

# Recommended: install the package with the web extra
pip install -e ".[web]"

# Or, for a development environment (tests + lint + typing)
pip install -e ".[web,dev]"
```

Alternatively, install the pinned runtime dependencies directly. The root
`requirements.txt` now contains **everything the web application needs**
(streamlit and plotly included) with lower and upper version bounds:

```bash
pip install -r requirements.txt        # runtime (engine + web UI)
pip install -r requirements-dev.txt    # runtime + test/lint/typing tools
```

`web_ui/requirements.txt` is kept only for backwards compatibility and simply
redirects to the root `requirements.txt`.

### Run the Application

**Enhanced Web UI (Recommended):**
```bash
streamlit run web_ui/app_enhanced.py
```

**Simple Web UI:**
```bash
streamlit run web_ui/app.py
```

**Command-Line Pipeline:**
```bash
python examples/complete_pipeline_with_files.py
```

The web dashboard will open at: **http://localhost:8501**

---

## Docker Installation (Recommended)

### Why Docker?
✅ No dependency conflicts
✅ Consistent environment
✅ Easy deployment
✅ Production-ready

### Image layout

The image is built from the **single `Dockerfile` at the repository root**
(the former `web_ui/Dockerfile` was a duplicate and has been removed):

- **Multi-stage build** — a `builder` stage compiles the dependencies into a
  virtualenv at `/opt/venv`; the `runtime` stage is a slim `python:3.12-slim`
  that receives only that virtualenv plus the code needed at runtime.
- **Non-root** — the container runs as the `financyou` user (UID/GID 10001),
  applied before `CMD`.
- **Selective `COPY`** — `.git`, `legacy/`, `outputs/`, `tests/` and the
  example scripts are excluded through `.dockerignore` (build context drops
  from roughly 40 MB to under 0.5 MB).
- Streamlit still listens on **port 8501** and keeps its `/_stcore/health`
  healthcheck.

Because the container runs as UID 10001, a bind-mounted `./outputs` directory
on the host must be writable by that UID:

```bash
mkdir -p outputs && sudo chown 10001:10001 outputs
```

### Option 1: Docker Compose (Easiest)

```bash
# From project root directory
docker compose up -d

# View logs
docker compose logs -f

# Stop the application
docker compose down
```

Access at: **http://localhost:8501**

### Option 2: Docker Build & Run

```bash
# Build the image
docker build -t financyou:0.2.0 .

# Run the container
docker run -d \
  --name financyou-app \
  -p 8501:8501 \
  -v $(pwd)/outputs:/app/outputs \
  financyou:0.2.0

# View logs
docker logs -f financyou-app

# Stop the container
docker stop financyou-app
docker rm financyou-app
```

---

## Manual Installation

### Step 1: Install the FinancYou Package

```bash
# From project root — pulls the pinned dependencies automatically
pip install -e ".[web,dev]"
```

### Step 2: Verify Installation

```bash
# Distribution metadata
pip show financyou          # Name: financyou, Version: 0.2.0

# Test imports (module names are unchanged)
python -c "import investment_calculator, time_series_slicer; print('✓ Packages OK')"
python -c "from investment_calculator.modules import scenario_generator; print('✓ Core modules OK')"

# Test web UI dependencies
python -c "import streamlit, plotly; print('✓ Web UI dependencies OK')"

# Run tests
pytest tests/ -v
```

### Step 3: Run the Application

```bash
streamlit run web_ui/app_enhanced.py
```

---

## Installation by Component

### Core Financial Engine Only

```bash
# Minimal installation for programmatic use — no extra needed
pip install -e .
```

Then use in Python:
```python
from investment_calculator.modules import (
    scenario_generator,
    tax_engine,
    user_profile,
    optimizer,
    reporting
)
```

### Web Interface Only

```bash
# Core engine + streamlit + plotly
pip install -e ".[web]"

# Run the web app
streamlit run web_ui/app_enhanced.py
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'plotly'"

**Solution:**
```bash
pip install plotly
```

Or with specific version:
```bash
pip install plotly>=5.17.0
```

### Issue: "Port 8501 is already in use"

**Solution 1 - Use different port:**
```bash
streamlit run app_enhanced.py --server.port=8502
```

**Solution 2 - Kill existing process:**
```bash
# Linux/Mac
lsof -ti:8501 | xargs kill -9

# Windows
netstat -ano | findstr :8501
taskkill /PID <PID> /F
```

### Issue: Import errors with investment_calculator modules

**Solution:**
```bash
# Ensure you're in the project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in editable mode
pip install -e .
```

### Issue: Docker build fails

**Solution:**
```bash
# Clean Docker cache
docker system prune -a

# Rebuild with no cache
docker build --no-cache -t financyou:latest .
```

### Issue: Plotly charts not displaying

**Solution:**
```bash
# Update Streamlit and Plotly
pip install --upgrade streamlit plotly

# Clear Streamlit cache
streamlit cache clear
```

---

## Platform-Specific Instructions

### Windows

```bash
# Use PowerShell or CMD
pip install -e ".[web]"
streamlit run web_ui/app_enhanced.py
```

### macOS

```bash
# Use Homebrew to install Python if needed
brew install python@3.11

# Install dependencies
pip3 install -e ".[web]"

# Run application
streamlit run web_ui/app_enhanced.py
```

### Linux (Ubuntu/Debian)

```bash
# Install Python and dependencies
sudo apt-get update
sudo apt-get install python3.11 python3-pip

# Install project dependencies
pip3 install -e ".[web]"

# Run application
streamlit run web_ui/app_enhanced.py
```

---

## Virtual Environment (Recommended)

Using a virtual environment prevents dependency conflicts:

```bash
# Create virtual environment
python -m venv financyou-env

# Activate it
# Windows:
financyou-env\Scripts\activate

# macOS/Linux:
source financyou-env/bin/activate

# Install dependencies
pip install -e ".[web]"

# Run application
streamlit run web_ui/app_enhanced.py

# Deactivate when done
deactivate
```

---

## Cloud Deployment

### Streamlit Cloud

1. Push code to GitHub
2. Go to https://share.streamlit.io
3. Connect your repository
4. Set app path: `web_ui/app_enhanced.py`
5. Deploy!

### Heroku

```bash
# Create Procfile
echo "web: streamlit run web_ui/app_enhanced.py --server.port=\$PORT --server.address=0.0.0.0" > Procfile

# Deploy
heroku create financyou-app
git push heroku main
heroku open
```

### AWS/Azure/GCP

Use the provided Dockerfile and docker-compose.yml for container deployment.

---

## Verification

After installation, verify everything works:

```bash
# Run all tests
pytest tests/ -v

# Should collect 246 tests (245 passed, 1 skipped)

# Run example pipeline
python examples/complete_pipeline_with_files.py

# Should complete without errors

# Access web UI
streamlit run web_ui/app_enhanced.py
# Navigate to http://localhost:8501
```

---

## Getting Help

- **Tests failing?** Check that all dependencies are installed correctly
- **Import errors?** Ensure PYTHONPATH is set or package is installed with `pip install -e .`
- **Web UI issues?** Try clearing cache: `streamlit cache clear`
- **Docker issues?** Check Docker is running: `docker --version`

For more help, see the main README.md and web_ui/README.md files.

FROM python:3.11-slim

LABEL maintainer="FinancYou Team"
LABEL description="FinancYou Interactive Financial Planning Dashboard"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY .. /app

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run the app
CMD ["streamlit", "run", "web_ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

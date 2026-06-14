# Use official Python base image
FROM python:3.11-slim

# Install system dependencies (curl for healthcheck, git for possible dependencies, and build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the app
COPY . .

# Expose Streamlit's default port
EXPOSE 8501

# Healthcheck (optional but recommended for Render)
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Command to run the app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download Hugging Face models to cache them
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
RUN python -c "from transformers import AutoTokenizer, AutoModelForCausalLM; AutoTokenizer.from_pretrained('microsoft/Phi-3-mini-4k-instruct', trust_remote_code=True); print('Model cached')" || echo "Model download skipped (will download on first use)"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/lab_markers data/nutrition data/conditions templates static

# Build vector database at build time (if data exists)
RUN python build_vector_db.py || echo "Vector DB will be built on first data upload"

# Expose port
EXPOSE 7860

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/app/.cache
ENV HF_HOME=/app/.cache

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--timeout", "300", "--workers", "1", "--threads", "2", "app:app"]
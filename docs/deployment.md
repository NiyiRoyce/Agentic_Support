# Deployment Guide

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Redis (for production memory store)
- OpenAI API key (or Anthropic)
- ChromaDB (vector store)

## Environment Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd Agentic_Support
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

Required environment variables:
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
- `REDIS_URL` (for production memory)
- `APP_ENV=production`
- `LOG_LEVEL=INFO`
- `OTLP_ENDPOINT` (optional, for tracing)

## Local Development

1. Start dependencies:
```bash
docker-compose up -d redis chroma
```

2. Run the application:
```bash
uvicorn app.main:app --reload
```

3. Access API at http://localhost:8000

## Production Deployment

### Docker Deployment

1. Build the image:
```bash
docker build -t ai-support-agent .
```

2. Run with Docker Compose:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Manual Deployment

1. Set up Redis and ChromaDB services

2. Configure reverse proxy (nginx):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /metrics {
        proxy_pass http://127.0.0.1:8000/metrics;
        allow 10.0.0.0/8;  # Restrict access to monitoring
        deny all;
    }
}
```

3. Set up systemd service:
```ini
[Unit]
Description=AI Support Agent
After=network.target

[Service]
User=ai-support
WorkingDirectory=/path/to/app
ExecStart=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

4. Enable and start service:
```bash
sudo systemctl enable ai-support-agent
sudo systemctl start ai-support-agent
```

## Initial Setup

1. Ingest knowledge base:
```bash
python scripts/ingest_docs.py ./docs
```

2. Rebuild vector index (if needed):
```bash
python scripts/rebuild_index.py
```

3. Backfill embeddings (if needed):
```bash
python scripts/backfill_embeddings.py
```

## Scaling Considerations

- Use Redis for memory store in production
- Scale LLM providers based on load
- Monitor memory usage and vector store performance
- Consider load balancer for multiple instances

## Security Checklist

- [ ] API keys stored securely (not in code)
- [ ] HTTPS enabled
- [ ] Rate limiting configured
- [ ] CORS properly restricted
- [ ] Secrets rotated regularly
- [ ] Audit logging enabled

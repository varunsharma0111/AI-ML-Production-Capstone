# AuraML Production Deployment Guide

---

## 1. Target Infrastructure Stack

- **Frontend SPA**: Vercel or Cloudflare Pages
- **API Server & Async Worker**: Render, AWS ECS, or DigitalOcean Apps
- **Database**: Managed PostgreSQL (Neon / AWS RDS)
- **Redis Cache & Queue**: Managed Redis (Upstash / Render Redis / AWS ElastiCache)
- **Object Storage**: AWS S3, MinIO, or Cloudflare R2

---

## 2. Environment Variables Checklist

### API & Worker Environment Variables
```env
APP_ENV=production
APP_NAME=AuraML Platform
LOG_LEVEL=INFO
PORT=8000

# Database
DATABASE_URL=postgresql+asyncpg://user:password@ep-prod.neon.tech/auraml_prod?sslmode=require

# Cache & Redis Queue
REDIS_URL=rediss://default:password@prod-redis.upstash.io:6379

# Object Storage Configuration
STORAGE_BACKEND=s3
S3_BUCKET=auraml-prod-artifacts
S3_REGION=us-east-1
S3_ENDPOINT_URL=https://s3.us-east-1.amazonaws.com
S3_ACCESS_KEY_ID=AKIA...
S3_SECRET_ACCESS_KEY=secret...

# Identity & OIDC Authentication
OIDC_ISSUER=https://auth.auraml.com/
OIDC_AUDIENCE=auraml-api
OIDC_JWKS_URL=https://auth.auraml.com/.well-known/jwks.json

# Security & CORS
CORS_ORIGINS=https://app.auraml.com
```

---

## 3. Database Migration Deployment Step

Always execute database migrations prior to deploying API instances:

```bash
alembic upgrade head
```

---

## 4. Containerized Production Deployment

### Dockerfile.api
```bash
docker build -t auraml-api:latest -f infra/docker/Dockerfile.api .
docker run -d -p 8000:8000 --env-file .env auraml-api:latest
```

### Dockerfile.worker
```bash
docker build -t auraml-worker:latest -f infra/docker/Dockerfile.worker .
docker run -d --env-file .env auraml-worker:latest
```

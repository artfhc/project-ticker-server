# Architecture Plan: Ticker API Migration to Render

## Executive Summary

**Current State:** Serverless AWS Lambda + API Gateway + ECR
**Target State:** Always-on FastAPI service on Render with simplified deployment

## Proposed Architecture

### 1. Application Layer Redesign

**Current Issues to Address:**
- Remove Mangum (AWS Lambda adapter) - not needed for Render
- Fix missing `uvicorn` import in `main.py:49`
- Simplify application structure for traditional web service model

**New FastAPI Structure:**
```
app/
├── main.py              # Pure FastAPI app (no Lambda handler)
├── health.py            # Health check endpoint for Render
├── api/
│   └── v1/
│       ├── ticker.py    # Enhanced ticker endpoints
│       └── users.py     # Future user management
├── core/
│   ├── config.py        # Environment-based configuration
│   └── ticker_mapping.py # Expanded ticker symbol mappings
└── requirements.txt     # Dependencies (remove mangum)
```

### 2. Infrastructure Simplification

**Remove AWS Components:**
- ✗ AWS Lambda + API Gateway
- ✗ ECR + Terraform infrastructure
- ✗ Complex Docker builds
- ✗ IAM roles and permissions

**New Render Infrastructure:**
- ✓ Single Web Service (FastAPI)
- ✓ Environment variable configuration
- ✓ Built-in SSL/custom domains
- ✓ Automatic Git deployment

### 3. Enhanced Ticker API Design

**Improved Endpoints:**
```
GET /health                 # Render health check
GET /api/v1/ticker/{symbol}/price    # Price data
GET /api/v1/ticker/{symbol}/info     # Complete info
GET /api/v1/ticker/{symbol}/history  # Historical data
GET /api/v1/search/{query}           # Symbol search
```

**New Features:**
- Expanded ticker mapping dictionary
- Symbol search functionality
- Caching layer for frequently requested tickers
- Rate limiting for Yahoo Finance API
- Better error handling and responses

### 4. Configuration Management

**Environment Variables:**
```bash
ENVIRONMENT=production
YAHOO_FINANCE_TIMEOUT=30
CACHE_TTL=300
LOG_LEVEL=INFO
CORS_ORIGINS=https://yourdomain.com
```

**Health Check Configuration:**
```python
# /health endpoint for Render monitoring
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "2.0.0"
    }
```

## Deployment Strategy

### 1. Render Service Configuration

**Service Settings:**
- **Environment:** Python 3.11
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/health`
- **Auto-Deploy:** Enable from main branch

### 2. Requirements Update

**New requirements.txt:**
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
yfinance==0.2.28
pydantic==2.5.0
python-multipart==0.0.6
# Remove: mangum (AWS-specific)
```

### 3. GitHub Actions Workflow

**Simple deployment pipeline:**
```yaml
name: Deploy to Render
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: johnbeynon/render-deploy-action@v0.0.8
        with:
          service-id: ${{ secrets.RENDER_SERVICE_ID }}
          api-key: ${{ secrets.RENDER_API_KEY }}
```

## Migration Benefits

### 1. Operational Simplicity
- **Before:** AWS CLI setup, ECR login, Terraform, complex Makefile
- **After:** Git push triggers automatic deployment

### 2. Cost Predictability
- **Before:** Pay per request + cold start overhead
- **After:** Fixed monthly cost ($7-25/month for production)

### 3. Development Experience
- **Before:** Local FastAPI dev, complex Lambda testing
- **After:** Identical local and production environments

### 4. Performance Improvements
- **Before:** Cold starts (100-500ms penalty)
- **After:** Always-warm service, sub-10ms response times

## Implementation Timeline

**Phase 1: Core Migration (2-3 days)**
1. Remove AWS dependencies (Mangum, Terraform)
2. Fix FastAPI application structure
3. Add health check endpoint
4. Set up Render service

**Phase 2: Enhanced Features (3-5 days)**
1. Expand ticker mapping
2. Add caching layer
3. Implement rate limiting
4. Add symbol search

**Phase 3: Production Hardening (2-3 days)**
1. Set up monitoring and alerts
2. Configure custom domain
3. Load testing and optimization
4. Documentation updates

## Risk Mitigation

**Traffic Scaling:**
- Start with Render Starter tier ($7/month)
- Monitor performance and scale up if needed
- Implement caching to reduce Yahoo Finance API calls

**Data Persistence:**
- Current app is stateless - no migration needed
- Future: Add Redis for caching if required

**Rollback Plan:**
- Keep AWS infrastructure temporarily
- Use feature flags for gradual migration
- DNS switch for instant rollback

This architecture eliminates AWS complexity while maintaining all current functionality and enabling easier future enhancements.
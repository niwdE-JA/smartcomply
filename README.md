# Transaction Monitoring Service

A production-ready backend service for financial transaction monitoring that evaluates monitoring rules asynchronously and generates alerts when suspicious activity is detected. Built with Django, PostgreSQL, Celery, and Redis.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Rate Limiting](#rate-limiting)
- [Architecture](#architecture)
- [Database Models](#database-models)
- [Configuration](#configuration)
- [Testing](#testing)
- [Deployment](#deployment)

## Overview

This service provides a robust, scalable solution for transaction monitoring in fintech and compliance platforms. It processes transactions asynchronously, evaluates them against configurable monitoring rules, and generates alerts for suspicious activity.

### Key Capabilities

- **Transaction Ingestion**: RESTful API for high-volume transaction submission
- **Dynamic Rule Management**: Create, update, and activate monitoring rules without downtime
- **Asynchronous Processing**: Celery-based rule evaluation with automatic retries
- **Alert Generation**: Real-time alerts with configurable deduplication
- **Audit Trail**: Complete audit history of all rule changes
- **Redis Caching**: Fast deduplication and rate limiting
- **OpenAPI Documentation**: Interactive Swagger UI for API exploration
- **Database Optimization**: Strategic indexing for fast queries

## Features

### Core Functionality

#### 1. Transaction Management
- **Create transactions**: `POST /api/v1/transactions/`
- **List transactions**: `GET /api/v1/transactions/`
- **Filter & search**: By account_id, type, currency
- **Sorting**: By timestamp, amount, created_at
- **Pagination**: Configurable (default 20, max 100 items per page)
- **Rate limiting**: 50 transactions per account per minute

#### 2. Monitoring Rules
- **Create rules**: `POST /api/v1/rules/`
- **Manage rules**: Update, delete, activate, deactivate
- **Supported types**:
  - **LARGE_TRANSACTION**: Alert when transaction exceeds amount threshold
  - **HIGH_FREQUENCY**: Alert when account has 5+ transactions within 24 hours
- **Rate limiting**: 30 rule operations per user per hour
- **Audit trail**: All changes tracked with timestamps and performer info

#### 3. Alert Management
- **List alerts**: `GET /api/v1/alerts/`
- **Filter alerts**: By rule, account, status
- **Update status**: Mark as reviewed, dismissed, or resolved
- **Rate limiting**: 100 alert operations per user per hour
- **Deduplication**: Prevent duplicate alerts within configurable time window

#### 4. Audit Trail
- **Track rule changes**: Who created/modified and when
- **Record actions**: CREATE, UPDATE, ACTIVATE, DEACTIVATE, DELETE
- **Capture changes**: Before/after values for all modifications
- **List audit logs**: `GET /api/v1/audit-logs/`
- **Filter by rule**: `GET /api/v1/audit-logs/by_rule/?rule_id=<uuid>`

#### 5. API Documentation
- **Swagger UI**: Interactive endpoint explorer at `/api/docs/`
- **OpenAPI Schema**: Raw JSON schema at `/api/schema/`
- **Try-it-out**: Test all endpoints directly from browser
- **Full schema**: Request/response examples and validations

### Performance Features

#### Redis Deduplication
- **O(1) lookups**: Fast duplicate alert detection
- **Configurable TTL**: Different time windows per rule type
- **Batch operations**: Efficient bulk checking
- **Automatic expiration**: Redis handles cleanup

#### Rate Limiting
- **Global limits**: 100/hour for anonymous, 1000/hour for authenticated users
- **Endpoint-specific limits**:
  - Transaction creation: 50 per account per minute
  - Rule management: 30 per user per hour
  - Alert operations: 100 per user per hour
- **Distributed**: Works across multiple workers
- **Fail-open**: Allows requests if Redis unavailable

## Technology Stack

### Backend
- **Django 4.2.13**: Web framework with ORM, security, admin panel
- **Django REST Framework 3.14.0**: REST API toolkit
- **drf-spectacular 0.27.0**: OpenAPI 3.0 schema generation

### Database
- **PostgreSQL 15**: Primary data store with advanced features
- **Connection pooling**: Efficient database connections
- **Strategic indexes**: On (account_id, timestamp), transaction_id, created_at

### Async Processing
- **Celery 5.3.4**: Distributed task queue
- **Exponential backoff**: Automatic retry with increasing delays
- **Max retries**: 3 attempts before failure
- **Task timeout**: 30 minutes per task

### Caching & Message Broker
- **Redis 7**: Message broker, result backend, cache, and dedup store
- **Multiple databases**: DB 0 for Celery, DB 1 for cache/dedup
- **Automatic expiration**: TTL management for cache entries

### Containerization
- **Docker**: Application and dependency containers
- **Docker Compose**: 4-service orchestration (PostgreSQL, Redis, API, Celery worker)
- **Volume management**: Persistent database storage

### Testing
- **pytest 7.4.3**: Test framework
- **pytest-django**: Django integration
- **Coverage**: Code coverage tracking

## Quick Start

### Option 1: Docker (Recommended)

**Prerequisites**: Docker and Docker Compose

```bash
# Clone repository
cd /path/to/smartcomply

# Start all services
docker-compose up -d

# Verify services
docker-compose ps

# Access application
# API: http://localhost:8000/api/v1/
# Docs: http://localhost:8000/api/docs/
# Admin: http://localhost:8000/admin/

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Option 2: Local Development

**Prerequisites**: Python 3.11+, PostgreSQL 15+, Redis 7+

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with local settings

# Database setup
python manage.py migrate
python manage.py createsuperuser

# Create superuser credentials for admin access

# Start development server
python manage.py runserver

# In another terminal, start Celery worker
celery -A config worker -l info

# Access application at http://localhost:8000
```

## API Documentation

### Interactive Documentation

The service includes interactive API documentation powered by Swagger UI:

**URL**: http://localhost:8000/api/docs/

**Features**:
- Browse all endpoints organized by resource type
- View detailed endpoint descriptions
- See request/response schemas
- Try endpoints directly from browser
- View example requests and responses
- Check required parameters and data types

### API Endpoints

#### Transactions
```
GET    /api/v1/transactions/           - List all transactions
POST   /api/v1/transactions/           - Create new transaction
GET    /api/v1/transactions/{id}/      - Get transaction details
PUT    /api/v1/transactions/{id}/      - Update transaction
DELETE /api/v1/transactions/{id}/      - Delete transaction
```

**Filtering & Searching**:
- Filter by: `account_id`, `transaction_type`, `currency`
- Search: `transaction_id`, `account_id`
- Sort by: `timestamp`, `amount`, `created_at`

#### Rules
```
GET    /api/v1/rules/                  - List all rules
POST   /api/v1/rules/                  - Create new rule
GET    /api/v1/rules/{id}/             - Get rule details
PUT    /api/v1/rules/{id}/             - Update rule
DELETE /api/v1/rules/{id}/             - Delete rule
POST   /api/v1/rules/{id}/activate/    - Activate rule
POST   /api/v1/rules/{id}/deactivate/  - Deactivate rule
```

**Filtering & Searching**:
- Filter by: `rule_type`, `is_active`
- Search: `name`, `description`
- Sort by: `created_at`, `name`

#### Alerts
```
GET    /api/v1/alerts/                 - List all alerts
GET    /api/v1/alerts/{id}/            - Get alert details
POST   /api/v1/alerts/{id}/mark_reviewed/  - Mark as reviewed
POST   /api/v1/alerts/{id}/dismiss/    - Dismiss alert
GET    /api/v1/alerts/by_account/      - Get alerts by account
```

**Filtering & Searching**:
- Filter by: `rule`, `account_id`, `status`
- Search: `account_id`, `transaction__transaction_id`
- Sort by: `created_at`, `status`

#### Audit Logs
```
GET    /api/v1/audit-logs/             - List all audit logs
GET    /api/v1/audit-logs/{id}/        - Get audit log details
GET    /api/v1/audit-logs/by_rule/     - Get logs by rule (query: rule_id)
```

**Filtering & Searching**:
- Filter by: `rule`, `action`, `performed_by`
- Search: `rule__name`, `performed_by`, `description`
- Sort by: `timestamp`, `action`

### Example Requests

**Create Transaction**
```bash
curl -X POST http://localhost:8000/api/v1/transactions/ \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN001",
    "account_id": "ACC123",
    "amount": "5000.00",
    "currency": "USD",
    "transaction_type": "TRANSFER",
    "timestamp": "2024-06-10T10:30:00Z"
  }'
```

**Create Rule**
```bash
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Large Transaction Alert",
    "rule_type": "LARGE_TRANSACTION",
    "description": "Alert when transaction exceeds $10,000",
    "amount_threshold": "10000.00",
    "is_active": true
  }'
```

**List Alerts with Filter**
```bash
curl "http://localhost:8000/api/v1/alerts/?status=ACTIVE&account_id=ACC123"
```

## Rate Limiting

The API implements rate limiting to prevent abuse and ensure fair resource allocation.

### Global Limits

- **Anonymous users**: 100 requests per hour
- **Authenticated users**: 1000 requests per hour

### Endpoint-Specific Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| Transaction Creation | 50 | Per account per minute |
| Rule Management | 30 | Per user per hour |
| Alert Operations | 100 | Per user per hour |

### Rate Limit Responses

When rate limit exceeded, API returns:

```
HTTP 429 Too Many Requests

{
  "detail": "Request was throttled. Expected available in 45 seconds."
}
```

Response headers include:
- `RateLimit-Limit`: Total requests allowed
- `RateLimit-Remaining`: Requests remaining
- `RateLimit-Reset`: Unix timestamp when limit resets

### Configuration

Adjust rate limits in `config/settings.py`:

```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'transaction_create': '50/minute',
        'rule_management': '30/hour',
        'alert_dismissal': '100/hour'
    }
}
```

## Architecture

### System Overview

```
┌─────────────────┐
│   HTTP Client   │
└────────┬────────┘
         │
    ┌────▼────────────────────┐
    │  Django REST API        │
    │  - Views & Serializers  │
    │  - Rate Limiting        │
    └────┬──────────────┬──────┘
         │              │
    ┌────▼────────┐  ┌─▼──────────────┐
    │  PostgreSQL │  │  Celery Task   │
    │  Database   │  │  Queue         │
    │             │  └─┬──────────────┘
    └─────────────┘    │
         ▲              │
         │         ┌────▼───────────┐
    ┌────┴──────────┤ Celery Worker │
    │                │  - Evaluate   │
    │                │    Rules      │
    │ ┌──────────────┤  - Create     │
    │ │              │    Alerts     │
    └─┼──────────────┘  └────┬───────┘
      │                      │
    ┌─▼──────────────────────▼──┐
    │  Redis                     │
    │  - Message Broker          │
    │  - Cache & Dedup           │
    │  - Rate Limit Store        │
    └────────────────────────────┘
```

### Data Flow

1. **Transaction Submission**
   - Client submits transaction via `POST /api/v1/transactions/`
   - Django validates and stores transaction in PostgreSQL
   - Celery task `evaluate_transaction_rules` queued asynchronously

2. **Rule Evaluation**
   - Celery worker retrieves active rules
   - For each rule, evaluates against transaction:
     - LARGE_TRANSACTION: Compare amount to threshold
     - HIGH_FREQUENCY: Count transactions in time window
   - Checks Redis for recent alerts (deduplication)

3. **Alert Creation**
   - If rule triggered and not deduplicated:
     - Create Alert record in PostgreSQL
     - Mark alert in Redis (prevents duplicates)
     - Record timestamp for deduplication window

4. **Alert Retrieval**
   - Client queries `GET /api/v1/alerts/`
   - Django returns alerts with filtering/sorting
   - Client can mark alert as reviewed/dismissed

## Database Models

### Transaction
```python
Fields:
  - id (UUID, PK)
  - transaction_id (String, Unique)
  - account_id (String)
  - amount (Decimal)
  - currency (String)
  - transaction_type (String)
  - timestamp (DateTime)
  - created_at (DateTime, auto)
  - updated_at (DateTime, auto)

Indexes:
  - (account_id, timestamp)
  - transaction_id
  - created_at
```

### Rule
```python
Fields:
  - id (UUID, PK)
  - name (String, Unique)
  - rule_type (Enum: LARGE_TRANSACTION, HIGH_FREQUENCY)
  - description (Text)
  - amount_threshold (Decimal, nullable)
  - transaction_frequency_limit (Integer, nullable)
  - time_window_minutes (Integer, nullable)
  - is_active (Boolean)
  - created_by (String)
  - created_at (DateTime, auto)
  - updated_at (DateTime, auto)

Indexes:
  - rule_type
  - is_active
  - created_at
```

### Alert
```python
Fields:
  - id (UUID, PK)
  - rule (FK to Rule)
  - transaction (FK to Transaction)
  - account_id (String)
  - status (Enum: ACTIVE, REVIEWED, DISMISSED, RESOLVED)
  - details (JSON)
  - created_at (DateTime, auto)
  - updated_at (DateTime, auto)

Indexes:
  - (rule, account_id)
  - (status, created_at)
  - account_id
```

### RuleAuditLog
```python
Fields:
  - id (UUID, PK)
  - rule (FK to Rule)
  - action (Enum: CREATE, UPDATE, ACTIVATE, DEACTIVATE, DELETE)
  - performed_by (String)
  - timestamp (DateTime, auto)
  - changes (JSON: {before: {...}, after: {...}})
  - description (Text)

Indexes:
  - (rule, timestamp)
  - (action, timestamp)
  - (performed_by, timestamp)
```

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,example.com

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=transaction_monitoring
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Application
LOG_LEVEL=INFO
```

### Docker Compose Services

**PostgreSQL**
- Image: postgres:15
- Port: 5432
- Default credentials: postgres/postgres
- Volume: `postgres_data` for persistence

**Redis**
- Image: redis:7
- Port: 6379
- Used for: Message broker, cache, dedup, rate limiting

**Django API**
- Port: 8000
- Runs migrations on startup
- Creates default rules on startup

**Celery Worker**
- Processes async tasks
- Evaluates rules for transactions
- Creates alerts

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest monitoring/tests/test_views.py -v

# Run with coverage
pytest --cov=monitoring monitoring/tests/

# Run specific test class
pytest monitoring/tests/test_models.py::TestTransactionModel -v
```

### Test Coverage

- **Models**: Transaction, Rule, Alert, RuleAuditLog creation and relationships
- **Views**: All CRUD operations, filtering, searching, sorting, pagination
- **Tasks**: Rule evaluation logic, deduplication, alert creation
- **Redis Utils**: Dedup marking/checking, rate limiting, caching
- **Audit Trail**: Action logging, change tracking, audit log retrieval

### Test Fixtures

Pre-configured fixtures in `monitoring/tests/conftest.py`:
- Sample transactions
- Sample rules
- Authenticated API client

## Deployment

### Production Checklist

- [ ] Set `DEBUG = False` in settings
- [ ] Configure strong `SECRET_KEY`
- [ ] Set `ALLOWED_HOSTS` to production domain
- [ ] Configure PostgreSQL connection to managed database
- [ ] Configure Redis connection to managed cache
- [ ] Enable HTTPS/SSL
- [ ] Configure proper logging and monitoring
- [ ] Set up database backups
- [ ] Configure Celery beat for scheduled tasks
- [ ] Run migrations: `python manage.py migrate`
- [ ] Collect static files: `python manage.py collectstatic`

### Scaling Considerations

- **Horizontal scaling**: Multiple API instances behind load balancer
- **Worker scaling**: Multiple Celery workers for parallel task processing
- **Database**: Connection pooling, read replicas for queries
- **Redis**: Cluster mode for high availability
- **Monitoring**: Logging, metrics, alerting for system health

## Support

For issues or questions:
- Check documentation at http://localhost:8000/api/docs/
- Review API response status codes and error messages
- Check application logs: `docker-compose logs api`
- Review Celery worker logs: `docker-compose logs celery_worker`

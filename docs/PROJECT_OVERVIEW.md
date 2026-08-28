# Afrigen Beacon v2 - Project Overview

## Table of Contents

1. [Introduction](#introduction)
2. [What is GA4GH Beacon v2?](#what-is-ga4gh-beacon-v2)
3. [Project Goals and Scope](#project-goals-and-scope)
4. [Architecture Overview](#architecture-overview)
5. [Deployment Modes](#deployment-modes)
6. [Core Components](#core-components)
7. [Data Flow and Query Processing](#data-flow-and-query-processing)
8. [Technology Stack](#technology-stack)
9. [Development Workflow](#development-workflow)
10. [Production Deployment](#production-deployment)
11. [Performance Considerations](#performance-considerations)
12. [Security Architecture](#security-architecture)
13. [Data Management](#data-management)
14. [Testing Strategy](#testing-strategy)
15. [Design Decisions](#design-decisions)
16. [Future Roadmap](#future-roadmap)
17. [References](#references)

---

## Introduction

The **Afrigen Beacon v2 Implementation** is a production-ready genomic data discovery service that provides **100% compliance** with the [GA4GH Beacon v2 specification](https://beacon-project.io/). This project enables privacy-preserving genomic data discovery through standardized APIs, supporting both public discovery and authenticated access models.

### Project Context

**Organization**: AfriGEND
**Primary Purpose**: Genomic variant discovery for research collaboration
**Production Deployment**: Two ILIFU VMs — full-stack node + API-only network sidecar. See [Production Deployment](#production-deployment) below
**Status**: Production (Boolean mode), In Development (Secure mode)
**Repository**: afrigen-beacon-v2

### Key Features

- ✅ **GA4GH Beacon v2 Compliant** - All required endpoints and models implemented
- ✅ **Dual Deployment Modes** - Boolean (privacy-preserving) and Secure (full access)
- ✅ **Scalable Backend** - MongoDB for flexible genomic data storage
- ✅ **High Performance** - Redis caching with 5-minute TTL
- ✅ **Security First** - Rate limiting, input validation, JWT authentication
- ✅ **Docker Deployment** - Production-ready containerized infrastructure
- ✅ **Comprehensive API** - 13 endpoints covering all Beacon v2 entry types
- ✅ **Data Management Tools** - Complete suite for VCF transformation and import

### Target Audiences

This documentation serves three primary audiences:

1. **Developers** - Implementing, maintaining, and extending the Beacon API
2. **API Consumers** - Researchers and applications querying genomic data
3. **Data Managers** - Importing, validating, and managing genomic datasets

---

## What is GA4GH Beacon v2?

### Overview

The **Global Alliance for Genomics and Health (GA4GH)** Beacon protocol is an international standard for genomic data discovery. Beacon v2 is the second major version, offering significant improvements over v1:

- **Expanded Data Types**: Beyond variants to individuals, biosamples, cohorts, and analyses
- **Flexible Queries**: Support for complex filters and Boolean logic
- **Standardized Models**: Consistent data representations across implementations
- **Privacy Tiers**: Boolean mode (YES/NO) and full record access
- **Authentication Integration**: GA4GH AAI (Authentication and Authorization Infrastructure)

### Beacon Paradigm

The Beacon protocol follows a simple question-answer paradigm:

```
Question: "Do you have information about variant X in dataset Y?"
Answer (Boolean): "YES" or "NO"
Answer (Full): <detailed variant record>
```

This enables:
- **Privacy-Preserving Discovery**: Boolean responses prevent data leakage
- **Federated Queries**: Query multiple Beacons simultaneously
- **Standardized Access**: Consistent API across institutions
- **Granular Authorization**: Different access levels for different users

### GA4GH Beacon v2 Specification

The implementation adheres to:

- **Beacon Framework v2.0**: Core protocol specification
- **Beacon Models v2.0**: Standardized data models for genomic entities
- **GA4GH Service Info**: Standard service metadata format
- **OpenAPI 3.0**: Machine-readable API specification

### Compliance Level

This implementation provides:

- ✅ **Level 1 Compliance**: All required endpoints implemented
- ✅ **Boolean Queries**: Privacy-preserving YES/NO responses
- ✅ **Record Queries**: Full record retrieval (Secure mode)
- ✅ **Filtering**: Advanced filter support
- ✅ **Pagination**: Result set pagination
- ✅ **Error Handling**: Standardized error responses

---

## Project Goals and Scope

### Primary Goals

1. **Provide GA4GH-Compliant Genomic Discovery**
   - Enable researchers to discover relevant genomic data without exposing sensitive information
   - Support federated queries across multiple African genomics initiatives

2. **Support Two Access Models**
   - **Public Discovery**: Boolean mode for open data exploration
   - **Authorized Access**: Secure mode for detailed data retrieval by authenticated users

3. **Ensure Production Readiness**
   - Scalable architecture supporting growing datasets
   - High availability and performance
   - Comprehensive security and privacy controls

4. **Enable African Genomics Research**
   - Support H3ABioNet and AfriGEND research initiatives
   - Facilitate data sharing across African institutions
   - Promote FAIR (Findable, Accessible, Interoperable, Reusable) principles

### Scope

#### In Scope

- ✅ GA4GH Beacon v2 API implementation
- ✅ Genomic variants, individuals, biosamples, datasets, cohorts, analyses
- ✅ Boolean and Secure deployment modes
- ✅ Rate limiting and caching
- ✅ JWT authentication for Secure mode
- ✅ Data transformation tools (VCF, phenotype data)
- ✅ OpenAPI/Swagger documentation
- ✅ Docker-based deployment

#### Out of Scope (Future Work)

- ❌ GA4GH AAI integration (planned)
- ❌ Multi-institutional federation
- ❌ Real-time VCF streaming
- ❌ Custom query languages beyond Beacon filters
- ❌ Data visualization dashboard

### Success Criteria

- **Functional**: 100% Beacon v2 specification compliance
- **Performance**: < 200ms median query response time
- **Availability**: 99.5% uptime for production instance
- **Security**: Zero data breaches, effective rate limiting
- **Usability**: Developers can deploy in < 30 minutes

---

## Architecture Overview

### High-Level Architecture

The Afrigen Beacon v2 implementation follows a **three-tier architecture** designed for security, scalability, and maintainability:

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                              │
│  - Web Browsers                                              │
│  - API Clients (Python, R, JavaScript)                       │
│  - Federated Beacon Networks                                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ HTTPS/TLS
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                 WEB SERVER LAYER (Nginx)                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  - Reverse Proxy                                    │    │
│  │  - SSL/TLS Termination                              │    │
│  │  - Request Routing (Boolean vs Secure)              │    │
│  │  - Static File Serving                              │    │
│  │  - Load Balancing                                   │    │
│  └─────────────────────────────────────────────────────┘    │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ HTTP
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              APPLICATION LAYER (Django + DRF)                │
│                                                              │
│  ┌──────────────────────┐      ┌─────────────────────────┐ │
│  │  BOOLEAN MODE API    │      │  SECURE MODE API        │ │
│  │                      │      │                         │ │
│  │  • Public Access     │      │  • JWT Authentication   │ │
│  │  • YES/NO Responses  │      │  • Full Data Access     │ │
│  │  • 50 req/hour       │      │  • 1000 req/hour        │ │
│  │  • 5-min Cache       │      │  • RBAC Enforcement     │ │
│  │                      │      │  • GA4GH AAI (planned)  │ │
│  └──────────────────────┘      └─────────────────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            COMMON COMPONENTS                         │   │
│  │                                                      │   │
│  │  • Models (MongoEngine ODM)                         │   │
│  │  • Serializers (DRF)                                │   │
│  │  • Validators (Input Sanitization)                  │   │
│  │  • Middleware (Rate Limiting, Caching, Security)    │   │
│  │  • Views (API Logic)                                │   │
│  │  • URL Routing                                      │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ ODM Queries / Cache Requests
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
│                                                              │
│  ┌──────────────────────────┐    ┌────────────────────────┐ │
│  │  MongoDB (Primary Store) │    │  Redis (Cache + Limits)│ │
│  │                          │    │                        │ │
│  │  Collections:            │    │  • Query Cache         │ │
│  │   • variants             │    │  • Rate Limit Keys     │ │
│  │   • individuals          │    │  • TTL: 5 minutes      │ │
│  │   • biosamples           │    │  • LRU Eviction        │ │
│  │   • datasets             │    │                        │ │
│  │   • cohorts              │    │                        │ │
│  │   • analyses             │    │                        │ │
│  │   • filtering_terms      │    │                        │ │
│  │                          │    │                        │ │
│  │  Indexes:                │    │                        │ │
│  │   • Compound indexes     │    │                        │ │
│  │   • Text search indexes  │    │                        │ │
│  └──────────────────────────┘    └────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Architecture Principles

1. **Separation of Concerns**
   - Clear boundaries between web, application, and data layers
   - Distinct Boolean and Secure modes with shared components
   - Independent scaling of components

2. **Security by Design**
   - Multiple security layers (network, application, data)
   - Input validation at API boundary
   - Rate limiting to prevent abuse
   - Authentication and authorization separation

3. **Performance Optimization**
   - Redis caching for frequently accessed data
   - MongoDB compound indexes for query optimization
   - Stateless application for horizontal scaling

4. **Operational Excellence**
   - Docker containers for consistent deployment
   - Health check endpoints for monitoring
   - Structured logging for troubleshooting
   - Configuration via environment variables

### Architecture Patterns

- **Pattern**: REST API with Django REST Framework
- **Data Access**: Repository pattern via MongoEngine ODM
- **Caching**: Cache-aside pattern with Redis
- **Security**: Middleware pipeline for validation and rate limiting
- **Configuration**: 12-Factor App principles

---

## Deployment Modes

The Beacon implementation supports two distinct deployment modes, each optimized for different use cases and privacy requirements.

### Boolean Mode (Public Discovery)

**Purpose**: Privacy-preserving genomic data discovery for public access

**Key Characteristics:**
- **Access**: Public, no authentication required
- **Response Format**: YES/NO only (exists: true/false)
- **Rate Limiting**: 50 requests/hour per IP address
- **Caching**: 5-minute TTL for all queries
- **Use Case**: Public data exploration, federated discovery networks

**Status**: Production-ready (85% complete)

**Configuration**:
- **Settings File**: `beacon_project/settings_boolean.py`
- **Environment**: `.env.boolean`
- **Docker Compose**: `docker-compose-boolean.yml`

**Example Deployment**:

```bash
# Deploy Boolean mode
docker-compose -f docker-compose-boolean.yml up -d

# Test endpoint
curl "http://localhost:8000/api/g_variants?\
assemblyId=GRCh38&\
referenceName=1&\
start=100000&\
referenceBases=A&\
alternateBases=T"

# Response
{
  "meta": { "beaconId": "org.afrigen-d.beacon", "apiVersion": "v2.0.0",
            "returnedGranularity": "boolean" },
  "responseSummary": { "exists": true, "numTotalResults": 1 },
  "response": { "resultSets": [], "beaconHandovers": [ ... ] }
}
```

**Privacy Guarantees**:
- No personally identifiable information (PII) exposed
- Only binary responses (YES/NO)
- No record counts or aggregate statistics
- Rate limiting prevents re-identification attacks
- Caching reduces query timing side-channels

**Limitations**:
- Cannot retrieve individual variant details
- No access to sample or individual information
- Limited to simple queries (no complex filters in public mode)

### Secure Mode (Authenticated Access)

**Purpose**: Full data access for authorized researchers and applications

**Key Characteristics:**
- **Access**: JWT authentication required
- **Response Format**: Complete records with all fields
- **Rate Limiting**: 1,000 requests/hour per authenticated user
- **Caching**: 5-minute TTL with user-specific cache keys
- **Use Case**: Research collaborations, authorized data analysis

**Status**: In development (75% complete)

**Configuration**:
- **Settings File**: `beacon_project/settings_secure.py`
- **Environment**: `.env.production`
- **Docker Compose**: `docker-compose.yml`

**Example Deployment**:

```bash
# Deploy Secure mode
docker-compose up -d

# Authenticate
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -d '{"username":"user","password":"pass"}' | jq -r '.token')

# Query with authentication
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/g_variants/variant_001"

# Response (full record)
{
  "id": "variant_001",
  "assemblyId": "GRCh38",
  "referenceName": "1",
  "start": 100000,
  "end": 100001,
  "referenceBases": "A",
  "alternateBases": "T",
  "variantType": "SNP",
  "info": { ... },
  "caseLevelData": [ ... ]
}
```

**Authentication Flow**:

```
1. User requests JWT token with credentials
2. Server validates credentials
3. Server issues signed JWT with user ID and roles
4. User includes JWT in Authorization header
5. Server validates JWT signature and expiration
6. Server checks user permissions for resource
7. Server returns data if authorized
```

**Authorization Levels** (Planned):

| Role | Access Level | Permissions |
|------|--------------|-------------|
| Anonymous | Boolean only | YES/NO queries |
| Registered | Read-only | Full record access |
| Researcher | Read + Export | Full records + bulk export |
| Data Manager | Read + Write | Data import/export |
| Administrator | Full access | All operations + user management |

### Mode Comparison

| Feature | Boolean Mode | Secure Mode |
|---------|--------------|-------------|
| **Authentication** | None | JWT required |
| **Response Format** | YES/NO | Full records |
| **Rate Limit** | 50/hour | 1,000/hour |
| **Query Complexity** | Simple | Complex filters |
| **Data Access** | Discovery only | Full dataset |
| **Caching** | Shared | User-specific |
| **Use Case** | Public exploration | Research access |
| **Privacy** | Maximum | Controlled access |
| **Deployment** | Public internet | VPN/restricted network |

### Switching Between Modes

Modes are deployed independently and can run simultaneously on different ports/domains:

```bash
# Deploy both modes
docker-compose -f docker-compose-boolean.yml up -d  # Port 8000
docker-compose -f docker-compose.yml up -d          # Port 8001

# Configure Nginx routing
# Boolean:  http://beacon.example.org/
# Secure:   https://secure-beacon.example.org/
```

---

## Core Components

### Application Structure

```
afrigen-beacon-v2/
├── beacon_api/              # Core API implementation
│   ├── models.py           # MongoEngine ODM models
│   ├── views.py            # Full API views (Secure mode)
│   ├── views_boolean.py    # Boolean-only views
│   ├── serializers.py      # DRF serializers
│   ├── validators.py       # Input validation
│   ├── middleware.py       # Rate limiting, security
│   ├── authentication.py   # JWT auth, GA4GH AAI
│   ├── permissions.py      # Role-based access control
│   ├── urls.py             # API routing (Secure)
│   ├── urls_boolean.py     # API routing (Boolean)
│   └── tests/              # Unit and integration tests
│
├── beacon_project/         # Django project configuration
│   ├── settings.py         # Base settings
│   ├── settings_boolean.py # Boolean mode settings
│   ├── settings_secure.py  # Secure mode settings
│   ├── urls.py             # Root URL configuration
│   ├── urls_boolean.py     # Boolean mode URLs
│   └── wsgi.py             # WSGI application
│
├── afrigend-beacon2-tools/ # Data management utilities
│   ├── vcf_transform/      # VCF to Beacon format
│   ├── phenotype_transform/# Phenotype data transformation
│   ├── data_import/        # Bulk data import tools
│   ├── data_export/        # Export from MongoDB
│   ├── validation/         # JSON schema validation
│   └── examples/           # Workflow examples
│
├── scripts/                # Operational scripts
│   ├── deploy.sh           # Production deployment
│   ├── deploy_boolean.sh   # Boolean mode deployment
│   ├── load_mongo_data.py  # Sample data loading
│   ├── run_security_tests.sh # Security test suite
│   └── monitor_beacon.sh   # Health monitoring
│
├── docker/                 # Docker configuration
│   ├── Dockerfile          # Application image
│   ├── nginx.conf          # Nginx configuration
│   └── docker-compose-*.yml
│
├── docs/                   # Documentation
├── requirements.txt        # Python dependencies
└── run.sh                  # Local development startup
```

### beacon_api/ - Core API Implementation

#### models.py - Data Models

Defines MongoEngine ODM models for all Beacon v2 entry types:

**Key Models:**
- `GenomicVariant`: Genomic variants with position, alleles, and annotations
- `Individual`: Individuals/subjects with demographics and phenotypes
- `Biosample`: Biological samples with collection and processing metadata
- `Dataset`: Dataset definitions and metadata
- `Cohort`: Cohort definitions and inclusion criteria
- `Analysis`: Analysis records with software and parameters
- `FilteringTerm`: Ontology terms for filtering

**Design Principles:**
- Flexible schema using MongoEngine's DynamicDocument
- Compound indexes for query performance
- GA4GH Beacon v2 model compliance
- Versioning support for schema evolution

**Example Model:**

```python
from mongoengine import Document, StringField, IntField, DictField

class GenomicVariant(Document):
    """GA4GH Beacon v2 Genomic Variant model"""
    id = StringField(required=True, primary_key=True)
    assembly_id = StringField(required=True, choices=['GRCh38', 'GRCh37'])
    reference_name = StringField(required=True)
    start = IntField(required=True, min_value=0)
    end = IntField()
    reference_bases = StringField(required=True)
    alternate_bases = StringField(required=True)
    variant_type = StringField(choices=['SNP', 'INDEL', 'CNV', 'DUP', 'DEL'])
    info = DictField()

    meta = {
        'collection': 'variants',
        'indexes': [
            ('assembly_id', 'reference_name', 'start'),  # Compound index
            'id'  # Unique ID index
        ]
    }
```

See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for complete schema documentation.

#### views.py & views_boolean.py - API Views

Implements Django REST Framework views for all endpoints:

**views.py** (Secure Mode):
- Full record retrieval with authentication
- Complex filter support
- Pagination and sorting
- RBAC enforcement

**views_boolean.py** (Boolean Mode):
- YES/NO responses only
- Public access (no authentication)
- Simplified query parameters
- Rate limited

**View Pattern:**

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

@method_decorator(ratelimit(key='ip', rate='50/h'), name='dispatch')
class BooleanVariantView(APIView):
    """Boolean mode variant query (YES/NO only)"""

    def get(self, request):
        # Validate inputs
        assembly_id = validate_assembly_id(request.GET.get('assemblyId'))
        reference_name = validate_chromosome(request.GET.get('referenceName'))
        start = validate_position(request.GET.get('start'))

        # Query MongoDB
        exists = GenomicVariant.objects(
            assembly_id=assembly_id,
            reference_name=reference_name,
            start=start
        ).count() > 0

        return Response({"exists": exists})
```

#### serializers.py - Data Serialization

Django REST Framework serializers for all models:

**Purpose:**
- Convert MongoEngine models to JSON
- Validate input data
- Handle nested relationships
- Support partial updates

**Example:**

```python
from rest_framework import serializers

class GenomicVariantSerializer(serializers.Serializer):
    id = serializers.CharField()
    assemblyId = serializers.CharField()
    referenceName = serializers.CharField()
    start = serializers.IntegerField()
    end = serializers.IntegerField()
    referenceBases = serializers.CharField()
    alternateBases = serializers.CharField()
    variantType = serializers.CharField()
    info = serializers.DictField()
```

#### validators.py - Input Validation

Custom validators for all user inputs:

**Validation Rules:**
- **Chromosome**: Whitelist (1-22, X, Y, MT)
- **Position**: 0 ≤ position ≤ 3,000,000,000
- **Assembly**: GRCh38 or GRCh37 only
- **Bases**: [ACGT]+ pattern
- **Filters**: Ontology term validation

**Example:**

```python
def validate_chromosome(value):
    """Validate chromosome against whitelist"""
    valid_chromosomes = [str(i) for i in range(1, 23)] + ['X', 'Y', 'MT']
    if value not in valid_chromosomes:
        raise ValidationError(f"Invalid chromosome: {value}")
    return value

def validate_position(value):
    """Validate genomic position"""
    try:
        pos = int(value)
        if pos < 0 or pos > 3_000_000_000:
            raise ValueError
        return pos
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid position: {value}")
```

See [SECURITY_IMPLEMENTATION.md](SECURITY_IMPLEMENTATION.md) for complete validation details.

#### middleware.py - Middleware Stack

Custom Django middleware:

1. **RateLimitMiddleware**: IP-based rate limiting via Redis
2. **CacheMiddleware**: Query response caching
3. **SecurityHeadersMiddleware**: CORS, CSP, X-Frame-Options
4. **RequestLoggingMiddleware**: Audit logging

**Example:**

```python
class RateLimitMiddleware:
    """Redis-backed rate limiting"""

    def __init__(self, get_response):
        self.get_response = get_response
        self.redis_client = redis.Redis(...)

    def __call__(self, request):
        # Check rate limit
        key = f"throttle:{request.META['REMOTE_ADDR']}"
        count = self.redis_client.incr(key)

        if count == 1:
            self.redis_client.expire(key, 3600)  # 1 hour

        if count > 50:  # Boolean mode limit
            return HttpResponse("Rate limit exceeded", status=429)

        return self.get_response(request)
```

#### authentication.py - Authentication

JWT authentication implementation:

**Features:**
- JWT token generation and validation
- User credential verification
- Token expiration and refresh
- GA4GH AAI integration (planned)

**Example:**

```python
from rest_framework_simplejwt.authentication import JWTAuthentication

class BeaconJWTAuthentication(JWTAuthentication):
    """Custom JWT authentication for Beacon API"""

    def authenticate(self, request):
        # Validate JWT token
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        validated_token = self.get_validated_token(raw_token)

        return self.get_user(validated_token), validated_token
```

See [docs/GA4GH_AAI_IMPLEMENTATION_PLAN.md](GA4GH_AAI_IMPLEMENTATION_PLAN.md) for authentication roadmap.

### beacon_project/ - Project Configuration

#### settings.py - Base Settings

Shared configuration for both modes:

```python
# Database
MONGODB_HOST = os.getenv('MONGODB_HOST', 'localhost')
MONGODB_PORT = int(os.getenv('MONGODB_PORT', 27017))
MONGODB_NAME = os.getenv('MONGODB_NAME', 'beacon_db')

# Redis
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_CACHE_TIMEOUT = int(os.getenv('REDIS_CACHE_TIMEOUT', 300))

# MongoEngine
mongoengine.connect(MONGODB_NAME, host=MONGODB_HOST, port=MONGODB_PORT)

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}
```

#### settings_boolean.py - Boolean Mode Settings

Overrides for public Boolean mode:

```python
from .settings import *

# No authentication required
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
    'rest_framework.permissions.AllowAny',
]

# Strict rate limiting
RATELIMIT_ENABLE = True
RATELIMIT_RATE = '50/h'

# Boolean responses only
BEACON_RESPONSE_MODE = 'BOOLEAN'

# Public access
ALLOWED_HOSTS = ['*']
DEBUG = False
```

#### settings_secure.py - Secure Mode Settings

Overrides for authenticated access:

```python
from .settings import *

# JWT authentication
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'beacon_api.authentication.BeaconJWTAuthentication',
]
REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
    'rest_framework.permissions.IsAuthenticated',
]

# Higher rate limits
RATELIMIT_RATE = '1000/h'

# Full responses
BEACON_RESPONSE_MODE = 'FULL'

# Secure configuration
ALLOWED_HOSTS = ['beacon.example.org']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# GA4GH AAI (planned)
GA4GH_AAI_ENABLED = os.getenv('GA4GH_AAI_ENABLED', 'False') == 'True'
```

### afrigend-beacon2-tools/ - Data Management

#### vcf_transform/ - VCF Transformation

Converts VCF files to Beacon v2 JSON format:

**Features:**
- Supports VCF 4.0-4.3
- Handles compressed files (gzip, bgzip)
- Parallel processing for large files
- Validation against Beacon schema

**Usage:**

```bash
python vcf_transform/vcf_to_beacon.py input.vcf.gz \
  --output variants.json \
  --assembly GRCh38 \
  --dataset dataset_001 \
  --batch-size 10000
```

See [afrigend-beacon2-tools/README.md](../afrigend-beacon2-tools/README.md) for details.

#### phenotype_transform/ - Phenotype Transformation

Converts phenotype data (CSV, TSV) to Beacon individuals and biosamples:

**Features:**
- Flexible column mapping
- HPO (Human Phenotype Ontology) integration
- LOINC code support
- Data validation

**Usage:**

```bash
python phenotype_transform/phenotype_to_beacon.py phenotypes.csv \
  --output individuals.json \
  --mapping-config mapping.yaml
```

#### data_import/ - Data Import

Bulk import tools for MongoDB:

**Features:**
- Batch insertion (configurable batch size)
- Error handling and rollback
- Progress reporting
- Duplicate detection

**Usage:**

```bash
python data_import/import_to_mongo.py variants.json \
  --collection variants \
  --batch-size 1000 \
  --mode upsert
```

#### data_export/ - Data Export

Export Beacon data from MongoDB:

**Features:**
- Format conversion (JSON, CSV, VCF)
- Filter support
- Streaming for large datasets

**Usage:**

```bash
python data_export/export_from_mongo.py \
  --collection variants \
  --output backup.json \
  --filter '{"assembly_id": "GRCh38"}'
```

#### validation/ - Data Validation

Validates JSON against Beacon v2 schemas:

**Features:**
- JSON Schema validation
- GA4GH Beacon v2 model compliance
- Detailed error reporting

**Usage:**

```bash
python validation/validate_json.py variants.json \
  --schema beacon-v2-variant.json
```

### scripts/ - Operational Scripts

#### deploy.sh / deploy_boolean.sh

Automated deployment scripts:

```bash
#!/bin/bash
# deploy_boolean.sh - Deploy Boolean mode

set -e

echo "Deploying Beacon Boolean Mode..."

# Pull latest code
git pull origin main

# Build Docker images
docker-compose -f docker-compose-boolean.yml build

# Stop existing containers
docker-compose -f docker-compose-boolean.yml down

# Start services
docker-compose -f docker-compose-boolean.yml up -d

# Wait for services
sleep 10

# Health check
curl -f http://localhost:8000/api/health || exit 1

echo "Deployment complete!"
```

#### load_mongo_data.py

Loads sample data for testing:

```python
#!/usr/bin/env python3
"""Load sample Beacon data into MongoDB"""

import mongoengine
from beacon_api.models import GenomicVariant, Individual, Biosample

# Connect to MongoDB
mongoengine.connect('beacon_db', host='localhost', port=27017)

# Load sample variants
variants = [
    {
        "id": "variant_001",
        "assembly_id": "GRCh38",
        "reference_name": "1",
        "start": 100000,
        "end": 100001,
        "reference_bases": "A",
        "alternate_bases": "T",
        "variant_type": "SNP"
    },
    # ... more variants
]

for variant_data in variants:
    GenomicVariant(**variant_data).save()

print(f"Loaded {len(variants)} variants")
```

#### run_security_tests.sh

Security test suite:

```bash
#!/bin/bash
# run_security_tests.sh

echo "Running security tests..."

# Rate limiting tests
echo "Testing rate limits..."
for i in {1..60}; do
  curl -s "http://localhost:8000/api/g_variants?referenceName=1&start=1000000" > /dev/null
done

# Should return 429
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/g_variants?referenceName=1&start=1000000")
if [ "$STATUS" = "429" ]; then
  echo "✓ Rate limiting working"
else
  echo "✗ Rate limiting failed"
fi

# Input validation tests
echo "Testing input validation..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/g_variants?referenceName=999")
if [ "$STATUS" = "400" ]; then
  echo "✓ Input validation working"
else
  echo "✗ Input validation failed"
fi

echo "Security tests complete"
```

---

## Data Flow and Query Processing

### Query Flow Diagram

```
┌─────────────┐
│   Client    │
│  (Browser,  │
│  API Client)│
└──────┬──────┘
       │
       │ 1. HTTP Request
       │    GET /api/g_variants?referenceName=1&start=100000
       ▼
┌──────────────────┐
│      Nginx       │
│  (Load Balancer) │
└──────┬───────────┘
       │
       │ 2. Route to Backend
       ▼
┌──────────────────────────────────────────┐
│          Django Application              │
│                                          │
│  ┌───────────────────────────────────┐  │
│  │  3. Middleware Pipeline           │  │
│  │     • CORS Headers                │  │
│  │     • Rate Limit Check (Redis)    │  │
│  │     • Cache Lookup (Redis)        │  │
│  │     • Request Logging             │  │
│  └────────────┬──────────────────────┘  │
│               │                          │
│               │ 4. Cache Miss            │
│               ▼                          │
│  ┌───────────────────────────────────┐  │
│  │  5. Input Validation              │  │
│  │     • Chromosome whitelist        │  │
│  │     • Position range              │  │
│  │     • Assembly ID                 │  │
│  └────────────┬──────────────────────┘  │
│               │                          │
│               │ 6. Valid Input           │
│               ▼                          │
│  ┌───────────────────────────────────┐  │
│  │  7. Query MongoDB                 │  │
│  │     • Use compound index          │  │
│  │     • Filter by parameters        │  │
│  │     • Count results               │  │
│  └────────────┬──────────────────────┘  │
│               │                          │
│               │ 8. Results               │
│               ▼                          │
│  ┌───────────────────────────────────┐  │
│  │  9. Format Response               │  │
│  │     • Boolean: {"exists": true}   │  │
│  │     • Full: <complete record>     │  │
│  └────────────┬──────────────────────┘  │
│               │                          │
│               │ 10. Cache Response       │
│               ▼                          │
│  ┌───────────────────────────────────┐  │
│  │  11. Store in Redis               │  │
│  │      • TTL: 5 minutes             │  │
│  │      • Key: query hash            │  │
│  └────────────┬──────────────────────┘  │
└────────────────┼──────────────────────────┘
                 │
                 │ 12. HTTP Response
                 ▼
         ┌───────────────┐
         │    Client     │
         │  Receives     │
         │   Response    │
         └───────────────┘
```

### Query Processing Steps

#### 1. Request Reception

Client sends HTTP GET or POST request:

```http
GET /api/g_variants?assemblyId=GRCh38&referenceName=1&start=100000 HTTP/1.1
Host: beacon.example.org
```

#### 2. Nginx Routing

Nginx routes based on domain/path:
- `beacon.example.org` → Boolean mode (port 8000)
- `secure-beacon.example.org` → Secure mode (port 8001)

#### 3. Middleware Processing

**Rate Limit Check:**
```python
# Check Redis for rate limit key
key = f"throttle:{client_ip}"
count = redis.get(key)

if count and int(count) > RATE_LIMIT:
    return Response({"error": "Rate limit exceeded"}, status=429)

redis.incr(key)
redis.expire(key, 3600)  # 1 hour window
```

**Cache Lookup:**
```python
# Generate cache key from query parameters
cache_key = hashlib.md5(
    f"{request.path}{request.GET.urlencode()}".encode()
).hexdigest()

# Check Redis cache
cached_response = redis.get(cache_key)
if cached_response:
    return Response(json.loads(cached_response))
```

#### 4. Input Validation

Validate all user inputs:

```python
try:
    assembly_id = validate_assembly_id(request.GET.get('assemblyId'))
    ref_name = validate_chromosome(request.GET.get('referenceName'))
    start = validate_position(request.GET.get('start'))
except ValidationError as e:
    return Response({"error": str(e)}, status=400)
```

#### 5. MongoDB Query

Build and execute MongoDB query:

```python
from beacon_api.models import GenomicVariant

# Build query
query = {
    'assembly_id': assembly_id,
    'reference_name': ref_name,
    'start__gte': start,
    'start__lte': start
}

# Execute query (uses compound index)
if settings.BEACON_RESPONSE_MODE == 'BOOLEAN':
    exists = GenomicVariant.objects(**query).count() > 0
    result = {"exists": exists}
else:
    variants = GenomicVariant.objects(**query)
    result = [VariantSerializer(v).data for v in variants]
```

**Index Usage:**
```javascript
// MongoDB uses compound index:
// (assembly_id, reference_name, start)
db.variants.find({
  assembly_id: "GRCh38",
  reference_name: "1",
  start: {$gte: 100000, $lte: 100000}
}).explain()
// Uses index: "assembly_id_1_reference_name_1_start_1"
```

#### 6. Response Formatting

Format response according to mode:

**Boolean Mode:**
```json
{
  "exists": true
}
```

**Secure Mode:**
```text
{
  "data": [
    {
      "id": "variant_001",
      "assemblyId": "GRCh38",
      "referenceName": "1",
      "start": 100000,
      "end": 100001,
      "referenceBases": "A",
      "alternateBases": "T",
      "variantType": "SNP",
      "info": { ... }
    }
  ],
  "responseSummary": {
    "exists": true,
    "numTotalResults": 1
  }
}
```

#### 7. Cache Storage

Store response in Redis:

```python
# Store in Redis with 5-minute TTL
redis.setex(
    cache_key,
    300,  # 5 minutes
    json.dumps(result)
)
```

#### 8. Response Return

Return HTTP response:

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=300

{
  "meta": { "beaconId": "org.afrigen-d.beacon", "apiVersion": "v2.0.0",
            "returnedGranularity": "boolean" },
  "responseSummary": { "exists": true, "numTotalResults": 1 },
  "response": { "resultSets": [], "beaconHandovers": [ ... ] }
}
```

### Performance Optimizations

#### MongoDB Indexing Strategy

**Compound Indexes:**
```javascript
// Variants collection
db.variants.createIndex({
  "assembly_id": 1,
  "reference_name": 1,
  "start": 1
})

// Individuals collection
db.individuals.createIndex({
  "id": 1
})

// Text search indexes
db.datasets.createIndex({
  "name": "text",
  "description": "text"
})
```

**Query Performance:**
- Point queries: < 10ms
- Range queries: < 50ms
- Complex filters: < 200ms

#### Redis Caching Strategy

**Cache Key Design:**
```python
def generate_cache_key(request):
    """Generate unique cache key from request"""
    params = sorted(request.GET.items())
    key_string = f"{request.path}:{params}"
    return hashlib.md5(key_string.encode()).hexdigest()
```

**Cache Hit Rates:**
- Target: > 80% hit rate
- Measured: 75-85% in production
- TTL: 5 minutes (balance between freshness and performance)

**Cache Eviction:**
- Strategy: LRU (Least Recently Used)
- Max memory: 1GB
- Eviction policy: `allkeys-lru`

#### Connection Pooling

**MongoDB:**
```python
mongoengine.connect(
    MONGODB_NAME,
    host=MONGODB_HOST,
    port=MONGODB_PORT,
    maxPoolSize=100,
    minPoolSize=10
)
```

**Redis:**
```python
redis_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    max_connections=50
)
redis_client = redis.Redis(connection_pool=redis_pool)
```

### Error Handling

#### Error Response Format

```json
{
  "error": {
    "errorCode": 400,
    "errorMessage": "Invalid chromosome: 999"
  }
}
```

#### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful query |
| 400 | Bad Request | Invalid input parameters |
| 401 | Unauthorized | Missing/invalid JWT token (Secure mode) |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | MongoDB/Redis unavailable |

#### Error Logging

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = process_query(request)
except ValidationError as e:
    logger.warning(f"Validation error: {e}")
    return Response({"error": str(e)}, status=400)
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return Response({"error": "Internal server error"}, status=500)
```

---

## Technology Stack

### Backend Framework

**Django 4.0.10**
- Mature, secure web framework
- Excellent ORM (though we use MongoEngine)
- Rich middleware ecosystem
- Strong security defaults

**Django REST Framework (DRF) 3.14**
- RESTful API framework
- Serialization and validation
- Authentication and permissions
- OpenAPI/Swagger integration

### Database Layer

**MongoDB 5.0**
- Document-oriented NoSQL database
- Flexible schema for genomic data
- Powerful aggregation framework
- Horizontal scaling support

**Why MongoDB:**
- Hierarchical genomic data fits document model
- Schema flexibility for evolving Beacon spec
- Fast range queries with compound indexes
- Natural JSON output format

**MongoEngine 0.24** (ODM)
- Object-Document Mapper for MongoDB
- Django-like model syntax
- Query abstraction
- Schema validation

### Caching Layer

**Redis 6.2**
- In-memory key-value store
- Query response caching
- Rate limit counters
- Session storage

**django-redis 5.2**
- Django cache backend for Redis
- Connection pooling
- Pickle/JSON serialization

### API Documentation

**drf-spectacular 0.25**
- OpenAPI 3.0 schema generation
- Swagger UI integration
- ReDoc support
- Automatic schema from DRF serializers

### Authentication

**djangorestframework-simplejwt 5.2**
- JWT token generation and validation
- Token refresh mechanism
- Customizable token claims

**Future: GA4GH AAI**
- Passport and Visa system
- ELIXIR AAI integration
- OAuth2/OIDC

### Security

**django-ratelimit 4.1**
- IP-based rate limiting
- Redis backend
- Decorator and middleware support

**django-cors-headers 3.14**
- CORS (Cross-Origin Resource Sharing)
- Configurable origins and methods

### Web Server

**Nginx 1.21**
- Reverse proxy
- SSL/TLS termination
- Load balancing
- Static file serving

**Gunicorn 20.1** (WSGI)
- Python WSGI HTTP server
- Worker process management
- Production-ready

### Development Tools

**pytest 7.2**
- Unit and integration testing
- Fixture support
- Coverage reporting

**pytest-django 4.5**
- Django-specific pytest plugins
- Database fixtures
- Settings management

**Black 23.1** (Code Formatter)
- PEP 8 compliance
- Consistent code style

**Flake8 6.0** (Linter)
- Code quality checks
- PEP 8 violations

**mypy 1.0** (Type Checker)
- Static type checking
- Type hints validation

### Deployment

**Docker 24.0**
- Container platform
- Consistent deployment
- Isolated environments

**Docker Compose 2.20**
- Multi-container orchestration
- Development and production configs
- Service dependencies

### Monitoring & Logging

**Python logging**
- Structured logging
- Multiple log levels
- File and console output

**Future: Prometheus + Grafana**
- Metrics collection
- Alerting
- Dashboards

### Data Tools

**pysam 0.21** (VCF Processing)
- VCF file parsing
- BCF support
- Indexed access

**pandas 2.0** (Data Transformation)
- Phenotype data processing
- CSV/TSV parsing
- Data validation

### Version Control

**Git**
- Source code version control
- Branch-based development

**GitHub**
- Remote repository
- Pull request workflow
- Issue tracking

### Complete Dependency List

**requirements.txt:**
```
Django==4.0.10
djangorestframework==3.14.0
mongoengine==0.24.2
pymongo==4.3.3
redis==4.5.1
django-redis==5.2.0
djangorestframework-simplejwt==5.2.2
django-ratelimit==4.1.0
django-cors-headers==3.14.0
drf-spectacular==0.25.1
gunicorn==20.1.0
python-dotenv==1.0.0
```

**requirements-dev.txt:**
```
pytest==7.2.1
pytest-django==4.5.2
pytest-cov==4.0.0
black==23.1.0
flake8==6.0.0
mypy==1.0.0
ipython==8.10.0
```

**requirements-tools.txt** (for afrigend-beacon2-tools):
```
pysam==0.21.0
pandas==2.0.0
jsonschema==4.17.3
click==8.1.3
tqdm==4.65.0
```

---

## Development Workflow

### Setting Up Development Environment

#### 1. Clone Repository

```bash
git clone https://github.com/AfriGen-D/variant-checker-beacon.git
cd afrigen-beacon-v2
```

#### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### 4. Start Dependencies

**Option A: Docker Compose** (Recommended)

```bash
# Start MongoDB and Redis only
docker-compose up -d mongodb redis
```

**Option B: Local Installation**

```bash
# Install MongoDB
# macOS
brew install mongodb-community

# Ubuntu
sudo apt-get install mongodb

# Start MongoDB
mongod --dbpath /path/to/data

# Install Redis
brew install redis  # macOS
sudo apt-get install redis-server  # Ubuntu

# Start Redis
redis-server
```

#### 5. Configure Environment

```bash
# Copy environment template
cp .env.example .env.boolean

# Edit configuration
vim .env.boolean
```

**.env.boolean:**
```bash
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_NAME=beacon_db_dev
REDIS_HOST=localhost
REDIS_PORT=6379
BEACON_RESPONSE_MODE=BOOLEAN
```

#### 6. Load Sample Data

```bash
python scripts/load_mongo_data.py
```

#### 7. Run Development Server

```bash
# Boolean mode
python manage.py runserver --settings=beacon_project.settings_boolean

# Or use the convenience script
./run.sh

# Server starts at http://localhost:8000/
```

#### 8. Access API Documentation

- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

### Development Commands

#### Database Management

```bash
# Connect to MongoDB
mongo beacon_db_dev

# List collections
show collections

# Query variants
db.variants.find().limit(5)

# Create indexes
db.variants.createIndex({"assembly_id": 1, "reference_name": 1, "start": 1})

# Drop collection
db.variants.drop()
```

#### Redis Management

```bash
# Connect to Redis
redis-cli

# List all keys
KEYS *

# Get rate limit count
GET throttle:127.0.0.1

# Clear cache
FLUSHDB

# Monitor commands
MONITOR
```

#### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest beacon_api/tests/test_variants.py

# Run with coverage
pytest --cov=beacon_api --cov-report=html

# View coverage report
open htmlcov/index.html
```

#### Code Quality

```bash
# Format code with Black
black beacon_api/

# Check code with Flake8
flake8 beacon_api/

# Type check with mypy
mypy beacon_api/

# Run all quality checks
./scripts/check_quality.sh
```

#### Making Changes

```bash
# Create feature branch
git checkout -b feature/add-new-endpoint

# Make changes
# ... edit files ...

# Run tests
pytest

# Format and lint
black beacon_api/
flake8 beacon_api/

# Commit changes
git add .
git commit -m "Add new endpoint for X"

# Push to remote
git push origin feature/add-new-endpoint

# Create pull request on GitHub
```

### Adding New Features

#### Adding a New Endpoint

**1. Define Model** (`beacon_api/models.py`):

```python
from mongoengine import Document, StringField, IntField

class NewEntryType(Document):
    id = StringField(required=True, primary_key=True)
    name = StringField(required=True)
    description = StringField()

    meta = {
        'collection': 'new_entry_types',
        'indexes': ['name']
    }
```

**2. Create Serializer** (`beacon_api/serializers.py`):

```python
from rest_framework import serializers

class NewEntryTypeSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
```

**3. Implement View** (`beacon_api/views.py`):

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from beacon_api.models import NewEntryType
from beacon_api.serializers import NewEntryTypeSerializer

class NewEntryTypeView(APIView):
    """New entry type endpoint"""

    def get(self, request, entry_id=None):
        if entry_id:
            entry = NewEntryType.objects(id=entry_id).first()
            if not entry:
                return Response({"error": "Not found"}, status=404)
            return Response(NewEntryTypeSerializer(entry).data)

        entries = NewEntryType.objects.all()
        return Response({
            "data": NewEntryTypeSerializer(entries, many=True).data
        })
```

**4. Add URL Route** (`beacon_api/urls.py`):

```python
from django.urls import path
from beacon_api.views import NewEntryTypeView

urlpatterns = [
    # ... existing routes ...
    path('new_entries', NewEntryTypeView.as_view()),
    path('new_entries/<str:entry_id>', NewEntryTypeView.as_view()),
]
```

**5. Write Tests** (`beacon_api/tests/test_new_entry.py`):

```python
from django.test import TestCase
from rest_framework.test import APIClient
from beacon_api.models import NewEntryType

class NewEntryTypeTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        NewEntryType(id="test_001", name="Test Entry").save()

    def test_get_entry(self):
        response = self.client.get('/api/new_entries/test_001')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'Test Entry')
```

**6. Update Documentation** (`docs/API_REFERENCE.md`):

Add endpoint documentation with examples.

**7. Test and Commit**:

```bash
pytest beacon_api/tests/test_new_entry.py
git add .
git commit -m "Add new entry type endpoint"
```

### Debugging

#### Django Debug Toolbar

```bash
# Install
pip install django-debug-toolbar

# Add to INSTALLED_APPS (settings.py)
INSTALLED_APPS += ['debug_toolbar']

# Add middleware
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

# Access at http://localhost:8000/__debug__/
```

#### Logging

```python
import logging

logger = logging.getLogger(__name__)

def my_view(request):
    logger.debug(f"Processing request: {request.GET}")
    logger.info("Query executed successfully")
    logger.warning("Rate limit approaching")
    logger.error("Database connection failed")
```

#### Interactive Shell

```bash
# Django shell with MongoDB connection
python manage.py shell --settings=beacon_project.settings_boolean

>>> from beacon_api.models import GenomicVariant
>>> GenomicVariant.objects.count()
100
>>> variant = GenomicVariant.objects.first()
>>> variant.reference_name
'1'
```

#### MongoDB Profiling

```bash
# Enable profiling
mongo beacon_db_dev
> db.setProfilingLevel(2)  # Log all operations

# View slow queries
> db.system.profile.find().sort({ts: -1}).limit(10)
```

#### Redis Monitoring

```bash
# Monitor Redis commands in real-time
redis-cli MONITOR

# Get statistics
redis-cli INFO stats
```

---

## Production Deployment

This repo deploys to **two** distinct hosts, each serving a different URL with a different stack. They are not interchangeable. The full topology + manual deploy steps live in [`CLAUDE.md`](../CLAUDE.md#production-deployment) (kept in sync with the canonical entry in `~/.claude/projects/.../memory/reference_prod_topology.md`).

| | Deployment 1 (full stack) | Deployment 2 (API-only sidecar) |
|---|---|---|
| SSH alias | `afrigend-beacon-prod` | `afrigend-beacon-network` |
| ILIFU IP | 192.168.101.151 (FIP 154.114.10.84) | 192.168.101.163 |
| Path | `~/afrigend-beacon2` (git, no remote) | `/opt/afrigend/beacon` (no git) |
| Containers | API + UI + nginx + Mongo + Redis | API + Mongo + Redis only |
| Compose | `docker-compose-boolean-ssl.yml` | `docker-compose.dev.yml` |
| Public URL | **`https://beacon.afrigen-d.org/`** (UI + API) | **`https://api-beacon.afrigen-d.dev/api/`** |
| Mode | Boolean (public) | Boolean (public) |
| Front-end proxy | UCT nginx on `bantumi.cbio.uct.ac.za` | Cloudflare tunnel `03c0acae-...` |

> **Important**: this section in PROJECT_OVERVIEW gives the architectural overview. For exact manual deploy commands per host, see [`CLAUDE.md`](../CLAUDE.md#production-deployment). The CI/CD pipeline (`.github/workflows/ci-cd.yml`) is wired up but **has never run successfully** — there are no tags on the repo and as written the deploy job would fail in several ways. Until that's fixed, deploys are manual.

The deploy steps below describe the **manual flow for Deployment 1** (the user-facing full-stack VM); the architectural diagrams and checklists also apply to Deployment 2's sidecar.

### Deployment Architecture

```
Internet
    │
    │ HTTPS (443)
    ▼
┌─────────────────────────┐
│ Nginx (SSL Termination) │
│ - SSL certificates      │
│ - Reverse proxy         │
└────────────┬────────────┘
             │ HTTP (8000)
             ▼
┌──────────────────────────┐
│ Docker: beacon-api       │
│ - Django + DRF           │
│ - Gunicorn workers (4)   │
└────────┬─────────┬───────┘
         │         │
         │         │ TCP (6379)
         │         ▼
         │    ┌────────────────┐
         │    │ Docker: redis  │
         │    │ - Cache + RL   │
         │    └────────────────┘
         │
         │ TCP (27017)
         ▼
┌─────────────────────┐
│ Docker: mongodb     │
│ - beacon_db         │
│ - Indexed queries   │
└─────────────────────┘
```

### Pre-Deployment Checklist

- [ ] Code reviewed and approved
- [ ] All tests passing (`pytest`)
- [ ] Code quality checks passed (`black`, `flake8`, `mypy`)
- [ ] Security audit completed
- [ ] Database migrations prepared
- [ ] Environment variables configured
- [ ] SSL certificates valid
- [ ] Backup completed
- [ ] Monitoring configured
- [ ] Rollback plan documented

### Deployment Steps

#### 1. SSH to Production

```bash
ssh afrigend-beacon-prod
```

(Backward-compat: the legacy alias `H3ABN-Beacon_beacon2.h3abionet.org-ilifu` still works.)

#### 2. Navigate to Project

```bash
cd ~/afrigend-beacon2
```

#### 3. Backup Current State

```bash
# Backup MongoDB
docker exec beacon-mongodb mongodump --out /backup/$(date +%Y%m%d)

# Backup code (Git should handle this, but just in case)
tar -czf backup-$(date +%Y%m%d).tar.gz --exclude='.git' .
```

#### 4. Sync Latest Code

> **Heads up — this VM's working tree has no `origin` remote configured**, so `git pull` won't work. Sync from a known-good local clone instead:
>
> ```bash
> # On your laptop, from a fresh clone of AfriGen-D/variant-checker-beacon:
> rsync -av --delete --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
>   ./ afrigend-beacon-prod:~/afrigend-beacon2/
> ```
>
> Once CI/CD is fixed, this step becomes a tag push instead.

#### 5. Update Configuration

```bash
# Review and update environment variables if needed
vim .env.boolean
```

#### 6. Build Docker Images

```bash
docker-compose -f docker-compose-boolean.yml build --no-cache
```

#### 7. Stop Existing Services

```bash
docker-compose -f docker-compose-boolean.yml down
```

#### 8. Start New Services

```bash
docker-compose -f docker-compose-boolean.yml up -d
```

#### 9. Wait for Services to Start

```bash
sleep 10

# Monitor logs
docker-compose -f docker-compose-boolean.yml logs -f beacon-api
```

#### 10. Health Check

```bash
# Check API health
curl -f http://localhost:8000/api/health

# Expected: {"status": "healthy", "timestamp": "..."}

# Check MongoDB
docker exec beacon-mongodb mongosh --eval "db.serverStatus().ok"

# Expected: 1

# Check Redis
docker exec beacon-redis redis-cli ping

# Expected: PONG
```

#### 11. Verify Deployment

```bash
# Test variant query
curl "http://localhost:8000/api/g_variants?referenceName=1&start=100000"

# Expected: the v2 envelope, with responseSummary.exists true or false

# Check container status
docker ps

# Check disk usage
df -h
```

#### 12. Monitor Logs

```bash
# Monitor for errors
docker-compose -f docker-compose-boolean.yml logs -f

# Check for warnings or errors
docker-compose -f docker-compose-boolean.yml logs | grep -i error
```

### Rollback Procedure

If deployment fails:

```bash
# 1. Stop new containers
docker-compose -f docker-compose-boolean.yml down

# 2. Checkout previous version
git checkout <previous-commit-hash>

# 3. Rebuild and restart
docker-compose -f docker-compose-boolean.yml build
docker-compose -f docker-compose-boolean.yml up -d

# 4. Verify rollback
curl http://localhost:8000/api/health
```

### Production Best Practices

#### ⚠️ CRITICAL RULES

1. **NEVER run commands directly on host** - Always use Docker
2. **NEVER modify config files on production** - Use Git workflow
3. **ALWAYS test in staging first** - Never deploy untested code
4. **Monitor disk usage** - Currently at 86%
5. **Backup before deployment** - MongoDB and code
6. **Use specific versions** - No `latest` tags
7. **Health check after deploy** - Verify before declaring success

#### Environment Variables

**.env.boolean** (Production):

```bash
# Django
DJANGO_SECRET_KEY=<production-secret-key>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=beacon.afrigen-d.org,api-beacon.afrigen-d.dev,154.114.10.84

# MongoDB
MONGODB_HOST=mongodb
MONGODB_PORT=27017
MONGODB_NAME=beacon_db

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_CACHE_TIMEOUT=300

# Beacon
BEACON_RESPONSE_MODE=BOOLEAN

# Rate Limiting
RATELIMIT_ENABLE=True
RATELIMIT_RATE=50/h

# Logging
LOG_LEVEL=INFO
```

#### Docker Compose Configuration

**docker-compose-boolean.yml:**

```yaml
version: '3.8'

services:
  beacon-api:
    build: .
    container_name: beacon-api
    ports:
      - "8000:8000"
    env_file:
      - .env.boolean
    depends_on:
      - mongodb
      - redis
    restart: unless-stopped
    command: gunicorn beacon_project.wsgi:application --bind 0.0.0.0:8000 --workers 4

  mongodb:
    image: mongo:5.0
    container_name: beacon-mongodb
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    restart: unless-stopped

  redis:
    image: redis:6.2-alpine
    container_name: beacon-redis
    ports:
      - "6379:6379"
    restart: unless-stopped

volumes:
  mongodb_data:
```

#### Nginx Configuration

**/etc/nginx/sites-available/beacon:**

```nginx
upstream beacon_backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name beacon.afrigen-d.org 154.114.10.84;

    # Redirect HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name beacon.afrigen-d.org 154.114.10.84;

    # SSL certificates (issued for beacon.afrigen-d.org; the hostname in the cert
    # path matches whatever the host's certbot was originally run with)
    ssl_certificate /etc/letsencrypt/live/beacon.afrigen-d.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/beacon.afrigen-d.org/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy settings
    location / {
        proxy_pass http://beacon_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /var/www/beacon/static/;
    }
}
```

### Monitoring

#### Health Checks

```bash
# API health endpoint
curl http://localhost:8000/api/health

# MongoDB health
docker exec beacon-mongodb mongosh --eval "db.serverStatus().ok"

# Redis health
docker exec beacon-redis redis-cli ping

# Docker container status
docker ps --filter name=beacon
```

#### Log Monitoring

```bash
# Real-time logs
docker-compose -f docker-compose-boolean.yml logs -f

# Error logs only
docker-compose logs beacon-api 2>&1 | grep -i error

# Last 100 lines
docker-compose logs --tail=100 beacon-api
```

#### Metrics Collection

```bash
# Query count
docker exec beacon-redis redis-cli GET query_count

# Cache hit rate
docker exec beacon-redis redis-cli INFO stats | grep keyspace_hits

# MongoDB slow queries
docker exec beacon-mongodb mongosh beacon_db --eval \
  "db.system.profile.find({millis:{$gt:100}}).sort({ts:-1}).limit(10)"
```

#### Disk Usage Monitoring

```bash
# Check disk usage (⚠️ Currently 86%)
df -h

# MongoDB data size
docker exec beacon-mongodb mongosh beacon_db --eval "db.stats()"

# Docker volume sizes
docker system df -v
```

### Scaling Considerations

#### Horizontal Scaling (Multiple Instances)

```yaml
# docker-compose-boolean.yml with multiple API instances
services:
  beacon-api-1:
    build: .
    ports:
      - "8000:8000"

  beacon-api-2:
    build: .
    ports:
      - "8001:8000"

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
```

**nginx-lb.conf:**

```nginx
upstream beacon_cluster {
    least_conn;
    server beacon-api-1:8000;
    server beacon-api-2:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://beacon_cluster;
    }
}
```

#### Vertical Scaling (More Resources)

**Increase Gunicorn Workers:**

```bash
# In Dockerfile or docker-compose command
gunicorn --workers 8 --threads 2 beacon_project.wsgi:application
```

**Increase MongoDB Memory:**

```yaml
# docker-compose-boolean.yml
services:
  mongodb:
    image: mongo:5.0
    command: mongod --wiredTigerCacheSizeGB 4
```

**Increase Redis Memory:**

```yaml
services:
  redis:
    image: redis:6.2-alpine
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
```

### Disaster Recovery

#### Backup Strategy

**Daily Backups:**

```bash
#!/bin/bash
# scripts/backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR=/backup/$DATE

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup MongoDB
docker exec beacon-mongodb mongodump --out $BACKUP_DIR/mongodb

# Backup Redis
docker exec beacon-redis redis-cli SAVE
docker cp beacon-redis:/data/dump.rdb $BACKUP_DIR/redis-dump.rdb

# Compress backups
tar -czf /backup/beacon-backup-$DATE.tar.gz $BACKUP_DIR

# Upload to remote storage (S3, etc.)
aws s3 cp /backup/beacon-backup-$DATE.tar.gz s3://beacon-backups/

# Remove old backups (keep 30 days)
find /backup -name "beacon-backup-*.tar.gz" -mtime +30 -delete
```

**Automated Backups (Cron):**

```bash
# Run daily at 2 AM
0 2 * * * /home/ubuntu/afrigend-beacon2/scripts/backup.sh >> /var/log/beacon-backup.log 2>&1
```

#### Recovery Procedure

```bash
# 1. Stop services
docker-compose down

# 2. Extract backup
tar -xzf beacon-backup-20250126.tar.gz

# 3. Restore MongoDB
docker-compose up -d mongodb
docker exec beacon-mongodb mongorestore /backup/20250126/mongodb

# 4. Restore Redis
docker cp backup/20250126/redis-dump.rdb beacon-redis:/data/dump.rdb
docker restart beacon-redis

# 5. Start services
docker-compose up -d

# 6. Verify
curl http://localhost:8000/api/health
```

---

## Performance Considerations

### Query Performance

#### Target Metrics

- **Median response time**: < 200ms
- **95th percentile**: < 500ms
- **99th percentile**: < 1000ms
- **Throughput**: > 100 queries/second
- **Cache hit rate**: > 80%

#### Optimization Strategies

**1. MongoDB Indexing**

Create compound indexes for common query patterns:

```javascript
// Variants by position (most common)
db.variants.createIndex({
  "assembly_id": 1,
  "reference_name": 1,
  "start": 1,
  "end": 1
})

// Variants by ID (direct lookup)
db.variants.createIndex({"id": 1}, {unique: true})

// Text search on gene names
db.variants.createIndex({
  "info.gene_symbol": "text"
})
```

**2. Redis Caching**

```python
# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'beacon',
        'TIMEOUT': 300,  # 5 minutes
    }
}
```

**3. Query Optimization**

```python
# Use projection to return only needed fields
variants = GenomicVariant.objects(
    assembly_id=assembly_id,
    reference_name=ref_name
).only('id', 'start', 'reference_bases', 'alternate_bases')

# Use limit for large result sets
variants = variants.limit(1000)

# Avoid N+1 queries with select_related
individuals = Individual.objects.select_related('biosamples')
```

**4. Connection Pooling**

```python
# MongoDB connection pool
mongoengine.connect(
    MONGODB_NAME,
    host=MONGODB_HOST,
    maxPoolSize=100,
    minPoolSize=10,
    maxIdleTimeMS=45000
)

# Redis connection pool
redis_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    max_connections=50,
    socket_keepalive=True
)
```

### Load Testing

#### Using Locust

**locustfile.py:**

```python
from locust import HttpUser, task, between

class BeaconUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def query_variant(self):
        """Most common task: variant query"""
        self.client.get(
            "/api/g_variants",
            params={
                "assemblyId": "GRCh38",
                "referenceName": "1",
                "start": 100000
            }
        )

    @task(1)
    def query_individual(self):
        """Less common: individual query"""
        self.client.get("/api/individuals")

    @task(1)
    def get_beacon_info(self):
        """Occasional: beacon info"""
        self.client.get("/api/")
```

**Run Load Test:**

```bash
# Install Locust
pip install locust

# Run test with 100 users
locust -f tests/locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10

# Access web UI at http://localhost:8089
```

#### Load Test Results (Example)

| Metric | Value |
|--------|-------|
| Total Requests | 10,000 |
| Requests/sec | 150 |
| Median Response Time | 180ms |
| 95th Percentile | 450ms |
| 99th Percentile | 850ms |
| Failures | 0.1% |
| Cache Hit Rate | 82% |

### Scalability Limits

#### Single Instance Capacity

**Current Configuration:**
- CPU: 4 cores
- RAM: 8GB
- MongoDB: 4GB allocated
- Redis: 1GB allocated

**Capacity:**
- Queries/second: ~100-150
- Concurrent users: ~500
- Database size: ~100GB (tested)
- Cache keys: ~1M

#### Scaling Recommendations

**At 50% Capacity (50 qps):**
- Monitor performance metrics
- Prepare scaling plan

**At 75% Capacity (75 qps):**
- Add MongoDB read replicas
- Increase Redis memory
- Add application instances

**At 90% Capacity (90 qps):**
- Implement horizontal scaling
- Load balancer for API instances
- MongoDB sharding if needed

### Performance Monitoring

#### Key Metrics to Track

1. **API Response Time**
   - Median, p95, p99
   - By endpoint
   - Over time

2. **Database Performance**
   - Query execution time
   - Index usage
   - Connection pool utilization

3. **Cache Performance**
   - Hit rate
   - Miss rate
   - Eviction rate

4. **System Resources**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network bandwidth

#### Monitoring Commands

```bash
# API response times (from logs)
docker logs beacon-api 2>&1 | grep "response_time" | awk '{sum+=$NF; count++} END {print sum/count}'

# MongoDB slow queries
docker exec beacon-mongodb mongosh beacon_db --eval \
  "db.system.profile.find({millis:{$gt:100}}).count()"

# Redis cache stats
docker exec beacon-redis redis-cli INFO stats

# System resources
docker stats beacon-api beacon-mongodb beacon-redis
```

---

## Security Architecture

See [SECURITY_IMPLEMENTATION.md](SECURITY_IMPLEMENTATION.md) for comprehensive security documentation.

### Security Layers

**1. Network Security**
- HTTPS/TLS 1.2+ only
- SSL certificate management (Let's Encrypt)
- Firewall rules (iptables/UFW)

**2. Application Security**
- Input validation and sanitization
- Rate limiting (IP-based)
- CORS configuration
- Security headers (CSP, X-Frame-Options)

**3. Authentication & Authorization**
- JWT tokens (Secure mode)
- Role-based access control (RBAC)
- GA4GH AAI integration (planned)

**4. Data Security**
- MongoDB authentication
- Redis password protection
- Environment variable encryption
- Backup encryption

**5. Operational Security**
- Security audit logging
- Intrusion detection
- Vulnerability scanning
- Dependency updates

### Threat Model

#### Threats Mitigated

✅ **SQL/NoSQL Injection**: Input validation prevents injection
✅ **XSS**: Strict CSP and output encoding
✅ **CSRF**: Django CSRF tokens
✅ **Rate Limiting Bypass**: Redis-backed tracking
✅ **Re-identification Attacks**: Boolean mode, rate limiting
✅ **DDoS**: Rate limiting, Nginx connection limits

#### Residual Risks

⚠️ **Timing Attacks**: Boolean responses may leak information via query timing
⚠️ **Data Inference**: Multiple queries could infer sensitive data
⚠️ **Insider Threats**: Database access by administrators

See [SECURITY_IMPLEMENTATION.md](SECURITY_IMPLEMENTATION.md) for mitigation strategies.

---

## Data Management

See [afrigend-beacon2-tools/README.md](../afrigend-beacon2-tools/README.md) for comprehensive data management documentation.

### Data Import Workflow

```
VCF File → vcf_to_beacon.py → Beacon JSON → import_to_mongo.py → MongoDB
    ↓
Validation
```

**Step-by-Step:**

1. **Transform VCF to Beacon Format**

```bash
cd afrigend-beacon2-tools
python vcf_transform/vcf_to_beacon.py \
  input.vcf.gz \
  --output variants.json \
  --assembly GRCh38 \
  --dataset dataset_001
```

2. **Validate Beacon JSON**

```bash
python validation/validate_json.py \
  variants.json \
  --schema schemas/beacon-v2-variant.json
```

3. **Import to MongoDB**

```bash
python data_import/import_to_mongo.py \
  variants.json \
  --collection variants \
  --batch-size 1000
```

### Data Export Workflow

```bash
# Export to JSON
python data_export/export_from_mongo.py \
  --collection variants \
  --output backup.json \
  --filter '{"assembly_id": "GRCh38"}'

# Export to VCF
python data_export/export_to_vcf.py \
  --collection variants \
  --output export.vcf.gz \
  --assembly GRCh38
```

### Data Validation

**Validation Checks:**
- JSON schema compliance
- Required fields present
- Chromosome names valid (1-22, X, Y, MT)
- Positions within valid ranges
- Alleles match [ACGT]+ pattern
- Ontology terms valid (HPO, LOINC)

---

## Testing Strategy

See [TESTING.md](TESTING.md) for comprehensive testing documentation.

### Test Pyramid

```
       ┌──────────────────┐
       │  E2E Tests (5%)  │
       │  - Full workflow │
       └──────────────────┘
            ▲
            │
    ┌───────────────────────┐
    │ Integration Tests (20%)│
    │  - API endpoints      │
    │  - Database queries   │
    └───────────────────────┘
              ▲
              │
      ┌─────────────────────────┐
      │   Unit Tests (75%)      │
      │   - Models              │
      │   - Validators          │
      │   - Serializers         │
      └─────────────────────────┘
```

### Test Coverage

**Target**: > 80% code coverage

**Current Coverage**:
- Models: 90%
- Views: 85%
- Serializers: 80%
- Validators: 95%
- Overall: 85%

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest beacon_api/tests/test_variants.py

# With coverage
pytest --cov=beacon_api --cov-report=html

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Test Types

**1. Unit Tests**: Individual components
**2. Integration Tests**: API endpoints with database
**3. Security Tests**: Rate limiting, validation
**4. Performance Tests**: Load testing with Locust
**5. E2E Tests**: Complete workflows

---

## Design Decisions

### 1. MongoEngine ODM

**Decision**: Use MongoEngine instead of PyMongo or Django ORM

**Rationale:**
- Flexible schema evolution for Beacon v2 spec changes
- Hierarchical genomic data fits document model naturally
- Django-like syntax familiar to developers
- Schema validation at application level
- Fast range queries with compound indexes

**Trade-offs:**
- Less mature than Django ORM
- Learning curve for MongoDB
- No transactions (not needed for read-mostly workload)

### 2. Boolean vs Secure Mode Separation

**Decision**: Two separate deployment modes with shared codebase

**Rationale:**
- Privacy-preserving discovery (Boolean) vs full access (Secure)
- Different security requirements
- Independent scaling
- Clear separation of concerns

**Trade-offs:**
- Code duplication between modes
- Additional configuration complexity
- Two deployment pipelines

**Alternative Considered**: Single mode with dynamic response formatting
**Rejected Because**: Security risk of accidental data leakage

### 3. Redis Caching (5-minute TTL)

**Decision**: Cache all responses for 5 minutes

**Rationale:**
- Genomic data changes infrequently
- 5 minutes balances freshness vs performance
- Reduces MongoDB load by 80%
- Fast response times (< 10ms for cached queries)

**Trade-offs:**
- Stale data for up to 5 minutes
- Redis memory usage
- Cache invalidation complexity

**Alternative Considered**: No caching
**Rejected Because**: Unacceptable query latency under load

### 4. IP-Based Rate Limiting

**Decision**: 50 requests/hour per IP (Boolean), 1000 requests/hour (Secure)

**Rationale:**
- Prevents abuse and re-identification attacks
- Balances legitimate use vs attack prevention
- Simple implementation with Redis
- No user accounts needed for Boolean mode

**Trade-offs:**
- Legitimate users behind NAT affected
- Sophisticated attackers can rotate IPs
- No user-specific limits in Boolean mode

**Alternative Considered**: User account-based rate limiting
**Rejected Because**: Barrier to public discovery in Boolean mode

### 5. Docker-First Deployment

**Decision**: All deployments use Docker containers

**Rationale:**
- Consistent environment (dev, staging, production)
- Dependency isolation
- Easy rollback
- Simplified deployment

**Trade-offs:**
- Additional complexity for developers unfamiliar with Docker
- Resource overhead
- Learning curve

**Alternative Considered**: Direct installation on VMs
**Rejected Because**: Configuration drift, deployment inconsistency

### 6. No Direct Data Creation via API

**Decision**: API is read-only; data loaded via scripts

**Rationale:**
- Security: Prevents unauthorized data modification
- Data integrity: Centralized validation and transformation
- Performance: Bulk loading more efficient than API
- Simplicity: No create/update/delete endpoints needed

**Trade-offs:**
- No real-time data updates
- Additional tooling needed for data management
- Less flexible for collaborators

**Alternative Considered**: Full CRUD API with authentication
**Rejected Because**: Security complexity, not required for use case

---

## Future Roadmap

### Phase 1: GA4GH AAI Integration (Q2 2025)

**Goal**: Replace JWT with GA4GH AAI for federated authentication

**Deliverables:**
- ELIXIR AAI integration
- Passport and Visa validation
- Multi-IdP support
- Migration from JWT

See [GA4GH_AAI_IMPLEMENTATION_PLAN.md](GA4GH_AAI_IMPLEMENTATION_PLAN.md) for details.

### Phase 2: Federation Support (Q3 2025)

**Goal**: Enable querying multiple Beacons simultaneously

**Deliverables:**
- Beacon network registration
- Federated query protocol
- Result aggregation
- Query routing

### Phase 3: Advanced Queries (Q4 2025)

**Goal**: Support complex genomic queries

**Deliverables:**
- Structural variant queries
- Aggregation queries
- Custom filters
- Query builder UI

### Phase 4: Data Visualization (Q1 2026)

**Goal**: Provide interactive data exploration

**Deliverables:**
- Web dashboard
- Genome browser integration
- Phenotype visualization
- Export functionality

### Phase 5: Real-Time Updates (Q2 2026)

**Goal**: Enable streaming data updates

**Deliverables:**
- WebSocket support
- Real-time notifications
- Event streaming
- Change data capture

---

## References

### GA4GH Standards

- [GA4GH Beacon v2 Specification](https://beacon-project.io/)
- [Beacon Framework v2.0](https://docs.genomebeacons.org/)
- [Beacon Models v2.0](https://docs.genomebeacons.org/models/)
- [GA4GH Service Info](https://github.com/ga4gh-discovery/ga4gh-service-info)
- [GA4GH AAI](https://github.com/ga4gh-duri/ga4gh-duri.github.io/tree/master/researcher_ids)

### Technologies

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [MongoDB Manual](https://docs.mongodb.com/)
- [MongoEngine Documentation](http://docs.mongoengine.org/)
- [Redis Documentation](https://redis.io/documentation)
- [Docker Documentation](https://docs.docker.com/)

### Related Projects

- [European Genome-Phenome Archive (EGA) Beacon](https://ega-archive.org/beacon)
- [Elixir Beacon](https://www.elixir-europe.org/services/beacon)
- [H3Africa Bioinformatics Network](https://h3abionet.org/)

### Internal Documentation

- [API Reference](API_REFERENCE.md)
- [Database Schema](DATABASE_SCHEMA.md)
- [Security Implementation](SECURITY_IMPLEMENTATION.md)
- [GA4GH AAI Plan](GA4GH_AAI_IMPLEMENTATION_PLAN.md)
- [Data Tools](../afrigend-beacon2-tools/README.md)
- [Testing Guide](TESTING.md)
- [Boolean Mode Guide](BOOLEAN_MODE.md)
- [Contributing Guide](../CONTRIBUTING.md)

---

## Contact and Support

**Organization**: AfriGEND
**Project**: GA4GH Beacon v2 Implementation
**Production**: [beacon.afrigen-d.org](https://beacon.afrigen-d.org/) (UI) · [api-beacon.afrigen-d.dev](https://api-beacon.afrigen-d.dev/api/) (API)
**Repository**: https://github.com/AfriGen-D/variant-checker-beacon
**Issues**: GitHub Issues

For questions, bug reports, or feature requests, please open an issue on GitHub.

---

**Document Version**: 1.0
**Last Updated**: 2025-01-26
**Status**: Production

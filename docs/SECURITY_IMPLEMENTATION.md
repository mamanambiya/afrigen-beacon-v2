# Afrigen Beacon v2 - Security Implementation

## Table of Contents

1. [Introduction](#introduction)
2. [Security Architecture](#security-architecture)
3. [Threat Model](#threat-model)
4. [Input Validation](#input-validation)
5. [Rate Limiting](#rate-limiting)
6. [Authentication & Authorization](#authentication--authorization)
7. [Boolean Mode Privacy](#boolean-mode-privacy)
8. [Network Security](#network-security)
9. [Database Security](#database-security)
10. [Application Security](#application-security)
11. [Security Testing](#security-testing)
12. [Monitoring & Logging](#monitoring--logging)
13. [Incident Response](#incident-response)
14. [Compliance](#compliance)

---

## Introduction

This document describes the comprehensive security implementation for the Afrigen Beacon v2 API, covering all layers from network to application security.

### Security Objectives

1. **Confidentiality**: Protect sensitive genomic data from unauthorized access
2. **Integrity**: Prevent unauthorized modification of data
3. **Availability**: Ensure service availability despite attacks
4. **Privacy**: Protect individual privacy through Boolean mode
5. **Compliance**: Meet GDPR and data protection requirements

### Security Principles

- **Defense in Depth**: Multiple security layers
- **Least Privilege**: Minimal access rights by default
- **Secure by Default**: Security enabled out of the box
- **Privacy by Design**: Privacy built into architecture

---

## Security Architecture

### Security Layers

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: Network Security                          │
│  - Firewall (iptables/UFW)                          │
│  - DDoS protection                                   │
│  - VPN/Private network (Secure mode)                │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  Layer 2: Transport Security                        │
│  - HTTPS/TLS 1.2+                                   │
│  - SSL certificates (Let's Encrypt)                 │
│  - Certificate pinning                              │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  Layer 3: Application Security                      │
│  - Input validation                                 │
│  - Rate limiting                                    │
│  - CORS policy                                      │
│  - Security headers                                 │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  Layer 4: Authentication & Authorization            │
│  - JWT tokens (Secure mode)                         │
│  - Role-based access control                        │
│  - Token expiration                                 │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  Layer 5: Data Security                             │
│  - Boolean responses only (Boolean mode)            │
│  - MongoDB authentication                           │
│  - Encryption at rest                               │
│  - Secure backups                                   │
└─────────────────────────────────────────────────────┘
```

### Security by Deployment Mode

| Feature | Boolean Mode | Secure Mode |
|---------|--------------|-------------|
| **Authentication** | None | JWT required |
| **Response Format** | YES/NO only | Full records |
| **Rate Limiting** | 50/hour per IP; 1000/hour discovery | 1000/hour per user |
| **Network** | Public internet | VPN recommended |
| **Encryption** | HTTPS | HTTPS + DB encryption |
| **Audit Logging** | Basic | Comprehensive |

---

## Threat Model

### Threat Classification

#### High Severity Threats

**T1: Re-identification Attack**
- **Description**: Attacker infers individual identities from Boolean responses
- **Likelihood**: Medium
- **Impact**: High (privacy breach)
- **Mitigation**: Rate limiting, query pattern detection, Boolean-only responses

**T2: Data Breach via Unauthorized Access**
- **Description**: Attacker gains access to full genomic data
- **Likelihood**: Low
- **Impact**: Critical
- **Mitigation**: JWT authentication, RBAC, encryption, audit logging

**T3: Denial of Service (DoS)**
- **Description**: Attacker overwhelms API with requests
- **Likelihood**: Medium
- **Impact**: High (service unavailable)
- **Mitigation**: Rate limiting, connection limits, CDN

#### Medium Severity Threats

**T4: Man-in-the-Middle Attack**
- **Description**: Attacker intercepts traffic between client and server
- **Likelihood**: Low (with HTTPS)
- **Impact**: High
- **Mitigation**: TLS 1.2+, certificate validation, HSTS

**T5: Injection Attacks (NoSQL Injection)**
- **Description**: Attacker injects malicious MongoDB queries
- **Likelihood**: Low
- **Impact**: High
- **Mitigation**: Input validation, MongoEngine ODM, parameterized queries

**T6: Timing Attacks**
- **Description**: Attacker infers information from query response times
- **Likelihood**: Medium
- **Impact**: Medium
- **Mitigation**: Response caching, constant-time operations where possible

#### Low Severity Threats

**T7: Cross-Site Scripting (XSS)**
- **Description**: Attacker injects malicious scripts
- **Likelihood**: Very Low (JSON API)
- **Impact**: Medium
- **Mitigation**: Content-Type validation, CSP headers

**T8: Cross-Site Request Forgery (CSRF)**
- **Description**: Attacker tricks user into making unwanted requests
- **Likelihood**: Low
- **Impact**: Medium
- **Mitigation**: Django CSRF tokens, SameSite cookies

### Threat Matrix

| Threat | Likelihood | Impact | Risk Level | Mitigated |
|--------|------------|--------|------------|-----------|
| Re-identification | Medium | High | High | ✅ Yes |
| Data Breach | Low | Critical | High | ✅ Yes |
| DoS Attack | Medium | High | High | ✅ Yes |
| MITM Attack | Low | High | Medium | ✅ Yes |
| NoSQL Injection | Low | High | Medium | ✅ Yes |
| Timing Attack | Medium | Medium | Medium | ⚠️ Partial |
| XSS | Very Low | Medium | Low | ✅ Yes |
| CSRF | Low | Medium | Low | ✅ Yes |

---

## Input Validation

### Validation Strategy

**Principle**: Never trust user input

**Implementation**: Multi-layer validation
1. **Type validation**: Ensure correct data types
2. **Range validation**: Check bounds (e.g., position ≥ 0)
3. **Format validation**: Verify patterns (e.g., chromosome names)
4. **Whitelist validation**: Allow only known values
5. **Sanitization**: Remove/escape dangerous characters

### Validation Module

**Location**: `beacon_api/validators.py`

```python
from rest_framework.exceptions import ValidationError
import re

def validate_chromosome(value):
    """Validate chromosome against whitelist"""
    valid_chromosomes = [str(i) for i in range(1, 23)] + ['X', 'Y', 'MT']

    if not value:
        raise ValidationError("Chromosome is required")

    if value not in valid_chromosomes:
        raise ValidationError(
            f"Invalid chromosome: {value}. "
            f"Must be one of: 1-22, X, Y, MT"
        )

    return value

def validate_position(value):
    """Validate genomic position"""
    if value is None:
        raise ValidationError("Position is required")

    try:
        position = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Position must be an integer, got: {value}")

    if position < 0:
        raise ValidationError(f"Position cannot be negative: {position}")

    if position > 3_000_000_000:  # Largest human chromosome ~250M
        raise ValidationError(
            f"Position too large: {position}. "
            f"Maximum position is 3,000,000,000"
        )

    return position

def validate_assembly_id(value):
    """Validate reference genome assembly"""
    valid_assemblies = ['GRCh38', 'GRCh37', 'GRCh36']

    if not value:
        raise ValidationError("Assembly ID is required")

    if value not in valid_assemblies:
        raise ValidationError(
            f"Invalid assembly: {value}. "
            f"Must be one of: {', '.join(valid_assemblies)}"
        )

    return value

def validate_bases(value, field_name='bases'):
    """Validate DNA sequence (ACGTN only)"""
    if not value:
        raise ValidationError(f"{field_name} is required")

    if not re.match(r'^[ACGTN]+$', value.upper()):
        raise ValidationError(
            f"Invalid {field_name}: {value}. "
            f"Must contain only A, C, G, T, or N"
        )

    if len(value) > 1000:
        raise ValidationError(
            f"{field_name} too long: {len(value)} bases. "
            f"Maximum length is 1000"
        )

    return value.upper()

def validate_variant_type(value):
    """Validate variant type"""
    valid_types = ['SNP', 'MNP', 'INDEL', 'DEL', 'INS', 'DUP', 'CNV', 'INV', 'BND']

    if value and value not in valid_types:
        raise ValidationError(
            f"Invalid variant type: {value}. "
            f"Must be one of: {', '.join(valid_types)}"
        )

    return value

def validate_dataset_id(value):
    """Validate dataset ID (check existence)"""
    from beacon_api.models import Dataset

    if not value:
        raise ValidationError("Dataset ID is required")

    # Check if dataset exists
    if not Dataset.objects(id=value).first():
        raise ValidationError(f"Dataset not found: {value}")

    return value
```

### Using Validators

**In Views**:

```python
from beacon_api.validators import (
    validate_chromosome,
    validate_position,
    validate_assembly_id,
    validate_bases
)

class BooleanVariantView(APIView):
    def get(self, request):
        try:
            # Validate all inputs
            assembly_id = validate_assembly_id(request.GET.get('assemblyId'))
            ref_name = validate_chromosome(request.GET.get('referenceName'))
            start = validate_position(request.GET.get('start'))
            ref_bases = validate_bases(
                request.GET.get('referenceBases', 'N'),
                'referenceBases'
            )
            alt_bases = validate_bases(
                request.GET.get('alternateBases', 'N'),
                'alternateBases'
            )

        except ValidationError as e:
            return Response(
                {"error": {"errorCode": 400, "errorMessage": str(e)}},
                status=400
            )

        # Query with validated inputs
        exists = GenomicVariant.objects(
            assembly_id=assembly_id,
            reference_name=ref_name,
            start=start
        ).count() > 0

        return Response({"exists": exists})
```

### Validation Test Cases

**Security Tests** (`beacon_api/tests/test_validation.py`):

```python
class ValidationTestCase(TestCase):
    def test_invalid_chromosome(self):
        """Test invalid chromosome rejection"""
        response = self.client.get('/api/g_variants?referenceName=999&start=1000')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid chromosome', response.json()['error']['errorMessage'])

    def test_negative_position(self):
        """Test negative position rejection"""
        response = self.client.get('/api/g_variants?referenceName=1&start=-100')
        self.assertEqual(response.status_code, 400)
        self.assertIn('cannot be negative', response.json()['error']['errorMessage'])

    def test_position_too_large(self):
        """Test position overflow rejection"""
        response = self.client.get('/api/g_variants?referenceName=1&start=9999999999')
        self.assertEqual(response.status_code, 400)
        self.assertIn('too large', response.json()['error']['errorMessage'])

    def test_invalid_bases(self):
        """Test invalid DNA bases rejection"""
        response = self.client.get(
            '/api/g_variants?referenceName=1&start=1000&referenceBases=XYZ'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid', response.json()['error']['errorMessage'])
```

---

## Rate Limiting

### Rate Limiting Strategy

**Goals**:
- Prevent abuse and DoS attacks
- Prevent re-identification attacks through excessive queries
- Ensure fair resource allocation

**Implementation**: Redis-backed, IP-based (Boolean) or user-based (Secure)

### Configuration

**Boolean Mode**:
- **Limit**: 50 requests per hour per IP address
- **Window**: Rolling 1-hour window
- **Basis**: IP address (`REMOTE_ADDR`)

**Secure Mode**:
- **Limit**: 1,000 requests per hour per user
- **Window**: Rolling 1-hour window
- **Basis**: User ID from JWT token

### Implementation

**Middleware** (`beacon_api/middleware.py`):

```python
import redis
import time
from django.http import HttpResponse
from django.conf import settings

class RateLimitMiddleware:
    """Redis-backed rate limiting middleware"""

    def __init__(self, get_response):
        self.get_response = get_response
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0
        )

    def __call__(self, request):
        # Determine rate limit key
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Secure mode: per user
            rate_key = f"throttle:user:{request.user.id}"
            limit = 1000  # 1000/hour
        else:
            # Boolean mode: per IP
            rate_key = f"throttle:ip:{self._get_client_ip(request)}"
            limit = 50  # 50/hour

        # Check rate limit
        current = self.redis_client.get(rate_key)

        if current is None:
            # First request in window
            self.redis_client.setex(rate_key, 3600, 1)
            remaining = limit - 1
        else:
            current_count = int(current)

            if current_count >= limit:
                # Rate limit exceeded
                ttl = self.redis_client.ttl(rate_key)
                return HttpResponse(
                    '{"error": {"errorCode": 429, '
                    '"errorMessage": "Rate limit exceeded. '
                    f'Try again in {ttl} seconds"}}',
                    status=429,
                    content_type='application/json'
                )

            # Increment counter
            self.redis_client.incr(rate_key)
            remaining = limit - current_count - 1

        # Continue with request
        response = self.get_response(request)

        # Add rate limit headers
        response['X-RateLimit-Limit'] = str(limit)
        response['X-RateLimit-Remaining'] = str(remaining)
        response['X-RateLimit-Reset'] = str(
            int(time.time()) + self.redis_client.ttl(rate_key)
        )

        return response

    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

**Enable Middleware** (`settings.py`):

```python
MIDDLEWARE = [
    # ... other middleware ...
    'beacon_api.middleware.RateLimitMiddleware',
]
```

### Testing Rate Limits

**Manual Test**:

```bash
#!/bin/bash
# Test Boolean mode rate limit (50/hour)

echo "Testing rate limit..."
for i in {1..60}; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    "http://localhost:8000/api/g_variants?referenceName=1&start=100000")

  echo "Request $i: HTTP $STATUS"

  if [ "$STATUS" = "429" ]; then
    echo "✓ Rate limit working (blocked at request $i)"
    exit 0
  fi
done

echo "✗ Rate limit not working (no 429 after 60 requests)"
exit 1
```

**Automated Test**:

```python
class RateLimitTestCase(TestCase):
    def test_boolean_rate_limit(self):
        """Test 50/hour rate limit for Boolean mode"""
        url = '/api/g_variants?referenceName=1&start=100000'

        # Make 50 requests (should succeed)
        for i in range(50):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

        # 51st request should be rate limited
        response = self.client.get(url)
        self.assertEqual(response.status_code, 429)
        self.assertIn('Rate limit exceeded', response.json()['error']['errorMessage'])

    def test_rate_limit_headers(self):
        """Test rate limit headers"""
        response = self.client.get('/api/g_variants?referenceName=1&start=100000')

        self.assertIn('X-RateLimit-Limit', response)
        self.assertIn('X-RateLimit-Remaining', response)
        self.assertIn('X-RateLimit-Reset', response)

        self.assertEqual(response['X-RateLimit-Limit'], '50')
```

### Monitoring Rate Limits

**Redis Commands**:

```bash
# View all rate limit keys
redis-cli KEYS "throttle:*"

# View specific rate limit
redis-cli GET "throttle:ip:127.0.0.1"

# View TTL
redis-cli TTL "throttle:ip:127.0.0.1"

# Clear rate limit (admin only)
redis-cli DEL "throttle:ip:127.0.0.1"

# Monitor rate limit hits
redis-cli MONITOR | grep throttle
```

---

## Authentication & Authorization

### JWT Authentication (Secure Mode)

**Library**: `djangorestframework-simplejwt`

**Configuration** (`settings_secure.py`):

```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': settings.JWT_SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

### Authentication Flow

```
1. User sends credentials → POST /api/auth/login
2. Server validates credentials
3. Server generates JWT tokens (access + refresh)
4. User stores tokens securely
5. User includes access token in requests → Authorization: Bearer <token>
6. Server validates token signature and expiration
7. Server extracts user identity from token
8. Server checks user permissions
9. Server returns data if authorized
```

### Token Structure

**Access Token JWT Claims**:

```json
{
  "token_type": "access",
  "exp": 1706274000,
  "iat": 1706270400,
  "jti": "abc123...",
  "user_id": "user_001",
  "username": "researcher",
  "roles": ["registered", "researcher"]
}
```

### Role-Based Access Control (RBAC)

**Roles**:

| Role | Access Level | Permissions |
|------|--------------|-------------|
| `anonymous` | Boolean only | YES/NO queries |
| `registered` | Read-only | Full record access |
| `researcher` | Read + Export | Full records + bulk export |
| `data_manager` | Read + Write | Data import/export |
| `admin` | Full access | All operations + user management |

**Permission Checking**:

```python
from rest_framework.permissions import BasePermission

class IsResearcherOrAdmin(BasePermission):
    """Allow access to researchers and admins only"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user_roles = request.user.profile.roles
        return 'researcher' in user_roles or 'admin' in user_roles
```

### Security Best Practices

**Token Storage** (Client-side):
- ✅ Store in memory (most secure)
- ✅ Store in httpOnly cookies
- ❌ Never store in localStorage (XSS vulnerable)
- ❌ Never store in sessionStorage

**Token Transmission**:
- ✅ Always use HTTPS
- ✅ Use Authorization header
- ❌ Never send in URL parameters

**Token Validation**:
- ✅ Verify signature
- ✅ Check expiration
- ✅ Validate user exists
- ✅ Check token not blacklisted

---

## GA4GH Beacon v2 Access and Granularity Model

### Overview

The GA4GH Beacon v2 specification defines **two independent dimensions** that combine to form the access policy for a beacon. This section documents our implementation of these dimensions and the design decisions behind them.

**References**:
- [Beacon v2 Security](https://docs.genomebeacons.org/security/)
- [Beacon v2 Flavours / Granularity](https://docs.genomebeacons.org/beacon-flavours/)
- [Beacon v2 Framework](https://docs.genomebeacons.org/framework/)
- [Beacon v2 Paper (PMC9322265)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9322265/)

### Dimension 1: Access Levels (Who Can Query)

The Beacon v2 spec defines three access tiers, mapped to GA4GH AAI authentication:

| Access Level | Authentication Required | GA4GH AAI Mechanism | Description |
|-------------|------------------------|---------------------|-------------|
| **PUBLIC** | None (anonymous) | — | Anyone on the internet |
| **REGISTERED** | Identity verified | GA4GH Passport with `ResearcherStatus` visa | Bona fide researchers authenticated via ELIXIR AAI, ORCID, etc. |
| **CONTROLLED** | Approved by DAC | GA4GH Passport with `ControlledAccessGrants` visa | Users who applied for and received dataset-specific access |

### Dimension 2: Response Granularity (What They See)

The Beacon v2 spec defines three response granularity levels:

| Granularity | Response Content | Privacy Level |
|-------------|-----------------|---------------|
| **boolean** | `exists: true/false` only | Highest — no data exposed |
| **count** | `exists` + `numTotalResults` | Medium — aggregate counts only |
| **record** | Full `resultSets` with `GenomicVariation` records including `frequencyInPopulations` | Lowest — record-level data |

### The Access × Granularity Matrix

These two dimensions are **independent** — the beacon admin configures which granularity each access level receives. The spec explicitly states any combination is valid. Our configuration:

```
                        PUBLIC          REGISTERED        CONTROLLED
                    ─────────────── ─────────────────── ────────────────
  boolean               ✅                ✅                 ✅
  count                 ❌                ✅                 ✅
  record (variants)     ❌                ❌                 ✅
  record (frequency)    ✅ (opt-in)       ✅                 ✅
  record (individuals)  ❌                ❌                 ✅
```

### Key Design Decisions

**1. Population frequencies are PUBLIC-safe**

The Beacon v2 paper states that security ranges *"from total openness for allele frequencies in population studies to fully protected for particular diseases"*. Population-level allele frequencies are aggregate statistics, not individual-level data. They carry minimal re-identification risk and are routinely published in databases like gnomAD, dbSNP, and ALFA.

Our beacon exposes frequency data at PUBLIC access via `requestedGranularity=record`, following the spec's recommendation that *"non-sensitive Beacons should preferably opt for a `record` and `PUBLIC` combination"*.

**2. Individual-level data requires CONTROLLED access**

Entity endpoints that expose participant data (individuals, biosamples, analyses) are restricted to Secure mode with GA4GH AAI authentication. These endpoints require:
- A valid GA4GH Passport
- A `ControlledAccessGrants` visa matching the dataset
- Optionally, `AcceptedTermsAndPolicies` visa confirming data use agreement

**3. Catalog metadata is PUBLIC**

Endpoints that describe *what data exists* (datasets, cohorts, filtering terms) are available at PUBLIC access. These help users understand what they can query without exposing any participant data. Cohort responses exclude `individualIds` in Boolean mode.

### Endpoint Access Matrix

| Endpoint | PUBLIC (Boolean mode) | REGISTERED (Secure) | CONTROLLED (Secure) |
|----------|----------------------|---------------------|---------------------|
| `/api/` (info) | ✅ | ✅ | ✅ |
| `/api/health` | ✅ | ✅ | ✅ |
| `/api/g_variants` (boolean) | ✅ `exists` only | ✅ `exists` only | ✅ `exists` only |
| `/api/g_variants` (record) | ✅ frequency only | ✅ frequency + annotations | ✅ full records |
| `/api/datasets` | ✅ | ✅ | ✅ |
| `/api/cohorts` | ✅ (no individualIds) | ✅ | ✅ (with individualIds) |
| `/api/filtering_terms` | ✅ | ✅ | ✅ |
| `/api/individuals` | ❌ 404 | ✅ read-only | ✅ full access |
| `/api/biosamples` | ❌ 404 | ✅ read-only | ✅ full access |
| `/api/analyses` | ❌ 404 | ✅ read-only | ✅ full access |

### Beacon Configuration

The beacon advertises its granularity support in the `/api/` info response:

```json
{
  "configuration": {
    "securityLevels": ["PUBLIC", "REGISTERED", "CONTROLLED"],
    "defaultGranularity": "boolean",
    "maxGranularity": "record"
  }
}
```

### Request/Response Granularity Protocol

Clients specify desired granularity via `requestedGranularity` in the query. The beacon responds with the actual granularity used in `returnedGranularity`:

**Boolean request (default)**:
```json
{
  "query": { "referenceName": "11", "start": 5227002 },
  "requestedGranularity": "boolean"
}
```

Response:

```json
{
  "meta": { "returnedGranularity": "boolean" },
  "responseSummary": { "exists": true },
  "response": {
    "datasetAlleleResponses": [
      { "datasetId": "afrigend_wgs_001", "exists": true }
    ]
  }
}
```

**Record request with frequency** (PUBLIC access, opt-in):
```json
{
  "query": { "referenceName": "11", "start": 5227002 },
  "requestedGranularity": "record"
}
```

Response:

```json
{
  "meta": { "returnedGranularity": "record" },
  "responseSummary": { "exists": true },
  "response": {
    "resultSets": [
      {
        "id": "afrigend_wgs_001",
        "exists": true,
        "resultsCount": 1,
        "results": [
          {
            "variantInternalId": "var_sickle_cell_1",
            "variation": {
              "referenceName": "11",
              "start": 5227002,
              "referenceBases": "A",
              "alternateBases": "T"
            },
            "frequencyInPopulations": [
              {
                "source": "AfriGenD",
                "sourceReference": "https://afrigen-d.org",
                "frequencies": [
                  { "population": "African", "alleleFrequency": 0.08 },
                  { "population": "European", "alleleFrequency": 0.0001 }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Data Sensitivity Classification

| Data Type | Sensitivity | Access Level | Rationale |
|-----------|-------------|-------------|-----------|
| Variant existence (yes/no) | Low | PUBLIC | No individual data exposed |
| Variant count | Low-Medium | REGISTERED | Aggregate, but small counts could be identifying |
| Population allele frequency | Low | PUBLIC | Aggregate statistics, routinely published |
| Gene annotations | Low | PUBLIC | Public knowledge (OMIM, ClinVar) |
| Individual demographics | High | CONTROLLED | Directly identifying (sex, age, ethnicity) |
| Disease/phenotype data | High | CONTROLLED | Sensitive health information |
| Biosample details | Medium-High | CONTROLLED | Linked to individuals |
| Raw genotype data | Critical | CONTROLLED | Directly identifying |

### Mapping to GA4GH AAI Visas

When GA4GH AAI is implemented (see [GA4GH AAI Implementation Plan](GA4GH_AAI_IMPLEMENTATION_PLAN.md)), the access levels map to visa requirements:

| Access Level | Required Visas | Verification |
|-------------|---------------|--------------|
| **PUBLIC** | None | Anonymous access allowed |
| **REGISTERED** | `ResearcherStatus` | User is a verified bona fide researcher |
| **CONTROLLED** | `ControlledAccessGrants` + `AcceptedTermsAndPolicies` | User has DAC approval for specific dataset and accepted terms |

### Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Boolean mode (PUBLIC + boolean) | ✅ Production | Default mode |
| Catalog metadata at PUBLIC | ✅ Production | datasets, cohorts, filtering_terms |
| Participant endpoints restricted | ✅ Production | individuals, biosamples, analyses return 404 in Boolean mode |
| `requestedGranularity` support | 🔲 Planned | Enable opt-in record responses with frequency |
| Count granularity | 🔲 Planned | For REGISTERED access |
| GA4GH AAI integration | 🔲 Planned | See AAI Implementation Plan |
| Visa-based authorization | 🔲 Planned | Phase 3 of AAI plan |

---

## Boolean Mode Privacy

### Privacy Guarantees

**Boolean Mode Design Goals**:
1. **No PII Disclosure**: Only YES/NO responses
2. **Re-identification Prevention**: Rate limiting prevents excessive queries
3. **Timing Attack Mitigation**: Response caching
4. **K-anonymity**: Aggregated responses (future)

### Privacy Mechanisms

**1. Response Filtering**:

```python
class BooleanVariantView(APIView):
    """Boolean-only responses"""

    def get(self, request):
        # Query database
        exists = GenomicVariant.objects(**query_params).count() > 0

        # Return ONLY Boolean
        return Response({"exists": exists})

        # NEVER return:
        # - Variant IDs
        # - Individual IDs
        # - Counts
        # - Aggregates
        # - Any identifying information
```

**2. Rate Limiting**:
- 50 requests/hour per IP
- Prevents brute-force re-identification

**3. Query Pattern Detection** (Future):
- Detect suspicious query patterns
- Block systematic genomic region scanning

**4. Response Caching**:
- Reduces timing side-channels
- Same query always returns in same time

### Re-identification Attack Prevention

**Attack Scenario**:
```
Attacker queries many positions for individual X
Attacker infers haplotype from YES/NO pattern
Attacker matches haplotype to public database
Attacker identifies individual
```

**Mitigations**:
1. **Rate Limiting**: Limits queries per hour
2. **Query Logging**: Monitor suspicious patterns
3. **Differential Privacy** (Future): Add noise to responses
4. **Query Budget** (Future): Limit lifetime queries per user

### Privacy Trade-offs

| Feature | Privacy Impact | Utility Impact |
|---------|----------------|----------------|
| Boolean responses | High privacy | Limited utility |
| Rate limiting (50/h) | Medium privacy | Medium utility |
| No aggregates | High privacy | Low utility |
| Query caching | Low privacy (timing) | High performance |

---

## Network Security

### HTTPS/TLS Configuration

**Minimum TLS Version**: TLS 1.2

**Nginx Configuration**:

```nginx
server {
    listen 443 ssl http2;
    server_name beacon.example.org;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/beacon.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/beacon.example.org/privkey.pem;

    # TLS configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5:!3DES;
    ssl_prefer_server_ciphers on;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;

    # Session cache
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
}
```

### CORS Configuration

**Django Settings**:

```python
# CORS configuration
CORS_ALLOWED_ORIGINS = [
    'https://beacon.example.org',
    'https://secure-beacon.example.org',
]

CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'OPTIONS',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'authorization',
    'content-type',
]

# Boolean mode: Allow all origins (public)
# Secure mode: Restrict to approved origins
if settings.BEACON_RESPONSE_MODE == 'BOOLEAN':
    CORS_ALLOW_ALL_ORIGINS = True
```

### Security Headers

**Middleware** (`beacon_api/middleware.py`):

```python
class SecurityHeadersMiddleware:
    """Add security headers to all responses"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'

        # Prevent MIME sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # XSS protection
        response['X-XSS-Protection'] = '1; mode=block'

        # HSTS (force HTTPS)
        response['Strict-Transport-Security'] = \
            'max-age=31536000; includeSubDomains'

        # Content Security Policy
        response['Content-Security-Policy'] = \
            "default-src 'self'; script-src 'self'; style-src 'self'"

        # Referrer policy
        response['Referrer-Policy'] = 'no-referrer'

        return response
```

---

## Database Security

### MongoDB Authentication

**Production Configuration**:

```yaml
# docker-compose.yml
mongodb:
  image: mongo:5.0
  environment:
    MONGO_INITDB_ROOT_USERNAME: admin
    MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_ROOT_PASSWORD}
    MONGO_INITDB_DATABASE: beacon_db
  command: mongod --auth
```

**Application Connection**:

```python
mongoengine.connect(
    'beacon_db',
    host='mongodb',
    port=27017,
    username='beacon_app',
    password=os.getenv('MONGODB_PASSWORD'),
    authentication_source='admin'
)
```

### Redis Security

**Password Protection**:

```bash
# redis.conf
requirepass your_secure_password_here

# Connection in Django
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/0',
        'OPTIONS': {
            'PASSWORD': os.getenv('REDIS_PASSWORD'),
        }
    }
}
```

### Encryption at Rest

**MongoDB Encryption**:

```yaml
# Enable encryption at rest
security:
  enableEncryption: true
  encryptionKeyFile: /data/keyfile
```

**Backup Encryption**:

```bash
# Encrypted backups
mongodump --archive | openssl enc -aes-256-cbc -salt -out backup.enc
```

---

## Application Security

### Django Security Settings

```python
# Production security settings
DEBUG = False
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')  # Strong random key
ALLOWED_HOSTS = ['beacon.example.org']

# Session security
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Strict'  # CSRF protection

# CSRF protection
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
```

### Dependency Security

**Regular Updates**:

```bash
# Check for vulnerabilities
pip-audit

# Update dependencies
pip install --upgrade -r requirements.txt

# Check outdated packages
pip list --outdated
```

---

## Security Testing

### Automated Security Tests

**Run Security Test Suite**:

```bash
./scripts/run_security_tests.sh
```

**Test Script**:

```bash
#!/bin/bash
# run_security_tests.sh

echo "Running security tests..."

# Rate limiting
echo "Testing rate limits..."
python -c "
import requests
for i in range(55):
    r = requests.get('http://localhost:8000/api/g_variants?referenceName=1&start=100000')
    if r.status_code == 429:
        print('✓ Rate limiting working')
        break
else:
    print('✗ Rate limiting failed')
"

# Input validation
echo "Testing input validation..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/g_variants?referenceName=999")
if [ "$STATUS" = "400" ]; then
  echo "✓ Input validation working"
else
  echo "✗ Input validation failed"
fi

# HTTPS redirect
echo "Testing HTTPS redirect..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -L "http://beacon.example.org")
if [ "$STATUS" = "200" ]; then
  echo "✓ HTTPS redirect working"
else
  echo "✗ HTTPS redirect failed"
fi

echo "Security tests complete"
```

### Penetration Testing

**Recommended Tools**:
- **OWASP ZAP**: Web application security scanner
- **Burp Suite**: Security testing platform
- **SQLMap**: SQL injection testing (adapt for NoSQL)
- **Nmap**: Network security scanner

**Schedule**: Quarterly penetration testing

---

## Monitoring & Logging

### Security Event Logging

**Log Events**:
- Authentication attempts (success/failure)
- Rate limit violations
- Input validation failures
- Unauthorized access attempts
- Database connection failures

**Log Format**:

```python
import logging

security_logger = logging.getLogger('security')

# Log authentication failure
security_logger.warning(
    'Authentication failed',
    extra={
        'event': 'auth_failure',
        'ip': request.META['REMOTE_ADDR'],
        'username': username,
        'timestamp': datetime.now().isoformat()
    }
)
```

### Intrusion Detection

**Monitor for**:
- Excessive failed login attempts
- Unusual query patterns
- Rate limit violations from single IP
- Suspicious user agents

---

## Incident Response

### Incident Response Plan

**1. Detection**: Identify security incident
**2. Containment**: Isolate affected systems
**3. Investigation**: Determine scope and impact
**4. Eradication**: Remove threat
**5. Recovery**: Restore services
**6. Lessons Learned**: Update procedures

### Emergency Contacts

- **Security Team**: security@example.org
- **On-Call**: +1-XXX-XXX-XXXX
- **Incident Hotline**: incidents@example.org

---

## Compliance

### GDPR Compliance

- ✅ Data minimization (Boolean mode)
- ✅ Consent management
- ✅ Right to access
- ✅ Right to deletion
- ✅ Data breach notification
- ✅ Privacy by design

### Data Protection

- ✅ Encryption in transit (HTTPS)
- ✅ Encryption at rest (MongoDB)
- ✅ Access controls (RBAC)
- ✅ Audit logging
- ✅ Regular backups

---

**Document Version**: 1.0
**Last Updated**: 2025-01-26
**Status**: Production

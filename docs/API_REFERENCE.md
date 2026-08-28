# Afrigen Beacon v2 - API Reference

## Table of Contents

1. [Introduction](#introduction)
2. [API Overview](#api-overview)
3. [Authentication](#authentication)
4. [Base URLs](#base-urls)
5. [Request Formats](#request-formats)
6. [Response Formats](#response-formats)
7. [Core Informational Endpoints](#core-informational-endpoints)
8. [Data Discovery Endpoints](#data-discovery-endpoints)
9. [Error Handling](#error-handling)
10. [Rate Limiting](#rate-limiting)
11. [Caching](#caching)
12. [Query Examples](#query-examples)
13. [Client Libraries](#client-libraries)

---

## Introduction

This document provides complete API documentation for the Afrigen Beacon v2 implementation. The API is **100% compliant** with the [GA4GH Beacon v2 specification](https://beacon-project.io/) and provides genomic data discovery through standardized REST endpoints.

### API Version

- **Beacon Version**: v2.0
- **API Version**: 1.0
- **OpenAPI Specification**: 3.0

### Target Audience

- **API Consumers**: Developers querying the Beacon API
- **Client Developers**: Building client libraries and applications
- **Data Scientists**: Exploring genomic datasets programmatically

### Getting Help

- **Interactive Documentation**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/) (Swagger UI)
- **OpenAPI Schema**: [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)
- **GitHub Issues**: [Repository Issues](https://github.com/AfriGen-D/variant-checker-beacon/issues)

---

## API Overview

### Endpoint Summary

The Beacon API provides **13 primary endpoints** organized into two categories:

**Core Informational Endpoints** (6 endpoints):
- `GET /api/` - Beacon information
- `GET /api/service-info` - GA4GH service info
- `GET /api/configuration` - Beacon configuration
- `GET /api/entry_types` - Available entry types
- `GET /api/map` - Endpoint map
- `GET /api/health` - Health check

**Data Discovery Endpoints** (7 endpoints):
- `GET/POST /api/g_variants` - Genomic variants
- `GET/POST /api/individuals` - Individuals
- `GET/POST /api/biosamples` - Biosamples
- `GET/POST /api/datasets` - Datasets
- `GET/POST /api/cohorts` - Cohorts
- `GET/POST /api/analyses` - Analyses
- `GET/POST /api/filtering_terms` - Filtering terms

### HTTP Methods

| Method | Use Case | Body Required |
|--------|----------|---------------|
| GET | Simple queries with URL parameters | No |
| POST | Complex queries with filters | Yes (JSON) |

### Content Types

**Request**:
- `application/json` (POST requests)
- `application/x-www-form-urlencoded` (GET requests)

**Response**:
- `application/json` (all responses)

---

## Authentication

### Boolean Mode (Public)

**Access**: No authentication required

```bash
# Simple query - no auth needed
curl "http://localhost:8000/api/g_variants?referenceName=1&start=100000"
```

**Rate Limit**: 50 requests/hour per IP address

### Secure Mode (Authenticated)

**Access**: JWT token required

**1. Obtain JWT Token**:

```bash
# Login endpoint
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'

# Response
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_in": 3600
}
```

**2. Use Token in Requests**:

```bash
# Include token in Authorization header
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  http://localhost:8000/api/g_variants/variant_001
```

**3. Refresh Token**:

```bash
# Refresh expired token
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }'
```

**Rate Limit**: 1,000 requests/hour per user

**Token Lifetime**:
- Access token: 1 hour
- Refresh token: 7 days

---

## Base URLs

### Boolean Mode (Public)

- **Production (UI + API on the same host)**: `https://beacon.afrigen-d.org/api/`
- **Production (API-only, Beacon Network sidecar)**: `https://api-beacon.afrigen-d.dev/api/`
- **Local Development**: `http://localhost:8000/api/`

### Secure Mode (Authenticated)

- **Production**: `https://secure-beacon.h3abionet.org-ilifu/api/`
- **Local Development**: `http://localhost:8001/api/`

---

## Request Formats

### GET Requests

**Query Parameters in URL**:

```
GET /api/g_variants?assemblyId=GRCh38&referenceName=1&start=100000
```

**Parameter Encoding**:
- URL encode special characters
- Arrays: Repeat parameter (e.g., `?filter=a&filter=b`)

### POST Requests

**JSON Body**:

```bash
curl -X POST http://localhost:8000/api/g_variants \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "assemblyId": "GRCh38",
      "referenceName": "1",
      "start": 100000,
      "end": 100001
    },
    "filters": [
      {"id": "MONDO:0007254"}
    ]
  }'
```

**JSON Schema**:

```json
{
  "query": {
    "assemblyId": "string",
    "referenceName": "string",
    "start": "integer",
    "end": "integer",
    "referenceBases": "string",
    "alternateBases": "string"
  },
  "filters": [
    {
      "id": "string",
      "operator": "=",
      "value": "string"
    }
  ],
  "pagination": {
    "skip": 0,
    "limit": 100
  }
}
```

---

## Response Formats

### Boolean Mode Response

**Simple YES/NO**:

```json
{
  "exists": true
}
```

### Secure Mode Response

**Full Record Response**:

```json
{
  "meta": {
    "beaconId": "org.h3abionet.beacon",
    "apiVersion": "v2.0",
    "returnedSchemas": ["beacon-variant-v2.0"]
  },
  "responseSummary": {
    "exists": true,
    "numTotalResults": 1
  },
  "response": {
    "resultSets": [
      {
        "id": "dataset_001",
        "results": [
          {
            "id": "variant_001",
            "assemblyId": "GRCh38",
            "referenceName": "1",
            "start": 100000,
            "end": 100001,
            "referenceBases": "A",
            "alternateBases": "T"
          }
        ]
      }
    ]
  }
}
```

### Response Structure

**Root Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `meta` | Object | Beacon metadata |
| `responseSummary` | Object | Query result summary |
| `response` | Object | Actual data (Secure mode only) |

**meta Object**:

```json
{
  "beaconId": "org.h3abionet.beacon",
  "apiVersion": "v2.0",
  "returnedGranularity": "record",
  "receivedRequestSummary": {
    "apiVersion": "v2.0",
    "requestedGranularity": "record"
  },
  "returnedSchemas": [
    "beacon-variant-v2.0"
  ]
}
```

**responseSummary Object**:

```json
{
  "exists": true,
  "numTotalResults": 100
}
```

---

## Core Informational Endpoints

### GET /api/

**Description**: Returns Beacon metadata and organization information

**Authentication**: None required

**Parameters**: None

**Example Request**:

```bash
curl http://localhost:8000/api/
```

**Example Response**:

```json
{
  "meta": {
    "beaconId": "org.h3abionet.beacon",
    "apiVersion": "v2.0"
  },
  "response": {
    "id": "org.h3abionet.beacon",
    "name": "H3ABioNet Beacon",
    "description": "GA4GH Beacon v2 implementation for African genomics data",
    "version": "v2.0",
    "organization": {
      "id": "org.h3abionet",
      "name": "H3Africa Bioinformatics Network",
      "description": "Pan-African bioinformatics network",
      "address": "South Africa",
      "contactUrl": "https://h3abionet.org/contact",
      "logoUrl": "https://h3abionet.org/logo.png"
    },
    "welcomeUrl": "https://beacon.afrigen-d.org",
    "alternativeUrl": "https://beacon.afrigen-d.org/api/",
    "createDateTime": "2024-01-01T00:00:00Z",
    "updateDateTime": "2025-01-26T10:00:00Z"
  }
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Unique Beacon identifier |
| `name` | String | Beacon name |
| `description` | String | Beacon description |
| `version` | String | API version |
| `organization` | Object | Organization information |
| `welcomeUrl` | String | Beacon homepage URL |
| `createDateTime` | String | Creation timestamp (ISO 8601) |
| `updateDateTime` | String | Last update timestamp (ISO 8601) |

**HTTP Status Codes**:
- `200 OK`: Successful response
- `500 Internal Server Error`: Server error

---

### GET /api/service-info

**Description**: Returns GA4GH Service Info specification compliant metadata

**Authentication**: None required

**Parameters**: None

**Example Request**:

```bash
curl http://localhost:8000/api/service-info
```

**Example Response**:

```json
{
  "id": "org.h3abionet.beacon",
  "name": "H3ABioNet Beacon",
  "type": {
    "group": "org.ga4gh",
    "artifact": "beacon",
    "version": "2.0"
  },
  "description": "GA4GH Beacon v2 implementation",
  "organization": {
    "name": "H3Africa Bioinformatics Network",
    "url": "https://h3abionet.org"
  },
  "contactUrl": "https://h3abionet.org/contact",
  "documentationUrl": "https://beacon.afrigen-d.org/docs",
  "createdAt": "2024-01-01T00:00:00Z",
  "updatedAt": "2025-01-26T10:00:00Z",
  "environment": "production",
  "version": "1.0.0"
}
```

**Specification**: [GA4GH Service Info](https://github.com/ga4gh-discovery/ga4gh-service-info)

**HTTP Status Codes**:
- `200 OK`: Successful response
- `500 Internal Server Error`: Server error

---

### GET /api/configuration

**Description**: Returns Beacon configuration including entry types and filters

**Authentication**: None required

**Parameters**: None

**Example Request**:

```bash
curl http://localhost:8000/api/configuration
```

**Example Response**:

```json
{
  "meta": {
    "beaconId": "org.h3abionet.beacon",
    "apiVersion": "v2.0"
  },
  "response": {
    "maturityAttributes": {
      "productionStatus": "PROD"
    },
    "securityAttributes": {
      "defaultGranularity": "boolean",
      "securityLevels": ["PUBLIC", "REGISTERED", "CONTROLLED"]
    },
    "entryTypes": {
      "genomicVariant": {
        "id": "genomicVariant",
        "name": "Genomic Variant",
        "ontologyTermForThisType": {
          "id": "SO:0001059",
          "label": "sequence_alteration"
        },
        "partOfSpecification": "Beacon v2.0",
        "defaultSchema": {
          "id": "beacon-variant-v2.0",
          "name": "Beacon Variant Schema",
          "referenceToSchemaDefinition": "https://docs.genomebeacons.org/schemas/genomicVariant/"
        }
      },
      "individual": {
        "id": "individual",
        "name": "Individual",
        "ontologyTermForThisType": {
          "id": "NCIT:C25190",
          "label": "Person"
        },
        "partOfSpecification": "Beacon v2.0"
      }
    },
    "filteringTerms": [
      {
        "type": "ontology",
        "scope": "individuals",
        "id": "HP:0000001"
      },
      {
        "type": "ontology",
        "scope": "variants",
        "id": "SO:0001059"
      }
    ]
  }
}
```

**HTTP Status Codes**:
- `200 OK`: Successful response
- `500 Internal Server Error`: Server error

---

### GET /api/entry_types

**Description**: Returns list of available entry types (variant, individual, etc.)

**Authentication**: None required

**Parameters**: None

**Example Request**:

```bash
curl http://localhost:8000/api/entry_types
```

**Example Response**:

```json
{
  "meta": {
    "beaconId": "org.h3abionet.beacon",
    "apiVersion": "v2.0"
  },
  "response": {
    "entryTypes": [
      {
        "id": "genomicVariant",
        "name": "Genomic Variant",
        "ontologyTermForThisType": {
          "id": "SO:0001059",
          "label": "sequence_alteration"
        }
      },
      {
        "id": "individual",
        "name": "Individual"
      },
      {
        "id": "biosample",
        "name": "Biosample"
      },
      {
        "id": "dataset",
        "name": "Dataset"
      },
      {
        "id": "cohort",
        "name": "Cohort"
      },
      {
        "id": "analysis",
        "name": "Analysis"
      }
    ]
  }
}
```

**HTTP Status Codes**:
- `200 OK`: Successful response
- `500 Internal Server Error`: Server error

---

### GET /api/map

**Description**: Returns map of all available endpoints

**Authentication**: None required

**Parameters**: None

**Example Request**:

```bash
curl http://localhost:8000/api/map
```

**Example Response**:

```json
{
  "meta": {
    "beaconId": "org.h3abionet.beacon",
    "apiVersion": "v2.0"
  },
  "response": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "endpointSets": {
      "genomicVariant": {
        "entryType": "genomicVariant",
        "rootUrl": "http://localhost:8000/api/g_variants",
        "singleEntryUrl": "http://localhost:8000/api/g_variants/{id}",
        "endpoints": {
          "genomicVariant": {
            "returnedEntryType": "genomicVariant",
            "url": "http://localhost:8000/api/g_variants"
          }
        }
      },
      "individual": {
        "entryType": "individual",
        "rootUrl": "http://localhost:8000/api/individuals",
        "endpoints": {
          "individual": {
            "returnedEntryType": "individual",
            "url": "http://localhost:8000/api/individuals"
          },
          "genomicVariant": {
            "returnedEntryType": "genomicVariant",
            "url": "http://localhost:8000/api/individuals/{id}/g_variants"
          }
        }
      }
    }
  }
}
```

**HTTP Status Codes**:
- `200 OK`: Successful response
- `500 Internal Server Error`: Server error

---

### GET /api/health

**Description**: Health check endpoint for monitoring

**Authentication**: None required

**Parameters**: None

**Example Request**:

```bash
curl http://localhost:8000/api/health
```

**Example Response (Healthy)**:

```json
{
  "status": "healthy",
  "timestamp": "2025-01-26T10:30:00Z",
  "services": {
    "api": "ok",
    "mongodb": "ok",
    "redis": "ok"
  },
  "version": "1.0.0"
}
```

**Example Response (Unhealthy)**:

```json
{
  "status": "unhealthy",
  "timestamp": "2025-01-26T10:30:00Z",
  "services": {
    "api": "ok",
    "mongodb": "error",
    "redis": "ok"
  },
  "errors": [
    "MongoDB connection failed"
  ]
}
```

**HTTP Status Codes**:
- `200 OK`: All services healthy
- `503 Service Unavailable`: One or more services unhealthy

**Monitoring**: Use this endpoint for load balancer health checks

---

## Data Discovery Endpoints

### GET/POST /api/g_variants

**Description**: Query genomic variants by position, alleles, or filters

**Authentication**:
- Boolean mode: None
- Secure mode: JWT required

**Methods**: GET (simple queries), POST (complex queries with filters)

#### GET Request

**Query Parameters**:

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `assemblyId` | String | Yes | Reference genome. Recognised: `GRCh38`, `GRCh37`, and their UCSC synonyms `hg38`/`hg19`. A recognised build the beacon holds no data for returns **501**, not `exists: false`. | `GRCh38` |
| `referenceName` | String | Yes | Chromosome | `1`-`22`, `X`, `Y`, `MT` |
| `start` | Integer | Yes | Start position (0-based) | `100000` |
| `end` | Integer | No | End position (0-based, exclusive) | `100001` |
| `referenceBases` | String | No | Reference allele | `A`, `AT` |
| `alternateBases` | String | No | Alternate allele | `T`, `G` |
| `variantType` | String | No | Variant type | `SNP`, `INDEL` |
| `datasetIds` | String | No | Dataset filter (comma-separated) | `dataset_001` |

**Example Request (Boolean Mode)**:

```bash
curl "http://localhost:8000/api/g_variants?\
assemblyId=GRCh38&\
referenceName=1&\
start=100000&\
referenceBases=A&\
alternateBases=T"
```

**Example Response (Boolean Mode)**:

```json
{
  "exists": true
}
```

**Example Request (Secure Mode)**:

```bash
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8001/api/g_variants?\
assemblyId=GRCh38&\
referenceName=1&\
start=100000&\
end=200000"
```

**Example Response (Secure Mode)**:

```json
{
  "meta": {
    "beaconId": "org.h3abionet.beacon",
    "apiVersion": "v2.0",
    "returnedGranularity": "record"
  },
  "responseSummary": {
    "exists": true,
    "numTotalResults": 5
  },
  "response": {
    "resultSets": [
      {
        "id": "dataset_001",
        "resultsCount": 5,
        "results": [
          {
            "id": "variant_001",
            "assemblyId": "GRCh38",
            "referenceName": "1",
            "start": 100000,
            "end": 100001,
            "referenceBases": "A",
            "alternateBases": "T",
            "variantType": "SNP",
            "info": {
              "gene_symbol": "GENE1",
              "consequence": "missense_variant"
            }
          },
          {
            "id": "variant_002",
            "assemblyId": "GRCh38",
            "referenceName": "1",
            "start": 150000,
            "end": 150001,
            "referenceBases": "G",
            "alternateBases": "C",
            "variantType": "SNP"
          }
        ]
      }
    ]
  }
}
```

#### POST Request

**Request Body**:

```json
{
  "query": {
    "assemblyId": "GRCh38",
    "referenceName": "1",
    "start": 100000,
    "end": 200000
  },
  "filters": [
    {
      "id": "MONDO:0007254",
      "scope": "individuals"
    },
    {
      "id": "SO:0001583",
      "scope": "variants"
    }
  ],
  "pagination": {
    "skip": 0,
    "limit": 100
  }
}
```

**Example Request**:

```bash
curl -X POST http://localhost:8001/api/g_variants \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "assemblyId": "GRCh38",
      "referenceName": "1",
      "start": 100000,
      "end": 200000
    },
    "filters": [
      {"id": "MONDO:0007254"}
    ]
  }'
```

**Filters**:

Filters use ontology terms to refine queries:

| Filter Type | Scope | Example Terms |
|-------------|-------|---------------|
| Disease | individuals | `MONDO:0007254` (breast cancer) |
| Phenotype | individuals | `HP:0000716` (depression) |
| Variant Type | variants | `SO:0001583` (missense variant) |
| Gene | variants | `gene:BRCA1` |

**HTTP Status Codes**:
- `200 OK`: Successful query
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Missing/invalid JWT (Secure mode)
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

### GET/POST /api/g_variants/{id}

**Description**: Retrieve specific variant by ID (Secure mode only)

**Authentication**: JWT required

**Path Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | String | Yes | Variant ID |

**Example Request**:

```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8001/api/g_variants/variant_001
```

**Example Response**:

```json
{
  "meta": {
    "beaconId": "org.h3abionet.beacon",
    "apiVersion": "v2.0"
  },
  "responseSummary": {
    "exists": true,
    "numTotalResults": 1
  },
  "response": {
    "resultSets": [
      {
        "id": "dataset_001",
        "results": [
          {
            "id": "variant_001",
            "assemblyId": "GRCh38",
            "referenceName": "1",
            "start": 100000,
            "end": 100001,
            "referenceBases": "A",
            "alternateBases": "T",
            "variantType": "SNP",
            "info": {
              "gene_symbol": "BRCA1",
              "consequence": "missense_variant",
              "clinical_significance": "likely_pathogenic",
              "allele_frequency": 0.001
            },
            "molecularAttributes": {
              "gene_id": "ENSG00000012048",
              "transcript_id": "ENST00000357654",
              "protein_change": "p.Arg1699Gln"
            },
            "caseLevelData": [
              {
                "biosampleId": "biosample_001",
                "individualId": "individual_001",
                "genotype": "0/1"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

**HTTP Status Codes**:
- `200 OK`: Variant found
- `404 Not Found`: Variant not found
- `401 Unauthorized`: Missing/invalid JWT

---

### GET/POST /api/individuals

**Description**: Query individuals/subjects/participants

**Authentication**:
- Boolean mode: None (limited response)
- Secure mode: JWT required

**Methods**: GET (simple), POST (with filters)

#### GET Request

**Query Parameters**:

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `sex` | String | No | Biological sex | `MALE`, `FEMALE` |
| `datasetIds` | String | No | Dataset filter | `dataset_001` |

**Example Request (Boolean Mode)**:

```bash
curl "http://localhost:8000/api/individuals?sex=FEMALE"
```

**Example Response (Boolean Mode)**:

```json
{
  "exists": true
}
```

**Example Request (Secure Mode)**:

```bash
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8001/api/individuals?sex=FEMALE"
```

**Example Response (Secure Mode)**:

```json
{
  "meta": {
    "beaconId": "org.h3abionet.beacon",
    "apiVersion": "v2.0"
  },
  "responseSummary": {
    "exists": true,
    "numTotalResults": 250
  },
  "response": {
    "resultSets": [
      {
        "id": "dataset_001",
        "resultsCount": 250,
        "results": [
          {
            "id": "individual_001",
            "sex": "FEMALE",
            "ethnicity": {
              "id": "NCIT:C42331",
              "label": "African"
            },
            "geographicOrigin": {
              "id": "GAZ:00000560",
              "label": "South Africa"
            },
            "diseases": [
              {
                "diseaseCode": {
                  "id": "MONDO:0007254",
                  "label": "breast carcinoma"
                }
              }
            ],
            "phenotypicFeatures": [
              {
                "featureType": {
                  "id": "HP:0000716",
                  "label": "Depression"
                }
              }
            ]
          }
        ]
      }
    ]
  }
}
```

#### POST Request

**Request Body**:

```json
{
  "query": {
    "sex": "FEMALE"
  },
  "filters": [
    {
      "id": "MONDO:0007254",
      "scope": "individual"
    },
    {
      "id": "HP:0000716",
      "scope": "individual"
    }
  ],
  "pagination": {
    "skip": 0,
    "limit": 100
  }
}
```

**Example Request**:

```bash
curl -X POST http://localhost:8001/api/individuals \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {"sex": "FEMALE"},
    "filters": [
      {"id": "MONDO:0007254"},
      {"id": "HP:0000716"}
    ]
  }'
```

**HTTP Status Codes**:
- `200 OK`: Successful query
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Missing/invalid JWT (Secure mode)
- `429 Too Many Requests`: Rate limit exceeded

---

### GET/POST /api/individuals/{id}

**Description**: Retrieve specific individual by ID (Secure mode only)

**Authentication**: JWT required

**Example Request**:

```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8001/api/individuals/individual_001
```

**Example Response**:

```json
{
  "meta": {
    "beaconId": "org.h3abionet.beacon",
    "apiVersion": "v2.0"
  },
  "responseSummary": {
    "exists": true,
    "numTotalResults": 1
  },
  "response": {
    "resultSets": [
      {
        "id": "dataset_001",
        "results": [
          {
            "id": "individual_001",
            "sex": "FEMALE",
            "ethnicity": {
              "id": "NCIT:C42331",
              "label": "African"
            },
            "diseases": [
              {
                "diseaseCode": {
                  "id": "MONDO:0007254",
                  "label": "breast carcinoma"
                },
                "ageOfOnset": {
                  "age": "P45Y"
                }
              }
            ],
            "phenotypicFeatures": [
              {
                "featureType": {
                  "id": "HP:0000716",
                  "label": "Depression"
                },
                "excluded": false
              }
            ],
            "measures": [
              {
                "assayCode": {
                  "id": "LOINC:29463-7",
                  "label": "Body weight"
                },
                "measurementValue": {
                  "quantity": {
                    "value": 65.5,
                    "unit": {"id": "UCUM:kg"}
                  }
                }
              }
            ]
          }
        ]
      }
    ]
  }
}
```

---

### GET/POST /api/biosamples

**Description**: Query biological samples

**Authentication**:
- Boolean mode: None
- Secure mode: JWT required

**Query Parameters**:

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `individualId` | String | No | Parent individual | `individual_001` |
| `datasetIds` | String | No | Dataset filter | `dataset_001` |

**Example Request (Secure Mode)**:

```bash
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8001/api/biosamples?individualId=individual_001"
```

**Example Response**:

```json
{
  "meta": {
    "beaconId": "org.h3abionet.beacon",
    "apiVersion": "v2.0"
  },
  "responseSummary": {
    "exists": true,
    "numTotalResults": 3
  },
  "response": {
    "resultSets": [
      {
        "id": "dataset_001",
        "results": [
          {
            "id": "biosample_001",
            "individualId": "individual_001",
            "biosampleStatus": {
              "id": "EFO:0009655",
              "label": "frozen specimen"
            },
            "sampleOriginDetail": {
              "id": "UBERON:0000310",
              "label": "breast"
            },
            "collectionDate": "2024-01-15"
          }
        ]
      }
    ]
  }
}
```

---

### GET/POST /api/datasets

**Description**: Query datasets

**Authentication**: None required

**Example Request**:

```bash
curl http://localhost:8000/api/datasets
```

**Example Response**:

```json
{
  "meta": {
    "beaconId": "org.h3abionet.beacon",
    "apiVersion": "v2.0"
  },
  "responseSummary": {
    "exists": true,
    "numTotalResults": 1
  },
  "response": {
    "resultSets": [
      {
        "results": [
          {
            "id": "dataset_001",
            "name": "African Genomics Dataset",
            "description": "Whole genome sequencing from African populations",
            "createDateTime": "2024-01-01T00:00:00Z",
            "updateDateTime": "2025-01-26T10:00:00Z",
            "version": "1.0",
            "externalUrl": "https://afrigenomics.org/datasets/001",
            "info": {
              "numVariants": 5000000,
              "numIndividuals": 500
            }
          }
        ]
      }
    ]
  }
}
```

---

### GET/POST /api/cohorts

**Description**: Query cohorts

**Authentication**: None required

**Example Request**:

```bash
curl http://localhost:8000/api/cohorts
```

**Example Response**:

```json
{
  "meta": {
    "beaconId": "org.h3abionet.beacon",
    "apiVersion": "v2.0"
  },
  "responseSummary": {
    "exists": true,
    "numTotalResults": 1
  },
  "response": {
    "resultSets": [
      {
        "results": [
          {
            "id": "cohort_001",
            "name": "Breast Cancer Cohort",
            "cohortType": "case-control study",
            "cohortSize": 500,
            "inclusionCriteria": {
              "ageRange": {"min": 18, "max": 75},
              "diseases": [
                {"id": "MONDO:0007254", "label": "breast carcinoma"}
              ]
            }
          }
        ]
      }
    ]
  }
}
```

---

### GET/POST /api/analyses

**Description**: Query analyses/pipelines

**Authentication**:
- Boolean mode: None
- Secure mode: JWT required

**Example Request**:

```bash
curl http://localhost:8000/api/analyses
```

**Example Response**:

```json
{
  "meta": {
    "beaconId": "org.h3abionet.beacon",
    "apiVersion": "v2.0"
  },
  "responseSummary": {
    "exists": true,
    "numTotalResults": 1
  },
  "response": {
    "resultSets": [
      {
        "results": [
          {
            "id": "analysis_001",
            "analysisDate": "2024-01-15T10:00:00Z",
            "pipelineName": "GATK HaplotypeCaller",
            "pipelineRef": "https://gatk.broadinstitute.org/",
            "variantCaller": "GATK v4.2.0.0",
            "biosampleId": "biosample_001",
            "datasetId": "dataset_001"
          }
        ]
      }
    ]
  }
}
```

---

### GET/POST /api/filtering_terms

**Description**: Query available filtering terms (ontology terms)

**Authentication**: None required

**Query Parameters**:

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `type` | String | No | Term type | `ontology`, `alphanumeric` |
| `scope` | String | No | Entry type scope | `individuals`, `variants` |

**Example Request**:

```bash
curl "http://localhost:8000/api/filtering_terms?scope=individuals"
```

**Example Response**:

```json
{
  "meta": {
    "beaconId": "org.h3abionet.beacon",
    "apiVersion": "v2.0"
  },
  "responseSummary": {
    "exists": true,
    "numTotalResults": 100
  },
  "response": {
    "resultSets": [
      {
        "results": [
          {
            "id": "HP:0000716",
            "type": "ontology",
            "label": "Depression",
            "scope": "individuals"
          },
          {
            "id": "MONDO:0007254",
            "type": "ontology",
            "label": "breast carcinoma",
            "scope": "individuals"
          }
        ]
      }
    ]
  }
}
```

---

## Error Handling

### Error Response Format

**Standard Error Response**:

```json
{
  "error": {
    "errorCode": 400,
    "errorMessage": "Invalid chromosome: 999"
  }
}
```

### HTTP Status Codes

| Code | Status | Description | Example |
|------|--------|-------------|---------|
| 200 | OK | Successful request | Query returned results |
| 400 | Bad Request | Invalid parameters | Invalid chromosome, negative position |
| 401 | Unauthorized | Missing/invalid authentication | JWT token missing or expired |
| 403 | Forbidden | Insufficient permissions | User lacks access to dataset |
| 404 | Not Found | Resource not found | Variant ID doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded | > 50 req/hour in Boolean mode |
| 500 | Internal Server Error | Server-side error | Database connection failed |
| 503 | Service Unavailable | Service down | MongoDB/Redis unavailable |

### Error Examples

**Invalid Chromosome (400)**:

```bash
curl "http://localhost:8000/api/g_variants?referenceName=999&start=100000"
```

```json
{
  "error": {
    "errorCode": 400,
    "errorMessage": "Invalid chromosome: 999. Must be 1-22, X, Y, or MT"
  }
}
```

**Missing Authentication (401)**:

```bash
curl http://localhost:8001/api/g_variants/variant_001
```

```json
{
  "error": {
    "errorCode": 401,
    "errorMessage": "Authentication credentials were not provided"
  }
}
```

**Rate Limit Exceeded (429)**:

```bash
# After 51st request in Boolean mode
curl "http://localhost:8000/api/g_variants?referenceName=1&start=100000"
```

```json
{
  "error": {
    "errorCode": 429,
    "errorMessage": "Rate limit exceeded. Limit: 50 requests/hour"
  }
}
```

**Variant Not Found (404)**:

```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8001/api/g_variants/nonexistent_variant
```

```json
{
  "error": {
    "errorCode": 404,
    "errorMessage": "Variant not found: nonexistent_variant"
  }
}
```

---

## Rate Limiting

### Limits by Mode

| Mode | Rate Limit | Basis | Reset Period |
|------|------------|-------|--------------|
| Boolean (Public) | 50 requests | Per IP address | 1 hour (rolling) |
| Secure (Authenticated) | 1,000 requests | Per user (JWT) | 1 hour (rolling) |

### Rate Limit Headers

**Response Headers**:

```
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1706270400
```

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Total requests allowed per window |
| `X-RateLimit-Remaining` | Requests remaining in current window |
| `X-RateLimit-Reset` | Unix timestamp when limit resets |

### Checking Rate Limit

```bash
# Make request and inspect headers
curl -i "http://localhost:8000/api/g_variants?referenceName=1&start=100000"

# Response includes:
# X-RateLimit-Limit: 50
# X-RateLimit-Remaining: 49
# X-RateLimit-Reset: 1706270400
```

### Rate Limit Best Practices

1. **Respect Limits**: Don't exceed rate limits
2. **Check Headers**: Monitor remaining requests
3. **Implement Backoff**: Wait before retrying after 429
4. **Cache Locally**: Store frequent queries locally
5. **Batch Queries**: Use POST with filters instead of many GET requests

### Example: Rate Limit Handling (Python)

```python
import requests
import time

def query_beacon(url, params):
    """Query with rate limit handling"""
    response = requests.get(url, params=params)

    # Check rate limit
    remaining = int(response.headers.get('X-RateLimit-Remaining', 0))

    if response.status_code == 429:
        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
        wait_seconds = reset_time - int(time.time())
        print(f"Rate limit exceeded. Waiting {wait_seconds} seconds...")
        time.sleep(wait_seconds + 1)
        return query_beacon(url, params)  # Retry

    return response.json()
```

---

## Caching

### Cache Strategy

**Cache Backend**: Redis

**Cache Duration**: 5 minutes (300 seconds)

**Cache Key**: Hash of query parameters

**Eviction Policy**: LRU (Least Recently Used)

### Cache Behavior

**First Request** (Cache Miss):
```
Client → API → MongoDB → API → Cache → Client
Response Time: ~200ms
```

**Subsequent Request** (Cache Hit):
```
Client → API → Cache → Client
Response Time: ~10ms
```

### Cache Headers

**Response Headers**:

```
X-Cache-Status: HIT
Cache-Control: public, max-age=300
```

| Header | Values | Description |
|--------|--------|-------------|
| `X-Cache-Status` | `HIT`, `MISS` | Whether response from cache |
| `Cache-Control` | `public, max-age=300` | Cache directives |

### Cache Invalidation

**Automatic**: Cached responses expire after 5 minutes

**Manual**: Not supported via API (admin operation only)

### Bypassing Cache

**Force Fresh Query** (Admin only):

```bash
curl -H "X-No-Cache: true" \
  "http://localhost:8000/api/g_variants?referenceName=1&start=100000"
```

**Note**: Cache bypass not available to regular users

---

## Query Examples

### Example 1: Simple Variant Query (Boolean Mode)

**Use Case**: Check if a specific SNP exists

```bash
curl "http://localhost:8000/api/g_variants?\
assemblyId=GRCh38&\
referenceName=1&\
start=100000&\
referenceBases=A&\
alternateBases=T"
```

**Response**:
```text
{
  "meta": { "beaconId": "org.afrigen-d.beacon", "apiVersion": "v2.0.0",
            "returnedGranularity": "boolean" },
  "responseSummary": { "exists": true, "numTotalResults": 1 },
  "response": { "resultSets": [], "beaconHandovers": [ ... ] }
}
```

---

### Example 2: Range Query (Secure Mode)

**Use Case**: Find all variants in a genomic region

```bash
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8001/api/g_variants?\
assemblyId=GRCh38&\
referenceName=1&\
start=100000&\
end=200000"
```

**Response**: List of variants in range

---

### Example 3: Gene-Based Query

**Use Case**: Find variants in a specific gene (POST with filter)

```bash
curl -X POST http://localhost:8001/api/g_variants \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "assemblyId": "GRCh38"
    },
    "filters": [
      {"id": "gene:BRCA1"}
    ]
  }'
```

---

### Example 4: Disease-Associated Variants

**Use Case**: Find variants in individuals with specific disease

```bash
curl -X POST http://localhost:8001/api/g_variants \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "assemblyId": "GRCh38",
      "referenceName": "17"
    },
    "filters": [
      {
        "id": "MONDO:0007254",
        "scope": "individuals"
      }
    ]
  }'
```

---

### Example 5: Phenotype Query

**Use Case**: Find individuals with specific phenotype

```bash
curl -X POST http://localhost:8001/api/individuals \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "sex": "FEMALE"
    },
    "filters": [
      {
        "id": "HP:0000716",
        "scope": "individual"
      }
    ]
  }'
```

---

### Example 6: Pagination

**Use Case**: Retrieve results in batches

```bash
curl -X POST http://localhost:8001/api/g_variants \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "assemblyId": "GRCh38",
      "referenceName": "1"
    },
    "pagination": {
      "skip": 0,
      "limit": 100
    }
  }'

# Next page
curl -X POST http://localhost:8001/api/g_variants \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "assemblyId": "GRCh38",
      "referenceName": "1"
    },
    "pagination": {
      "skip": 100,
      "limit": 100
    }
  }'
```

---

## Client Libraries

### Python

**Installation**:
```bash
pip install beacon-client
```

**Example**:
```python
from beacon_client import BeaconClient

# Boolean mode
client = BeaconClient('http://localhost:8000/api/')

# Query variant
result = client.query_variant(
    assembly_id='GRCh38',
    reference_name='1',
    start=100000,
    reference_bases='A',
    alternate_bases='T'
)

print(result['responseSummary']['exists'])  # True or False

# Secure mode with authentication
secure_client = BeaconClient(
    'http://localhost:8001/api/',
    token='your-jwt-token'
)

variants = secure_client.get_variants(
    assembly_id='GRCh38',
    reference_name='1',
    start=100000,
    end=200000
)

for variant in variants:
    print(f"{variant['id']}: {variant['referenceBases']} > {variant['alternateBases']}")
```

### R

**Installation**:
```r
install.packages("beaconr")
```

**Example**:
```r
library(beaconr)

# Connect to Beacon
beacon <- connect_beacon("http://localhost:8000/api/")

# Query variant
result <- query_variant(
  beacon,
  assembly_id = "GRCh38",
  reference_name = "1",
  start = 100000,
  reference_bases = "A",
  alternate_bases = "T"
)

print(result$exists)

# Secure mode
secure_beacon <- connect_beacon(
  "http://localhost:8001/api/",
  token = "your-jwt-token"
)

variants <- get_variants(
  secure_beacon,
  assembly_id = "GRCh38",
  reference_name = "1",
  start = 100000,
  end = 200000
)

print(variants)
```

### JavaScript

**Installation**:
```bash
npm install beacon-js-client
```

**Example**:
```javascript
const BeaconClient = require('beacon-js-client');

// Boolean mode
const client = new BeaconClient('http://localhost:8000/api/');

// Query variant
client.queryVariant({
  assemblyId: 'GRCh38',
  referenceName: '1',
  start: 100000,
  referenceBases: 'A',
  alternateBases: 'T'
}).then(result => {
  console.log(result.responseSummary.exists);
});

// Secure mode
const secureClient = new BeaconClient('http://localhost:8001/api/', {
  token: 'your-jwt-token'
});

secureClient.getVariants({
  assemblyId: 'GRCh38',
  referenceName: '1',
  start: 100000,
  end: 200000
}).then(variants => {
  variants.forEach(variant => {
    console.log(`${variant.id}: ${variant.referenceBases} > ${variant.alternateBases}`);
  });
});
```

---

**Document Version**: 1.0
**Last Updated**: 2025-01-26
**API Version**: v2.0
**Status**: Production

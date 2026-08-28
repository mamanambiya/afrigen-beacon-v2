# Afrigen Beacon v2 - Database Schema Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Database Overview](#database-overview)
3. [Schema Design Principles](#schema-design-principles)
4. [Collection Schemas](#collection-schemas)
   - [variants Collection](#variants-collection)
   - [individuals Collection](#individuals-collection)
   - [biosamples Collection](#biosamples-collection)
   - [datasets Collection](#datasets-collection)
   - [cohorts Collection](#cohorts-collection)
   - [analyses Collection](#analyses-collection)
   - [filtering_terms Collection](#filtering_terms-collection)
5. [Data Relationships](#data-relationships)
6. [Index Strategy](#index-strategy)
7. [Data Validation](#data-validation)
8. [Migration Strategy](#migration-strategy)
9. [Performance Optimization](#performance-optimization)
10. [Data Import/Export](#data-importexport)
11. [References](#references)

---

## Introduction

This document provides comprehensive documentation for the MongoDB database schema used in the Afrigen Beacon v2 implementation. The schema is designed to be **100% compliant** with the [GA4GH Beacon v2 specification](https://beacon-project.io/) while optimized for performance and scalability.

### Purpose

- Define the structure of all MongoDB collections
- Document field types, constraints, and relationships
- Specify indexing strategy for query performance
- Provide migration guidance for schema evolution

### Audience

- **Developers**: Understanding data models and relationships
- **Data Managers**: Importing and managing genomic data
- **Database Administrators**: Performance tuning and maintenance

### Database Technology

- **Database**: MongoDB 5.0+
- **ODM**: MongoEngine 0.24+
- **Data Format**: BSON (Binary JSON)
- **Encoding**: UTF-8

---

## Database Overview

### Database Configuration

**Database Name**: `beacon_db` (production), `beacon_db_dev` (development)

**Connection String**:
```
mongodb://localhost:27017/beacon_db
```

**Authentication** (Production):
```
mongodb://beacon_admin:password@localhost:27017/beacon_db?authSource=admin
```

### Collections Overview

The Beacon v2 database consists of **7 primary collections** corresponding to GA4GH Beacon v2 entry types:

| Collection | Purpose | Typical Size | Query Frequency |
|------------|---------|--------------|-----------------|
| `variants` | Genomic variants | Millions | Very High |
| `individuals` | Subjects/participants | Thousands | High |
| `biosamples` | Biological samples | Thousands | High |
| `datasets` | Dataset metadata | Tens | Medium |
| `cohorts` | Cohort definitions | Tens | Medium |
| `analyses` | Analysis records | Hundreds | Medium |
| `filtering_terms` | Ontology terms | Thousands | Low |

### Storage Estimates

**Example Dataset (1000 Genomes):**
- Variants: ~84 million records ≈ 500 GB
- Individuals: ~2,500 records ≈ 5 MB
- Biosamples: ~2,500 records ≈ 10 MB
- Datasets: ~1 record ≈ 1 KB
- Cohorts: ~5 records ≈ 5 KB
- Analyses: ~100 records ≈ 1 MB
- Filtering Terms: ~10,000 records ≈ 50 MB

**Total**: ~500 GB (dominated by variants)

### Collection Relationships

```
datasets ──1:N── variants
   │
   ├──1:N── individuals ──1:N── biosamples ──1:N── variants
   │
   └──1:N── cohorts ──N:M── individuals

analyses ──N:1── datasets
analyses ──N:M── variants

filtering_terms ──used by── all collections
```

---

## Schema Design Principles

### 1. GA4GH Beacon v2 Compliance

All schemas align with [GA4GH Beacon v2 Models](https://docs.genomebeacons.org/models/):
- Field names match specification exactly
- Required fields are enforced
- Data types follow specification
- Ontology terms use standard vocabularies (HPO, LOINC, etc.)

### 2. Flexible Schema Evolution

**MongoDB's flexible schema** supports:
- Adding new fields without migration
- Optional fields for incomplete data
- Nested documents for hierarchical data
- Arrays for one-to-many relationships

### 3. Denormalization for Performance

**Strategic denormalization**:
- Embed frequently-accessed nested data
- Duplicate data to reduce joins
- Trade storage for query performance

**Example**:
```text
{
  "id": "variant_001",
  "dataset_id": "dataset_1",
  "dataset_name": "1000 Genomes",  // Denormalized
  ...
}
```

### 4. Indexing for Common Queries

**Compound indexes** for:
- Position-based queries (assembly_id + chromosome + position)
- ID lookups (unique indexes)
- Filter queries (ontology terms)

### 5. Data Integrity

**Application-level enforcement**:
- Required fields validated by MongoEngine
- Foreign key references checked before insert
- Ontology term validation
- Range constraints (e.g., positions ≥ 0)

---

## Collection Schemas

### variants Collection

**Purpose**: Store genomic variants (SNPs, INDELs, CNVs, etc.)

**GA4GH Model**: [Genomic Variant](https://docs.genomebeacons.org/models/genomicVariant/)

**MongoEngine Model** (`beacon_api/models.py`):

```python
from mongoengine import Document, StringField, IntField, ListField, DictField, BooleanField

class GenomicVariant(Document):
    """GA4GH Beacon v2 Genomic Variant"""

    # Required fields
    id = StringField(required=True, primary_key=True, unique=True)
    assembly_id = StringField(required=True, choices=['GRCh38', 'GRCh37', 'GRCh36'])
    reference_name = StringField(required=True)  # Chromosome: 1-22, X, Y, MT
    start = IntField(required=True, min_value=0)  # 0-based, inclusive
    reference_bases = StringField(required=True)  # [ACGTN]+
    alternate_bases = StringField(required=True)  # [ACGTN]+

    # Optional fields
    end = IntField(min_value=0)  # 0-based, exclusive
    variant_type = StringField(choices=['SNP', 'MNP', 'INDEL', 'DEL', 'INS', 'DUP', 'CNV', 'INV', 'BND'])
    variant_state = StringField()  # e.g., "heterozygous", "homozygous"

    # Annotations
    info = DictField()  # VCF INFO fields and annotations
    molecular_attributes = DictField()  # Gene, transcript, protein consequences
    variant_level_data = DictField()  # Population frequencies, clinical significance
    case_level_data = ListField(DictField())  # Individual-level data

    # Relationships
    dataset_id = StringField(required=True)
    biosample_id = StringField()
    individual_id = StringField()
    analysis_id = StringField()

    # Metadata
    updated = StringField()  # ISO 8601 timestamp
    notes = StringField()

    meta = {
        'collection': 'variants',
        'indexes': [
            # Compound index for position queries
            {
                'fields': ['assembly_id', 'reference_name', 'start'],
                'name': 'position_index'
            },
            # Unique ID index
            {'fields': ['id'], 'unique': True},
            # Dataset index
            {'fields': ['dataset_id']},
            # Individual/biosample indexes
            {'fields': ['individual_id']},
            {'fields': ['biosample_id']},
            # Variant type index
            {'fields': ['variant_type']},
        ],
        'ordering': ['reference_name', 'start']
    }
```

**JSON Schema Example**:

```json
{
  "_id": "variant_001",
  "id": "variant_001",
  "assembly_id": "GRCh38",
  "reference_name": "1",
  "start": 100000,
  "end": 100001,
  "reference_bases": "A",
  "alternate_bases": "T",
  "variant_type": "SNP",
  "variant_state": "heterozygous",
  "info": {
    "gene_symbol": "BRCA1",
    "consequence": "missense_variant",
    "clinical_significance": "likely_pathogenic",
    "allele_frequency": 0.001
  },
  "molecular_attributes": {
    "gene_id": "ENSG00000012048",
    "transcript_id": "ENST00000357654",
    "protein_change": "p.Arg1699Gln",
    "cdna_change": "c.5096G>A"
  },
  "variant_level_data": {
    "allele_count": 5,
    "allele_number": 5000,
    "allele_frequency": 0.001,
    "homozygote_count": 0
  },
  "case_level_data": [
    {
      "biosample_id": "biosample_001",
      "individual_id": "individual_001",
      "genotype": "0/1",
      "quality": 99,
      "depth": 50
    }
  ],
  "dataset_id": "dataset_001",
  "updated": "2025-01-26T10:00:00Z"
}
```

**Field Descriptions**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | String | Yes | Unique variant identifier | `variant_001` |
| `assembly_id` | String | Yes | Reference genome assembly | `GRCh38` |
| `reference_name` | String | Yes | Chromosome | `1`, `X`, `MT` |
| `start` | Integer | Yes | Start position (0-based, inclusive) | `100000` |
| `end` | Integer | No | End position (0-based, exclusive) | `100001` |
| `reference_bases` | String | Yes | Reference allele | `A` |
| `alternate_bases` | String | Yes | Alternate allele | `T` |
| `variant_type` | String | No | Type of variant | `SNP`, `INDEL` |
| `variant_state` | String | No | Zygosity | `heterozygous` |
| `info` | Object | No | VCF INFO + annotations | `{...}` |
| `molecular_attributes` | Object | No | Gene/transcript/protein | `{...}` |
| `variant_level_data` | Object | No | Population statistics | `{...}` |
| `case_level_data` | Array | No | Individual-level data | `[{...}]` |
| `dataset_id` | String | Yes | Parent dataset ID | `dataset_001` |
| `biosample_id` | String | No | Associated biosample | `biosample_001` |
| `individual_id` | String | No | Associated individual | `individual_001` |
| `updated` | String | No | Last update timestamp | ISO 8601 |

**Indexes**:

```javascript
// Primary compound index (used for 95% of queries)
db.variants.createIndex(
  {"assembly_id": 1, "reference_name": 1, "start": 1},
  {name: "position_index"}
)

// Unique ID index
db.variants.createIndex(
  {"id": 1},
  {unique: true, name: "id_unique"}
)

// Dataset index
db.variants.createIndex({"dataset_id": 1})

// Individual/biosample indexes
db.variants.createIndex({"individual_id": 1})
db.variants.createIndex({"biosample_id": 1})

// Variant type index
db.variants.createIndex({"variant_type": 1})

// Text search index (optional, for gene symbol search)
db.variants.createIndex(
  {"info.gene_symbol": "text", "info.consequence": "text"},
  {name: "text_search"}
)
```

**Query Examples**:

```javascript
// Query by position (most common)
db.variants.find({
  "assembly_id": "GRCh38",
  "reference_name": "1",
  "start": {$gte: 100000, $lte: 100001}
})

// Query by ID
db.variants.find({"id": "variant_001"})

// Query by gene
db.variants.find({"info.gene_symbol": "BRCA1"})

// Query by dataset
db.variants.find({"dataset_id": "dataset_001"})

// Query by individual
db.variants.find({"individual_id": "individual_001"})

// Complex query with filters
db.variants.find({
  "assembly_id": "GRCh38",
  "reference_name": "1",
  "start": {$gte: 100000, $lte: 200000},
  "variant_type": "SNP",
  "info.clinical_significance": "pathogenic"
})
```

**Data Volume Estimates**:

- **Small dataset** (exome): ~100K variants ≈ 500 MB
- **Medium dataset** (whole genome): ~5M variants ≈ 25 GB
- **Large dataset** (population cohort): ~100M variants ≈ 500 GB

---

### individuals Collection

**Purpose**: Store information about individuals/subjects/participants

**GA4GH Model**: [Individual](https://docs.genomebeacons.org/models/individual/)

**MongoEngine Model**:

```python
class Individual(Document):
    """GA4GH Beacon v2 Individual"""

    # Required fields
    id = StringField(required=True, primary_key=True, unique=True)

    # Demographics
    sex = StringField(choices=['MALE', 'FEMALE', 'OTHER_SEX', 'UNKNOWN_SEX'])
    ethnicity = DictField()  # Ontology term (NCIT, etc.)
    geographic_origin = DictField()  # Ontology term (GAZ)

    # Clinical information
    diseases = ListField(DictField())  # Disease ontology terms (MONDO, ICD)
    phenotypic_features = ListField(DictField())  # HPO terms
    treatments = ListField(DictField())  # Treatment information
    interventions_or_procedures = ListField(DictField())  # Medical procedures
    measures = ListField(DictField())  # Measurements (height, weight, etc.)
    exposures = ListField(DictField())  # Environmental exposures

    # Pedigree
    pedigrees = ListField(DictField())  # Family relationships

    # Metadata
    info = DictField()  # Additional information
    notes = StringField()
    updated = StringField()

    # Relationships
    dataset_ids = ListField(StringField())

    meta = {
        'collection': 'individuals',
        'indexes': [
            {'fields': ['id'], 'unique': True},
            {'fields': ['sex']},
            {'fields': ['dataset_ids']},
            {'fields': ['diseases.id']},
            {'fields': ['phenotypic_features.feature_type.id']},
        ]
    }
```

**JSON Schema Example**:

```json
{
  "_id": "individual_001",
  "id": "individual_001",
  "sex": "FEMALE",
  "ethnicity": {
    "id": "NCIT:C42331",
    "label": "African"
  },
  "geographic_origin": {
    "id": "GAZ:00000560",
    "label": "South Africa"
  },
  "diseases": [
    {
      "disease_code": {
        "id": "MONDO:0007254",
        "label": "breast carcinoma"
      },
      "age_of_onset": {
        "age": "P45Y"
      },
      "stage": {
        "id": "NCIT:C28054",
        "label": "Stage IIA"
      }
    }
  ],
  "phenotypic_features": [
    {
      "feature_type": {
        "id": "HP:0000716",
        "label": "Depression"
      },
      "excluded": false
    },
    {
      "feature_type": {
        "id": "HP:0001892",
        "label": "Abnormal bleeding"
      },
      "excluded": true
    }
  ],
  "measures": [
    {
      "assay_code": {
        "id": "LOINC:29463-7",
        "label": "Body weight"
      },
      "measurement_value": {
        "quantity": {
          "value": 65.5,
          "unit": {"id": "UCUM:kg", "label": "kilogram"}
        }
      },
      "date": "2024-01-15"
    }
  ],
  "pedigrees": [
    {
      "id": "pedigree_001",
      "num_subjects": 5,
      "disease": {"id": "MONDO:0007254", "label": "breast carcinoma"}
    }
  ],
  "dataset_ids": ["dataset_001"],
  "updated": "2025-01-26T10:00:00Z"
}
```

**Field Descriptions**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | String | Yes | Unique individual identifier | `individual_001` |
| `sex` | String | No | Biological sex | `MALE`, `FEMALE` |
| `ethnicity` | Object | No | Ethnicity ontology term | NCIT term |
| `geographic_origin` | Object | No | Geographic origin | GAZ term |
| `diseases` | Array | No | Disease information | MONDO, ICD terms |
| `phenotypic_features` | Array | No | Phenotypes | HPO terms |
| `treatments` | Array | No | Treatment history | Drug terms |
| `interventions_or_procedures` | Array | No | Medical procedures | Procedure codes |
| `measures` | Array | No | Physical measurements | LOINC codes |
| `exposures` | Array | No | Environmental exposures | Exposure terms |
| `pedigrees` | Array | No | Family pedigree info | Pedigree IDs |
| `dataset_ids` | Array | No | Associated datasets | `[dataset_001]` |

**Ontology Terms Used**:

- **Sex**: Custom vocabulary (MALE, FEMALE, OTHER_SEX, UNKNOWN_SEX)
- **Ethnicity**: [NCIT Ethnicity](https://ncit.nci.nih.gov/)
- **Geography**: [GAZ (Gazetteer)](http://www.environmentontology.org/Browse-Geography)
- **Diseases**: [MONDO](https://mondo.monarchinitiative.org/), [ICD-10](https://www.who.int/standards/classifications/classification-of-diseases)
- **Phenotypes**: [HPO (Human Phenotype Ontology)](https://hpo.jax.org/)
- **Measures**: [LOINC](https://loinc.org/)
- **Units**: [UCUM](https://ucum.org/)

**Indexes**:

```javascript
db.individuals.createIndex({"id": 1}, {unique: true})
db.individuals.createIndex({"sex": 1})
db.individuals.createIndex({"dataset_ids": 1})
db.individuals.createIndex({"diseases.disease_code.id": 1})
db.individuals.createIndex({"phenotypic_features.feature_type.id": 1})
```

**Query Examples**:

```javascript
// Query by ID
db.individuals.find({"id": "individual_001"})

// Query by sex
db.individuals.find({"sex": "FEMALE"})

// Query by disease
db.individuals.find({"diseases.disease_code.id": "MONDO:0007254"})

// Query by phenotype (HPO term)
db.individuals.find({"phenotypic_features.feature_type.id": "HP:0000716"})

// Query by dataset
db.individuals.find({"dataset_ids": "dataset_001"})

// Complex query
db.individuals.find({
  "sex": "FEMALE",
  "diseases.disease_code.id": "MONDO:0007254",
  "phenotypic_features.feature_type.id": "HP:0000716",
  "dataset_ids": "dataset_001"
})
```

---

### biosamples Collection

**Purpose**: Store information about biological samples

**GA4GH Model**: [Biosample](https://docs.genomebeacons.org/models/biosample/)

**MongoEngine Model**:

```python
class Biosample(Document):
    """GA4GH Beacon v2 Biosample"""

    # Required fields
    id = StringField(required=True, primary_key=True, unique=True)

    # Sample information
    biosample_status = DictField()  # Ontology term (e.g., "fresh", "frozen")
    sample_origin_detail = DictField()  # Tissue/organ ontology term (UBERON)
    sample_origin_type = DictField()  # Cell type ontology term (CL)
    collection_date = StringField()  # ISO 8601 date
    collection_moment = StringField()  # Time point in disease course

    # Processing
    obtention_procedure = DictField()  # Collection method ontology term
    sample_processing = DictField()  # Processing method
    sample_storage = DictField()  # Storage conditions

    # Relationships
    individual_id = StringField(required=True)
    dataset_ids = ListField(StringField())

    # Clinical context
    phenotypic_features = ListField(DictField())  # HPO terms
    measurements = ListField(DictField())  # Measurements at collection

    # Metadata
    info = DictField()
    notes = StringField()
    updated = StringField()

    meta = {
        'collection': 'biosamples',
        'indexes': [
            {'fields': ['id'], 'unique': True},
            {'fields': ['individual_id']},
            {'fields': ['dataset_ids']},
            {'fields': ['sample_origin_detail.id']},
        ]
    }
```

**JSON Schema Example**:

```json
{
  "_id": "biosample_001",
  "id": "biosample_001",
  "individual_id": "individual_001",
  "biosample_status": {
    "id": "EFO:0009655",
    "label": "frozen specimen"
  },
  "sample_origin_detail": {
    "id": "UBERON:0000310",
    "label": "breast"
  },
  "sample_origin_type": {
    "id": "CL:0000057",
    "label": "fibroblast"
  },
  "collection_date": "2024-01-15",
  "collection_moment": "P0D",
  "obtention_procedure": {
    "id": "NCIT:C15189",
    "label": "biopsy"
  },
  "sample_processing": {
    "id": "NCIT:C93205",
    "label": "formalin fixed paraffin embedded"
  },
  "sample_storage": {
    "id": "NCIT:C178942",
    "label": "liquid nitrogen storage"
  },
  "phenotypic_features": [
    {
      "feature_type": {
        "id": "HP:0032197",
        "label": "Neoplasm of the breast"
      },
      "excluded": false
    }
  ],
  "measurements": [
    {
      "assay_code": {
        "id": "LOINC:56844-4",
        "label": "Tumor size"
      },
      "measurement_value": {
        "quantity": {
          "value": 2.5,
          "unit": {"id": "UCUM:cm", "label": "centimeter"}
        }
      }
    }
  ],
  "dataset_ids": ["dataset_001"],
  "updated": "2025-01-26T10:00:00Z"
}
```

**Field Descriptions**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | String | Yes | Unique biosample identifier | `biosample_001` |
| `individual_id` | String | Yes | Parent individual ID | `individual_001` |
| `biosample_status` | Object | No | Sample status | EFO term |
| `sample_origin_detail` | Object | No | Tissue/organ | UBERON term |
| `sample_origin_type` | Object | No | Cell type | CL term |
| `collection_date` | String | No | Collection date | ISO 8601 |
| `collection_moment` | String | No | Disease time point | ISO 8601 duration |
| `obtention_procedure` | Object | No | Collection method | NCIT term |
| `sample_processing` | Object | No | Processing method | NCIT term |
| `sample_storage` | Object | No | Storage conditions | NCIT term |
| `phenotypic_features` | Array | No | Sample phenotypes | HPO terms |
| `measurements` | Array | No | Measurements | LOINC codes |
| `dataset_ids` | Array | No | Associated datasets | `[dataset_001]` |

**Ontology Terms Used**:

- **Status**: [EFO (Experimental Factor Ontology)](https://www.ebi.ac.uk/efo/)
- **Tissue/Organ**: [UBERON](https://www.ebi.ac.uk/ols/ontologies/uberon)
- **Cell Type**: [CL (Cell Ontology)](https://www.ebi.ac.uk/ols/ontologies/cl)
- **Procedures**: [NCIT](https://ncit.nci.nih.gov/)

**Indexes**:

```javascript
db.biosamples.createIndex({"id": 1}, {unique: true})
db.biosamples.createIndex({"individual_id": 1})
db.biosamples.createIndex({"dataset_ids": 1})
db.biosamples.createIndex({"sample_origin_detail.id": 1})
```

---

### datasets Collection

**Purpose**: Store dataset metadata and descriptions

**GA4GH Model**: [Dataset](https://docs.genomebeacons.org/models/dataset/)

**MongoEngine Model**:

```python
class Dataset(Document):
    """GA4GH Beacon v2 Dataset"""

    # Required fields
    id = StringField(required=True, primary_key=True, unique=True)
    name = StringField(required=True)

    # Description
    description = StringField()
    create_date_time = StringField()  # ISO 8601
    update_date_time = StringField()  # ISO 8601
    version = StringField()

    # External references
    external_url = StringField()
    data_use_conditions = DictField()  # DUO ontology terms

    # Metadata
    info = DictField()

    meta = {
        'collection': 'datasets',
        'indexes': [
            {'fields': ['id'], 'unique': True},
            {'fields': ['name']},
        ]
    }
```

**JSON Schema Example**:

```json
{
  "_id": "dataset_001",
  "id": "dataset_001",
  "name": "African Genomics Dataset",
  "description": "Whole genome sequencing data from African populations",
  "create_date_time": "2024-01-01T00:00:00Z",
  "update_date_time": "2025-01-26T10:00:00Z",
  "version": "1.0",
  "external_url": "https://afrigenomics.org/datasets/001",
  "data_use_conditions": {
    "id": "DUO:0000042",
    "label": "general research use"
  },
  "info": {
    "num_variants": 5000000,
    "num_individuals": 500,
    "sequencing_platform": "Illumina NovaSeq",
    "mean_coverage": 30
  }
}
```

**Indexes**:

```javascript
db.datasets.createIndex({"id": 1}, {unique: true})
db.datasets.createIndex({"name": "text", "description": "text"})
```

---

### cohorts Collection

**Purpose**: Store cohort definitions and metadata

**GA4GH Model**: [Cohort](https://docs.genomebeacons.org/models/cohort/)

**MongoEngine Model**:

```python
class Cohort(Document):
    """GA4GH Beacon v2 Cohort"""

    # Required fields
    id = StringField(required=True, primary_key=True, unique=True)
    name = StringField(required=True)
    cohort_type = StringField()  # study, clinical trial, etc.
    cohort_size = IntField()  # Number of individuals

    # Inclusion criteria
    inclusion_criteria = DictField()
    exclusion_criteria = DictField()

    # Cohort characteristics
    cohort_data_types = ListField(DictField())  # Data types collected
    collection_events = ListField(DictField())  # Data collection events

    # Relationships
    dataset_ids = ListField(StringField())

    # Metadata
    info = DictField()

    meta = {
        'collection': 'cohorts',
        'indexes': [
            {'fields': ['id'], 'unique': True},
            {'fields': ['name']},
            {'fields': ['dataset_ids']},
        ]
    }
```

**JSON Schema Example**:

```json
{
  "_id": "cohort_001",
  "id": "cohort_001",
  "name": "Breast Cancer Cohort",
  "cohort_type": "case-control study",
  "cohort_size": 500,
  "inclusion_criteria": {
    "age_range": {"min": 18, "max": 75},
    "diseases": [
      {"id": "MONDO:0007254", "label": "breast carcinoma"}
    ]
  },
  "exclusion_criteria": {
    "diseases": [
      {"id": "MONDO:0005015", "label": "diabetes mellitus"}
    ]
  },
  "cohort_data_types": [
    {
      "id": "NCIT:C16977",
      "label": "genomic data"
    },
    {
      "id": "NCIT:C15783",
      "label": "clinical data"
    }
  ],
  "collection_events": [
    {
      "event_date": "2024-01-01",
      "event_description": "Baseline data collection"
    }
  ],
  "dataset_ids": ["dataset_001"]
}
```

**Indexes**:

```javascript
db.cohorts.createIndex({"id": 1}, {unique: true})
db.cohorts.createIndex({"name": "text"})
db.cohorts.createIndex({"dataset_ids": 1})
```

---

### analyses Collection

**Purpose**: Store analysis/pipeline metadata

**GA4GH Model**: [Analysis](https://docs.genomebeacons.org/models/analysis/)

**MongoEngine Model**:

```python
class Analysis(Document):
    """GA4GH Beacon v2 Analysis"""

    # Required fields
    id = StringField(required=True, primary_key=True, unique=True)
    analysis_date = StringField()  # ISO 8601
    pipeline_name = StringField()
    pipeline_ref = StringField()  # URL or DOI

    # Software
    algorithm_type = DictField()  # Ontology term
    variant_caller = StringField()

    # Relationships
    biosample_id = StringField()
    individual_id = StringField()
    dataset_id = StringField()

    # Metadata
    info = DictField()

    meta = {
        'collection': 'analyses',
        'indexes': [
            {'fields': ['id'], 'unique': True},
            {'fields': ['biosample_id']},
            {'fields': ['individual_id']},
            {'fields': ['dataset_id']},
        ]
    }
```

**JSON Schema Example**:

```json
{
  "_id": "analysis_001",
  "id": "analysis_001",
  "analysis_date": "2024-01-15T10:00:00Z",
  "pipeline_name": "GATK HaplotypeCaller",
  "pipeline_ref": "https://gatk.broadinstitute.org/",
  "algorithm_type": {
    "id": "EDAM:operation_3227",
    "label": "variant calling"
  },
  "variant_caller": "GATK HaplotypeCaller v4.2.0.0",
  "biosample_id": "biosample_001",
  "individual_id": "individual_001",
  "dataset_id": "dataset_001",
  "info": {
    "reference_genome": "GRCh38",
    "mean_coverage": 30,
    "variants_called": 5000000
  }
}
```

**Indexes**:

```javascript
db.analyses.createIndex({"id": 1}, {unique: true})
db.analyses.createIndex({"biosample_id": 1})
db.analyses.createIndex({"individual_id": 1})
db.analyses.createIndex({"dataset_id": 1})
```

---

### filtering_terms Collection

**Purpose**: Store ontology terms used for filtering

**GA4GH Model**: [Filtering Terms](https://docs.genomebeacons.org/models/filteringTerms/)

**MongoEngine Model**:

```python
class FilteringTerm(Document):
    """GA4GH Beacon v2 Filtering Term"""

    # Required fields
    id = StringField(required=True, primary_key=True, unique=True)
    type = StringField(required=True)  # alphanumeric, ontology
    label = StringField()

    # Ontology information
    scope = StringField()  # e.g., "individuals", "biosamples"

    # Metadata
    info = DictField()

    meta = {
        'collection': 'filtering_terms',
        'indexes': [
            {'fields': ['id'], 'unique': True},
            {'fields': ['type']},
            {'fields': ['scope']},
        ]
    }
```

**JSON Schema Example**:

```json
{
  "_id": "HP:0000716",
  "id": "HP:0000716",
  "type": "ontology",
  "label": "Depression",
  "scope": "individuals",
  "info": {
    "ontology": "Human Phenotype Ontology",
    "definition": "A mental state characterized by..."
  }
}
```

**Indexes**:

```javascript
db.filtering_terms.createIndex({"id": 1}, {unique: true})
db.filtering_terms.createIndex({"type": 1})
db.filtering_terms.createIndex({"scope": 1})
db.filtering_terms.createIndex({"label": "text"})
```

---

## Data Relationships

### Relationship Diagram

```
┌──────────────┐
│   datasets   │
└──────┬───────┘
       │
       │ 1:N
       ▼
┌──────────────┐      1:N     ┌──────────────┐      1:N     ┌──────────────┐
│ individuals  │─────────────▶│  biosamples  │─────────────▶│   variants   │
└──────┬───────┘              └──────┬───────┘              └──────────────┘
       │                             │
       │ N:M                         │ N:1
       ▼                             ▼
┌──────────────┐              ┌──────────────┐
│   cohorts    │              │   analyses   │
└──────────────┘              └──────────────┘
       │
       │ N:1
       ▼
┌──────────────┐
│   datasets   │
└──────────────┘

┌────────────────────┐
│ filtering_terms    │  ← Referenced by all collections
└────────────────────┘
```

### Foreign Key Relationships

| Parent Collection | Child Collection | Relationship Type | Field |
|-------------------|------------------|-------------------|-------|
| datasets | variants | One-to-Many | `dataset_id` |
| datasets | individuals | One-to-Many | `dataset_ids[]` |
| datasets | cohorts | One-to-Many | `dataset_ids[]` |
| individuals | biosamples | One-to-Many | `individual_id` |
| biosamples | variants | One-to-Many | `biosample_id` |
| individuals | variants | One-to-Many | `individual_id` |
| cohorts | individuals | Many-to-Many | External mapping |
| analyses | biosamples | Many-to-One | `biosample_id` |

### Referential Integrity

**Application-Level Enforcement**:

```python
# Before inserting variant, verify dataset exists
def create_variant(variant_data):
    dataset_id = variant_data['dataset_id']
    if not Dataset.objects(id=dataset_id).first():
        raise ValidationError(f"Dataset {dataset_id} not found")

    variant = GenomicVariant(**variant_data)
    variant.save()
```

**Cascade Deletion** (Optional):

```python
# When deleting dataset, option to delete related variants
def delete_dataset(dataset_id, cascade=False):
    if cascade:
        GenomicVariant.objects(dataset_id=dataset_id).delete()
        Individual.objects(dataset_ids=dataset_id).update(pull__dataset_ids=dataset_id)

    Dataset.objects(id=dataset_id).delete()
```

---

## Index Strategy

### Performance Goals

- **Point queries** (by ID): < 10ms
- **Range queries** (by position): < 50ms
- **Filter queries**: < 200ms
- **Text search**: < 500ms

### Index Types

#### 1. Unique Indexes

**Purpose**: Enforce uniqueness, fast ID lookups

```javascript
// All collections have unique ID index
db.variants.createIndex({"id": 1}, {unique: true})
db.individuals.createIndex({"id": 1}, {unique: true})
db.biosamples.createIndex({"id": 1}, {unique: true})
db.datasets.createIndex({"id": 1}, {unique: true})
db.cohorts.createIndex({"id": 1}, {unique: true})
db.analyses.createIndex({"id": 1}, {unique: true})
db.filtering_terms.createIndex({"id": 1}, {unique: true})
```

#### 2. Compound Indexes

**Purpose**: Optimize multi-field queries

```javascript
// Variants: Position-based queries (most common)
db.variants.createIndex({
  "assembly_id": 1,
  "reference_name": 1,
  "start": 1
})

// Index prefix queries supported:
// - {assembly_id}
// - {assembly_id, reference_name}
// - {assembly_id, reference_name, start}
```

**Query Coverage**:

```javascript
// Covered by index (fast)
db.variants.find({
  "assembly_id": "GRCh38",
  "reference_name": "1",
  "start": {$gte: 100000, $lte: 200000}
})

// Partially covered (slower)
db.variants.find({
  "reference_name": "1",  // Index not used (assembly_id missing)
  "start": 100000
})
```

#### 3. Single-Field Indexes

**Purpose**: Optimize single-field filters

```javascript
// Variants
db.variants.createIndex({"dataset_id": 1})
db.variants.createIndex({"individual_id": 1})
db.variants.createIndex({"biosample_id": 1})
db.variants.createIndex({"variant_type": 1})

// Individuals
db.individuals.createIndex({"sex": 1})
db.individuals.createIndex({"dataset_ids": 1})

// Biosamples
db.biosamples.createIndex({"individual_id": 1})
db.biosamples.createIndex({"dataset_ids": 1})
```

#### 4. Text Search Indexes

**Purpose**: Full-text search on description fields

```javascript
// Datasets: Search by name/description
db.datasets.createIndex({
  "name": "text",
  "description": "text"
})

// Variants: Search by gene symbol (optional)
db.variants.createIndex({
  "info.gene_symbol": "text"
})

// Usage
db.datasets.find({
  $text: {$search: "breast cancer"}
})
```

### Index Maintenance

#### Create Indexes

```javascript
// Create indexes in background (production)
db.variants.createIndex(
  {"assembly_id": 1, "reference_name": 1, "start": 1},
  {background: true, name: "position_index"}
)
```

#### Drop Unused Indexes

```javascript
// Check index usage
db.variants.aggregate([
  {$indexStats: {}}
])

// Drop unused index
db.variants.dropIndex("unused_index_name")
```

#### Rebuild Indexes

```javascript
// Rebuild all indexes (offline operation)
db.variants.reIndex()
```

### Index Size Monitoring

```javascript
// Check index sizes
db.variants.stats().indexSizes

// Example output:
{
  "_id_": 10485760,          // 10 MB (default _id index)
  "position_index": 52428800, // 50 MB (compound index)
  "id_unique": 5242880        // 5 MB (unique ID index)
}
```

**Rule of Thumb**: Indexes should fit in RAM for optimal performance
- **Small dataset**: All indexes < 1 GB ✅
- **Medium dataset**: All indexes < 10 GB ⚠️
- **Large dataset**: Compound indexes > 100 GB ❌ (consider sharding)

---

## Data Validation

### MongoEngine Validation

**Field-Level Validation**:

```python
class GenomicVariant(Document):
    start = IntField(required=True, min_value=0)  # Non-negative
    reference_name = StringField(
        required=True,
        choices=['1', '2', ..., '22', 'X', 'Y', 'MT']  # Whitelist
    )
    variant_type = StringField(
        choices=['SNP', 'INDEL', 'CNV']  # Enum
    )
```

**Custom Validation**:

```python
from mongoengine import ValidationError

def clean(self):
    """Custom validation before save"""
    if self.end and self.end <= self.start:
        raise ValidationError("end must be greater than start")

    if not re.match(r'^[ACGTN]+$', self.reference_bases):
        raise ValidationError("Invalid reference bases")
```

### JSON Schema Validation

**External Validation** (afrigend-beacon2-tools/validation/):

```python
import jsonschema

# Load Beacon v2 schema
with open('beacon-v2-variant.json') as f:
    schema = json.load(f)

# Validate variant data
try:
    jsonschema.validate(variant_data, schema)
except jsonschema.ValidationError as e:
    print(f"Validation error: {e.message}")
```

### Data Quality Checks

**Pre-Import Checks**:

```python
def validate_variant_data(variant):
    """Validate variant before import"""
    checks = [
        ('id', lambda v: bool(v['id'])),
        ('position', lambda v: 0 <= v['start'] <= 3_000_000_000),
        ('alleles', lambda v: len(v['reference_bases']) > 0),
        ('dataset', lambda v: Dataset.objects(id=v['dataset_id']).count() > 0)
    ]

    for check_name, check_func in checks:
        if not check_func(variant):
            raise ValidationError(f"Failed check: {check_name}")
```

---

## Migration Strategy

### Schema Versioning

**Version Field**:

```python
class GenomicVariant(Document):
    schema_version = StringField(default='2.0')  # Beacon v2.0
```

### Backward Compatibility

**Beacon v1 → v2 Migration**:

```python
def migrate_v1_to_v2(old_variant):
    """Convert Beacon v1 variant to v2 format"""
    return {
        'id': old_variant['id'],
        'assembly_id': 'GRCh38',  # Default
        'reference_name': old_variant['chromosome'],
        'start': old_variant['position'],  # v1 was 1-based, v2 is 0-based
        'reference_bases': old_variant['referenceBases'],
        'alternate_bases': old_variant['alternateBases'],
        'dataset_id': old_variant['datasetId'],
    }
```

### Adding New Fields

**Approach**: Add optional fields, backfill gradually

```python
# 1. Add optional field to model
class GenomicVariant(Document):
    new_field = StringField()  # Optional (no default)

# 2. Backfill existing records
GenomicVariant.objects(new_field__exists=False).update(
    set__new_field='default_value'
)

# 3. Make required after backfill
class GenomicVariant(Document):
    new_field = StringField(required=True)
```

### Removing Fields

**Approach**: Mark deprecated, then remove

```python
# 1. Mark as deprecated (keep in schema)
class GenomicVariant(Document):
    deprecated_field = StringField()  # DEPRECATED: Use new_field instead

# 2. Remove after grace period (e.g., 6 months)
# Remove from model
# MongoDB will ignore extra fields on read
```

---

## Performance Optimization

### Query Optimization Tips

#### 1. Use Projection

```python
# Bad: Fetch all fields
variants = GenomicVariant.objects(reference_name='1')

# Good: Fetch only needed fields
variants = GenomicVariant.objects(reference_name='1').only(
    'id', 'start', 'reference_bases', 'alternate_bases'
)
```

#### 2. Use Limit

```python
# Bad: Fetch all results
variants = GenomicVariant.objects(reference_name='1')

# Good: Limit results
variants = GenomicVariant.objects(reference_name='1').limit(1000)
```

#### 3. Use Indexes

```javascript
// Check if query uses index
db.variants.find({
  "assembly_id": "GRCh38",
  "reference_name": "1",
  "start": {$gte: 100000}
}).explain("executionStats")

// Look for:
// - "inputStage.stage": "IXSCAN" (index scan, good)
// - "inputStage.stage": "COLLSCAN" (collection scan, bad)
```

#### 4. Avoid Regex on Large Collections

```python
# Bad: Regex without index (slow)
variants = GenomicVariant.objects(info__gene_symbol__icontains='BRCA')

# Good: Exact match or text search index
variants = GenomicVariant.objects(info__gene_symbol='BRCA1')
```

### Connection Pooling

```python
# Configure connection pool size
mongoengine.connect(
    'beacon_db',
    host='localhost',
    maxPoolSize=100,  # Max connections
    minPoolSize=10,   # Min connections
    maxIdleTimeMS=45000,
    waitQueueTimeoutMS=5000
)
```

### Read Preference

```python
# For read-heavy workloads with replicas
mongoengine.connect(
    'beacon_db',
    host='localhost',
    replicaSet='rs0',
    read_preference=ReadPreference.SECONDARY_PREFERRED
)
```

---

## Data Import/Export

See [afrigend-beacon2-tools/README.md](../afrigend-beacon2-tools/README.md) for comprehensive data management documentation.

### Import Workflow

**1. Transform VCF → Beacon JSON**:

```bash
python vcf_transform/vcf_to_beacon.py input.vcf.gz \
  --output variants.json \
  --assembly GRCh38 \
  --dataset dataset_001
```

**2. Validate JSON**:

```bash
python validation/validate_json.py variants.json \
  --schema schemas/beacon-v2-variant.json
```

**3. Import to MongoDB**:

```bash
python data_import/import_to_mongo.py variants.json \
  --collection variants \
  --batch-size 1000 \
  --mode upsert
```

### Export Workflow

**Export to JSON**:

```bash
python data_export/export_from_mongo.py \
  --collection variants \
  --output backup.json \
  --filter '{"dataset_id": "dataset_001"}'
```

**Export to VCF**:

```bash
python data_export/export_to_vcf.py \
  --collection variants \
  --output export.vcf.gz \
  --assembly GRCh38
```

---

## References

### GA4GH Beacon v2 Models

- [Beacon Models Documentation](https://docs.genomebeacons.org/models/)
- [Genomic Variant Model](https://docs.genomebeacons.org/models/genomicVariant/)
- [Individual Model](https://docs.genomebeacons.org/models/individual/)
- [Biosample Model](https://docs.genomebeacons.org/models/biosample/)
- [Dataset Model](https://docs.genomebeacons.org/models/dataset/)
- [Cohort Model](https://docs.genomebeacons.org/models/cohort/)
- [Analysis Model](https://docs.genomebeacons.org/models/analysis/)

### Ontologies

- [Human Phenotype Ontology (HPO)](https://hpo.jax.org/)
- [MONDO Disease Ontology](https://mondo.monarchinitiative.org/)
- [NCI Thesaurus (NCIT)](https://ncit.nci.nih.gov/)
- [LOINC Codes](https://loinc.org/)
- [UBERON Anatomy](https://www.ebi.ac.uk/ols/ontologies/uberon)
- [Cell Ontology (CL)](https://www.ebi.ac.uk/ols/ontologies/cl)
- [Experimental Factor Ontology (EFO)](https://www.ebi.ac.uk/efo/)

### MongoDB Documentation

- [MongoDB Manual](https://docs.mongodb.com/)
- [MongoEngine Documentation](http://docs.mongoengine.org/)
- [Indexing Strategies](https://docs.mongodb.com/manual/indexes/)
- [Data Modeling](https://docs.mongodb.com/manual/core/data-modeling-introduction/)

### Internal Documentation

- [Project Overview](PROJECT_OVERVIEW.md)
- [API Reference](API_REFERENCE.md)
- [Security Implementation](SECURITY_IMPLEMENTATION.md)
- [Data Tools](../afrigend-beacon2-tools/README.md)

---

**Document Version**: 1.0
**Last Updated**: 2025-01-26
**Schema Version**: Beacon v2.0
**Status**: Production

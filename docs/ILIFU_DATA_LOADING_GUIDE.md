# Loading H3Africa Data into Beacon v2 on ILIFU

This guide walks through transforming real H3Africa genomic data into GA4GH Beacon v2 format and loading it into the production MongoDB instance.

## Architecture Overview

```
┌─────────────────────┐     ┌──────────────────┐     ┌───────────────────────┐
│  ILIFU Compute Node │     │  SSH Tunnel       │     │  Beacon Server        │
│                     │     │                   │     │  (<your-server-ip>)      │
│  VCF files          │────>│  localhost:27017  │────>│  MongoDB (Docker)     │
│  ↓                  │     │  ←→               │     │  ↓                    │
│  vcf_to_beacon.py   │     └──────────────────┘     │  Beacon API           │
│  ↓                  │                               │  ↓                    │
│  validate_json.py   │                               │  Frontend             │
│  ↓                  │                               └───────────────────────┘
│  import_to_mongo.py │
└─────────────────────┘
```

**Why ILIFU?** VCF transformation is compute-intensive (parsing millions of variants). ILIFU compute nodes provide the CPU, memory, and direct access to H3Africa reference data that this requires.

## Prerequisites

| Requirement | Details |
|---|---|
| ILIFU SSH access | `ssh slurm.ilifu.ac.za` |
| Beacon server SSH | `ssh <your-ssh-alias>` |
| Python 3.9+ | Available on ILIFU compute nodes |
| VCF data | `.vcf.gz` files in `/cbio/dbs/` or `/cbio/projects/` |

## Quick Start (Automated Pipeline)

The fastest path — a single script handles everything:

```bash
# 1. SSH into ILIFU
ssh slurm.ilifu.ac.za

# 2. Get a compute node (NEVER run on login node)
srun --pty --nodes=1 --ntasks-per-node=1 --cpus-per-task=4 \
     --mem=32G --time=7-0:0:0 --nodelist=compute-[205,209] bash

# 3. Run the pipeline
cd /cbio/users/mamana/afrigen-beacon-v2
./scripts/run_ilifu_pipeline.sh /path/to/h3africa.vcf.gz
```

### Pipeline Options

```bash
# With phenotype data
./scripts/run_ilifu_pipeline.sh /path/to/data.vcf.gz \
    --phenotypes /path/to/phenotypes.csv

# Transform + validate only (no MongoDB import)
./scripts/run_ilifu_pipeline.sh /path/to/data.vcf.gz --skip-import

# Custom assembly and output location
./scripts/run_ilifu_pipeline.sh /path/to/data.vcf.gz \
    --assembly GRCh37 \
    --output /scratch3/users/mamana/beacon_output

# Preview what will happen (no execution)
./scripts/run_ilifu_pipeline.sh /path/to/data.vcf.gz --dry-run

# Tune for large datasets
./scripts/run_ilifu_pipeline.sh /path/to/data.vcf.gz \
    --batch-size 10000 \
    --workers 4
```

## Step-by-Step Guide (Manual)

If you prefer to run each step individually for more control.

### Step 1: Get a Compute Node

```bash
ssh slurm.ilifu.ac.za

# Request interactive session with resources for VCF processing
srun --pty --nodes=1 --ntasks-per-node=1 --cpus-per-task=4 \
     --mem=32G --time=7-0:0:0 --nodelist=compute-[205,209] bash
```

**Resource guidance:**

| Dataset Size | CPUs | Memory | Notes |
|---|---|---|---|
| < 1M variants | 2 | 16G | Small panel / exome |
| 1-10M variants | 4 | 32G | Standard WGS |
| 10M+ variants | 8 | 64G | Large cohort VCF |

### Step 2: Install the Tools

```bash
cd /cbio/users/mamana

# Clone if not already present
git clone https://github.com/AfriGen-D/variant-checker-beacon.git
cd variant-checker-beacon/afrigend-beacon2-tools

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (setuptools<70 is required for django-mongoengine)
pip install --upgrade pip "setuptools<70" wheel
pip install -r requirements.txt

# Verify installation
python vcf_transform/vcf_to_beacon.py --help
python validation/validate_json.py --help
python data_import/import_to_mongo.py --help
```

**Troubleshooting installs:**
- `cyvcf2` requires `htslib` — usually available on ILIFU, but if not: `conda install -c bioconda cyvcf2`
- If `pip install` is slow, try: `pip install --no-cache-dir -r requirements.txt`

### Step 3: Locate H3Africa Data

```bash
# Common locations on ILIFU:
ls /cbio/dbs/refpanels/          # Reference panels (H3AR3b, H3AR6x)
ls /cbio/projects/               # Project data
ls /cbio/users/mamana/           # Your workspace

# Search for VCF files
find /cbio/dbs/ -name "*.vcf.gz" -type f 2>/dev/null | head -20
find /cbio/projects/ -name "*.vcf.gz" -type f 2>/dev/null | head -20

# Check a VCF file header to confirm assembly and samples
module load bcftools  # if available
bcftools view -h /path/to/file.vcf.gz | head -30
bcftools query -l /path/to/file.vcf.gz | wc -l   # count samples
```

### Step 4: Transform VCF to Beacon JSON

```bash
source /cbio/users/mamana/afrigen-beacon-v2/afrigend-beacon2-tools/.venv/bin/activate
cd /cbio/users/mamana/afrigen-beacon-v2/afrigend-beacon2-tools

python vcf_transform/vcf_to_beacon.py /path/to/h3africa.vcf.gz \
    --output /cbio/users/mamana/beacon_output/vcf_output \
    --assembly GRCh38 \
    --config config/settings.yaml \
    --verbose
```

**What this produces:**

| File | Description |
|---|---|
| `variants_batch.jsonl` | One JSON variant record per line (JSONL format) |
| `individuals.json` | Individual records derived from VCF sample names |
| `variant_genotypes.json` | Mapping of variants → individuals → genotypes |
| `transformation_summary.json` | Stats: variants processed/filtered, individuals found |

**Understanding the output:**

```text
// variants_batch.jsonl (one line per variant)
{"id": "1:100001:A:T", "assembly_id": "GRCh38", "reference_name": "1",
 "start": 100000, "end": 100001, "reference_bases": "A",
 "alternate_bases": "T", "variant_type": "SNV", "annotations": [...]}

// individuals.json
[{"id": "SAMPLE001", "sex": null, "ethnicity": null, ...}]
```

Note: `start` uses 0-based coordinates (VCF POS is 1-based, so `start = POS - 1`).

### Step 5: Transform Phenotype Data (Optional)

If you have clinical/phenotype data (CSV/TSV/XLSX):

```bash
python phenotype_transform/phenotype_to_beacon.py /path/to/phenotypes.csv \
    --output /cbio/users/mamana/beacon_output/phenotype_output \
    --individuals /cbio/users/mamana/beacon_output/vcf_output/individuals.json \
    --config config/settings.yaml \
    --verbose
```

**Expected input columns (flexible naming):**

| Standard Name | Also Accepts | Required? |
|---|---|---|
| `individual_id` | `sample_id`, `patient_id`, `subject_id` | Yes |
| `phenotype_id` | `hpo_id`, `term_id` | For phenotypes |
| `phenotype_label` | `phenotype_name`, `phenotype` | For phenotypes |
| `disease_id` | `mondo_id`, `ordo_id` | For diseases |
| `disease_label` | `disease_name`, `diagnosis` | For diseases |
| `observed` | `present`, `status` | No (defaults to true) |

The transformer auto-detects column names and normalizes them.

### Step 6: Validate

```bash
# Validate variants (strict mode = stop on first error)
python validation/validate_json.py \
    /cbio/users/mamana/beacon_output/vcf_output/variants_batch.jsonl \
    --schema-type variant --strict

# Validate individuals
python validation/validate_json.py \
    /cbio/users/mamana/beacon_output/vcf_output/individuals.json \
    --schema-type individual --strict

# Validate phenotypes (if generated)
python validation/validate_json.py \
    /cbio/users/mamana/beacon_output/phenotype_output/phenotypes.json \
    --schema-type phenotype --strict
```

**Validation checks:**
- Required fields present (`id`, `assembly_id`, `reference_name`, `start`, `end`, `reference_bases`, `alternate_bases` for variants)
- Correct data types (`start` is integer, `id` is string)
- Value ranges (`start >= 0`, valid chromosome names)

### Step 7: Import to Production MongoDB

MongoDB runs inside Docker on the beacon server (<your-server-ip>). You need an SSH tunnel.

```bash
# Terminal 1 (or use tmux/screen): Create SSH tunnel
ssh -f -N -L 27017:localhost:27017 <your-ssh-alias>

# Verify tunnel is up
nc -z localhost 27017 && echo "Tunnel OK" || echo "Tunnel FAILED"
```

```bash
# Terminal 2: Import data through the tunnel
MONGO_URI="mongodb://localhost:27017/"

# Import variants
python data_import/import_to_mongo.py \
    /cbio/users/mamana/beacon_output/vcf_output/variants_batch.jsonl \
    --db beacon_db --collection variants \
    --mongo-uri "$MONGO_URI" --verbose

# Import individuals
python data_import/import_to_mongo.py \
    /cbio/users/mamana/beacon_output/vcf_output/individuals.json \
    --db beacon_db --collection individuals \
    --mongo-uri "$MONGO_URI" --verbose

# Import phenotypes (if available)
python data_import/import_to_mongo.py \
    /cbio/users/mamana/beacon_output/phenotype_output/phenotypes.json \
    --db beacon_db --collection phenotypes \
    --mongo-uri "$MONGO_URI" --verbose
```

**Alternative: Copy files to beacon server and import locally**

```bash
# From ILIFU compute node:
scp -r /cbio/users/mamana/beacon_output \
    <your-ssh-alias>:~/

# SSH to beacon server:
ssh <your-ssh-alias>

# Import using mongoimport (via Docker)
docker exec -i beacon-mongodb mongoimport \
    --db beacon_db --collection variants \
    --type json --file /dev/stdin < ~/beacon_output/vcf_output/variants_batch.jsonl

docker exec -i beacon-mongodb mongoimport \
    --db beacon_db --collection individuals \
    --type json ~/beacon_output/vcf_output/individuals.json
```

### Step 8: Verify

```bash
# Flush Redis cache (old test data may be cached)
ssh <your-ssh-alias> \
    "docker exec beacon-redis redis-cli FLUSHDB"

# Check datasets endpoint
curl -s "http://<your-server-ip>:8000/api/datasets" | python -m json.tool

# Query a known variant
curl -s "http://<your-server-ip>:8000/api/g_variants?\
assemblyId=GRCh38&referenceName=1&start=100000&\
referenceBases=A&alternateBases=T" | python -m json.tool

# Check variant count in MongoDB
ssh <your-ssh-alias> \
    "docker exec beacon-mongodb mongosh beacon_db --eval 'db.variants.countDocuments({})'"

# Check individual count
ssh <your-ssh-alias> \
    "docker exec beacon-mongodb mongosh beacon_db --eval 'db.individuals.countDocuments({})'"
```

## Performance Tuning

### For Large H3Africa Datasets (>10M variants)

Edit `config/settings.yaml` or pass `--batch-size` / `--workers` to the pipeline script:

```yaml
processing:
  batch_size: 10000     # Process 10k variants per batch (up from 1000)
  max_workers: 4        # Match your --cpus-per-task SLURM allocation
  memory_limit: 8192    # 8GB per worker
```

### SLURM Resource Requests

```bash
# For large WGS cohort VCFs (100+ samples, 10M+ variants)
srun --pty --nodes=1 --ntasks-per-node=1 --cpus-per-task=8 \
     --mem=64G --time=3-0:0:0 bash

# For smaller exome/panel data
srun --pty --nodes=1 --ntasks-per-node=1 --cpus-per-task=2 \
     --mem=16G --time=1-0:0:0 bash
```

### Using Screen/Tmux for Long Runs

For large datasets that may take hours:

```bash
# Start a tmux session (persists if SSH disconnects)
tmux new -s beacon

# Run pipeline inside tmux
./scripts/run_ilifu_pipeline.sh /path/to/large.vcf.gz

# Detach: Ctrl+B then D
# Re-attach later: tmux attach -t beacon
```

## Troubleshooting

### Common Issues

**`cyvcf2` import error:**
```
ModuleNotFoundError: No module named 'cyvcf2'
```
Fix: Ensure the venv is activated (`source .venv/bin/activate`). If `cyvcf2` failed to install, try `pip install --no-cache-dir cyvcf2` or use conda.

**SSH tunnel refused:**
```
ssh: connect to host ... port 22: Connection refused
```
Fix: Verify your SSH config has the `<your-ssh-alias>` alias. Check `~/.ssh/config`.

**MongoDB connection timeout:**
```
pymongo.errors.ServerSelectionTimeoutError
```
Fix: Verify the SSH tunnel is active: `nc -z localhost 27017`. Re-create if needed.

**Validation errors on phenotype data:**
```
Record 42: 'sex' is not one of ['MALE', 'FEMALE', 'OTHER', 'UNKNOWN']
```
Fix: The individual schema expects uppercase sex values. Normalize your input data or adjust the schema.

**Out of memory on compute node:**
Fix: Request more memory (`--mem=64G`) or reduce batch size (`--batch-size 500`).

### Checking Pipeline Output

```bash
# Count lines in variants file
wc -l beacon_output/vcf_output/variants_batch.jsonl

# Peek at first variant
head -1 beacon_output/vcf_output/variants_batch.jsonl | python -m json.tool

# Check transformation summary
cat beacon_output/vcf_output/transformation_summary.json | python -m json.tool
```

## Tool Reference

| Tool | Purpose | Input | Output |
|---|---|---|---|
| `vcf_to_beacon.py` | VCF → Beacon JSON | `.vcf.gz` | `variants_batch.jsonl`, `individuals.json` |
| `phenotype_to_beacon.py` | Phenotypes → Beacon JSON | `.csv`/`.tsv` | `phenotypes.json`, `diseases.json` |
| `validate_json.py` | Validate against schemas | `.json`/`.jsonl` | PASS/FAIL report |
| `import_to_mongo.py` | Import to MongoDB | `.json`/`.jsonl` | Records in MongoDB |
| `export_from_mongo.py` | Export from MongoDB | MongoDB query | `.json` files |

## Verification Checklist

After completing the pipeline, verify:

- [ ] Tools installed and `--help` works
- [ ] VCF transformed without errors (check `transformation_summary.json`)
- [ ] Validation passes in strict mode
- [ ] Data imported to MongoDB (check counts)
- [ ] Beacon API returns results for real variants
- [ ] Frontend displays real datasets (not `[Test]` prefixed)
- [ ] Redis cache flushed

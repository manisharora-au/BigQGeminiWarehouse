# Terraform Infrastructure

This directory contains the complete infrastructure-as-code for the BigQuery Gemini Data Warehouse using a modular Terraform approach.

## Directory Structure

```
terraform/
├── main.tf                    # Root module configuration
├── variables.tf              # Input variables
├── outputs.tf               # Output values
├── providers.tf             # Provider configuration
├── terraform.tfvars.example # Configuration template
└── modules/                 # Reusable modules
    ├── apis/               # API enablement
    ├── storage/            # GCS buckets with lifecycle rules
    ├── bigquery/           # Datasets and governance tables
    ├── iam/                # Service accounts and IAM roles
    ├── networking/         # Pub/Sub topics and VPC controls
    ├── dataplex/           # Data lake and governance
    └── monitoring/         # Alerting and dashboards
```

## Seven Infrastructure Modules

1. **APIs** - Enables 15 required GCP APIs
2. **Storage** - Creates data lake buckets with 6 prefixes (inbox/, raw/, validated/, quarantine/, archive/, temp/)
3. **BigQuery** - Creates 4 datasets + governance tables
4. **IAM** - Creates 7 service accounts with least-privilege roles
5. **Networking** - Creates Pub/Sub topics and optional VPC Service Controls
6. **Dataplex** - Creates data lake with 3 zones for medallion architecture
7. **Monitoring** - Creates log-based metrics and alert policies

## Usage

1. Copy the example configuration:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your project values:
   ```hcl
   project_id           = "your-gcp-project-id"
   region              = "us-central1" 
   environment         = "dev"
   project_name        = "hackathon"
   organization_prefix = "yourorg"
   ```

3. Deploy the infrastructure:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

## Security Notes

- ✅ All sensitive files are excluded from git via `.gitignore`
- ✅ No hardcoded credentials in source code
- ✅ Service accounts use least-privilege IAM roles
- ✅ State files and `.tfvars` files are gitignored
- ✅ Example configuration provided for documentation

## Resource Naming

All resources follow the pattern: `{organization_prefix}-{project_name}-{environment}`

Example: `intelia-hackathon-dev-raw-data`
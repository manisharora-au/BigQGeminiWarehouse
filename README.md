# Generic Data Warehouse Infrastructure

A parameterized, reusable data warehouse infrastructure setup for GCP using Terraform and automated scripts.

## Quick Start

### 1. Configure Your Environment

Copy the example configuration:
```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your settings:
```hcl
project_id           = "your-gcp-project-id"
region              = "us-central1"
environment         = "dev"
project_name        = "datawarehouse"
organization_prefix = "mycompany"
```

### 2. Setup GCP Project

Run the automated setup script:
```bash
./scripts/setup-project-generic.sh \
  --project-id your-gcp-project-id \
  --project-name datawarehouse \
  --org-prefix mycompany \
  --environment dev
```

### 3. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## Configuration Options

### Required Variables

- `project_id` - Your GCP Project ID
- `project_name` - Base name for resources (e.g., "datawarehouse")
- `organization_prefix` - Your company/organization prefix (e.g., "acme")
- `region` - GCP region for resources
- `environment` - Environment name (dev/staging/prod)

### Optional Overrides

- `raw_dataset_name` - BigQuery raw dataset name (default: "raw_ext")
- `curated_dataset_name` - BigQuery curated dataset name (default: "curated")  
- `consumption_dataset_name` - BigQuery consumption dataset name (default: "consumption_marts")
- `service_account_name` - Custom service account name
- `raw_data_retention_days` - GCS lifecycle policy (default: 30 days)
- `labels` - Additional resource labels

## Generated Resources

The infrastructure creates resources with consistent naming:
- **GCS Bucket**: `{org-prefix}-{project-name}-{env}-raw-data`
- **BigQuery Datasets**: Configurable names with environment suffixes
- **Service Account**: `{org-prefix}-{project-name}-{env}-agent-sa`

## Examples

### Development Environment
```bash
./scripts/setup-project-generic.sh \
  -p my-dev-project \
  -n analytics \
  -o acme \
  -e dev
```

### Production Environment
```bash
./scripts/setup-project-generic.sh \
  -p my-prod-project \
  -n analytics \
  -o acme \
  -e prod \
  -r australia-southeast1
```

### Custom Service Account
```bash
./scripts/setup-project-generic.sh \
  -p my-project \
  -n dataplatform \
  -o company \
  -s custom-agent-sa
```

## Architecture

This creates a 3-layer data architecture:

1. **Raw Layer**: GCS bucket + BigQuery external tables
2. **Curated Layer**: BigQuery datasets for cleaned/transformed data
3. **Consumption Layer**: BigQuery data marts for analytics

All resources are labeled and follow consistent naming conventions for easy management and cost tracking.

## Security

- Service account follows principle of least privilege
- IAM roles limited to data operations only
- No administrative or billing permissions
- Credentials stored securely in `~/.gcp/credentials/`

## File Structure

```
├── terraform/
│   ├── main.tf           # Main infrastructure resources
│   ├── variables.tf      # All configuration variables  
│   ├── outputs.tf        # Output values for integration
│   └── providers.tf      # GCP provider configuration
├── scripts/
│   └── setup-project-generic.sh  # Automated project setup
├── terraform.tfvars.example      # Configuration template
└── README.md                     # This file
```
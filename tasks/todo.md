# Todo

- [/] Repository Sync & Infrastructure Overhaul
    - [x] Create 7 modular Terraform components
    - [x] Update architecture docs v3
    - [x] Create PROJECT_STATUS.md
    - [ ] Stage all changes for Git
    - [ ] Commit with summary message
    - [ ] Push to origin main
- [/] Mount GCS buckets as local folders
    - [/] Install `macFUSE` and `gcsfuse` (Waiting for sudo password)
    - [ ] Create mount points (`/intelia-hackathon-files` and `/intelia-hackathon-dev-raw-data`)
    - [ ] Mount buckets using `gcsfuse`

---

## Terraform Documentation Tasks (From Upstream)

The goal is to review and add comprehensive documentation/comments to the key Terraform configuration files to explain their purpose and internal components.

### Plan

- [x] `terraform/variables.tf`: Add inline documentation explaining the purpose, constraints, and usage of each input variable.
- [x] `terraform/main.tf`: Add module-level explanations and documentation detailing how each component (e.g., project API, storage, BigQuery, IAM, networking) fits into the overall architecture.
- [x] `terraform/outputs.tf`: Add descriptions summarizing each logical grouping of output values (project, storage, data components, etc.).
- [x] `terraform/providers.tf`: Add documentation describing the Terraform required version, required providers, and the primary Google provider configuration.
- [x] `terraform/terraform.tfvars.example`: Enhance the example file with step-by-step instructions and clearer explanations for the required vs. optional fields to guide new users.

---

## Completed Tasks History

- [x] Stage changes in `docs/solutions_architecture_v2.md` and `docs/image/`
- [x] Commit with message: "Update solutions architecture and images"
- [x] Push to origin main
- [x] Fix Mermaid diagram in `docs/solutions_architecture_v2.md`
- [x] Commit and push fix
- [x] Push current updates to GitHub (solutions architecture, git commands, and todo list)
- [x] Publish solutions architecture v3 and update todo.md
    - [x] Stage `docs/solutions_architecture_v3.md` and `tasks/todo.md`
    - [x] Commit with message: "Update solutions architecture v3 and todo list"
    - [x] Push to origin main
- [x] Pull latest changes from origin
    - [x] Stash local changes to `tasks/todo.md`
    - [x] Pull latest changes from origin main
    - [x] Pop stash and handle any conflicts in `tasks/todo.md`
- [x] Publish local changes to GitHub
    - [x] Stage and commit `docs/solutions_architecture_v3.md`
    - [x] Push all local commits to origin main

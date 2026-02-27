# Workflow: `sync_workflows.yml`

## 1. High-Level Overview & Purpose

The `sync_workflows.yml` file is a **"meta" workflow** designed for administrative and operational purposes. Its primary function is to enforce consistency and propagate updates to a predefined set of standard GitHub Actions workflow files across all relevant repositories within the `HIE-Elixir` GitHub organization.

It acts as a centralized management tool for the organization's CI/CD processes. By maintaining a single "source of truth" for common workflows, it ensures that all repositories are using the latest, most secure, and most efficient versions of these critical automations.

> **⚠️ WARNING: High-Impact Workflow**
> This workflow has the administrative power to automatically commit changes to the `main` branch of every repository in the organization that uses the managed workflows. It should be operated with **extreme caution** and only by authorized personnel. A faulty update to a template can break CI/CD pipelines across the entire organization. It is strongly recommended to use the manual `workflow_dispatch` trigger for supervised runs.

## 2. Core Components

-   **Workflow File:** otherWorkflows/sync_workflows.yml
-   **Source of Truth (Templates):** The `/workflow-templates/` directory within this repository. This directory contains the master copies of the workflows that are to be synchronized across the organization.
-   **Target Repositories:** All repositories within the `HIE-Elixir` GitHub organization that are found to contain one or more of the managed workflow files.

## 3. Workflow Breakdown (`sync_workflows.yml`)

### Trigger

-   **`push` to `main`**: The workflow runs automatically whenever a change is pushed to the `main` branch of this repository. This is a high-risk trigger and should be used with care.
-   **`workflow_dispatch`**: Allows for safe, manual execution from the GitHub Actions UI.

### Job: `check-repo-workflows`

This single, powerful job performs all the logic for checking and synchronizing the workflows.

-   **Runner**: `ebf-pod-ubuntu-latest@${{ github.run_id }}-check-repo-workflows`

#### Step 1: `Extract Version Number`

-   **Purpose**: To build a manifest of the correct, up-to-date versions for each managed workflow based on the local template files.
-   **Logic**:
    1.  It iterates through a hardcoded list of workflow filenames (e.g., `elixir-doc-generation.yml`, `external-link-check.yml`, etc.).
    2.  For each filename, it reads the corresponding file from the local `workflow-templates/` directory.
    3.  It uses `grep` and `sed` to parse the `VERSION:` field within the file's `env` block.
    4.  It constructs a JSON object that maps each workflow filename to its canonical version. This JSON object is then set as a job output (`steps.check_version.outputs.versions_json`) for use in the next step.

#### Step 2: `List organization repositories`

-   **Purpose**: This is the main engine of the workflow. It iterates through every repository in the organization, compares the versions of any managed workflows it finds, and updates them if they are out of date.
-   **Logic**:

    1.  **Repository Iteration**: It uses the GitHub API to fetch a list of all repositories in the `HIE-Elixir` organization, handling pagination to ensure a complete list.

    2.  **Workflow Discovery**: For each repository, it checks for the existence of a `.github/workflows` directory. If it exists, it checks if any of the files within it match the names of the managed workflows.

    3.  **Version Comparison (`_checkVersion`)**: If a managed workflow file is found in a target repository, the script:
        a. Reads the content of the remote file via the GitHub API.
        b. Extracts its `VERSION:` number.
        c. Compares this version to the correct version from the JSON manifest created in Step 1.
        d. If the versions do not match, or if the remote file is missing a version number, it flags the file to be updated.

    4.  **Conditional Deployment**: The script contains special logic to ensure CI/CD capabilities evolve together. For example:
        -   If it finds `elixir-updata-ditac-info.yml` in a repository but does *not* find `external-link-check.yml`, it will automatically add `external-link-check.yml` to that repository, deploying a new capability alongside an existing one.

    5.  **The Update Process (Git Data API)**: If any workflow needs to be updated or added, the script performs a series of direct Git operations using the GitHub API. This avoids the overhead of cloning each repository.
        a. **Create Blob**: It reads the new workflow content from the local `/workflow-templates/` directory and sends it to the target repository's `git/blobs` API endpoint. This creates a new file object in the repository's Git database and returns its unique SHA.
        b. **Create Tree**: It constructs a new Git tree object based on the branch's current tree. This new tree object includes the updated workflow file, pointing to the new blob SHA created in the previous step.
        c. **Create Commit**: It creates a new commit object that points to the new tree. A detailed commit message is generated automatically, listing exactly which workflows were updated and to which versions (e.g., `Update workflow files
- elixir-doc-generation.yml to v1.2.1`).
        d. **Update Ref**: In the final, critical action, it performs a `PATCH` request to the repository's `git/refs/heads/main` endpoint, moving the head of the `main` branch to point to the newly created commit. This makes the changes live in the target repository.

    6.  **Summary**: At the end of the run, the script prints a sorted list of all repositories that were modified.

## 4. Secrets

-   `HIE_SERVICE_GITHUB_TOKEN`: A GitHub Personal Access Token (PAT) or GitHub App token with `repo` scope (or more granularly, `contents: write`) for all repositories in the `HIE-Elixir` organization. The security of this secret is paramount to the security of the organization's codebase.

## 5. Operational Procedure

1.  **To Update a Workflow**: A developer modifies one of the workflow files in the `/workflow-templates/` directory and updates its `VERSION:` number.
2.  **Commit and Push**: The change is committed and pushed to the `main` branch of this repository.
3.  **Trigger Workflow**: The developer navigates to the "Actions" tab, selects the "Check Repository Workflows" workflow, and runs it manually using the `workflow_dispatch` trigger.
4.  **Monitor**: The developer monitors the workflow run, paying close attention to the log output to ensure the correct repositories are identified and updated as expected.
5.  **Verify**: After the run is complete, the developer can spot-check a few of the updated repositories to confirm that the new commit was created successfully and the workflow file content is correct.

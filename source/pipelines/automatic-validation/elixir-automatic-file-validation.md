---
title: Automated DITA Validation Pipeline (elixir-automatic-file-validation.yml)
category: automation
audience:
  - engineering-leaders
  - devops-engineers
  - content-architects
tags:
  - dita
  - ci-cd
  - github-actions
  - validation
  - content-governance
  - automation
summary: A fully automated GitHub Actions CI pipeline that validates DITA content, enforces metadata standards, performs DITA-OT dry-run validation, and synchronizes a centralized outputclass database.
status: published
---

# Automated DITA Validation Pipeline (elixir-automatic-file-validation.yml)

## 1. High-Level Overview & Purpose

The `elixir-automatic-file-validation.yml` workflow is a comprehensive and fully automated CI (Continuous Integration) pipeline for DITA-based documentation projects. Its primary purpose is to act as a quality gate, ensuring that all content adheres to a strict set of structural, metadata, and syntactical standards before it can be published. It runs automatically on every push and pull request to the `main` or `master` branch, providing immediate feedback to authors and maintainers.

The workflow performs a multi-stage validation process that includes:

1.  **Configuration Validation**: Ensures the project has a valid `elixir-settings.yml` file.
2.  **File & Attribute Validation**: Uses a custom Go application to perform deep validation of filenames, `outputclass` attributes, `rev` attributes, `xml:lang` attributes, and more.
3.  **DITA-OT Validation**: Executes a `dry run` of the DITA Open Toolkit (DITA-OT) to catch any syntactical or structural errors that would break the final publication.
4.  **Database Synchronization**: On successful validation of a push to the `main` branch, it automatically updates a centralized `outputclass` database with the latest information from the project.

This automated process is critical for maintaining the integrity of a large, multi-repository documentation ecosystem.

## 2. Core Components

-   **Workflow File:** elixir-automatic-file-validation.yml
-   **Project Configuration:** A mandatory `en-us/ExternalContent/elixir-settings.yml` file in the target repository that defines the project's language, root ditamap, and renaming strategy.
-   **Custom Validation Action:** A composite action (`HIE-ELIXIR/elixir-rename-validator`) that encapsulates the Go-based validation logic.
-   **Validation Utilities (Go):**
    -   [`Go Utility: fileValidator`](./file-validator.md): A detailed document explaining the comprehensive validation utility that checks for a wide range of content and metadata errors.
    -   [`Go Utility: fileRename`](./file-rename.md): A detailed document explaining the utility that handles file renaming based on `outputclass` and updates all internal cross-references.
-   **DITA-OT Action:** The standard `actions/doc-generation@elixir` action used for DITA-OT processing.
-   **Outputclass Database:** The `HIE-ELIXIR/outputclassDatabase` repository, which serves as a centralized database of all `outputclass` values used across the organization.

## 3. Workflow Breakdown (`elixir-automatic-file-validation.yml`)

### Trigger

The workflow is triggered by:

-   **`push`**: To the `main` or `master` branch, targeting changes within the `en-us/` directory.
-   **`pull_request`**: To the `main` or `master` branch, targeting changes within the `en-us/` directory.
-   **`workflow_dispatch`**: For manual runs.

### Job: `generate`

This single job contains all the logic for the validation pipeline.

-   **Runner**: `ebf-pod-ubuntu-latest@${{ github.run_id }}-elixir-doc-generation`

#### Steps

1.  **`Checkout`**: Checks out the primary repository containing the DITA source code.

2.  **`Checkout database repo`**: Checks out the `HIE-ELIXIR/outputclassDatabase` repository into a local `outputclassDatabase/` directory so that it can be updated if needed.

3.  **`Read settings`**: Reads the `en-us/ExternalContent/elixir-settings.yml` file and parses its key-value pairs (`language`, `ditamap`, `ditaval`, `rename_type`) into job outputs. The workflow fails if this file is not found.

4.  **`Set parameters`**: Consumes the outputs from the previous step, validates them to ensure no required settings are empty or invalid, and sets them as outputs for subsequent steps.

5.  **`Verify file existence`**: Checks that the `ditamap` and (if specified) `ditaval` files declared in the settings actually exist within the `en-us/` directory. The workflow fails if they do not.

6.  **`Validate outputclass and other attributes`**: This is the core custom validation step.
    -   It calls the composite action `HIE-ELIXIR/elixir-rename-validator@main`.
    -   This action executes the compiled Go utilities (`fileValidator` and `fileRename`) to perform the deep validation of the DITA files. See the specific design documents for [`Go Utility: fileValidator`](./file-validator.md) and [`Go Utility: fileRename`](./file-rename.md) for a full breakdown of the logic.
    -   The `SKIP_RENAME: true` input ensures that the action only performs validation and does not actually rename any files.

7.  **`Validate XML using DITAC`**: This step uses the standard DITA-OT action (`actions/doc-generation@elixir`) with `DRYRUN: true`. This invokes the DITA-OT pre-processing and validation without generating a full output, serving as a powerful final check for any syntax errors, broken cross-references, or other issues that would cause the publication to fail.

8.  **`Update database`**: (Conditional: runs only on `push` events) This step executes the `outputclassDatabase/update_databases.py` script. This Python script scans the project's source directory and updates the centralized database with any new or modified `outputclass` information.

9.  **`Commit and push database changes`**: (Conditional: runs only on `push` events) If the previous step resulted in any changes to the `outputclassDatabase` repository, this step commits and pushes them back to the `main` branch. It includes a retry loop with a `git pull --rebase` to handle potential race conditions if multiple validation workflows run simultaneously.

## 4. Secrets

-   `HIE_SERVICE_GITHUB_TOKEN`: A GitHub token with `contents: write` and `pull-requests: write` permissions for the source repository, as well as write access to the `HIE-ELIXIR/outputclassDatabase` repository.
-   `PDF_PWD_*`: Secrets for password-protecting PDF outputs, though they are not used in this workflow as it only performs a dry run.

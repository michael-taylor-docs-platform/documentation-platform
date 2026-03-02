---
title: GitHub Workflow - Elixir KB Article Publish Worker
category: pipeline
audience:
  - devops-engineers
  - solution-architects
  - engineering-leaders
tags:
  - ci-cd
  - github-actions
  - dispatcher-worker-pattern
  - dita
  - reference-processing
  - static-site
  - azure-blob-storage
  - api-integration
  - automation-scripts
project: enterprise-knowledge-lifecycle-platform
layer: platform
status: published
summary: Reusable GitHub Actions worker workflow that builds DITA documentation from a specific repository commit, performs differential blob deployment to Azure Storage, orchestrates asynchronous OHC API imports, and reports publication status back to the central dispatcher.
---

# GitHub Workflow - Elixir KB Article Publish Worker

**Parent Document:** [`GitHub KB Article Publishing Workflow`](./github-architecture.md)

This document provides a detailed breakdown of the `elixir-kbarticle-publish-worker.yml` reusable workflow. This is the DITA-OT publication engine, responsible for taking a prepared content repository, building the DITA content, and publishing it to the Online Help Center (OHC).

## I. Purpose and Model

-   **Purpose:** To execute a single, specific publication task. It takes a content repository at a specific commit, a set of publication parameters (language, format, destination, etc.), generates the documentation using DITA-OT, and handles the final publication to the OHC.
-   **Model:** This workflow is called by the `elixir-kbarticle-dispatcher.yml` orchestrator within a `strategy.matrix`. This means multiple instances of this worker can run in parallel for different languages or audiences.

## II. Inputs & Secrets

This workflow has a large number of inputs and secrets, reflecting its role as a highly configurable publication engine.

### Inputs

-   `PUB_JOB_ID` (string, required): A unique identifier for this specific publication run, passed from the dispatcher's matrix generation job.
-   `FORMAT` (string, required): The output format (e.g., `ASPX`, `HTML`, `PDF`).
-   `LANGUAGE` (string, required): The language of the content to be published.
-   `DITAMAP` (string, required): The path to the `.ditamap` file to be built.
-   `DITAVAL` (string, optional): The path to a `.ditaval` file for conditional content.
-   `PUBLISH_TO` (string, required): The target environment (`production` or `staging`).
-   `PUBLISH_LANGUAGE` (string, required): The GUID for the language in the OHC.
-   `PUBLISH_PRODUCT` (string, required): The GUID for the product in the OHC.
-   `PUBLICATION_INFO` (string, required): A JSON string containing publication details, including the resolved `location` (publication ID) from the OHC API.
-   `REPO_NAME` (string, required): The content repository to check out.
-   `COMMIT_SHA` (string, required): The specific commit SHA of the content repository to build from.

### Secrets

This workflow inherits all necessary secrets from the calling workflow.

## III. Job Breakdown

---

### 1. `generate_doc`

This job is responsible for the core DITA-OT documentation generation process.

-   **Runner:** `ebf-pod-ubuntu-latest@${{ github.run_id }}-elixir-doc-generation`

#### Outputs:

-   `PUBLICATION_ID` (string): The resolved publication ID from the OHC, extracted from the `PUBLICATION_INFO` input.

#### Steps:

1.  **`Log all workflow inputs`**: Prints all the received inputs for debugging purposes.
2.  **`Parse publication info`**: Extracts the `location` (the publication ID) from the `PUBLICATION_INFO` JSON input string and sets it as a job output.
3.  **`actions/checkout@v4`**: Checks out the specified `REPO_NAME` at the exact `COMMIT_SHA` provided.
4.  **`Set parameters`**: Sets up various environment variables and outputs based on the inputs, determining the `type` of build (`webhelp`, `pdf`, etc.) for the DITA-OT action.
5.  **`Dry-run validation`**: (Conditional) If the format is `ASPX`, it first runs the `actions/doc-generation` action with `DRYRUN: true` to validate the DITA content without producing a full build.
6.  **`Doc generation`**: Calls the `actions/doc-generation@test` action with `DRYRUN: false` to perform the full DITA-OT build. This action generates the final output (HTML, PDF, etc.) and creates an artifact named after the ditamap (e.g., `MyDitamap_GUID`).

---

### 2. `upload_generation_to_blob`

This job takes the generated documentation and uploads it to the appropriate Azure Blob Storage container.

-   **Runner:** `ebf-pod-ubuntu-latest@${{ github.run_id }}-elixir-check_previous_publication`
-   **Dependency:** `generate_doc`

#### Outputs:

-   `UPLOAD_STATUS` (string): `SUCCESS` or `FAILURE`.
-   `UPLOAD_MAP` (string): The path to the `publish.json` map file.

#### Steps:

1.  **`Set parameters`**: Determines the correct Azure Storage Connection String (`production` or `staging`) based on the `PUBLISH_TO` input.
2.  **`Determine Artifact Name`**: Creates the expected artifact name based on the input `DITAMAP` name.
3.  **`Download specific artifact`**: Downloads the documentation artifact created by the `generate_doc` job.
4.  **`Clone artifacts`**: Extracts the contents of the downloaded artifact (e.g., unzips the webhelp package).
5.  **`Download generated files from the Azure Blob`**: Downloads the *previous* version of the publication from the blob container. This is part of a diffing process.
6.  **`Commit previous files`**: Commits the downloaded previous version into a temporary local git repository.
7.  **`Check modified files`**: Copies the newly generated files over the old ones and uses `git status` to identify which `.html` files have actually changed. It creates a `modify.json` file listing these changed files.
8.  **`Upload files to Azure blob storage`**: Uses the `HIE-ELIXIR/elixir-publish-action@v1.0` action to upload the newly generated content to the Azure Blob Storage container for the OHC.
9.  **`Show uploading result`**: Checks the output of the upload action and fails the job if the upload was not successful.

---

### 3. `publish`

This job triggers the final import process within the Online Help Center (OHC).

-   **Runner:** `ebf-pod-ubuntu-latest@${{ github.run_id }}-elixir-upload-doc-to-blob`
-   **Dependencies:** `generate_doc`, `upload_generation_to_blob`
-   **Condition:** Runs only if the `UPLOAD_STATUS` from the previous job was `SUCCESS`.

#### Outputs:

-   `PUBLISH_RESULT` (string): `SUCCESS` or `FAILURE`.

#### Steps:

1.  **`Set environments`**: Determines the correct OHC API endpoints (`production` or `staging`) based on the `PUBLISH_TO` input.
2.  **`Publish document to D365`**: Sends a `POST` request to the OHC "Import KB" API endpoint. This API call starts an asynchronous import process on the OHC side and returns a `statusQueryGetUri`.
3.  **`Check status of importing document to D365`**: Enters a `while` loop that polls the `statusQueryGetUri` every 10 seconds. It waits until the `runtimeStatus` returned by the API is either `Completed` or `Failed`.
4.  **`Update D365 KB status`**: If the import was successful, it sends another `POST` request to the OHC "Update KB Status" API to set the publication's status to `Active`.
5.  **`Check D365 KB update status`**: Enters another `while` loop to poll the status of the update request, similar to the import check.
6.  **`Publish Result`**: Downloads the final `publish.json` manifest from the blob storage and sets the job output `PUBLISH_RESULT` to `SUCCESS`.
7.  **`Upload Publish Information`**: Uploads the downloaded `publish.json` as an artifact for downstream summary jobs.

---

### 4. `report-status`

This final job reports the overall success or failure of this specific worker instance back to the main dispatcher workflow.

-   **Runner:** `ebf-pod-ubuntu-latest@${{ github.run_id }}-elixir-status-reporter`
-   **Dependency:** `publish`
-   **Condition:** `if: always()`

#### Steps:

1.  **`Determine Final Status`**: Checks the `result` of the `publish` job and sets a `FINAL_STATUS` variable to `success` or `failure`.
2.  **`Create Result JSON`**: Creates a simple `result.json` file containing the `pub_job_id` for this worker instance and its final `status`.
3.  **`Upload Result Artifact`**: Uploads the `result.json` file as an artifact named `result-${{ inputs.PUB_JOB_ID }}`. The main dispatcher workflow will download all such artifacts to determine the overall outcome of the entire run.

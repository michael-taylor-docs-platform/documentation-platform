---
title: GitHub Workflow - KB Article Dispatcher
category: pipeline
audience:
  - engineering-leaders
  - devops-engineers
  - solution-architects
tags:
  - ci-cd
  - github-actions
  - workflow-orchestration
  - dispatcher-worker-pattern
  - automation-scripts
  - sharepoint
project: enterprise-knowledge-lifecycle-platform
layer: platform
status: published
summary: Central GitHub Actions dispatcher workflow that identifies approved and archived SharePoint articles, prevents race conditions via immediate status updates, dynamically constructs publication matrices, orchestrates parallel worker executions, aggregates results, and synchronizes final publishing outcomes back to the CMS.
---

# GitHub Workflow - KB Article Dispatcher

**Parent Document:** [`GitHub KB Article Publishing Workflow`](./github-architecture.md)

This document provides a detailed breakdown of the `elixir-kbarticle-dispatcher.yml` workflow, which acts as the central orchestrator for the Knowledge Base publishing process.

## I. Trigger and Purpose

-   **Trigger:** The workflow can be triggered in two ways:
    1.  **Scheduled:** It runs automatically every hour (`cron: '0 * * * *'`).
    2.  **Manual:** It can be triggered manually via `workflow_dispatch`.
-   **Purpose:** To identify recently approved or archived articles in SharePoint, dispatch them to the appropriate content processing and publication workflows, and handle the final status updates based on the results.

## II. Job Breakdown

The workflow is composed of several sequential and parallel jobs.

---

### 1. `gather-and-sort-changes`

This is the first and most critical job, responsible for identifying all articles that require processing.

-   **Runner:** `ebf-pod-ubuntu-latest@${{ github.run_id }}-kb-gatherer`
-   **Purpose:** To query SharePoint for new/updated articles and recently archived articles, sort them by audience (Internal/Public), and pass the results to downstream jobs.

#### Outputs:

-   `has_internal_changes` (boolean): `true` if changes for the "Internal" audience were found.
-   `has_external_changes` (boolean): `true` if changes for the "Public" audience were found.
-   `archives_list_id` (string): The SharePoint list ID for the `Knowledge Base Article Archive`.
-   `updates_list_id` (string): The SharePoint list ID for the `Knowledge Base Articles` list.

#### Steps:

1.  **`actions/checkout@v4`**: Checks out the repository to access local actions.
2.  **`Get Microsoft Graph API token`**: Calls the reusable `.github/actions/get-graph-token` action to get an authentication token for the Microsoft Graph API.
3.  **`Get List IDs and Timestamps`**:
    -   Uses `curl` to make a GET request to the Graph API to list all SharePoint lists.
    -   Uses `jq` to parse the JSON response and extract the IDs for the "Knowledge Base Articles" and "Knowledge Base Article Archive" lists.
    -   Generates timestamps for "yesterday" and "now" to use in subsequent queries.
    -   Outputs the list IDs and timestamps for other steps in the job.
4.  **`Query for New and Updated Articles`**:
    -   Uses `curl` to query the "Knowledge Base Articles" list.
    -   The query filters for items where:
        -   `Status` (`field_4`) is `Approved`.
        -   `Publish On Date` (`field_15`) is less than or equal to the current time (`now_iso`).
    -   Saves the JSON response to `updates.json`.
5.  **`Query for Recently Archived Articles`**:
    -   Uses `curl` to query the "Knowledge Base Article Archive" list.
    -   The query filters for items where:
        -   `Unpublished` is `false`.
        -   `Status` (`field_4`) is `Published`.
        -   `IsLatestVersion` is `true`.
    -   Saves the JSON response to `archives.json`.
6.  **`Sort and Group Changes`**:
    -   Uses `jq` to combine `updates.json` and `archives.json` into a single array.
    -   Adds a `change_type` (`update` or `archive`) to each item.
    -   Filters the combined array into two new files based on the `Audience` (`field_6`):
        -   `internal-changes.json` (Audience is "Internal")
        -   `public-changes.json` (Audience is "Public")
    -   Sets the `has_internal_changes` and `has_external_changes` outputs based on whether these files contain data.
7.  **`Upload Change Data as Artifact`**: Uploads `internal-changes.json` and `public-changes.json` as a build artifact named `change-data`.

---

### 2. `set-status-to-publishing`

This job prevents race conditions by immediately marking articles as "in progress".

-   **Runner:** `ebf-pod-ubuntu-latest@${{ github.run_id }}-kb-status-updater`
-   **Dependency:** `gather-and-sort-changes`
-   **Condition:** Runs only if `has_internal_changes` or `has_external_changes` is `true`.
-   **Purpose:** To update the status of all newly identified articles in SharePoint from "Approved" to "Publishing..." to ensure they are not processed by a subsequent workflow run.

#### Steps:

1.  **`actions/checkout@v4`**: Checks out the repository.
2.  **`Get Microsoft Graph API token`**: Acquires a Graph API token.
3.  **`Download Change Data Artifact`**: Downloads the `change-data` artifact.
4.  **`Update status to 'Publishing...'`**:
    -   Combines the `internal-changes.json` and `public-changes.json` files.
    -   Extracts the SharePoint item IDs for all items with `change_type: "update"`.
    -   Loops through the IDs and sends a `PATCH` request to the Graph API for each item, updating its `Status` (`field_4`) to "Publishing...".

---

### 3. `process-internal-repo` & `process-external-repo`

These two jobs run in parallel and are responsible for processing the content for each audience.

-   **Dependencies:** `gather-and-sort-changes`, `set-status-to-publishing`
-   **Condition:** Each job runs only if its corresponding `has_..._changes` flag is `true`.
-   **Purpose:** To call the reusable `process-kb-repo.yml` workflow, which handles the logic for checking out the content repository, converting HTML to DITA, handling images, and committing the changes.

#### Inputs to Reusable Workflow:

-   `repo-name`: The name of the target content repository (e.g., `HIE-ELIXIR/KnowledgeBaseArticles-Internal`).
-   `audience`: The audience (`internal` or `public`).
-   `change-data-artifact-name`: The name of the artifact containing the change data (`change-data`).
-   `service-acct-token`: The GitHub token for the service account.
-   `graph-api-token`: The Microsoft Graph API token.
-   `runner-prefix`: The prefix for the runner name.

---

### 4. `prepare-public-matrix` & `prepare-internal-matrix`

These jobs generate the dynamic strategy matrix that the publication worker jobs will use.

-   **Dependencies:** `gather-and-sort-changes` and the corresponding `process-...-repo` job.
-   **Condition:** Each job runs only if its corresponding `has_..._changes` flag is `true`.
-   **Purpose:** To create a JSON matrix of publication jobs based on the languages and audiences of the changed articles and the configuration in `.github/config/publish-params.json`. It also reconciles configuration errors and generates a manifest mapping SharePoint IDs to publication jobs.

#### Outputs:

-   `matrix` (json): The strategy matrix for the worker jobs.
-   `has_config_errors` (boolean): `true` if any articles could not be mapped to a publication due to missing configuration.

#### Steps:

1.  **`Checkout workflow repo to read config`**: Checks out the repository.
2.  **`Download Change Data`**: Downloads the `change-data` artifact.
3.  **`Generate Matrix and Reconcile Config Errors`**:
    -   Reads the `publish-params.json` config file and the appropriate `...-changes.json` file.
    -   Identifies the unique combinations of audience and language from the changed articles.
    -   For each combination, it finds the corresponding parameters in the config file.
    -   It calls the OHC "Create Publication" API to get a resolved publication ID.
    -   It constructs a **manifest** that maps the SharePoint IDs to a generated `pub_job_id`.
    -   It constructs the final **matrix** entry, including all parameters needed by the worker job.
    -   It compares the input SharePoint IDs with the IDs in the final manifest to find **orphans** (articles with no matching configuration).
    -   If orphans are found, it sets `has_config_errors` to `true` and creates a `...-config-errors.json` artifact.
4.  **`Upload ... Manifest Artifact`**: Uploads the generated manifest file (e.g., `public-manifest.json`).
5.  **`Upload ... Config Errors Artifact`**: If errors were found, uploads the config errors file.

---

### 5. `call-public-worker` & `call-internal-worker`

These jobs execute the actual publication process based on the matrix generated in the previous phase.

-   **Dependencies:** `gather-and-sort-changes`, and the corresponding `prepare-...-matrix` job.
-   **Condition:** Each job runs only if its corresponding `has_..._changes` flag is `true`.
-   **Strategy:** `fail-fast: false` with a matrix strategy that includes the JSON output from the `prepare-...-matrix` job.
-   **Purpose:** To call the reusable `elixir-kbarticle-publish-worker.yml` workflow for each entry in the strategy matrix.

---

### 6. `processing-complete`

This is a simple anchor job to ensure the workflow proceeds to the results processing stage, even if one of the publication branches fails or is skipped.

-   **Runner:** `ebf-pod-ubuntu-latest@${{ github.run_id }}-kb-anchor`
-   **Dependencies:** `call-public-worker`, `call-internal-worker`
-   **Condition:** `if: always()`
-   **Purpose:** To act as a synchronization point, allowing the workflow to reliably proceed to the `process-results` job.

---

### 7. `process-results`

This job aggregates the results from all the parallel publication worker jobs.

-   **Runner:** `ebf-pod-ubuntu-latest@${{ github.run_id }}-elixir-result-processor`
-   **Dependencies:** `gather-and-sort-changes`, `processing-complete`, `prepare-public-matrix`, `prepare-internal-matrix`
-   **Condition:** Runs `if: always()` as long as there were changes to process.
-   **Purpose:** To download all `result.json` artifacts from the worker jobs, combine them, and determine the `overall_status` of the publication phase.

#### Outputs:

-   `overall_status` (string): `success` or `failure`.

---

### 8. `handle-publishing-failure`

This is the centralized error handler for the entire workflow.

-   **Runner:** `ebf-pod-ubuntu-latest@${{ github.run_id }}-kb-failure-handler`
-   **Dependencies:** All major processing and publication jobs.
-   **Condition:** A complex `if: always()` condition that triggers if any of the upstream jobs failed, reported failures in their outputs, or if the `overall_status` is a failure.
-   **Purpose:** To consolidate all known errors from every stage of the workflow (content processing, configuration, publication), and update the corresponding SharePoint items with a "Publishing Failed" status and a specific error message.

---

### 9. `update-sharepoint-status`

This job marks archived articles as "Unpublished" in SharePoint.

-   **Runner:** `ebf-pod-ubuntu-latest@${{ github.run_id }}-kb-updater`
-   **Dependencies:** `gather-and-sort-changes`, `process-internal-repo`, `process-external-repo`, `process-results`
-   **Condition:** Runs only if the `overall_status` from `process-results` is `success`.
-   **Purpose:** To clean up successfully processed archives by setting their `Unpublished` flag to `true` in the SharePoint archive list.

---

### 10. `set-status-to-published`

This job marks successfully published articles with their final status.

-   **Runner:** `ebf-pod-ubuntu-latest@${{ github.run_id }}-kb-finalizer`
-   **Dependencies:** `gather-and-sort-changes`, `process-results`
-   **Condition:** Runs `if: always()` as long as there were changes.
-   **Purpose:** To correlate the successful publication jobs with the original SharePoint items and update their status to "Published" or "Published - Image errors", providing a clear, final status to the content authors.

---

### 11. `prepare-state` & `prepare_summary_matrix` & `dispatch-summaries`

These final jobs handle the post-publication summary generation and synchronization with an external system.

-   **`prepare-state`**: Downloads the current state from an Azure Blob Storage container.
-   **`prepare_summary_matrix`**: Creates a new strategy matrix based on the successful publications, preparing the inputs for the final summary and sync job.
-   **`dispatch-summaries`**: Calls the `reusable-summarize-and-sync.yml` workflow for each successful publication to generate summaries and push them to an Azure Service Bus queue.

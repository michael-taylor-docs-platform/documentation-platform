# Reusable Workflow: `reusable-summarize-and-sync.yml`

**Parent Document:** [`GitHub KB Article Publishing Workflow`](./github-architecture.md)

This document provides a detailed breakdown of the `reusable-summarize-and-sync.yml` reusable workflow. This workflow is the final stage in the publication pipeline, responsible for post-processing, summary generation, and state synchronization.

## I. Purpose and Model

-   **Purpose:** To take the results of a successful publication, update the consolidated state of the knowledge base, and trigger an external process by sending a message to a service bus. It handles both new/updated articles and the removal of archived articles.
-   **Model:** This workflow is called by the `dispatch-summaries` job in the main `elixir-kbarticle-dispatcher.yml` workflow. It is triggered for each successful publication, identified by a unique combination of audience and language.

## II. Inputs & Secrets

### Inputs

-   `language` (string, required): The language of the publication (e.g., `en-us`).
-   `audience` (string, required): The audience of the publication (`internal` or `public`).
-   `html_artifact_name` (string, required): The name of the artifact containing the generated HTML files for the publication.
-   `publish_info_artifact_name` (string, required): The name of the artifact containing the `publish.json` file.
-   `repo_name` (string, required): The name of the source content repository.
-   `commit_sha` (string, required): The commit SHA that the publication was built from.
-   `has_met_files` (string, required): A boolean flag (`'true'` or `'false'`) indicating if partial `.met` files were generated for this run.

### Secrets

-   `HIE_SERVICE_GITHUB_TOKEN`: The service account token for GitHub operations.
-   `KB_SUMMARY_STORAGE_CONNECTION_STRING`: Connection string for the Azure Blob Storage account where the final state is stored.
-   `KB_SUMMARY_STORAGE_CONTAINER`: The name of the container within the storage account.
-   `COMPANION_SERVICE_BUS_NAMESPACE`: The namespace of the Azure Service Bus.
-   `COMPANION_SERVICE_BUS_QUEUE_NAME`: The name of the queue to which the final message will be sent.
-   `COMPANION_SERVICE_BUS_SAS_POLICY_NAME`: The SAS policy name for the service bus.
-   `COMPANION_SERVICE_BUS_SAS_TOKEN`: The SAS token for the service bus.

## III. Job Breakdown

The workflow consists of a single job, `summarize-and-sync`.

-   **Runner:** `ebf-pod-ubuntu-latest@${{ github.run_id }}-${{ inputs.language }}-summarize` (Dynamically named runner).

### Steps:

1.  **`Set Publication Path & Create Staging Directory`**: 
    -   Constructs a `PUBLICATION_PATH` (e.g., `public-publication/en-us`) which represents the folder structure in the Azure Blob Storage container.
    -   Creates a clean, local `publication-staging` directory to assemble the final state before uploading.

2.  **`Download current state artifact`**: Downloads the `current-azure-state` artifact, which contains a snapshot of the entire blob container from the beginning of the workflow run.

3.  **`Prepare Initial State from Artifact`**: 
    -   Checks if a folder matching the `PUBLICATION_PATH` exists within the downloaded state artifact.
    -   If it exists, it copies the contents into the `publication-staging` directory. This seeds the staging area with the last known state for this specific publication (audience/language).
    -   If not, it starts with an empty staging directory.

4.  **`Download change-data artifact`**: Downloads the `change-data` artifact containing the `internal-changes.json` and `public-changes.json` files.

5.  **`Download HTML artifact`**: Downloads the artifact containing the newly generated HTML files for this publication, specified by `inputs.html_artifact_name`.

6.  **`Unzip HTML artifact`**: Unzips the downloaded HTML artifact into a `new-html` directory.

7.  **`Process Archived Articles`**: 
    -   Reads the appropriate `...-changes.json` file.
    -   Filters for articles with `change_type == "archive"` that match the current job's language.
    -   For each archived article, it deletes the corresponding `.md`, `.html`, and `.MET` files from the `publication-staging` directory.

8.  **`Setup Tools for New/Updated Articles`**: Installs `pandoc` and downloads a custom tool (`beautifulGoose`) needed for HTML-to-Markdown conversion.

9.  **`Convert HTML to Markdown`**: Uses the `beautifulGoose` tool to convert the newly generated HTML files from the `new-html` directory into Markdown files in a `new-markdown` directory.

10. **`Bulk Copy New/Updated Files`**: Copies all `.md` files from `new-markdown` and all `.html` files from the unzipped `new-html` directory into the `publication-staging` directory. This overwrites any existing files with the newly generated content.

11. **`Download Partial MET files`**: (Conditional) If `inputs.has_met_files` is `'true'`, it downloads the `partial-met-files` artifact.

12. **`Finalize MET Files`**: (Conditional) If MET files were downloaded:
    -   It iterates through every `.md` file in the staging directory.
    -   It extracts the `canonical_id` from the markdown filename.
    -   It looks for a corresponding `${canonical_id}.MET` file in the downloaded `partial-met-files` directory.
    -   If found, it uses `jq` to inject the full content of the `.md` file into the `.content` field of the MET file, saving the result as the final `.MET` file in the staging directory.

13. **`Sync Final State to Azure`**: 
    -   First, it deletes all existing blobs under the target `PUBLICATION_PATH` in the Azure container to ensure a clean slate.
    -   Then, it performs a batch upload of all files from the local `publication-staging` directory into the target `PUBLICATION_PATH` in the container.

14. **`Send Summary Message`**: 
    -   (Conditional) Runs only if the Azure sync was successful.
    -   Uses the `HIE-ELIXIR/doc-summary-caller-actions@v1.0.0` action.
    -   This action sends a message to the configured Azure Service Bus queue. The message contains the path to the folder in the blob container that was just updated, signaling to an external system that a new summary is ready for processing.

15. **`Upload Staging Directory as Artifact`**: 
    -   (Conditional) `if: always()`.
    -   Uploads the final contents of the `publication-staging` directory as an artifact (e.g., `final-summary-public-en-us`). This is for debugging and archival purposes.

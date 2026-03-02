# Go Utility: `fileValidator`

**Parent Document:** [`Workflow: elixir-automatic-file-validation.yml`](./elixir-automatic-file-validation.md)

---

## 1. High-Level Overview & Purpose

The `fileValidator` is a powerful, command-line Go utility that serves as the primary engine for quality control within the `elixir-automatic-file-validation.yml` workflow. Its purpose is to perform a deep and comprehensive scan of a DITA project's source files and report on a wide range of potential errors, from metadata inconsistencies to structural problems.

It is designed to be run from the command line and accepts a directory path as input. It recursively walks the directory and generates a series of log files and JSON reports detailing any issues it finds. If any critical errors are detected, it exits with a non-zero status code, which causes the parent GitHub Actions workflow to fail.

## 2. Command-Line Arguments

-   `-dir` (string, required): The path to the target directory that contains the DITA source files (e.g., `en-us/`).
-   `-legacyRenaming` (boolean, optional): A flag that, when set to `true`, disables certain validation checks (like the `outputclass` length check and "What's New" validation) that are not relevant for projects using an older file naming convention.

## 3. Validation Checks Performed

The utility performs an extensive list of checks, which can be categorized as follows:

### a. Filename and Identifier Validation

-   **Filename Structure**: Checks that every filename contains at least one `=` character, which is a fundamental part of the file naming convention.
-   **GUID/Timestamp Validity**: For each filename, it extracts the unique identifier (either a GUID or a 14-digit timestamp) that follows the `=` and validates it. It ensures the identifier is either a correctly formatted GUID or a valid 14-digit timestamp.
-   **Duplicate GUIDs/Timestamps**: It scans all files in the project and identifies any instances where the same GUID or timestamp is used in more than one filename (excluding cases where they are different versions of the same article). This is critical for preventing ID collisions.
-   **Duplicate Filenames**: It checks if there are any files with the exact same name located in different subdirectories within the project, which could cause ambiguity or build failures.

### b. XML Attribute and Content Validation

-   **Missing `outputclass`**: It parses every `.xml` and `.dita` file and ensures that the `<title>` element contains an `outputclass` attribute. Files missing this attribute are logged.
-   **Duplicate `outputclass`**: It aggregates all `outputclass` values across the entire project. If the same `outputclass` is found in multiple files, it identifies this as a duplication error. It intelligently uses the `rev` attribute to determine which file is the "original" (the one with the oldest revision timestamp).
-   **Long `outputclass`**: It checks if any `outputclass` value is 36 characters or longer and logs these instances, as they can cause issues with downstream publishing systems.
-   **Missing `xml:lang`**: It verifies that every `.xml`, `.dita`, and `.ditamap` file contains a valid `xml:lang="<language-code>"` attribute somewhere in its content.
-   **Missing `rev` Attribute**: It checks that the `<title>` element in every `.xml` and `.dita` file contains a `rev` attribute with a valid 14-digit timestamp, which is essential for version tracking.

### c. "What's New" Feature Validation

This is a special set of checks specifically for `<data>` elements that are used to define "What's New" entries.

-   **Element Discovery**: It finds all `<data outputclass="WhatsNew">` elements in the project.
-   **Attribute Validation**: For each of these elements, it validates the following attributes:
    -   `product`: Must not be empty or the default "Select...".
    -   `rev`: Must be a valid date in `YYYY-MM-DD` format.
    -   `platform`: Must not be empty or the default "Select...".
    -   `props`: Must not be empty or the default "Select...".
-   Any element that fails these checks is added to a detailed JSON error report.

## 4. Output Artifacts

The utility does not modify any files directly. Instead, it generates a series of log files and JSON reports in the root directory where it is run. If a specific type of error is not found, the corresponding log file is not created.

-   **`filenameErrors.log`**: A simple list of files that fail the basic filename structure validation.
-   **`longFileNames.log`**: A log of files whose `outputclass` attribute is too long.
-   **`outputclassMissing.log`**: A list of files that are missing the `outputclass` attribute in their `<title>`.
-   **`langAttributeMissing.log`**: A list of files missing the `xml:lang` attribute.
-   **`revMissing.log`**: A list of files missing the `rev` attribute in their `<title>`.
-   **`WhatsNewErrors.json`**: A detailed JSON report of all `<data outputclass="WhatsNew">` elements that have missing or invalid attributes.
-   **`duplicateGUIDs.json`**: A JSON report listing all GUIDs or timestamps that were found in multiple filenames, along with the paths to those files.
-   **`outputclassDuplicates.json`**: A JSON report listing all `outputclass` values that were found in multiple files. For each duplicate, it provides a list of the conflicting files and identifies which one is the "original" based on its revision timestamp.
-   **`duplicateFiles.json`**: A JSON report listing any files that have the same name but exist in different locations within the project.

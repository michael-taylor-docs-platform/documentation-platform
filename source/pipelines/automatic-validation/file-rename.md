# Go Utility: `fileRename`

**Parent Document:** [`Workflow: elixir-automatic-file-validation.yml`](./elixir-automatic-file-validation.md)

---

## 1. High-Level Overview & Purpose

The `fileRename` utility is a specialized command-line tool written in Go. It is designed to solve a very specific problem in DITA content management: ensuring that filenames are programmatically aligned with their content, and that all links within the project are updated to reflect these changes. This creates a more predictable and maintainable file structure where the filename is directly derived from its primary metadata.

The utility operates in two distinct phases:

1.  **Renaming Phase**: It scans all `.xml` and `.dita` files, extracts the `outputclass` attribute from their `<title>` tag, and renames the file to match that `outputclass` value.
2.  **Reference Update Phase**: After all files have been renamed, it re-scans the entire project (including `.ditamap` files) and performs a search-and-replace to update any cross-references (`<xref>`), topic references (`<topicref>`), or other links that pointed to the old filenames.

This two-phase approach ensures that the renaming process does not break the integrity of the DITA project's link structure.

## 2. Command-Line Arguments

-   `-dir` (string, required): The path to the target directory that contains the DITA source files (e.g., `en-us/`).
-   `-verbose` (boolean, optional): When set to `true`, it enables detailed logging, printing a message for every file that is renamed and every file in which references are updated.

## 3. Core Logic & Execution Flow

The `main` function orchestrates the entire two-phase process.

### Phase 1: File Discovery and Renaming

1.  **Gather Files**: The `findFiles()` function is called to recursively walk the directory specified by the `-dir` flag and create a complete, sorted list of all files.

2.  **Iterate and Rename**: The script iterates through the file list.
    a. It processes only files with `.xml` or `.dita` extensions.
    b. For each file, it calls `extractOutputclassFromTitle()`. This function opens the file and uses Go's native `encoding/xml` package to parse it token by token. It finds the first `<title>` element and returns the value of its `outputclass` attribute.
    c. If an `outputclass` is found, the script constructs the new filename (e.g., `my-outputclass-value.xml`).
    d. It performs the rename operation using `os.Rename()`.
    e. Crucially, it stores a record of the change in a `fileMap`, mapping the original base filename (e.g., `old-name.xml`) to the new base filename (e.g., `my-outputclass-value.xml`).

### Phase 2: Reference Updating

1.  **Re-scan Files**: After the renaming loop is complete, the `findFiles()` function is called a second time. This is necessary to get an updated list of all files in the directory, which now have their new names.

2.  **Iterate and Update**: The script iterates through this new file list.
    a. It processes `.xml`, `.dita`, and `.ditamap` files, as all three can contain references.
    b. It reads the entire content of each file into a string.
    c. It then iterates through the `fileMap` that was built during the renaming phase.
    d. For each entry in the map, it performs a simple but effective `strings.ReplaceAll()` on the file's content, replacing all occurrences of the old filename with the new filename.
    e. If any replacements were made (i.e., the content has changed), it writes the updated content back to the file using `os.WriteFile()`.

This ensures that any links, such as `<xref href="old-name.xml"/>` or `<topicref href="old-name.dita"/>`, are automatically updated to `<xref href="my-outputclass-value.xml"/>` or `<topicref href="my-outputclass-value.dita"/>`.

## 4. Error Handling

The utility is designed to be robust. If it encounters an error while processing a file (e.g., it cannot open the file, or a `<title>` tag or `outputclass` attribute cannot be found), it logs the error to the console and simply skips that file, continuing on to the next one. This prevents a single malformed file from halting the entire process.

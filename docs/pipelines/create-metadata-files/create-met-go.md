# Design Doc: `createMET.go` - Advanced MET File Generator

## 1. Overview

`createMET.go` is a sophisticated command-line utility written in Go. Its primary function is to automate the creation of `.MET` (metadata) files for a collection of Markdown (`.md`) articles. These `.MET` files are structured as JSON and contain rich, consolidated metadata that is essential for content management systems, search indexes, and front-end frameworks to properly render, categorize, and link articles.

The utility gathers information from multiple sources:

1.  **YAML Front Matter:** Extracts basic metadata directly from the header of each Markdown file.
2.  **`publish.json`:** A master JSON file defining the primary product hierarchy, navigation structure (breadcrumbs), and article inventory.
3.  **`subproduct.json` (Optional):** A supplementary JSON file that provides more granular, nested breadcrumb data for specific sub-sections of the product.
4.  **File Content:** The Markdown body is parsed to identify and extract all internal and external links.

By combining these sources, the tool generates a comprehensive `.MET` file for each corresponding Markdown file, significantly enhancing the discoverability and context of each article. This utility is a more advanced and feature-rich successor to the `create-kb-met.go` script.

## 2. Command-Line Interface

The script is executed from the command line and accepts the following flags:

*   `-mdPath` (Required): Specifies the directory path containing the source Markdown files.
*   `-jsonPath` (Required): Specifies the path to the primary `publish.json` file.
*   `-subproductJSON` (Optional): Specifies the path to the `subproduct.json` file for enhanced breadcrumb generation.
*   `-outputPath` (Required): Specifies the directory where the generated `.MET` files will be saved.

### Example Usage

```bash
go run createMET.go \
  -mdPath "./markdown_articles" \
  -jsonPath "./data/publish.json" \
  -subproductJSON "./data/subproduct.json" \
  -outputPath "./output/met_files"
```

## 3. Core Architecture & Data Flow

The program follows a clear, multi-stage process for each Markdown file it discovers in the source directory.

![Data Flow Diagram](https://i.imgur.com/example.png)  <!-- Placeholder for a real diagram -->

1.  **Initialization:**
    *   The program parses the command-line flags to get the necessary file paths.
    *   It loads the primary `publish.json` into memory.
    *   If the path is provided, it loads the `subproduct.json` into memory.

2.  **File Iteration:**
    *   The utility walks the directory specified by `-mdPath`.
    *   For each `.md` file found, it triggers the `createMETFile` function.

3.  **Metadata Aggregation (`createMETFile`):**
    *   **Front Matter Parsing:** It opens the Markdown file and parses the YAML front matter (e.g., `title`, `description`) using the `gopkg.in/yaml.v2` library.
    *   **Breadcrumb Generation:** This is the most complex step. The logic attempts to build the most specific breadcrumb trail possible by searching for the article's file path in the JSON data sources in a specific order of precedence:
        1.  **Sub-Product Search:** It first searches the `subproduct.json` data. If a match is found, it constructs a deep, detailed breadcrumb trail from this granular data.
        2.  **Primary Product Search:** If no match is found in the sub-product data, it falls back to searching the main `publish.json` data to construct a more general breadcrumb trail.
        3.  **Default:** If the file isn't found in either JSON file, it generates a minimal breadcrumb trail, typically just consisting of the root product title.
    *   **Link Extraction:** It reads the full content of the Markdown file and uses a regular expression (`\[([^\]]+)\]\(([^)]+)\)`) to find all embedded links, which are stored in the `InternalLinks` array.
    *   **Last Modified Date:** It retrieves the `last_modified` date for the article from the `publish.json` data.

4.  **MET File Creation:**
    *   All the aggregated data (Title, Link, Breadcrumbs, Product info, Links, etc.) is assembled into the `METFile` struct.
    *   The struct is marshaled into a well-formatted JSON string.
    *   A new file with the same name as the original Markdown file but with a `.MET` extension is created in the `-outputPath` directory, and the JSON string is written to it.

5.  **Completion:** The process repeats until all Markdown files have been processed.

## 4. Key Functions & Logic

### `main()`

*   **Entry Point:** Parses flags and orchestrates the entire process.
*   **File Discovery:** Uses `filepath.Walk` to recursively find all `.md` files in the source directory.
*   **Error Handling:** Contains top-level error handling. If loading the main `publish.json` fails, the program cannot continue and exits.

### `createMETFile()`

*   **Core Logic:** The heart of the application, responsible for orchestrating the metadata aggregation for a single file.
*   **Breadcrumb Strategy:** Implements the hierarchical search logic for breadcrumbs, prioritizing `subproduct.json` over `publish.json`. This ensures that articles belonging to a more specific sub-category get the correct, deeper navigation path.

### `findBreadcrumbs()` & `findMatch()`

*   **Recursive Search:** These functions work together to perform a depth-first search through the nested `Map` and `Children` arrays within the `publish.json` and `subproduct.json` structures.
*   **Path Matching:** They recursively build a path of titles (the breadcrumbs) as they descend into the JSON tree, stopping when they find a `Section` whose `FilePath` matches the target Markdown file.

### `extractLinksFromMarkdown()`

*   **Regex Parsing:** Uses a single, effective regular expression to parse standard Markdown links. It captures both the link text (e.g., "Google") and the URL (e.g., "https://www.google.com").
*   **Data Structuring:** Populates the `LinkEntry` struct, which categorizes each link by its text and destination URL.

### `parseFrontMatter()`

*   **YAML Parsing:** A dedicated function to safely extract metadata from the YAML front matter block at the top of a Markdown file. It looks for the `---` delimiters to isolate the block before parsing.

## 5. Data Structures

The utility defines several `struct` types to accurately model the JSON data and the final `.MET` output.

*   **`Product` & `SubProduct`:** These structs map directly to the structure of `publish.json` and `subproduct.json`, respectively. They include fields like `Title`, `ProductSectionID`, and a nested `Map` or `Children` array of `Section` structs, which creates the hierarchical tree.
*   **`Section`:** Represents a single node in the product hierarchy (a page or a category). It contains the `Title`, `URL`, and `FilePath` used for matching.
*   **`METFile`:** The master struct that defines the final JSON output. It aggregates all the data collected during the process, including the generated `Breadcrumbs` and the extracted `InternalLinks`.
*   **`Breadcrumb` & `LinkEntry`:** Simple structs used within `METFile` to represent a single breadcrumb (Title and URL) and a single extracted link.

## 6. Error Handling

The program incorporates standard Go error handling patterns:

*   Functions that can fail (e.g., file I/O, JSON parsing) return an `error` type.
*   The calling function checks if the returned `error` is `nil`. If it is not, the error is logged, and the program often stops processing the current file or exits entirely if the error is critical (like being unable to load `publish.json`).
*   `log.Fatalf` is used for critical errors that prevent the program from running at all, while `log.Printf` is used for non-fatal errors that affect a single file.

This robust approach ensures that the utility fails gracefully and provides clear feedback when it encounters problems, such as a missing file or malformed JSON.

## 7. Appendix: Sample `.MET` File

Below is an example of a `.MET` file generated by the `createMET.go` utility. This JSON output demonstrates how the aggregated metadata is structured.

```json
{
  "Title": "How to Configure Apex One as a Service",
  "Link": "/apex-one-as-a-service/get-started/configuring-apex-one.html",
  "Breadcrumbs": [
    {
      "Title": "Apex One as a Service",
      "URL": "/apex-one-as-a-service.html"
    },
    {
      "Title": "Getting Started",
      "URL": "/apex-one-as-a-service/get-started.html"
    },
    {
      "Title": "Configuring Apex One",
      "URL": "/apex-one-as-a-service/get-started/configuring-apex-one.html"
    }
  ],
  "Language": "en-us",
  "Product": "Apex One as a Service",
  "SubProduct": "Getting Started",
  "ConsoleURL": "https://example.console.url",
  "ContentType": "Article",
  "LastUpdated": "2023-10-27T10:00:00Z",
  "Version": "14.0",
  "InternalLinks": [
    {
      "Text": "product documentation",
      "URL": "/apex-one/docs/product-guide.html"
    },
    {
      "Text": "troubleshooting guide",
      "URL": "/apex-one/support/troubleshooting.html"
    },
    {
      "Text": "Trend Micro Vision One",
      "URL": "https://www.trendmicro.com/vision-one"
    }
  ]
}
```

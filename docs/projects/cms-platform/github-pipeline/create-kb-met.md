# `create-kb-met` Go Utility

## 1. Overview

The `create-kb-met` utility is a command-line tool written in Go. Its primary function is to transform a JSON payload, typically originating from a SharePoint list item, into a `.MET` metadata file. This `.MET` file is a crucial component for the DITA-OT (DITA Open Toolkit) publishing process, as it contains the structured metadata required to generate the final knowledge base article.

The script parses command-line flags to get input and output file paths, reads the SharePoint JSON, maps its fields to a predefined `METFile` structure, and then marshals this structure into a new JSON file (`.MET`).

## 2. Location

-   **Source Code:** create-kb-met.go
-   **Executable:** The Go source is compiled into an executable named `create-kb-met` which is used in the workflows.

## 3. Command-Line Arguments

The utility is executed with the following command-line flags:

| Flag        | Description                                     | Required | Example                               |
| :---------- | :---------------------------------------------- | :------- | :------------------------------------ |
| `-input`    | The path to the input JSON file from SharePoint. | Yes      | `-input article_data.json`            |
| `-output`   | The path where the output `.MET` file will be saved. | Yes      | `-output KB-12345.met`                |
| `-logs`     | The path to the log file for debugging.         | No       | `-logs /path/to/actions_runner.log`   |
| `-base-url` | The base URL for constructing the article link. | Yes      | `-base-url "https://example.com/kb"`  |

## 4. Input JSON Structure (`SharePointInput`)

The script expects an input JSON file with a structure that mirrors the data retrieved from a SharePoint list.

```json
{
  "id": "string",
  "fields": {
    "Title": "string",
    "field_3": "string", // ArticleID
    "CanonicalArticleID": "string",
    "ArticleVersion": "number",
    "field_19": "string", // Language
    "field_14": "string", // Keywords
    "Product_x002f_Service": "string", // Products
    "field_13": "string", // Versions
    "field_11": "string", // SolutionType
    "field_6": "string", // Audience
    "Modified": "string", // Timestamp
    "field_5": "string", // Overview/Description
    "field_20": "string"  // HTMLContent
  }
}
```

## 5. Output `.MET` File Structure (`METFile`)

The script processes the input and generates a `.MET` file with the following JSON structure. This file consolidates and formats the metadata for the DITA-OT process.

```json
{
  "knowledgearticleid": "string",
  "articlepublicnumber": "string",
  "title": "string",
  "articleVersion": "string",
  "description": "string",
  "link": "string",
  "language": "string",
  "language_long": "string",
  "keywords": "string",
  "products": ["string"],
  "versions": ["string"],
  "solutionType": "string",
  "visibility": "string",
  "isinternal": "boolean",
  "lastUpdated": "string",
  "createdAt": "string",
  "content": "string",
  "internalLinks": [
    {
      "href": "string",
      "text": "string"
    }
  ]
}
```

## 6. Core Logic (`main` function)

1.  **Flag Parsing:** It initializes and parses the `-input`, `-output`, `-logs`, and `-base-url` command-line flags.
2.  **Logging Setup:** If the `-logs` flag is provided, it configures the `log` package to write to the specified file.
3.  **File I/O:** It reads the content of the input file specified by `-input`.
4.  **JSON Unmarshaling:** It unmarshals the input JSON into the `SharePointInput` struct.
5.  **Field Mapping & Transformation:**
    *   It maps fields from the `SharePointInput` struct to the `METFile` struct.
    *   **Language:** It converts the short language code (e.g., "en-us") to its long-form equivalent (e.g., "English (United States)").
    *   **Audience/Visibility:** It determines the `visibility` and `isinternal` fields based on the `Audience` value from SharePoint.
    *   **Link:** It constructs the canonical article `link` using the `-base-url` and the `CanonicalArticleID`.
    *   **Timestamps:** It parses and reformats the `Modified` timestamp to RFC3339 format for `lastUpdated`.
    *   **Arrays:** It splits the semicolon-delimited `Products` and `Versions` strings into JSON arrays.
    *   **HTML Content:** It extracts the raw `HTMLContent`.
    *   **Internal Links:** It calls the `extractLinks` function to find all internal hyperlinks within the `HTMLContent`.
6.  **JSON Marshaling:** It marshals the populated `METFile` struct into a formatted JSON byte array.
7.  **Write Output:** It writes the resulting JSON to the output file specified by `-output`.

## 7. Helper Function (`extractLinks`)

-   **Purpose:** This function uses a regular expression to find all `<a>` tags within the provided HTML content that have an `href` attribute pointing to a specific internal domain (`/kb/`).
-   **Regex:** `href="(/kb/[^"]+)"`
-   **Output:** It returns a slice of `LinkEntry` structs, where each struct contains the `href` and the inner text of the anchor tag. This is used to populate the `internalLinks` field in the final `.MET` file.

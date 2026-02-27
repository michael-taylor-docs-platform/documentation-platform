# Design Doc: HTML Sanitizer Azure Function

**Version: 1.0**

## 1. Overview and Purpose

This document provides a detailed explanation of the `html-sanitizer` Node.js Azure Function.

The primary purpose of this function is to act as a centralized and robust HTML cleaning service. It was created to solve several critical data integrity and usability issues that arise from the interaction between the Power Apps Rich Text Editor (RTE) and SharePoint's "Enhanced rich text" fields.

This function is called by the `Orchestrate-GenerateAltTextAndSaveArticle` Power Automate flow before any data is saved to SharePoint.

## 2. Core Problems Addressed

The sanitizer solves the following specific problems:

1.  **Invalid XML Characters:** The primary driver for this function's creation. Pasting content from external sources (like Microsoft Word) can introduce invisible control characters (e.g., `U+000B` - Vertical Tab) into the HTML. These characters are not valid in XML and cause the downstream DITA XML conversion process to fail.
2.  **SharePoint Wrapper Divs:** When data is saved to a SharePoint "Enhanced rich text" field, SharePoint automatically wraps the entire content in an extraneous `<div class="ExternalClass...">` tag.
3.  **Power Apps RTE Paragraphs:** The Power Apps Rich Text Editor wraps each paragraph in a `<p class="editor-paragraph">` tag.
4.  **Infinite Nesting:** The combination of the SharePoint and Power Apps wrappers leads to a situation where, on each save cycle, the existing content (including the old wrappers) gets wrapped again. This results in deeply nested, invalid HTML that is difficult to parse and manage (e.g., `<div><p><div><p>...content...</p></div></p></div>`).
5.  **Sanitization Artifacts:** The process of stripping the nested wrapper tags can leave behind empty, invalid paragraph tags (`<p></p>`) as artifacts.

## 3. Sanitization Logic and Rules

The function uses the `sanitize-html` npm library to perform the cleaning. The logic is implemented in a specific order to produce clean, valid, and usable HTML.

### 3.1. Allowed Tags and Attributes

The configuration starts with a strict whitelist of allowed HTML tags and attributes. Any tag or attribute not on this list will be stripped, but its content will be preserved.

*   **Allowed Tags:** `h1`, `h2`, `h3`, `h4`, `h5`, `h6`, `p`, `b`, `i`, `u`, `strong`, `em`, `strike`, `del`, `s`, `a`, `img`, `ul`, `ol`, `li`, `table`, `thead`, `tbody`, `tr`, `th`, `td`, `br`, `hr`
*   **Allowed Attributes:** `href` (for `<a>` tags), `src`, `alt` (for `<img>` tags)

### 3.2. Stripping Wrapper Tags (Default Behavior)

The function **intentionally does not** include `div` in the `allowedTags` list. Because of this, the `sanitize-html` library automatically performs the following actions:
*   It encounters the `<div class="ExternalClass...">` tag.
*   It recognizes that `div` is not an allowed tag.
*   It removes the `div` tag but **keeps all the content inside it**.

This is the key mechanism for removing the SharePoint wrapper without using complex or risky filters. The same process removes the `class` attribute from the `<p>` tags, as `class` is not an allowed attribute.

### 3.3. Stripping Invalid Characters (`textFilter`)

The `textFilter` is a function that runs on all text content within the HTML. It uses the regular expression `/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g` to find and remove any invalid XML 1.0 control characters, solving the primary DITA conversion issue.

### 3.4. Final Cleanup of Artifacts and Preservation of Blank Lines

After the main sanitization, two final cleanup steps occur:

1.  **Remove Sanitization Artifacts:** A regular expression, `replace(/<p><\/p>/g, '')`, is used to remove only truly empty `<p></p>` tags. These are the artifacts left over from stripping the nested wrapper tags.
2.  **Preserve Author Intent:** The regex above is intentionally precise. It does **not** remove paragraph tags containing a non-breaking space (`<p>&nbsp;</p>`). This is the standard HTML representation for a blank line created when an author hits "Enter" in an editor. This ensures that intentional formatting is preserved.

## 4. API Contract

The function expects and returns a simple JSON object.

*   **Request Body:** A JSON object with a single key, `html`.
    ```json
    {
      "html": "<div class=\"ExternalClass...\"><p>Hello World</p></div>"
    }
    ```
*   **Success Response (200 OK):** A JSON object with a single key, `cleanHtml`.
    ```json
    {
      "cleanHtml": "<p>Hello World</p>"
    }
    ```

## 5. Related Documentation

*   **Security:** For details on how to secure this function and call it from Power Automate, see: [`HtmlSanitizer_Security_designDoc.md`](./HtmlSanitizer_Security_designDoc.md)
*   **Usage Context:** For details on how this function is called within the broader article-saving process, see: [`Orchestrate-GenerateAltTextAndSaveArticle.md`](./PowerAutomate_DesignDoc/Orchestrate-GenerateAltTextAndSaveArticle.md)

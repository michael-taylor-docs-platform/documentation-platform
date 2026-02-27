# Python Script: `create-rss.py`

---

## 1. High-Level Overview & Purpose

The `create-rss.py` script is a command-line utility designed to generate a standards-compliant RSS 2.0 feed from a collection of HTML files. Its primary purpose is to create a "What's New" feed by intelligently filtering a directory of HTML articles, extracting metadata and content only from those explicitly marked as "What's New," and then assembling them into a single `rss_feed.xml` file.

The script is highly configurable, relying on an external JSON file to define the feed's channel properties (like title and description) and to correctly construct absolute URLs for the content. This separation of logic and configuration makes it adaptable for different products or documentation sets without modifying the script itself.

## 2. Core Components

-   **Python Script:** create-rss.py - The core engine for parsing and generation.
-   **Input HTML Files:** A directory containing one or more `.html` files. The script specifically looks for a `<meta name='is-what-new' content='1'>` tag within these files to identify articles for inclusion.
-   **Input JSON Configuration:** A configuration file (e.g., `config.json`) that provides all the necessary metadata for the RSS channel and for constructing links.
-   **Output RSS Feed:** A single `rss_feed.xml` file that is generated in the same directory as the input HTML files.

## 3. Execution Flow & Command-Line Arguments

The script is executed from the command line with two required arguments:

```bash
python create-rss.py <html_directory> <config_file>
```

-   `<html_directory>`: The path to the directory containing the source `.html` files.
-   `<config_file>`: The path to the JSON configuration file.

The script then:
1.  Identifies all `.html` files in the specified directory.
2.  Calls the main `create_rss_feed()` function, passing it the list of HTML files, the desired output path (`rss_feed.xml`), and the path to the configuration file.

## 4. Function Breakdown

The script is logically divided into several functions, each with a distinct responsibility.

### a. `create_rss_feed(html_files, output_file, config_file)`

This is the main orchestrating function.

1.  **Load Configuration**: It opens and parses the provided JSON `config_file` to load channel metadata (`Title`, `ProductSectionid`) and link-building parameters (`ProductSectionKey`, `Language`).
2.  **Build RSS Header**: It constructs the static `<channel>` portion of the RSS feed using the loaded configuration.
3.  **Process HTML Files**: It iterates through every HTML file passed to it.
    a. It uses BeautifulSoup to parse the HTML.
    b. **Filtering**: It first checks for the existence of `<meta name='is-what-new' content='1'>`. If this tag is not present, the file is skipped entirely.
    c. **Extraction**: If the file is a "What's New" article, it calls the helper functions `extract_metadata()` and `extract_content()`.
    d. **Item Creation**: It calls `create_rss_item()` to assemble the final `<item>` XML block for the article.
    e. The resulting item and its publication date are stored in a list.
4.  **Sort Items**: After processing all files, it sorts the list of generated items by their publication date in ascending order (oldest first).
5.  **Assemble and Write**: It joins the RSS header, the sorted items, and the RSS footer, injects the final `lastBuildDate`, and writes the complete XML content to the `output_file`.

### b. `extract_metadata(soup)`

-   **Purpose**: To extract all necessary metadata from `<meta>` tags within the HTML's `<head>`.
-   **Logic**: It uses BeautifulSoup's `find()` method to locate specific meta tags by their `name` attribute (e.g., `map-description`, `category`, `change-date`) and returns their `content`.

### c. `extract_content(soup, file_name, product_section_key, language)`

-   **Purpose**: To extract the primary article content and, critically, to rewrite all internal links to be absolute URLs suitable for an RSS feed.
-   **Logic**:
    1.  It finds the main content `<div>`, which must have a class of either `conbody` or `refbody`.
    2.  It then finds all `<a>` tags within that content div.
    3.  For each link, it checks if it is an external link (i.e., has `target="_blank"`) and skips it if so.
    4.  For all other links, it rewrites the `href` attribute, transforming a relative link like `my-article.html` into an absolute URL like `https://docs.trendmicro.com/en-us/documentation/article/PRODUCT-KEY-my-article`.
    5.  Finally, it returns the processed inner HTML of the content `<div>` as a string.

### d. `create_rss_item(...)`

-   **Purpose**: To construct a single, complete `<item>` block for the RSS feed.
-   **Logic**:
    1.  It formats the `change_date` into the RFC 822 format required by the RSS specification (e.g., `Mon, 25 Feb 2026 00:00:00 GMT`).
    2.  It constructs a unique, non-permalink `<guid>`. This GUID is intentionally designed to be the same for all articles of the same category published in the same month, allowing feed readers to group related "What's New" updates.
    3.  It assembles the final XML string, wrapping the content in `<![CDATA[...]]>` to ensure the HTML is rendered correctly and does not break the XML structure.

## 5. Configuration and Dependencies

-   **Dependencies**: The script relies on one external library, `BeautifulSoup4` (`bs4`), which must be installed.
-   **JSON Configuration File**: The script requires a JSON file with the following structure:

    ```json
    {
      "Title": "Product Name - What's New",
      "ProductSectionid": "A brief description of the product feed.",
      "ProductSectionKey": "PRODUCT-KEY",
      "Language": "en-us"
    }
    ```

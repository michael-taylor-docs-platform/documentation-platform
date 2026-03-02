# Workflow: `external-link-check.yml`

This document provides a detailed breakdown of the `external-link-check.yml` workflow and its associated Python script, `externalLinkCheck.py`. This system is designed to proactively find and report broken external links within the XML-based knowledge base articles.

## 1. Overview

The system uses a GitHub Actions workflow to periodically scan all `.xml` files in the content repository. It extracts all external links (`<xref scope="external">`) and attempts to validate them using a sophisticated, multi-layered approach. Broken links are compiled into a JSON report, and a notification is sent if any failures are detected.

## 2. Core Components

-   **Workflow File:** otherWorkflows/external-link-check.yml
-   **Python Script:** otherWorkflows/externalLinkCheck.py
-   **Exception List:** `externalLinkExceptions.txt` (located in the script repository) - A simple text file containing a list of URLs to ignore, even if they fail validation.

## 3. Workflow Breakdown (`external-link-check.yml`)

### Trigger and Purpose

-   **Trigger**: The workflow runs on a schedule (every Monday at 12:00 AM Taipei time) and can also be triggered manually (`workflow_dispatch`).
-   **Purpose**: To automate the process of checking for broken external links in the knowledge base content and report the findings.

### Job: `check-links`

This is the single job that orchestrates the entire process.

-   **Runner**: `ebf-pod-ubuntu-latest@${{ github.run_id }}-external-link-validator`

#### Steps

1.  **`Checkout repository`**: Checks out the primary content repository (e.g., `KBConsolidation`) to gain access to the `.xml` files that need to be scanned.
2.  **`Checkout script repository`**: Checks out the `HIE-ELIXIR/external-link-validator` repository into a separate `validator_script` directory. This repository contains the `externalLinkCheck.py` script and the `externalLinkExceptions.txt` file.
3.  **`Set up Python`**: Initializes a Python 3.10 environment.
4.  **`Install dependencies`**: Installs the necessary Python libraries:
    -   `lxml`: For parsing XML files.
    -   `requests`: For making HTTP requests.
    -   `playwright`: For running a headless browser to validate JavaScript-heavy pages.
    -   `tqdm`: For displaying a progress bar in the logs.
    -   It also runs `playwright install chromium` to download the required browser.
5.  **`Run externalLinkCheck.py`**: Executes the main Python script to perform the link validation.
6.  **`Upload broken links report`**: If the script generates a `brokenLinks.json` file, it is uploaded as a workflow artifact named `broken-links-report`. This step runs `if: always()` to ensure the report is available even if the script exits with an error.
7.  **`Upload other protocols log`**: If the script generates an `otherProtocols.log` file (for links that are not `http` or `https`), it is uploaded as an artifact named `other-protocols-log`.
8.  **`Send failure notification email`**: If any previous step in the job fails (including the script exiting with a non-zero status code), this step runs. It constructs a JSON payload and uses `curl` to send an email notification to a predefined distribution list via the `$CI_SENDMAIL` endpoint.

## 4. Python Script Breakdown (`externalLinkCheck.py`)

The script is the engine of the validation process. It employs a robust strategy to minimize false positives.

### Core Logic

1.  **File Discovery**: The `find_xml_files()` function recursively searches the `en-us` directory for all `.xml` files, respecting a configurable `EXCLUDED_DIRS` list to skip certain folders (e.g., `ExternalContent`).

2.  **Link Extraction**: The `process_xrefs()` function parses each XML file using `lxml`. It finds all `<xref>` tags with `scope="external"` and extracts their `href` attribute.

3.  **Link Validation Strategy**: The validation is multi-layered to handle different web technologies and anti-bot measures.

    a.  **Initial `requests` Check (`check_link_with_retries`)**:
        -   It first attempts a lightweight `requests.head()` call.
        -   If this fails with a client or server error (e.g., 404, 405), it retries with a `requests.get()` call.
        -   It handles `429 Too Many Requests` responses by respecting the `Retry-After` header or using exponential backoff.
        -   **If a `404 Not Found` is received, it does not immediately fail.** Instead, it triggers the Playwright check as a fallback.
        -   If a timeout occurs, it also triggers the Playwright check.

    b.  **Playwright Fallback (`js_check_url`, `check_with_playwright_and_fallback`)**:
        This is the script's most powerful feature, designed to handle modern web complexities and reduce false positives. It is triggered when a simple `requests` check returns a `404 Not Found` or times out.
    
        -   **Purpose**: To correctly validate pages that rely heavily on JavaScript. Many modern websites are Single Page Applications (SPAs) or use client-side rendering. These sites might return a technically "successful" HTTP status code but then use JavaScript to display a "Page Not Found" error. Conversely, some sites might return an initial 404 error but then load the correct content dynamically. A simple HTTP check cannot detect this behavior.
    
        -   **Layer 1: Standard Browser Rendering**: The script launches a headless Chromium browser using Playwright to load the URL. It waits for the DOM to be fully loaded (`domcontentloaded`) and then analyzes the page's final state. This allows it to check the content of the page *after* JavaScript has executed.
    
        -   **Layer 2: Anti-Bot Evasion (Cloudflare)**: The script specifically looks for the title "Just a moment...", which is characteristic of Cloudflare's anti-bot challenge page. If detected, it intelligently waits for the title to change, giving the automated browser time to solve the challenge and reach the actual destination page before making a final validation decision.
    
        -   **Layer 3: Human-Like Context (Protocol Error Fallback)**: In rare cases, a server's bot detection is so advanced that it rejects even a standard Playwright request, often resulting in a specific `ERR_HTTP2_PROTOCOL_ERROR`. To overcome this, the script has a final fallback. It creates a new, "human-like" browser context with a common `User-Agent` string and a standard viewport size. This makes the request less distinguishable from that of a real user, allowing it to bypass more stringent fingerprinting-based bot detectors. This is the last resort for the most difficult-to-validate links.
    
        -   **Final Check**: After rendering, it checks the page content and URL against a list of known patterns (`CONTENT_PATTERNS`). If a pattern is found, the script considers the link valid, even if the initial status code was 404. This helps to correctly identify "soft 404s".
    
        This multi-layered browser-based validation ensures that the link checker is resilient and accurate when dealing with the complexities of the modern web.

4.  **Exception Handling**: Before reporting a link as broken, the script checks if the URL is present in the `externalLinkExceptions.txt` file. If it is, the failure is ignored.

5.  **Output Generation**:
    -   **`brokenLinks.json`**: A structured JSON file listing each file that contains broken links, and for each broken link, its URL, link text, the HTTP response code (or error message), and the line number where it was found.
    -   **`otherProtocols.log`**: A simple log of any links found that do not use `http://` or `https://`.

6.  **Exit Code**: If, after all checks and exceptions, there are still broken links in the final report, the script calls `sys.exit(1)`. This non-zero exit code causes the GitHub Actions step to fail, which in turn triggers the email notification step. If no broken links are found, the script exits with 0.

## 5. Artifacts

-   **`broken-links-report`**: A zip file containing `brokenLinks.json`.
-   **`other-protocols-log`**: A zip file containing `otherProtocols.log`.

## 6. Notifications

If the workflow fails, an email is sent to `alloftrendcxexternallinkvalidators@dl.trendmicro.com` with a subject line indicating failure and a link to the workflow run for detailed analysis.

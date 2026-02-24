# LogSystemEvent

## Executive Summary

This document provides a complete and detailed specification for the `Child Flow - LogSystemEvent` Power Automate workflow. This is a critical infrastructure component, acting as the centralized error and activity logger for the entire Knowledge Base backend system.

Its primary function is to be called as a **Child Flow** from the `Catch` block of other, "parent" flows. This provides a robust, standardized, and highly maintainable way to record system-level events. This architecture decouples error logging from business logic and, most importantly, **centralizes the connection to Azure Table Storage**, simplifying secret management.

--- 

## Prerequisites: Centralized Configuration

To ensure the system is maintainable and adaptable to different environments (e.g., Dev, Test, Prod), we avoid hardcoding environment-specific values. Instead, we use a central SharePoint list named `appConfiguration` to store these settings.

**Action Required:** Before building this flow, ensure the following items exist in your `appConfiguration` list. The `Title` column is the key, and the `Value` column is the setting.

| Title (Key) | Value | Purpose |
| :--- | :--- | :--- |
| `AUDIT_STORAGE_ACCOUNT_NAME` | `kbauditstorage20260123` | **(Shared)** The name of the Azure Storage Account where all log tables reside. |
| `AUDIT_TABLE_SYSTEM_LOGS` | `SystemActivityLogs` | **(New)** The specific table name for storing system-level logs. |
| `DEV_CONTACT_EMAIL` | `michael.taylor@trendmicro.com` (temp value) | **(Shared)** The email address for critical failure notifications. |

--- 

## Detailed Implementation Guide

This section provides a step-by-step walkthrough for building the flow.

### 1. Trigger: Manually trigger a flow

This seems counter-intuitive, but to create a flow that can be called as a child, you start with the `Manually trigger a flow` trigger. When you save this flow inside a solution, it automatically becomes available to be called by other flows in the same solution.

1.  Select the `Manually trigger a flow` trigger.
2.  Add four **`Text`** input fields. These will serve as the parameters that parent flows will pass in.
    *   `logLevel`
    *   `source`
    *   `message`
    *   `context`

### 2. Step 1: Variable Initialization

We initialize all variables at the beginning of the flow. This is a best practice that improves readability and makes the flow easier to debug.

1.  **Initialize `storageAccountName`** (Type: `String`): To hold the name of the Azure Storage Account.
2.  **Initialize `systemLogTableName`** (Type: `String`): To hold the name of the target table.
3.  **Initialize `devContactEmail`** (Type: `String`): To hold the email address for critical failure notifications.
4.  **Initialize `rowKey`** (Type: `String`)
    *   **Value:** `@string(sub(ticks('9999-12-31T23:59:59Z'), ticks(utcNow())))`
    *   **Explanation:** This expression creates a reverse-chronological, globally unique key. By subtracting the current time's "ticks" (a very granular time measurement) from a fixed future date's ticks, we ensure that newer log entries have a lexicographically *smaller* `RowKey`. This is a powerful technique in Azure Table Storage that causes new items to always appear at the top when sorted, making queries for "the latest N items" extremely efficient.
5.  **Initialize `partitionKeyDate`** (Type: `String`)
    *   **Value:** `@utcNow('yyyy-MM-dd')`
    *   **Explanation:** This creates a simple date string (e.g., `2026-01-23`). We use this as the `PartitionKey` to group all of a day's system logs together. This is highly efficient for querying all logs for a specific day.

### 3. Step 2: Retrieve Configuration

Here, we fetch our configuration values from the `appConfiguration` list.

1.  **Action: `Get items` (SharePoint)**
    *   **Name:** `Get_System_Log_Configuration`
    *   **Filter Query:** `Title eq 'AUDIT_STORAGE_ACCOUNT_NAME' or Title eq 'AUDIT_TABLE_SYSTEM_LOGS' or Title eq 'DEV_CONTACT_EMAIL'`
    *   **Explanation:** This single, efficient call retrieves all the configuration rows we need for this flow.

2.  **Action: `Apply to each` & `Switch`**
    *   **Input:** The `value` output from the `Get items` action.
    *   **Inside the loop, add a `Switch` action.**
        *   **On:** `@item()?['Title']`
        *   **Explanation:** This is an efficient pattern for processing the results of the `Get items` call. The `Switch` statement checks the `Title` of each configuration item returned and routes it to the correct `Set variable` action. This is more scalable than using multiple condition checks.
        *   **Case 1:** `AUDIT_STORAGE_ACCOUNT_NAME` -> **Action:** `Set variable` `storageAccountName` to `@item()?['Value']`
        *   **Case 2:** `AUDIT_TABLE_SYSTEM_LOGS` -> **Action:** `Set variable` `systemLogTableName` to `@item()?['Value']`
        *   **Case 3:** `DEV_CONTACT_EMAIL` -> **Action:** `Set variable` `devContactEmail` to `@item()?['Value']`

### 4. Step 3: Core Logic (`Try` Scope)

We will place the main logic inside a `Try` scope. This allows us to "catch" any failures that occur within it and handle them gracefully in a separate `Catch` scope.

1.  Add a **`Scope`** action and rename it `Try`.
2.  Inside the `Try` scope, add the following action:

    *   **Action:** `Insert Entity` (Azure Table Storage)
        *   **Name:** `Insert_Entity_into_SystemActivityLogs`
    *   **Connection:** Use the **Connection Reference** linked to your Service Principal.
    *   **Storage Account Name:** `@variables('storageAccountName')`
    *   **Table Name:** `@variables('systemLogTableName')`
    *   **Entity:**
        ```json
        {
          "PartitionKey": "@{variables('partitionKeyDate')}",
          "RowKey": "@{variables('rowKey')}",
          "LogLevel": "@{triggerBody()?['text']}",
          "Source": "@{triggerBody()?['text_1']}",
          "Message": "@{triggerBody()?['text_2']}",
          "Context": "@{triggerBody()?['text_3']}"
        }
        ```

**Explanation of Entity Expressions:** The `trigger()` expressions now refer to the input fields from the manual trigger. `text` corresponds to the first input (`logLevel`), `text_1` to the second (`source`), and so on.

### 5. Step 4: Robust Error Handling (`Catch` Scope)

This scope will only execute if any action inside the `Try` scope fails.

1.  Add a new **`Scope`** action after the `Try` scope and rename it `Catch`.
2.  **Configure run after** for the `Catch` scope to run on `has failed`, `is skipped`, and `has timed out`.
3.  Inside the `Catch` scope, add the following action:

    *   **Action:** `Send an email (V2)` (Office 365 Outlook)
    *   **To:** `@variables('devContactEmail')`
    *   **Subject:** `CRITICAL FAILURE in KB Logging Workflow: LogSystemEvent`
    *   **Body:** Switch to Code View (`</>`) and paste the following HTML.

        ```html
        <h2>Critical Logging Failure</h2>
        <p>The <strong>LogSystemEvent</strong> workflow failed to write a log to Azure Table Storage. This is a critical error, as it means the system's primary error logging mechanism has failed.</p>
        <hr>
        <h3>Original Log Payload:</h3>
        <pre>
        <strong>Log Level:</strong> @{triggerBody()?['text']}<br>
                <strong>Source:</strong> @{triggerBody()?['text_1']}<br>
                <strong>Message:</strong> @{triggerBody()?['text_2']}<br>
                <strong>Context:</strong> @{triggerBody()?['text_3']}
        </pre>
        <hr>
        <h3>Error Details:</h3>
        <pre>@{first(skip(result('Try'), 0))?['error']?['message']}</pre>
        ```

### 6. Step 5: Respond to Parent Flow

A child flow must formally respond to its parent so the parent knows it has finished.

1.  Add a **`Respond to a PowerApp or flow`** action at the very end of the flow, after the `Try/Catch` blocks.
2.  Click the ellipsis (...) on this action and select **Configure run after**.
3.  Check the boxes for all four possible outcomes of the preceding `Catch` block: `is successful`, `has timed out`, `is skipped`, and `has failed`.
4.  This ensures that the child flow will always send a response back to the parent flow, regardless of whether an error occurred, preventing the parent flow from timing out.

--- 

## Security Model

*   **Authentication:** This flow authenticates using the **shared Connection Reference** from the solution. This is the key to centralized secret management. The Service Principal (`SharePoint-KB-Publisher-Action`) permissions are managed in one place.

--- 

## Testing

Because this is a child flow, it cannot be run directly. It must be tested by a parent flow. The `LogAuditEvent` flow will serve as its first parent and test harness.
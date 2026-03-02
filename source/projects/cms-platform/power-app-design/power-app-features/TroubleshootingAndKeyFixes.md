---
title: Troubleshooting & Key Fixes (Direct SharePoint Connection)
category: architecture
audience:
  - developers
  - solution-architects
  - engineering-leaders
tags:
  - power-apps
  - canvas-app
  - sharepoint
  - power-automate
  - power-automate-integration
  - delegation
  - filtering
  - state-management
  - workflow-orchestration
  - data-modeling
project: knowledge-base-manager
layer: application
status: published
summary: Implementation-level architectural patterns and critical fixes for the direct SharePoint-connected Power Apps CMS, including delegable gallery filtering, DisplayMode gating logic, multi-select person configuration, declarative state management using Coalesce, manual refresh patterns, and Power Automate connection repair.
---

# Troubleshooting & Key Fixes (Direct SharePoint Connection)

This section documents critical fixes required for the direct SharePoint connection.

## Gallery `Items` Formula (`scr_Browse`)

The formula for the main articles gallery (`gal_Articles`) must use SharePoint column names and be delegable.

*   **Corrected Formula:**
    ```powerapps
    SortByColumns(
        Filter(
            'Knowledge Base Articles',
            StartsWith(
                Title,
                txt_Search.Text
            )
        ),
        "Modified",
        SortOrder.Descending
    )
    ```
*   **Key Points:**
    *   The formula filters on the SharePoint `Title` column.
    *   It sorts by the SharePoint `Modified` column.
    *   `StartsWith` is a delegable function for SharePoint, ensuring the search runs on the server.

## Data Card `Default` Property for Choice Columns

When using a direct SharePoint connection, setting the default value for a Choice column is simpler. You can directly reference the Choice record from the item.

*   **Example (`Language` field):**
    ```powerapps
    ThisItem.Language
    ```
*   **Explanation:** Unlike with virtual tables, there is no need for a complex `LookUp` against the `Choices()` function. The direct reference `ThisItem.Language` provides the correct record that the dropdown/combo box control expects.

## Data Card `DisplayMode` Logic

The logic to make fields read-only must reference SharePoint column names.

*   **Goal:** Fields should be editable only for new articles OR for existing articles that are still in "Draft" status.
*   **Corrected Formula:**
    ```powerapps
    // This is the final, correct formula that also checks the version.
    If(
        frm_ArticleContent.Mode = FormMode.New || (gblSelectedItem.field_4.Value = "Draft" && gblSelectedItem.IsLatestVersion),
        DisplayMode.Edit,
        DisplayMode.View
    )
    ```
*   **Breakdown of Changes:**
    1.  The formula now uses `gblSelectedItem.field_4.Value`. This is the **logical name** for the `Status` field.

*   **Developer's Note on Logical Names:** Using logical field names (`field_1`, `field_4`, etc.) is a best practice in this app to prevent formulas from breaking if the underlying SharePoint list is ever replaced or its column display names are changed. While less readable, it provides crucial long-term stability.

## Field Display Modes

To control which fields are editable, we use the `DisplayMode` property on each data card. There are three primary strategies used in this app.

### 1. Always Read-Only
For fields that are system-generated and should never be edited by the user (e.g., Created By, Modified Date), the `DisplayMode` property of the data card is set to a static value.

*   **Property:** `DisplayMode`
*   **Formula:**
    ```powerapps
    DisplayMode.View
    ```

### 2. Editable for New or Draft Articles
For most authorable fields, the logic allows editing only if the article is brand new or is an existing draft. Once it has been submitted for review, the fields become read-only to preserve the integrity of the version being reviewed.

*   **Property:** `DisplayMode`
*   **Formula:**
    ```powerapps
    // This is the final, correct formula that also checks the version.
    If(
        frm_ArticleContent.Mode = FormMode.New || (gblSelectedItem.field_4.Value = "Draft" && gblSelectedItem.IsLatestVersion),
        DisplayMode.Edit,
        DisplayMode.View
    )
    ```

### 3. Conditional Editability Based on Status
For specific fields that are part of the review process, such as 'Assigned SME', editing is only allowed during specific review statuses.

*   **Property:** `DisplayMode`
*   **Formula:**
    ```powerapps
    // This is the final, correct formula that uses gblSelectedItem and also checks the version.
    If(
        gblSelectedItem.field_4.Value in ["Waiting for Reviewer", "In Review"] && gblSelectedItem.IsLatestVersion,
        DisplayMode.Edit,
        DisplayMode.View
    )
    ```

## Data Card for Person (Multi-Select) Columns

Configuring a field that allows multiple Person/Group selections (like the `Contributors` field) requires specific steps if the default control is incorrect. If Power Apps generates a text box instead of a combo box, it must be manually replaced and configured.

*   **Problem:** The data card for a multi-select Person field shows a text box, causing data type errors, instead of a control that allows selecting multiple users.

*   **Solution:** Replace the text box with a correctly configured Combo Box.

    1.  **Unlock the Data Card:** Select the card (e.g., `Contributors_DataCard`) and unlock it to change its properties.
    2.  **Delete the Text Input:** Remove the default text input control inside the card.
    3.  **Insert a Combo Box:** Add a new `Combo Box` control into the data card.
    4.  **Configure the Combo Box:**
        *   **`Items` Property:** Set this to the available choices for that column.
            ```powerapps
            Choices([@'Knowledge Base Articles'].Contributors)
            ```
        *   **`DefaultSelectedItems` Property:** This is the most important property for displaying the currently saved people. It expects a table of user records, which the SharePoint field provides directly.
            ```powerapps
            ThisItem.Contributors
            ```
        *   **Fields (in Properties pane):** Click "Edit" on the Fields property to configure what is displayed.
            *   **Primary text:** `DisplayName`
            *   **SearchField:** `DisplayName`
    5.  **Configure the Data Card's `Update` Property:** The card itself must be told to save the output from the new combo box.
        *   Select the parent data card.
        *   Set its `Update` property to the `SelectedItems` of the combo box.
            ```powerapps
            // If the new combo box is named ComboBox1
            ComboBox1.SelectedItems
            ```

## Initial Data Loading and State Management

A primary challenge in this single-screen application was ensuring data loads correctly on startup without interfering with subsequent user selections. The final, robust solution avoids timing-related "race conditions" by using a declarative pattern.

*   **The Problem:** Initial attempts to load data using the screen's `OnVisible` property failed because the logic would execute *before* the gallery had finished loading its items from SharePoint. This resulted in the form displaying a "Getting your data..." message because its data source was blank.

*   **The Solution: Declarative Loading with `Coalesce`:** The root cause was addressed by making the form's `Item` property smarter. Instead of relying on timed events, the form now declaratively selects its own data source.

    *   **Form `Item` Property:** `Coalesce(gblSelectedItem, First(gal_Articles.AllItems))`
    *   **Title Label `Text` Property:** `If(frm_Article.Mode = FormMode.New, "New Article", Coalesce(gblSelectedItem, First(gal_Articles.AllItems)).Title)`

    This `Coalesce` pattern is the core of the state management architecture. It creates a reliable "waterfall": the app tries to use `gblSelectedItem` first. If that's blank (as it is on initial load), it automatically falls back to the `First()` item in the gallery as soon as it becomes available. This completely eliminates the race condition.

*   **Role of `OnVisible`:** With this new architecture, the screen's `OnVisible` property is no longer responsible for data loading. Its sole purpose is to reset the UI to a known state, such as ensuring the correct tab is selected.
    ```powerapps
    // scr_Article.OnVisible
    UpdateContext({ selectedTab: "KB Content" })
    ```

This separation of concerns—letting the controls' properties handle data state and letting screen events handle UI state—is a best practice for creating reliable and maintainable Power Apps.

## Manual Data Refresh

A manual refresh mechanism is implemented to address the inherent data caching behavior of Power Apps, which can cause the app to display stale data after a backend process (like a Power Automate flow) modifies an item.

*   **The Problem:** Power Apps maintains a local cache of data from SharePoint, which only refreshes automatically every 30 minutes by default. The **`KBApprovalWorkflow`** is designed to allow reviewers to approve or reject articles from multiple platforms (the Power App, email, or Teams). If a user rejects an approval via email, the `Status` in SharePoint changes, but the app will continue to show the old status (e.g., "In Review") for up to 30 minutes, which is confusing for the author.
*   **The Solution:** A user-initiated refresh action is provided. This gives the user control to sync the app with the backend data on demand.
*   **Implementation:**
    1.  **`ico_Refresh` (Icon):** A "Reload" icon is placed in the header of the article gallery.
    2.  **`OnSelect` Property:** The formula refreshes the data source and then immediately re-selects the current item to update the form.
        ```powerapps
        // Step 1: Refresh the main data source from SharePoint
        Refresh('Knowledge Base Articles');

        // Step 2: Re-lookup the currently selected item from the refreshed data source
        // and update the global variable with the fresh data.
        Set(
            gblSelectedItem,
            LookUp(
                'Knowledge Base Articles',
                ID = gblSelectedItem.ID
            )
        );
        ```
    *   **How it Works:** `Refresh()` updates the gallery's data source. `Set(gblSelectedItem, LookUp(...))` then updates the variable that the main form is bound to, ensuring both the gallery and the form display the latest data.

## Fixing the `InvokerConnectionOverrideFailed` Error

This is a critical error that can occur when a Power Automate flow's connection to the Power App is broken. It is not an error in the Power Fx code, but rather a problem with the flow's underlying connection reference.

*   **Symptom:** When a button in the Power App calls a flow, a generic error message appears stating, "The requested operation is invalid. Server Response: The service returned an error: `InvokerConnectionOverrideFailed`". The flow does not run.

*   **Root Cause:** This error indicates that the connection reference used by the Power App to call the flow is no longer valid. This can happen if the flow has been moved, re-shared, or if its connections have been updated directly in the Power Automate portal.

*   **Solution:** The fix requires resetting the connection reference on the flow's details page in the Power Automate portal. It cannot be fixed from within the Power App editor.

   1.  **Navigate to the Flow:** Go to the Power Automate portal (make.powerautomate.com).
   2.  **Find the Flow:** Locate the flow that is causing the error (e.g., `Instant - Discard Article Draft`).
   3.  **Open the Details Page:** Click on the flow's name to open its main details page.
   4.  **Locate the "Run only users" Pane:** On the right side of the page, find the pane titled "Run only users".
   5.  **Edit Connections:** Click the "Edit" button in this pane.
   6.  **Reset the Connection:** You will see the connection that the Power App uses (e.g., "Connected to PowerApps"). Even if it looks correct, you must re-select it. Choose the option "Use this connection (<your_username@your_domain.com>)" from the dropdown.
   7.  **Save:** Click the "Save" button.

After saving, return to the Power App and test the button again. The error should be resolved. This process effectively re-establishes the secure connection between the Power App trigger and the flow itself.
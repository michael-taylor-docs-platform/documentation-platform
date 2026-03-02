---
title: Knowledge Base Manager – Power App Architecture
category: architecture
audience:
  - engineering-leaders
  - content-architects
  - devops-engineers
tags:
  - power-apps
  - sharepoint
  - power-automate
  - enterprise-architecture
  - workflow-orchestration
  - structured-content
  - metadata-modeling
  - concurrency-control
  - polling-pattern
  - canvas-app
project: knowledge-base-manager
layer: application
status: published
summary: Architectural specification of the Knowledge Base Manager Power App, including V2 centralized workflow design, concurrency control, backend polling patterns, and SharePoint integration strategy.
---

# Knowledge Base Manager – Power App Architecture

## 1. Overview

This document details the design, architecture, and key configurations of the "Knowledge Base Manager" standalone Power App. It serves as a technical reference for future development and maintenance.

## 2. Application Architecture

*   **App Type:** Standalone Canvas App
*   **Primary Use Case:** Creating and editing articles for the Knowledge Base. Designed for portability and future integration with Microsoft Teams.

## 3. Data Architecture: V2 - Centralized Power Automate Workflow

### 3.1. Executive Summary

This application has been refactored to a V2 architecture that **centralizes all create and update logic** into a single, robust Power Automate workflow: `Orchestrate-GenerateAltTextAndSaveArticle`. The Power App is no longer responsible for directly writing data to SharePoint. Instead, it gathers all form data into a JSON object and passes it to the workflow for processing.

This new architecture provides several key advantages:
*   **Centralized Logic:** All business rules, data validation, and backend updates are in one place, making the system easier to maintain and debug.
*   **Robust Error Handling:** The workflow handles all potential errors, including save conflicts and system failures, and returns a structured response to the Power App.
*   **Improved Performance:** Complex operations like image processing and contributor logic are offloaded to the backend, keeping the Power App responsive.
*   **Enhanced Concurrency Control:** A timestamp-based mechanism prevents users from accidentally overwriting each other's changes.

### 3.2. Data Flow

1.  **User Action:** The user clicks "Save Draft" or "Start Review" in the Power App.
2.  **JSON Construction:** The app gathers data from all form fields and constructs a single JSON object.
3.  **Flow Invocation:** The app calls the `Orchestrate-GenerateAltTextAndSaveArticle` flow, passing the JSON object as a parameter.
4.  **Backend Processing:** The flow performs all necessary actions:
    *   Parses the incoming JSON.
    *   Checks for save conflicts using the `loadTimestamp`.
    *   Creates or updates the SharePoint item.
    *   Processes embedded images.
    *   Handles contributor and author logic.
5.  **Structured Response:** The flow returns a JSON response to the Power App indicating the outcome (`Success`, `Failure`, or `Save Conflict`) along with a user-friendly message.
6.  **UI Update:** The Power App parses the response and updates the UI accordingly, either by displaying a success notification, showing an error message, or refreshing the data.

### 3.3. Concurrency Control: Timestamp Method

To prevent data loss when multiple users edit the same article simultaneously, a timestamp-based concurrency check is implemented.

*   **The Problem:** If User A opens an article and starts editing, and User B opens the same article and saves their changes first, User A's subsequent save would overwrite User B's work without warning.
*   **The Solution:** The app records a timestamp when an article is loaded. This timestamp is sent to the save workflow. The workflow compares this "load timestamp" with the SharePoint item's "Last Modified" date before saving.
    *   If the `loadTimestamp` is *older* than the `Modified` date, it means someone else has saved the article since the current user loaded it. The workflow rejects the save and returns a "Save Conflict" error.
    *   If the `loadTimestamp` is *not older* than the `Modified` date, it is safe to save, and the workflow proceeds.

#### 3.3.1. Power App Implementation

A local variable, `locLoadTimestamp`, is used to store the timestamp. It is crucial that this variable is set at the moment the user loads the data they intend to edit.

*   **On New Article:** The "New" button sets the timestamp.
    *   *Control:* `btn_New` | *Property:* `OnSelect`
        ```powerapps
        // ... existing NewForm logic ...
        UpdateContext({ locLoadTimestamp: Now() });
        ```
*   **On Selecting an Existing Article:** The gallery's `OnSelect` property sets the timestamp.
    *   *Control:* `gal_Articles` | *Property:* `OnSelect`
        ```powerapps
        // ... existing EditForm/Set logic ...
        UpdateContext({ locLoadTimestamp: Now() });
        ```
*   **Passing to Flow:** The `locLoadTimestamp` variable is included in the JSON object sent to the Power Automate workflow.

### 3.4. Backend State Confirmation (Polling Pattern)

To handle backend replication delays, especially with SharePoint create, update, or delete operations, a robust polling pattern is implemented within the Power Automate flows themselves. This ensures the Power App only proceeds after the backend state is guaranteed.

*   **The Problem:** A flow (e.g., `Instant-DiscardArticleDraft`) performs a `Delete item` action. SharePoint reports success to the flow immediately, but the deletion takes a few seconds to propagate across its backend. If the Power App refreshes its data source in this small window, it receives stale data where the item still exists, causing UI failures.

*   **The Solution: Backend Polling in Power Automate:** The flow is made responsible for confirming its own work.

    1.  **Initialize Variable:** After the primary action (e.g., `Delete item`), a boolean variable `IsStateConfirmed` is initialized to `false`.
    2.  **Do Until Loop:** A `Do until` loop runs until `IsStateConfirmed` is `true`.
    3.  **Poll for State:** Inside the loop, a `Get items` action queries SharePoint to check for the desired state. For a deletion, it queries for the item that was just deleted (`CanonicalArticleID eq '...' and ArticleVersion eq '...'`).
    4.  **Condition:** A condition checks if the `Get items` returns 0 records. If it does (confirming the deletion), the `IsStateConfirmed` variable is set to `true`, exiting the loop.
    5.  **Delay:** If the condition is false, a `Delay` action waits for a few seconds before the loop runs again.
    6.  **Respond to App:** The final action in the flow, `Respond to a Power App`, is only reached *after* the loop has successfully confirmed the state. It returns a status to the app.

*   **Power App Simplification:** With the flow guaranteeing the backend state, the Power App's logic becomes simple and reliable. It no longer needs timers or complex workarounds. The app simply calls the flow, waits for the response, and then safely refreshes its data.
    ```powerapps
    // A simplified example from the 'Discard Draft' action:

    // 1. Run the intelligent flow and wait for its response.
    // The app pauses here until the flow confirms the item is deleted.
    UpdateContext({ locDiscardResult: 'Instant-DiscardArticleDraft'.Run(gblSelectedItem.ID, ...) });

    // 2. Check the flow's response status.
    If(locDiscardResult.status = "Success",
        // --- On Success ---
        Notify(locDiscardResult.message, NotificationType.Success);
        Refresh('Knowledge Base Articles');
        Set(gblSelectedItem, LookUp('Knowledge Base Articles', ...));
    ,
        // --- On Failure ---
        Notify(locDiscardResult.message, NotificationType.Error)
    );
    ```

## 4. Naming Conventions

The app follows a standard naming convention: `[ControlTypeAbbreviation]_[ScreenName]_[Purpose]`.

*   **Screens:** `scr_Browse`, `scr_Edit`
*   **Galleries:** `gal_Articles`
*   **Forms:** `frm_Article`
*   **Buttons:** `btn_Submit`, `btn_SaveDraft`
*   **Icons:** `ico_NavigateToEdit`

## 5. App Startup, Architecture, and UI Logic

This section provides a comprehensive overview of the application's core client-side architecture and logic. It covers three main areas:

1.  **App Startup & Deep Linking:** The logic within `App.OnStart` that handles incoming URL parameters to enable deep linking directly to specific articles.
2.  **Workflow Integration Architecture:** The high-level design of how the Power App orchestrates and interacts with the decoupled Power Automate approval workflows.
3.  **Screen Breakdown & UI Logic:** The detailed implementation of the application's screens, forms, and state management.

For a detailed breakdown of the startup logic, architectural patterns, controls, properties, and formulas, please see the [App Startup, Architecture, and UI Logic](./power-app-features/ScreenBreakdownAndLogic.md) document.

## 6. Delegable Filtering and Searching

This section details the "helper column" architecture used to implement performant, delegable filtering and searching on complex Person columns in SharePoint, overcoming the 500-2000 item limit. It covers the SharePoint and Power Automate configuration, the Power App implementation of a custom filter component, and the advanced debugging process that led to the robust `Switch()` pattern.

For a detailed guide on the architecture, implementation, and debugging, please see the [Delegable Filtering and Searching](./power-app-features/DelegableFilteringAndSearching.md) document.

## 7. Article Versioning Feature

This section details the UI implementation for viewing historical article versions, creating new drafts from them, and managing the article lifecycle (discarding drafts, archiving). It includes the logic for the version history dialog, in-form previews, and the various action buttons.

For a detailed guide on the controls, formulas, and implementation patterns, please see the [Article Versioning Feature](./power-app-features/ArticleVersioningFeature.md) document.

## 8. Archived History Viewer & Reactivation

This feature is composed of two distinct but related components: a front-end UI for viewing archived articles and a back-end workflow for reactivating them.

### 8.1. Archive Viewer (UI)

The Archive Viewer provides a read-only mode within the Power App, allowing users to browse, search, and view the full version history of articles stored in the `Knowledge Base Articles Archive` list. This is managed via an icon toggle (`ico_ArchiveView`) that controls the `locIsArchiveView` variable, which in turn dynamically switches the main gallery's data source. This ensures a seamless user experience without duplicating screens.

For a detailed guide on the UI controls, state management, and dynamic gallery filtering, please see the [Archived History Management](./power-app-features/ArchivedHistoryManagement.md) document.

### 8.2. Article Reactivation (Backend Workflow)

The Reactivation process is handled by a robust, transactional Power Automate flow (`Instant - Reactivate Archived Article`) that ensures data integrity. The flow uses a commit/rollback pattern: it first copies all article versions to the active list while collecting their IDs, and only upon successful creation of a new draft does it commit the changes by deleting the original archive items. If any step fails, the flow automatically rolls back the changes by deleting any newly created active items, preventing orphaned records and ensuring the system remains in a clean state.

For a detailed guide on the transactional architecture, step-by-step implementation of the Power Automate workflow, and advanced error handling, please see the [Instant - Reactivate Archived Article](../power-automate-flows/flow-designs/Instant_-_Reactivate_Archived_Article.md) document.

## 9. Generic UI Components

This section documents the implementation of reusable UI components, focusing on a generic, data-driven confirmation dialog that provides a consistent user experience for critical actions like reverting, discarding, or archiving articles.

For a detailed guide on the implementation, context variables, and control properties, please see the [Generic UI Components](./power-app-features/GenericUIComponents.md) document.

## 10. UI/UX Best Practices

This section outlines key UI/UX best practices implemented in the app, including patterns for consistent read-only visuals, handling blank dates, and managing spacing in modern containers.

For a detailed guide on these UI/UX patterns, please see the [UI/UX Best Practices](./power-app-features/UIUXBestPractices.md) document.

## 11. Troubleshooting & Key Fixes (Direct SharePoint Connection)

This section documents critical fixes and solutions for issues encountered when connecting the Power App directly to SharePoint data sources.

For a detailed breakdown of the troubleshooting steps and key fixes, please see the [Troubleshooting & Key Fixes](./power-app-features/TroubleshootingAndKeyFixes.md) document.

## 12. Advanced Troubleshooting

This section documents critical, non-obvious issues encountered during development and their definitive solutions, covering topics like retrieving item IDs in a V2 architecture, handling stale flow connections, and resolving image URL and data type issues.

For a detailed breakdown of these troubleshooting scenarios, please see the [Advanced Troubleshooting](./power-app-features/AdvancedTroubleshooting.md) document.

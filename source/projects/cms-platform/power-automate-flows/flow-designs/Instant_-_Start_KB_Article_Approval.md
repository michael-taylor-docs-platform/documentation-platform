---
title: Instant - Start KB Article Approval (V2 - Decoupled Response)
category: architecture
audience:
  - developers
  - solution-architects
  - engineering-leaders
tags:
  - power-automate
  - power-automate-integration
  - workflow-orchestration
  - lifecycle-management
  - transactional-pattern
  - state-management
  - concurrency-control
  - response-handling
project: knowledge-base-manager
layer: workflow
status: published
summary: Decoupled Power Automate workflow for initiating KB article review, implementing synchronous locking and structured response handling to the Power App, conditional regional routing, asynchronous approval processing, audit logging, and deterministic lifecycle state management.
---

# Instant - Start KB Article Approval (V2 - Decoupled Response)

This document provides a complete, granular specification for the `Instant - Start KB Article Approval` workflow, ensuring it follows the established V2 decoupled response pattern for consistency and robustness.

## Overview

This workflow is triggered on-demand from the Power App to initiate the formal review process for a KB article. It provides immediate feedback to the user while handling routing and potentially long-running approvals in the background.

### 1. Architectural Context

This workflow is a key component of the V3 decoupled application architecture. It is not a standalone process but is orchestrated and called directly by the main Power App. For a complete understanding of how this flow integrates with the user interface and other backend processes, please see the central design document.

*   **Parent Document:** [`App Startup, Architecture, and UI Logic`](../../power-app-design/power-app-features/ScreenBreakdownAndLogic.md)

Its primary responsibilities are:
1.  Receive the `ArticleID` from the Power App.
2.  Lock the article to prevent concurrent reviews.
3.  Route the article to the correct approval path based on the author's region.
4.  Provide immediate synchronous feedback to the Power App to confirm the review has started.
5.  Manage the long-running approval process asynchronously.
6.  Reliably unlock the article upon completion or failure.

### 2. Architectural Pattern

1.  **Default to Failure:** The flow initializes response variables to a "Failure" state.
2.  **Synchronous Logic in Try/Catch:** The flow gets the article and author details, then uses a `Switch` to route by region. Each regional branch contains a `Try/Catch` block for its synchronous actions (e.g., locking the item, updating status). If the synchronous actions succeed, response variables are updated to reflect success.
3.  **Single Immediate Response:** A single `Respond to a PowerApp or flow` action is placed after the main `Switch`. It runs regardless of the outcome and sends the final status of the variables back to the app.
4.  **Conditional Asynchronous Approval:** For branches requiring a long-running approval (i.e., Europe), the `Start and wait for an approval` action is placed *after* the response and is configured to run only if its preceding `Try` block was successful.

## Detailed Implementation Steps

### 1. Trigger: PowerApps (V2)

- **Action:** `PowerApps (V2)`
- **Name:** `PowerApps (V2)`
- **Inputs:** The trigger will require two inputs from the Power App:
    - **Name:** `ArticleID`
    - **Type:** `Number`
    - **Required:** `Yes`
    - **Name:** `appURL`
    - **Type:** `Text`
    - **Required:** `Yes`

### 2. Initialize Variables

These actions must be placed immediately after the trigger.

*   **Action 1: Initialize `responseStatus`**
    *   **Name:** `Initialize_responseStatus`
    *   **Type:** `String`
    *   **Value:** `Failed`
*   **Action 2: Initialize `responseMessage`**
    *   **Name:** `Initialize_responseMessage`
    *   **Type:** `String`
    *   **Value:** `An unknown error occurred while starting the review process.`

## Workflow Logic

### 1. Get KB Article Details
- **Action:** `Get item` (SharePoint)
- **Name:** `GetKBArticle`
- **Site Address:** `(kmt_KnowledgeManagementSharePointSiteURL)` (Environment Variable)
- **List Name:** `(kmt_KnowledgeManagementKBArticlesListName)` (Environment Variable)
- **Id:** `@triggerBody()?['ArticleID']`
- **Purpose:** This action retrieves all the properties and column values for the SharePoint list item based on the `ArticleID` passed from the Power App.

### 2. Get Author's Profile
- **Action:** `Get user profile (V2)` (Office 365 Users)
- **Name:** `GetAuthorProfile`
- **Purpose:** This action retrieves the Office 365 user profile of the person who last authored the article. This is essential for routing the approval based on the author's region.
- **Configuration:**
    - **User (UPN):** `@outputs('GetKBArticle')?['body/LastAuthor/Email']`

### 3. Route Approval based on Author's Region
- **Action:** `Switch`
- **Name:** `Check Region`
- **Purpose:** This action routes the approval to a specific regional approval path. If the author's region doesn't match a defined case, it proceeds to a default process.
- **Configuration:**
    - **On:** `@coalesce(outputs('GetAuthorProfile')?['body/country'], '')`
- **Note:** The input to the Switch is wrapped in a `coalesce()` expression. This is a robust error-handling mechanism that prevents the flow from failing if the author's `country` field is null or empty in their user profile. If the field is blank, the expression provides an empty string, which safely routes the logic to the `Default Case`.
- **Cases:**
    - **Case 'EU':** Contains the dedicated approval process for authors based in Europe, which includes a long-running approval and requires a locking mechanism.
    - **Default:** Contains the standard process for all other regions, which involves posting to a Teams channel and terminating.

### 4. Default Case Logic

This branch executes if the author's region does not match the 'EU' case. It uses a `Try/Catch` block to handle the synchronous actions and provide immediate feedback to the Power App.

#### 4.1. Try Block (Default Case)

- **Action: `Update Status to Waiting for Reviewer`**
    - **Action:** `Update item` (SharePoint)
    - **Purpose:** Sets the article's status to "Waiting for Reviewer" to indicate it is pending SME assignment.
    - **Configuration:**
        - **Id:** `@outputs('GetKBArticle')?['body/ID']`
        - **Status Value (`field_4`):** `Waiting for Reviewer`

- **Action: `Post SME Request to Teams Channel`**
- **Action: Run a Child Flow (Log Audit Event - Default)**
    - **Purpose:** To log that the review process has started.
    - **Child Flow:** `Instant - LogAuditEvent`
    - **Parameters:**
        - `action`: `Article Submitted for Review`
        - `modifiedBy`: `outputs('GetAuthorProfile')?['body/mail']`
        - `canonicalArticleId`: `outputs('GetKBArticle')?['body/CanonicalArticleID']`
        - `articleVersion`: `outputs('GetKBArticle')?['body/ArticleVersion']`
        - `details`: `An article was submitted for review; routed to Default (Teams) process.`
        - `contentDiff`: `''`
    - **Action:** `Post card in a chat or channel` (Microsoft Teams)
    - **Purpose:** Posts an Adaptive Card to the designated channel to request an SME to volunteer for the review.
    - **Configuration:**
        - **Post as:** `Flow bot`
        - **Post in:** `Channel`
        - **Team:** `(kmt_KnowledgeManagementTeamId)` (Environment Variable - **MUST be the Team's GUID**)
        - **Channel:** `(kmt_KnowledgeManagementKBReviewChannelId)` (Environment Variable - **MUST be the Channel's GUID**)
        - **Message:** An Adaptive Card JSON payload (see below).

- **Adaptive Card & Deep Link Implementation:**
    - The action uses a detailed Adaptive Card to present the request, showing the Article ID, Title, and Author.
    - The card includes an `Action.OpenUrl` button titled "View Article in Power App".
    - The `url` for this button is dynamically constructed to create a deep link that opens the Power App directly to the correct article.
    - **URL Expression:**
        ```
        concat(triggerBody()?['text'], '?tenantId=3e04753a-ae5b-42d4-a86d-d6f05460f9e4&ArticleID=', outputs('GetKBArticle')?['body/field_3'])
        ```
    - **Breakdown of the URL:**
        1.  `triggerBody()?['text']`: Retrieves the base URL for the Power App passed from the trigger. **Note:** For a V2 trigger, text inputs are referenced by order (`text`, `text_1`, etc.), not by the name given in the trigger UI (`appURL`).
        2.  `?tenantId=...`: Appends the required tenant ID query parameter.
        3.  `&ArticleID=...`: Appends the `ArticleID` parameter, passing the unique ID (`field_3`) of the current article from the `GetKBArticle` step.
        4.  This complete URL is processed by the deep linking logic configured in the Power App's `App.OnStart` property.

    - **Adaptive Card JSON Schema:**
        ```json
        {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "New KB Article Ready for Review",
                    "weight": "Bolder",
                    "size": "Medium"
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {
                            "title": "Article ID:",
                            "value": "@{outputs('GetKBArticle')?['body/field_3']}"
                        },
                        {
                            "title": "Title:",
                            "value": "@{outputs('GetKBArticle')?['body/Title']}"
                        },
                        {
                            "title": "Author:",
                            "value": "@{outputs('GetKBArticle')?['body/LastAuthor/DisplayName']}"
                        }
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "View Article in Power App",
                    "url": "@{concat(triggerBody()?['text'], '?tenantId=3e04753a-ae5b-42d4-a86d-d6f05460f9e4&ArticleID=', outputs('GetKBArticle')?['body/field_3'])}"
                }
            ]
        }
        ```

- **Action: `Set Success Response Variables`**
    - **Action 1: Set `responseStatus`**
        - **Name:** `Set_variable_responseStatus_to_Success`
        - **Value:** `Success`
    - **Action 2: Set `responseMessage`**
        - **Name:** `Set_variable_responseMessage_to_Success`
        - **Value:** `The review request has been posted to the SME channel.`

#### 4.2. Catch Block (Default Case)

This block only runs if any action in the preceding `Try` block fails.

- **Configure run after:** Click the ellipsis (...) on the `Catch` scope and select "Configure run after". Check **only** the `has failed`, `is skipped`, and `has timed out` box for the `Try` scope.
- **Inside the Catch Scope:**
    - **Action 1: Set Failure Message**
        - **Action:** `Set variable`
        - **Name:** `Set_variable_responseMessage_on_Failure`
        - **Value:** `An error occurred while posting the request to Teams. Error: @{result('Try_Default_Review')[0]?['error']?['message']}`
    - **Action 2: Log System Error**
        - **Action:** `Run a Child Flow`
        - **Flow:** `Child Flow - LogSystemEvent`
        - **Parameters (Standardized Schema):**
            - `logLevel` (Text): `Error`
            - `source` (Text): `Instant - Start KB Article Approval (Default Case)`
            - `message` (Text): `variables('responseMessage')`
            - `context` (Text):
                ```json
                {
                  "articleID": "@{triggerBody()?['number']}",
                  "appURL": "@{triggerBody()?['text']}"
                }
                ```

#### 4.3. Respond to Power App (Default Case)

This action is the final step in the `Default Case` branch. It is configured to run after the `Catch_Default_Review` scope, regardless of whether the preceding `Try` block succeeded or failed. This guarantees that the Power App always receives a response for this branch.

- **Action:** `Respond to a PowerApp or flow`
- **Configure run after:** Click the ellipsis (...) on this action and select "Configure run after". Check the boxes for `is successful`, `has failed`, `is skipped`, and `has timed out` for the `Catch_Default_Review` scope.
- **Outputs:**
    - **`responsestatus`** (Text): `variables('responseStatus')`
    - **`responsemessage`** (Text): `variables('responseMessage')`

### 5. Case 'EU' Logic

This branch executes if the author's `country` from their O365 profile is `EU`. It uses a `Try/Catch` block to manage the initial synchronous actions before kicking off the long-running approval.

#### 5.1. Try Block (EU Case)

- **Action: `Lock Article and Set Status`**
    - **Action:** `Update item` (SharePoint)
    - **Purpose:** This single, atomic action performs two critical functions: it "locks" the item by setting the `RunningWorkflowID` and simultaneously updates the `Status` to "In Review".
    - **Configuration:**
        - **Id:** `@outputs('GetKBArticle')?['body/ID']`
        - **RunningWorkflowID:** `@workflow()['run']['name']`
        - **Status Value (`field_4`):** `In Review`

- **Action: `Set Success Response Variables`**
- **Action: Run a Child Flow (Log Audit Event - EU)**
    - **Purpose:** To log that the review process has started.
    - **Child Flow:** `Instant - LogAuditEvent`
    - **Parameters:**
        - `action`: `Article Submitted for Review`
        - `modifiedBy`: `outputs('GetAuthorProfile')?['body/mail']`
        - `canonicalArticleId`: `outputs('GetKBArticle')?['body/CanonicalArticleID']`
        - `articleVersion`: `outputs('GetKBArticle')?['body/ArticleVersion']`
        - `details`: `User submitted article for review; routed to EU (Approvals) process.`
        - `contentDiff`: `''`
    - **Action 1: Set `responseStatus`**
        - **Name:** `Set_variable_responseStatus_to_Success`
        - **Value:** `Success`
    - **Action 2: Set `responseMessage`**
        - **Name:** `Set_variable_responseMessage_to_Success`
        - **Value:** `The article has been sent for EU approval.`

#### 5.2. Catch Block (EU Case)

This block only runs if the `Update item` action in the `Try` block fails.

- **Configure run after:** Check **only** the `has failed` box for the `Try` scope.
- **Inside the Catch Scope:**
    - **Action 1: Set Failure Message**
        - **Action:** `Set variable`
        - **Name:** `Set_variable_responseMessage_on_Failure`
        - **Value:** `An error occurred while starting the EU approval process. Error: @{result('Try_Europe')[0]?['error']?['message']}`
    - **Action 2: Log System Error**
        - **Action:** `Run a Child Flow`
        - **Flow:** `Child Flow - LogSystemEvent`
        - **Parameters (Standardized Schema):**
            - `logLevel` (Text): `Error`
            - `source` (Text): `Instant - Start KB Article Approval (EU Case)`
            - `message` (Text): `variables('responseMessage')`
            - `context` (Text):
                ```json
                {
                  "articleID": "@{triggerBody()?['number']}",
                  "appURL": "@{triggerBody()?['text']}"
                }
                ```

#### 5.3. Respond to Power App (EU Case)

This action is the final synchronous step in the `EU Case` branch. It is configured to run after the `Catch_Europe_Review` scope, regardless of whether the preceding `Try` block succeeded or failed. This guarantees that the Power App always receives a response for this branch.

- **Action:** `Respond to a PowerApp or flow`
- **Name:** `Respond_to_a_Power_App_-_Europe`
- **Configure run after:** Click the ellipsis (...) on this action and select "Configure run after". Check the boxes for `is successful`, `has failed`, `is skipped`, and `has timed out` for the `Catch_Europe_Review` scope.
- **Outputs:**
    - **`responsestatus`** (Text): `variables('responseStatus')`
    - **`responsemessage`** (Text): `variables('responseMessage')`

### 6. Asynchronous EU Approval Process

This section only runs if the initial synchronous part of the EU case was successful. It runs completely in the background, after the response has already been sent to the Power App.

- **Configure run after:** The entire block of actions below will have their "run after" configured to depend on the `Respond_to_a_Power_App_-_Europe` action. Crucially, the *first* action (`Start and wait for Europe approval`) must also be configured to run only if the `Catch_Europe_Review` scope was skipped. This ensures the long-running process only starts if the `Try` block succeeded.

- **Action: `Start and wait for Europe approval`**
    - **Action:** `Start and wait for an approval` (Approvals)
    - **Configure run after:** Check **only** the `is skipped` box for the `Catch_Europe_Review` scope.
    - **Purpose:** Formally initiates the approval process, pausing the workflow until the approver responds.
    - **Configuration:**
        - **Approval type:** `Approve/Reject - First to respond`
        - **Assigned to:** `euapprovalDLPlaceholder@trendmicro.com` (Placeholder for EU Reviewers DL)
        - **Title:** `KB Article Review Request: @{outputs('GetKBArticle')?['body/Title']}`
        - **Item link:** `concat(triggerBody()?['text'], '?tenantId=3e04753a-ae5b-42d4-a86d-d6f05460f9e4&ArticleID=', outputs('GetKBArticle')?['body/field_3'])`

- **Action: `Condition: Check Europe Approval Outcome`**
    - **Purpose:** Checks the outcome of the approval task.
    - **Condition:** `Outcome` from the approval action `is equal to` `Approve`.
    - **If Yes (Approved):**
        - **Action: `Update Status to Approved & Unlock`**
            - **Action:** `Update item` (SharePoint)
            - **Purpose:** Finalizes the approval by setting the `Status` to "Approved", recording the `ApprovedDate`, capturing comments, and clearing the `RunningWorkflowID` to unlock the article.
            - **Configuration:**
                - **Id:** `@outputs('GetKBArticle')?['body/ID']`
                - **Status Value (`field_4`):** `Approved`
                - **ApprovedDate:** `@utcNow()`
                - **Review Comments (`field_10`):** `@outputs('Start_and_wait_for_Europe_approval')?['body/responses']?[0]?['comments']`
                - **RunningWorkflowID:** `null` (Set using an expression)
    - **If No (Rejected):**
        - **Action: `Update Status to Draft & Unlock`**
            - **Action:** `Update item` (SharePoint)
            - **Purpose:** Processes the rejection by setting the `Status` back to "Draft", saving comments, and clearing the `RunningWorkflowID` to unlock the article.
            - **Configuration:**
                - **Id:** `@outputs('GetKBArticle')?['body/ID']`
                - **Status Value (`field_4`):** `Draft`
                - **Review Comments (`field_10`):** `@outputs('Start_and_wait_for_Europe_approval')?['body/responses']?[0]?['comments']`
                - **RunningWorkflowID:** `null` (Set using an expression)




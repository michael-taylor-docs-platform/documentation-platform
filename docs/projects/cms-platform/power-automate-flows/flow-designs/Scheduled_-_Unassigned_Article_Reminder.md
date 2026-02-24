# Design Doc: Scheduled - Article Review Reminder

**Prerequisite:** This workflow requires a new column named `ReminderTimestamp` (Date and Time type) to be added to the `Knowledge Base Articles` SharePoint list.

This document provides a complete, granular specification for the `Scheduled - Article Review Reminder` workflow. This workflow is designed to be robust, maintainable, and clearly documented.

## 1.0. Overview

This workflow runs on a daily schedule to identify and act upon knowledge base articles that have become stale in the review process. It handles two distinct scenarios in parallel:

### 1.1. Architectural Context

This scheduled workflow is a supporting background process for the V3 decoupled application architecture. It is not triggered by the Power App directly but is a critical part of the ecosystem, ensuring articles do not get stuck in the approval pipeline. For a complete understanding of the main application logic that this flow supports, please see the central design document.

*   **Parent Document:** [`ScreenBreakdownAndLogic.md`](../../power-app-design/power-app-features/ScreenBreakdownAndLogic.md)

### 1.2. Core Responsibilities

1.  **Unassigned Articles:** It finds articles in the "Waiting for Reviewer" status for more than 24 hours and posts a general reminder to the Knowledge Management team channel.
2.  **Stale Assigned Articles:** It finds articles in the "In Review" status for more than 24 hours and sends a direct reminder to the assigned Subject Matter Expert (SME) via a private Teams chat.

Its primary responsibilities are:
1.  Run automatically every hour.
2.  Simultaneously query for stale unassigned articles and stale assigned articles.
3.  For unassigned articles, post a public reminder to a Teams channel.
4.  For assigned articles, send a private reminder to the assigned SME.
5.  Update each reminded article in SharePoint to refresh its `Modified` date, preventing continuous reminders.

## 2.0. Detailed Implementation Steps

### 2.1. Trigger: Schedule

- **Action:** `Recurrence`
- **Name:** `Recurrence`
- **Purpose:** This trigger will automatically run the workflow every hour.
- **Configuration:**
    - **Interval:** `1`
    - **Frequency:** `Hour`

### 2.2. Initialize App URL Variable

Immediately after the trigger, the flow must initialize a variable to hold the hard-coded URL for the Power App.

**Note on Hard-Coding:** While using an Environment Variable is best practice, it has proven unreliable in this specific context for scheduled flows. To ensure maximum reliability for the deep links in the reminder notifications, the URL is hard-coded here. If the Power App URL ever changes, this variable **must** be updated.

- **Action:** `Initialize variable`
- **Name:** `Initialize_varAppURL`
- **Variable Name:** `varAppURL`
- **Type:** `String`
- **Value:** `https://apps.powerapps.com/play/e/6a796a64-8b93-e3d8-9837-7d6a4b43508c/a/ff359c83-d62e-4b89-a659-6454df83cca1`

### 2.3. Parallel Branches

To handle both scenarios simultaneously, the workflow will use a `Parallel branch` control immediately after the initialization step.

---

### 3.0. Branch A: Unassigned Article Reminders

This branch handles articles waiting for an SME to be assigned.

#### 3.1. Get Stale, Unassigned Articles

- **Action:** `Get items` (SharePoint)
- **Name:** `Get_Stale_Unassigned_Articles`
- **Purpose:** Queries the SharePoint list to find all articles that are unassigned and have not been modified in the last 24 hours.
- **Configuration:**
    - **Site Address:** `(kmt_KnowledgeManagementSharePointSiteURL)` (Environment Variable)
    - **List Name:** `(kmt_KnowledgeManagementKBArticlesListName)` (Environment Variable)
    - **Filter Query:** `field_4 eq 'Waiting for Reviewer' and Modified le '@{addDays(utcNow(), -1)}'`
- **Filter Query Breakdown:**
    - `field_4 eq 'Waiting for Reviewer'`: Selects only articles in the unassigned queue.
    - `Modified le '@{addDays(utcNow(), -1)}'`: Selects articles not modified within the last 24 hours.
- **Scalability - Pagination:**
    - To ensure the flow can process more than the default 100 items, pagination must be enabled.
    - In the action's settings (click **...** > **Settings**):
        - **Pagination:** Turn the toggle **On**.
        - **Threshold:** Set the limit to `5000`.

#### 3.2. Process Each Unassigned Article

- **Action:** `Apply to each`
- **Name:** `For_each_unassigned_article`
- **Purpose:** This loop iterates through every article returned by the `Get_Stale_Unassigned_Articles` action.
- **Configuration:**
    - **Select an output from previous steps:** `value` (from `Get_Stale_Unassigned_Articles`)

##### 3.2.1. Post Reminder to Teams Channel

- **Action:** `Post card in a chat or channel` (Microsoft Teams)
- **Name:** `Post_Unassigned_Reminder_Card`
- **Purpose:** Posts a public Adaptive Card to the main KM Team channel.
- **Configuration:**
    - **Post as:** `Flow bot`
    - **Post in:** `Channel`
    - **Team:** `(kmt_KnowledgeManagementTeamId)` (Environment Variable - **MUST be the Team's GUID**)
    - **Channel:** `(kmt_KnowledgeManagementKBReviewChannelId)` (Environment Variable - **MUST be the Channel's GUID**)
    - **Adaptive Card:** (See JSON schema in Appendix A)

##### 3.2.2. Update Modified Timestamp (Unassigned)

- **Action:** `Update item` (SharePoint)
- **Name:** `Update_Timestamp_for_Unassigned`
- **Purpose:** Updates the item's `Modified` date by writing the current time to the dedicated `ReminderTimestamp` column.
- **Configuration:**
    - **Id:** `@items('For_each_unassigned_article')?['ID']`
    - **ReminderTimestamp:** `@utcNow()`

---

### 4.0. Branch B: Assigned SME Reminders

This branch handles articles that are assigned to an SME but have not been actioned.

#### 4.1. Get Stale, Assigned Articles

- **Action:** `Get items` (SharePoint)
- **Name:** `Get_Stale_Assigned_Articles`
- **Purpose:** Queries the SharePoint list to find all articles that are "In Review" and have not been modified in the last 24 hours.
- **Configuration:**
    - **Site Address:** `(kmt_KnowledgeManagementSharePointSiteURL)` (Environment Variable)
    - **List Name:** `(kmt_KnowledgeManagementKBArticlesListName)` (Environment Variable)
    - **Filter Query:** `field_4 eq 'In Review' and Modified le '@{addDays(utcNow(), -1)}'`
- **Filter Query Breakdown:**
    - `field_4 eq 'In Review'`: Selects only articles currently assigned to an SME for review.
    - `Modified le '@{addDays(utcNow(), -1)}'`: Selects articles not modified within the last 24 hours.
- **Scalability - Pagination:**
    - To ensure the flow can process more than the default 100 items, pagination must be enabled.
    - In the action's settings (click **...** > **Settings**):
        - **Pagination:** Turn the toggle **On**.
        - **Threshold:** Set the limit to `5000`.

#### 4.2. Process Each Assigned Article

- **Action:** `Apply to each`
- **Name:** `For_each_assigned_article`
- **Purpose:** This loop iterates through every article returned by the `Get_Stale_Assigned_Articles` action.
- **Configuration:**
    - **Select an output from previous steps:** `value` (from `Get_Stale_Assigned_Articles`)

##### 4.2.1. Post Reminder to Assigned SME

- **Action:** `Post card in a chat or channel` (Microsoft Teams)
- **Name:** `Post_Assigned_Reminder_Card_to_SME`
- **Purpose:** Posts a private Adaptive Card directly to the assigned SME as a chat message.
- **Configuration:**
    - **Post as:** `Flow bot`
    - **Post in:** `Chat with Flow bot`
    - **Recipient:** `@items('For_each_assigned_article')?['AssignedSME']['Email']`
    - **Adaptive Card:** (See JSON schema in Appendix B)

##### 4.2.2. Update Modified Timestamp (Assigned)

- **Action:** `Update item` (SharePoint)
- **Name:** `Update_Timestamp_for_Assigned`
- **Purpose:** Updates the item's `Modified` date by writing the current time to the dedicated `ReminderTimestamp` column. This is a safe operation that does not conflict with the `RunningWorkflowID` used by the main approval workflow.
- **Configuration:**
    - **Id:** `@items('For_each_assigned_article')?['ID']`
    - **ReminderTimestamp:** `@utcNow()`

---

## 5.0. Appendix

### Appendix A: Adaptive Card for Unassigned Reminder

- **URL Expression for Deep Link:**
    ```
    concat(variables('varAppURL'), '?tenantId=3e04753a-ae5b-42d4-a86d-d6f05460f9e4&ArticleID=', items('For_each_unassigned_article')?['field_3'])
    ```
- **JSON Character Escaping:** The `value` for the `Title` field is wrapped in a nested `replace()` expression. This is critical for ensuring the Adaptive Card's JSON is not broken by special characters in the article title. The expression first replaces all backslashes (`\`) with a double backslash (`\\`), and then replaces all double quotes (`"`) with a backslash followed by a double quote (`\"`). This prevents unexpected card rendering failures.
- **JSON Schema:**
    ```json
    {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "Unassigned Article Reminder",
                "weight": "Bolder",
                "size": "Medium",
                "color": "Warning"
            },
            {
                "type": "TextBlock",
                "text": "The following article has been waiting for reviewer assignment for more than 24 hours. Please assign an SME to continue the review process.",
                "wrap": true
            },
            {
                "type": "FactSet",
                "facts": [
                    {
                        "title": "Article ID:",
                        "value": "@{items('For_each_unassigned_article')?['field_3']}"
                    },
                    {
                        "title": "Title:",
                        "value": "@{replace(replace(items('For_each_unassigned_article')?['Title'], '\', '\\'), '"', '\"')}"
                    }
                ]
            }
        ],
        "actions": [
            {
                "type": "Action.OpenUrl",
                "title": "View Article in Power App",
                "url": "@{concat(variables('varAppURL'), '?tenantId=3e04753a-ae5b-42d4-a86d-d6f05460f9e4&ArticleID=', items('For_each_unassigned_article')?['field_3'])}"
            }
        ]
    }
    ```

### Appendix B: Adaptive Card for Assigned SME Reminder

- **URL Expression for Deep Link:**
    ```
    concat(variables('varAppURL'), '?tenantId=3e04753a-ae5b-42d4-a86d-d6f05460f9e4&ArticleID=', items('For_each_assigned_article')?['field_3'])
    ```
- **JSON Character Escaping:** The `value` for the `Title` field is wrapped in a nested `replace()` expression. This is critical for ensuring the Adaptive Card's JSON is not broken by special characters in the article title. The expression first replaces all backslashes (`\`) with a double backslash (`\\`), and then replaces all double quotes (`"`) with a backslash followed by a double quote (`\"`). This prevents unexpected card rendering failures.
- **JSON Schema:**
    ```json
    {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "KB Article Review Reminder",
                "weight": "Bolder",
                "size": "Medium"
            },
            {
                "type": "TextBlock",
                "text": "This is a reminder that the following knowledge base article is assigned to you and has been awaiting your review for more than 24 hours.",
                "wrap": true
            },
            {
                "type": "FactSet",
                "facts": [
                    {
                        "title": "Article ID:",
                        "value": "@{items('For_each_assigned_article')?['field_3']}"
                    },
                    {
                        "title": "Title:",
                        "value": "@{replace(replace(items('For_each_assigned_article')?['Title'], '\', '\\'), '"', '\"')}"
                    }
                ]
            }
        ],
        "actions": [
            {
                "type": "Action.OpenUrl",
                "title": "View Article in Power App",
                "url": "@{concat(variables('varAppURL'), '?tenantId=3e04753a-ae5b-42d4-a86d-d6f05460f9e4&ArticleID=', items('For_each_assigned_article')?['field_3'])}"
            }
        ]
    }
    ```

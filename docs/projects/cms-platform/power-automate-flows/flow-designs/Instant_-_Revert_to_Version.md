# Revert to Version - Architecture and Implementation Plan

## 1. Executive Summary

This document outlines the architecture for a "Revert to Version" feature. This allows users to select a previous, historical version of an article and create a new draft based on that older content. This provides a safe and auditable way to roll back to a known good state without deleting any version history.

The solution follows the established "Create a New Item" architectural principle. It will introduce a new Power Automate flow (`Instant - Revert To Version`) and a new "Revert to this version" button in the Power App's version history dialog.

## 2. Guiding Principles

- **Non-Destructive:** The revert process is non-destructive. It does not delete or alter the version being reverted *from* (e.g., Version 3 in the user's example). It simply creates a new version (e.g., Version 4) that is a copy of the desired historical version (e.g., Version 2).
- **Clear Audit Trail:** The version numbers will continue to increment sequentially (V1, V2, V3, V4), ensuring a clear and unbroken history of changes.
- **Consistency:** The new flow will reuse the core logic from the existing `Instant - Create New Article Version` flow for consistency and reliability.

## 3. Workflow and Process Design

### 3.1. New Flow: `Instant - Revert To Version`

This is a new Power Automate flow, called directly from a "Revert to this version" button in the Power App.

- **Trigger:** `PowerApps (V2)`
- **Inputs:**
    - `revertFromItemID` (Number): The SharePoint `ID` of the historical article version to copy content from.
    - `latestItemID` (Number): The SharePoint `ID` of the current latest version, which needs its `IsLatestVersion` flag set to `No`.
    - `modifiedBy` (Text): The UPN/email of the user performing the action. Passed from `User().Email` in the app.

### 3.2. Detailed Configuration Steps (with Error Handling and Polling)

1.  **Initialize All Variables:** Add five `Initialize variable` actions at the start of the flow. This is a best practice to ensure all variables exist at the flow's global scope.
    *   **Action 1 (`responseStatus`):**
        *   **Name:** `responseStatus`
        *   **Type:** `String`
        *   **Value:** `Failure`
    *   **Action 2 (`responseMessage`):**
        *   **Name:** `responseMessage`
        *   **Type:** `String`
        *   **Value:** `An unknown error occurred during the revert process.`
    *   **Action 3 (`canonicalID`):**
        *   **Name:** `canonicalID`
        *   **Type:** `String`
        *   **Value:** (leave blank)
    *   **Action 4 (`IsCreationConfirmed`):**
        *   **Name:** `IsCreationConfirmed`
        *   **Type:** `Boolean`
        *   **Value:** `false`
    *   **Action 5 (`varNewArticleVersion`):**
        *   **Name:** `varNewArticleVersion`
        *   **Type:** `Integer`
        *   **Value:** `0`

2.  **Try (Scope):** Add a `Try` scope to contain all core logic. All subsequent steps until the `Catch` block should be placed inside this scope.

3.  **`Get Properties of Version to Revert From`**
    *   **Action:** `Get item` (SharePoint)
    *   **Id:** `revertFromItemID` from the trigger.

4.  **`Get Properties of Latest Version`**
    *   **Action:** `Get item` (SharePoint)
    *   **Id:** `latestItemID` from the trigger.

5.  **`Set New Version Number`**
    *   **Action:** `Set variable`
    *   **Name:** `varNewArticleVersion`
    *   **Value:** `int(add(outputs('Get_Properties_of_Latest_Version')?['body/ArticleVersion'], 1))`

6.  **`Compose New Article ID`**
    *   **Action:** `Compose`
    *   **Inputs:** `concat(outputs('Get_Properties_of_Version_to_Revert_From')?['body/CanonicalArticleID'], '-v', variables('varNewArticleVersion'))`

7.  **`Select Source Claims`**
    *   **Action:** `Select` (Data Operation)
    *   **From:** `outputs('Get_Properties_of_Version_to_Revert_From')?['body/Source']`
    *   **Map:**
        ```json
        {
          "Claims": "@{item()?['Claims']}"
        }
        ```
    *   **Note:** This action transforms the array of 'Person' objects into an array containing only their 'Claims' values, which is the format required by the SharePoint `Create item` action for multi-select Person fields.

8.  **`Select Contributors Claims`**
    *   **Action:** `Select` (Data Operation)
    *   **From:** `outputs('Get_Properties_of_Version_to_Revert_From')?['body/Contributors']`
    *   **Map:**
        ```json
        {
          "Claims": "@{item()?['Claims']}"
        }
        ```
    *   **Note:** This performs the same transformation as the previous step, but for the `Contributors` field.

9.  **`Create New Version Draft (from Reverted Content)`**
    *   **Action:** `Create item` (SharePoint)
    *   **Field Mappings (Copy from `Get Properties of Version to Revert From`):**
        *   `Title`
        *   `field_5` (Overview)
        *   `field_20` (ArticleContent)
        *   `field_14` (Keywords)
        *   `InternalNotes`
        *   `MetaTitle`
        *   `MetaDescription`
        *   `field_19` (Language)
        *   `field_11` (Solution Type)
        *   `field_7` (Author Region)
        *   `field_6` (Audience)
        *   `field_12` (Category)
        *   `field_13` (Product Version)
        *   `Product_x002f_Service`
        *   `isPrimary`
        *   `OwningBusinessUnit`
        *   `ContextSource`
        *   `SFDC_x0020_Article_x0020_Number`
        *   `SMEReviewer`
        *   `LastAuthor`
        *   `LegacyModifiedBy`
        *   `LegacyContributors`
        *   `LegacyAssignedSME`
        *   `LegacyCreatedBy`
    *   **Field Mappings (Override):**
        *   `Source`: `body('Select_Source_Claims')`
        *   `Contributors`: `body('Select_Contributors_Claims')`
        *   `field_3` (Article ID): `outputs('Compose_New_Article_ID')`
        *   `CanonicalArticleID`: `outputs('Get_Properties_of_Version_to_Revert_From')?['body/CanonicalArticleID']`
        *   `ArticleVersion`: `variables('varNewArticleVersion')`
        *   `field_4` (Status Value): `Draft`
        *   `IsLatestVersion`: `Yes`
        *   `field_10` (Review Comments): `null`
        *   `ApprovedDate`: `null`
        *   `GitHub URL`: `null`
        *   `field_15` (Publish On): `utcNow()`
        *   `field_16` (Expiration Date): `addToTime(utcNow(), 5, 'Year')`

10. **Backend Polling (`Do until` loop):**
    *   **10.1. Do Until Loop:**
        *   **Action:** `Do until` control.
        *   **Run until:** `IsCreationConfirmed` is equal to `true`.
    *   **10.2. Inside the Loop - Poll for New Item:**
        *   **Action:** `Get items` (SharePoint)
        *   **Filter Query:** `field_3 eq '@{outputs('Compose_New_Article_ID')}'`
        *   **Top Count:** `1`
    *   **10.3. Inside the Loop - Check Condition:**
        *   **Action:** `Condition` control.
        *   **Condition:** `length(outputs('Poll_for_New_Item')?['body/value'])` is greater than `0`.
        *   **If Yes branch (Transactional Logic):**
            *   **Action 1: `Update Old Latest Version Flag`**
                *   **Action:** `Update item` (SharePoint)
                *   **Id:** `triggerBody()?['number_1']`
                *   **IsLatestVersion:** `No`
            *   **Action 2: Log Audit Event**
                *   **Action:** `Run a Child Flow`
                *   **Flow:** `Instant - LogAuditEvent`
                *   **Parameters:**
                    *   `action` (Text): `Article Reverted`
                    *   `modifiedBy` (Text): `triggerBody()?['text']`
                    *   `canonicalArticleId` (Text): `outputs('Get_Properties_of_Version_to_Revert_From')?['body/CanonicalArticleID']`
                    *   `articleVersion` (Number): `variables('varNewArticleVersion')`
                    *   `details` (Text): `Concat('User reverted article to a previous version, creating new draft version ', variables('varNewArticleVersion'), '.')`
                    *   `contentDiff` (Text): (leave blank)
            *   **Action 3:** `Set variable` - `IsCreationConfirmed` to `true`.
            *   **Action 4:** `Set variable` - `responseStatus` to `Success`.
            *   **Action 5:** `Set variable` - `responseMessage` to `Successfully reverted to the selected version. A new draft has been created.`
            *   **Action 6:** `Set variable` - `canonicalID` to the `CanonicalArticleID` from the `Poll_for_New_Item` step: `first(outputs('Poll_for_New_Item')?['body/value'])?['CanonicalArticleID']`
        *   **If No branch:**
            *   **Action:** `Delay` for 2 seconds.

11. **Catch (Scope):** Add a `Catch` scope **after** the `Try` scope.
    *   **Configure run after:** Click the ellipsis (...) on the `Catch` scope and select "Configure run after". Check **only** the `has failed` box for the `Try` scope.
    *   **Inside the Catch Scope:**
        *   **Action 1: Set Failure Message**
            *   **Action:** `Set variable`
            *   **Name:** `responseMessage`
            *   **Value:** `An error occurred while reverting the article. Please contact support. Error: @{result('Try')[0]?['error']?['message']}`
        *   **Action 2: Log System Error**
            *   **Action:** `Run a Child Flow`
            *   **Flow:** `Child Flow - LogSystemEvent`
            *   **Parameters (Standardized Schema):**
                *   `logLevel` (Text): `Error`
                *   `source` (Text): `Instant - Revert to Version`
                *   `message` (Text): `variables('responseMessage')`
                *   `context` (Text):
                    ```json
                    {
                      "revertFromItemID": "@{triggerBody()?['number']}",
                      "latestItemID": "@{triggerBody()?['number_1']}",
                      "modifiedBy": "@{triggerBody()?['text']}"
                    }
                    ```

12. **Respond to Power App:** Add this action **after** the `Catch` scope.
    *   **Configure run after:** Click the ellipsis (...) and select "Configure run after". Check both the `is successful` and `is skipped` boxes for the `Catch` scope. This ensures this action runs regardless of whether the `Try` block succeeded or failed.
    *   **Action:** `Respond to a PowerApp or flow`
    *   **Outputs:**
        *   `responsestatus` (Text): `variables('responseStatus')`
        *   `responsemessage` (Text): `variables('responseMessage')`
        *   `canonicalid` (Text): `variables('canonicalID')`

## 4. Calling Document

This flow is called by the generic confirmation dialog. For the Power Fx implementation details of the `OnSelect` property that calls this flow, see the following document:

*   [`GenericUIComponents.md`](../../power-app-design/power-app-features/GenericUIComponents.md)

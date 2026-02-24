# Design: KB ID Generator Child Flow

## 1. Executive Summary
This document provides the detailed technical design and logic for the `KB-ID-Generator-Child` Power Automate flow. This flow is a reusable component designed to be called by parent flows (such as an API endpoint or a Power App) to handle the complex logic of generating and validating `Article ID` and `CanonicalArticleID` values for the Knowledge Base system. It operates based on a `mode` parameter to determine which logic path to execute.

## 2. Parent Flows

This child flow is called by the following parent flows:

*   [`Instant - Create New Article Version`](./Instant_-_Create_New_Article_Version.md)

## 3. Detailed Logic: ID Generation Flow (Child Flow)

This section provides the corrected, robust logic for the child flow to prevent save-time errors.

**Trigger:** `Manually trigger a flow`
*   **Inputs:** When defining the trigger, rename the default input names for clarity. **Crucially, the underlying expressions must use the original, immutable property names assigned by Power Automate, NOT the new titles.**
    *   `mode` (Text) -> `text`
    *   `canonicalArticleId` (Text) -> `text_1`
    *   `language` (Text) -> `text_2`
    *   `articleVersion` (Text) -> `text_3`
    *   `parentItemID` (Number) -> `number` (Required for `version` mode)
    *   `articlePayload` (Text) -> `text_4` (The JSON payload as a string. Required for `version` mode)

**Action: Initialize 6 variables**
*   `status` (String)
*   `NewArticleID` (String)
*   `NewCanonicalArticleID` (String)
*   `errorMessage` (String)
*   `NewArticleVersion` (Integer)
*   `NewItemID` (Integer)
*   `NewItemURL` (String)

**Action: Switch**
*   **On:** `triggerBody()?['text']`

---
### **Case: `new`**

1.  **Action: Condition** - `Is CanonicalArticleID provided?`
    *   **Condition:** `length(trim(triggerBody()?['text_1']))` is equal to `0`
    *   **Note:** This condition uses `trim()` to handle a specific requirement of the parent flow (`Instant-GenerateNextArticleID`). The parent flow intentionally passes a single space (`' '`) instead of a true empty string. This is because Power Automate can incorrectly wrap empty strings in quotes (`"''"`), causing them to evaluate as having a length of 2. The `trim()` function correctly removes the single space, allowing the length to be evaluated as `0` as intended.

    **If Yes (ID is blank, generate a new one):**
    1.  **Action: Get items (SP)** - `SP: Get Max ID from Active List`
        *   **Order By:** `CanonicalArticleID desc`, **Top Count:** `1`
    2.  **Action: Get items (SP)** - `SP: Get Max ID from Archive List`
        *   **Order By:** `CanonicalArticleID desc`, **Top Count:** `1`
    3.  **Action: Compose** - `Compose: Safe Active Max ID`
        *   **Inputs:** `if(empty(outputs('SP:_Get_Max_ID_from_Active_List')?['body/value']), 'KA-0000000', outputs('SP:_Get_Max_ID_from_Active_List')?['body/value'][0]?['CanonicalArticleID'])`
    4.  **Action: Compose** - `Compose: Safe Archive Max ID`
        *   **Inputs:** `if(empty(outputs('SP:_Get_Max_ID_from_Archive_List')?['body/value']), 'KA-0000000', outputs('SP:_Get_Max_ID_from_Archive_List')?['body/value'][0]?['CanonicalArticleID'])`
    5.  **Action: Compose** - `Compose: Highest Canonical ID`
        *   **Inputs:** `if(greater(outputs('Compose:_Safe_Active_Max_ID'), outputs('Compose:_Safe_Archive_Max_ID')), outputs('Compose:_Safe_Active_Max_ID'), outputs('Compose:_Safe_Archive_Max_ID'))`
    6.  **Action: Compose** - `Compose: Increment ID Number`
        *   **Inputs:** `add(int(last(split(outputs('Compose:_Highest_Canonical_ID'), '-'))), 1)`
    7.  **Action: Compose** - `Compose: Format New Canonical ID`
        *   **Inputs:** `concat('KA-', formatNumber(outputs('Compose:_Increment_ID_Number'), '0000000'))`
    8.  **Action: Set variable** - `Set NewCanonicalArticleID from format`
        *   **Name:** `NewCanonicalArticleID`
        *   **Value:** Output of `Compose: Format New Canonical ID`

    **If No (ID is provided, use it):**
    1.  **Action: Set variable** - `Set NewCanonicalArticleID from payload`
        *   **Name:** `NewCanonicalArticleID`
        *   **Value:** `triggerBody()?['text_1']`

2.  **Action: Compose** - `Compose: Format New Article ID`
    *   *This action runs after the condition and uses the variable for a reliable value.*
    *   **Inputs:** `concat(variables('NewCanonicalArticleID'), '-', triggerBody()?['text_2'], '-v1')`
3.  **Action: Set multiple variables**
    *   `status`: `Success`
    *   `NewArticleID`: Output of `Compose: Format New Article ID`
    *   `NewCanonicalArticleID`: `variables('NewCanonicalArticleID')`
    *   `NewArticleVersion`: `1`

---
### **Case: `version`**

1.  **Action: Get items (SP)** - `SP: Get Max Version for Article`
    *   **List Name:** Use Environment Variable `sp_list_active`.
    *   **Filter Query:** `CanonicalArticleID eq '@{triggerBody()?['text_1']}'`
    *   **Order By:** `ArticleVersion desc`, **Top Count:** `1`
2.  **Action: Compose** - `Compose: Increment Version Number`
    *   **Inputs:** `if(empty(outputs('SP:_Get_Max_Version_for_Article')?['body/value']), 1, add(int(outputs('SP:_Get_Max_Version_for_Article')?['body/value'][0]?['ArticleVersion']), 1))`
3.  **Action: Compose** - `Compose: Format New Version ID`
    *   **Inputs:** `concat(triggerBody()?['text_1'], '-', triggerBody()?['text_2'], '-v', string(outputs('Compose:_Increment_Version_Number')))`
4.  **Action: Get item (SP)** - `SP: Get Parent Article Properties`
    *   *This action fetches the full record of the parent item to be used for both the demotion and data-merge operations. It now runs before the update action.*
    *   **List Name:** Use Environment Variable `sp_list_active`.
    *   **Id:** `triggerBody()?['number']` (the `parentItemID` input).
5.  **Action: Parse JSON** - `Parse Payload`
    *   **Content:** `triggerBody()?['text_4']`
    *   **Schema:** *The schema must be updated to accept the pre-formatted object arrays for `contributors` and `source` from the main flow.*
       ```json
       {
           "type": "object",
           "properties": {
               "title": { "type": "string" },
               "overview": { "type": "string" },
               "articleContent": { "type": "string" },
               "lastAuthor": { "type": "string" },
               "metaTitle": { "type": "string" },
               "metaDescription": { "type": "string" },
               "audience": { "type": "string" },
               "productService": { "type": "string" },
               "isPrimary": { "type": "boolean" },
               "language": { "type": "string" },
               "productVersion": { "type": "string" },
               "owningBusinessUnit": { "type": "string" },
               "status": { "type": "string" },
               "expirationDate": { "type": "string" },
               "canonicalArticleId": { "type": "string" },
               "articleVersion": { "type": "string" },
               "keywords": { "type": "string" },
               "solutionType": { "type": "string" },
               "category": { "type": "string" },
               "publishOn": { "type": "string" },
               "internalNotes": { "type": "string" },
               "contextSource": { "type": "string" },
               "contributors": {
                   "type": "array",
                   "items": {
                       "type": "object",
                       "properties": {
                           "Claims": { "type": "string" }
                       },
                       "required": ["Claims"]
                   }
               },
               "source": {
                   "type": "array",
                   "items": {
                       "type": "object",
                       "properties": {
                           "Value": { "type": "string" }
                       },
                       "required": ["Value"]
                   }
               }
           }
       }
       ```
6.  **Action: Compose** - `Compose: Calculate Final PublishOn Date`
    *   **Inputs:** `if(and(not(empty(body('Parse_Payload')?['publishOn'])), greater(body('Parse_Payload')?['publishOn'], utcNow())), body('Parse_Payload')?['publishOn'], utcNow())`
    *   *Logic: Defaults to the current time unless the API provides a future date.*
7.  **Action: Compose** - `Compose: Calculate Final ExpirationDate`
    *   **Inputs:** `if(and(not(empty(body('Parse_Payload')?['expirationDate'])), less(body('Parse_Payload')?['expirationDate'], addToTime(utcNow(), 5, 'Year'))), body('Parse_Payload')?['expirationDate'], addToTime(utcNow(), 5, 'Year'))`
    *   *Logic: Defaults to 5 years from now unless the API provides an earlier date.*
8.  **Action: Compose** - `Compose: Merged Contributors`
    *   **Inputs:** `coalesce(body('Parse_Payload')?['contributors'], outputs('SP:_Get_Parent_Article_Properties')?['body/Contributors'])`
9.  **Action: Select** - `Select: Cleaned Contributors`
    *   **From:** `outputs('Compose:_Merged_Contributors')`
    *   **Map (Switch to text mode):**
        ```json
        {
          "Claims": "@{item()?['Claims']}"
        }
        ```
10. **Action: Compose** - `Compose: Merged Source`
    *   **Inputs:** `coalesce(body('Parse_Payload')?['source'], outputs('SP:_Get_Parent_Article_Properties')?['body/Source'])`
11. **Action: Select** - `Select: Cleaned Source`
    *   **From:** `outputs('Compose:_Merged_Source')`
    *   **Map (Switch to text mode):**
        ```json
        {
          "Value": "@{item()?['Value']}"
        }
        ```
12. **Action: Create item (SP)** - `SP: Create New Version`
    *   **List Name:** Use Environment Variable `sp_list_active`.
    *   **Field Mappings (Override):**
        *   `Article ID`: Output of `Compose: Format New Version ID`.
        *   `CanonicalArticleID`: `triggerBody()?['text_1']`.
        *   `ArticleVersion`: Output of `Compose: Increment Version Number`.
        *   `IsLatestVersion`: `Yes`.
        *   `Publish On`: Output of `Compose: Calculate Final PublishOn Date`.
        *   `Expiration Date`: Output of `Compose: Calculate Final ExpirationDate`.
    *   **Field Mappings (Coalesce from Source):**
        *   **Note:** The following table provides the complete list of `coalesce` expressions. For single-value Choice and Person fields, the expression must be placed in the "Enter custom value" input.

| SharePoint Field | Expression |
| :--- | :--- |
| **`Title`** | `coalesce(body('Parse_Payload')?['title'], outputs('SP:_Get_Parent_Article_Properties')?['body/Title'])` |
| **`Overview`** | `coalesce(body('Parse_Payload')?['overview'], outputs('SP:_Get_Parent_Article_Properties')?['body/field_5'])` |
| **`ArticleContent`** | `coalesce(body('Parse_Payload')?['articleContent'], outputs('SP:_Get_Parent_Article_Properties')?['body/field_20'])` |
| **`Keywords`** | `coalesce(body('Parse_Payload')?['keywords'], outputs('SP:_Get_Parent_Article_Properties')?['body/field_14'])` |
| **`Product Version`** | `coalesce(body('Parse_Payload')?['productVersion'], outputs('SP:_Get_Parent_Article_Properties')?['body/field_13'])` |
| **`Product/Service`** | `coalesce(body('Parse_Payload')?['productService'], outputs('SP:_Get_Parent_Article_Properties')?['body/Product_x002f_Service'])` |
| **`Category`** | `coalesce(body('Parse_Payload')?['category'], outputs('SP:_Get_Parent_Article_Properties')?['body/field_12'])` |
| **`InternalNotes`** | `coalesce(body('Parse_Payload')?['internalNotes'], outputs('SP:_Get_Parent_Article_Properties')?['body/InternalNotes'])` |
| **`ContextSource`** | `coalesce(body('Parse_Payload')?['contextSource'], outputs('SP:_Get_Parent_Article_Properties')?['body/ContextSource'])` |
| **`MetaTitle`** | `coalesce(body('Parse_Payload')?['metaTitle'], outputs('SP:_Get_Parent_Article_Properties')?['body/MetaTitle'])` |
| **`MetaDescription`** | `coalesce(body('Parse_Payload')?['metaDescription'], outputs('SP:_Get_Parent_Article_Properties')?['body/MetaDescription'])` |
| **`Audience`** | `coalesce(body('Parse_Payload')?['audience'], outputs('SP:_Get_Parent_Article_Properties')?['body/field_6/Value'])` |
| **`Language`** | `coalesce(body('Parse_Payload')?['language'], outputs('SP:_Get_Parent_Article_Properties')?['body/field_19/Value'])` |
| **`Solution Type`** | `coalesce(body('Parse_Payload')?['solutionType'], outputs('SP:_Get_Parent_Article_Properties')?['body/field_11/Value'])` |
| **`OwningBusinessUnit`** | `coalesce(body('Parse_Payload')?['owningBusinessUnit'], outputs('SP:_Get_Parent_Article_Properties')?['body/OwningBusinessUnit/Value'])` |
| **`LastAuthor`** Claims | `concat('i:0#.f|membership|', coalesce(body('Parse_Payload')?['lastAuthor'], outputs('SP:_Get_Parent_Article_Properties')?['body/LastAuthor/Email']))` |
| **`isPrimary`** | `coalesce(body('Parse_Payload')?['isPrimary'], outputs('SP:_Get_Parent_Article_Properties')?['body/isPrimary'])` |
| **`Contributors`** | `body('Select:_Cleaned_Contributors')` |
| **`Source`** | `body('Select:_Cleaned_Source')` |
| **`LegacyCreatedBy`** | `coalesce(body('Parse_Payload')?['legacyCreatedBy'], outputs('SP:_Get_Parent_Article_Properties')?['body/LegacyCreatedBy'])` |
| **`FirstPublishedDate`** | `coalesce(body('Parse_Payload')?['firstPublishedDate'], outputs('SP:_Get_Parent_Article_Properties')?['body/FirstPublishedDate'])` |
13. **Action: Update item (SP)** - `SP: Demote Parent Version`
    *   *This action now runs AFTER the new version is created, ensuring transactional integrity.*
    *   **Configure run after:** `SP: Create New Version` has succeeded.
    *   **List Name:** Use Environment Variable `sp_list_active`.
    *   **Id:** `triggerBody()?['number']` (the `parentItemID` input).
    *   **Article ID**: `outputs('SP:_Get_Parent_Article_Properties')?['body/field_3']` (From the action above, to satisfy the required field).
    *   **IsLatestVersion**: `No`
14. **Action: Set multiple variables**
    *   `status`: `Success`
    *   `NewArticleID`: Output of `Compose: Format New Version ID`
    *   `NewArticleVersion`: Output of `Compose: Increment Version Number`
    *   `NewItemID`: `ID` from `SP: Create New Version`.
    *   `NewItemURL`: `Link to item` from `SP: Create New Version`.

---
### **Case: `translation`**

1.  **Action: Get items (SP)** - `SP: Validate Primary Version`
    *   **Filter Query:** `CanonicalArticleID eq '@{triggerBody()?['text_1']}' and ArticleVersion eq @{triggerBody()?['text_3']} and isPrimary eq 1`
    *   **Top Count:** `1`
2.  **Action: Condition** - `Condition: Did Validation Succeed?`
    *   **Condition:** `length(outputs('SP:_Validate_Primary_Version')?['body/value'])` is greater than `0`.

**If Yes (Validation Succeeded):**
1.  **Action: Compose** - `Compose: Format Translation ID`
    *   **Inputs:** `concat(triggerBody()?['text_1'], '-', triggerBody()?['text_2'], '-v', triggerBody()?['text_3'])`
2.  **Action: Set multiple variables**
    *   `status`: `Success`
    *   `NewArticleID`: Output of `Compose: Format Translation ID`
    *   `NewCanonicalArticleID`: `triggerBody()?['text_1']`

**If No (Validation Failed):**
1.  **Action: Get items (SP)** - `SP: Get Primary Language Code`
    *   **Filter Query:** `CanonicalArticleID eq '@{triggerBody()?['text_1']}' and isPrimary eq 1`
    *   **Top Count:** `1`
2.  **Action: Compose** - `Compose: Primary Language Code`
    *   **Inputs:** `if(empty(outputs('SP:_Get_Primary_Language_Code')?['body/value']), 'n/a', outputs('SP:_Get_Primary_Language_Code')?['body/value'][0]?['Language'])`
3.  **Action: Compose** - `Compose: Error Message`
    *   **Inputs:** `concat('Validation Failed: The specified version (v', triggerBody()?['text_3'], ') does not exist for the primary article (', triggerBody()?['text_1'], ', ', outputs('Compose:_Primary_Language_Code'), ').')`
4.  **Action: Set multiple variables**
    *   `status`: `Failed`
    *   `errorMessage`: Output of `Compose: Error Message`

---
**(Outside the Switch)**

**Action: Respond to a PowerApp or flow**
*   **Outputs:**
    *   `status` (Text): `variables('status')`
    *   `NewArticleID` (Text): `variables('NewArticleID')`
    *   `NewCanonicalArticleID` (Text): `variables('NewCanonicalArticleID')`
    *   `errorMessage` (Text): `variables('errorMessage')`
    *   `NewArticleVersion` (Number): `variables('NewArticleVersion')`
    *   `NewItemID` (Number): `variables('NewItemID')`
    *   `NewItemURL` (Text): `variables('NewItemURL')`

---
## 4. Core Concept: The 'mode' Input Parameter

The `mode` input parameter is the key to making the `KB-ID-Generator-Child` flow reusable. It is a simple text value that acts as a command, telling the child flow which specific set of logic to execute. The parent flow (either the API Router or the refactored Power App flow) is responsible for determining the correct mode to use.

| Mode Value | Triggered By | Purpose |
| :--- | :--- | :--- |
| **`new`** | API Flow (if `canonicalArticleId` is not found in SharePoint) **OR** the refactored Power App flow. | If a `canonicalArticleId` is passed in, it uses it. If not, it finds the absolute highest `CanonicalArticleID` across both SharePoint lists and calculates the next sequential one. It returns the new IDs to the parent flow. |
| **`version`** | API Flow (if `canonicalArticleId` and `language` match an existing item) **OR** the Power App "Create New Version" flow. | Tells the child flow to calculate the next version number, demote the old version, and create the new version item in SharePoint using content provided by the parent. It returns the new IDs and URL to the parent flow. |
| **`translation`** | API Flow (if `canonicalArticleId` is provided but the `language` is new). | Tells the child flow to **validate** that the provided `articleVersion` exists for the primary version of the given `canonicalArticleId`. If it exists, it proceeds. If not, it returns a "Failed" status and a detailed error message. |

By using this parameter, we centralize all three complex logic scenarios into one reusable child flow, which is then commanded by different parent flows depending on their needs.

# Design Document: AI-Powered Alt Text & Article Save Workflow

**Version: 2.0**

## 1. Overview & Architectural Shift

This document outlines the architecture for the `Orchestrate-GenerateAltTextAndSaveArticle` Power Automate flow. This flow represents a significant architectural shift. It is no longer just an `alt` text generator; it is now the **central orchestrator for all article save and submit operations**, completely replacing the `Patch()` logic previously located in the Power App.

This change was made to accommodate the complex, multi-step server-side processing required for AI `alt` text generation, while also centralizing all critical business logic in a single, secure, and maintainable location.

## 2. Purpose & Core Responsibilities

*   **Centralized Business Logic:** Consolidate all business rules for creating and updating articles, including author/contributor management, ID generation, and status changes.
*   **AI `alt` Text Generation:** (Phased Approach) Parse embedded images from article HTML, call an external AI service to generate descriptions, and inject the results into the `alt` attribute of `<img>` tags.
*   **Data Persistence:** Reliably execute the final `Create Item` or `Update Item` operation in the `Knowledge Base Articles` SharePoint list.
*   **Security:** Securely manage the Bearer Token for the AI service, ensuring it is never exposed to the client-side Power App.
*   **Transactional Integrity:** Ensure that the article is saved only after all processing steps are complete.

## 3. User Auditing Strategy

Since this workflow runs under a service account context, the default SharePoint `Created By` and `Modified By` columns will always reflect the service account, not the end-user. To ensure a clear and accurate audit trail of user actions, the following fields are used:

*   **`LastAuthor` (Person Field):** This field is updated on every save/update operation with the `currentUserEmail` provided by the Power App. It serves as the definitive record of the **last person to modify the item**.

*   **`Contributors` (Multi-Person Field):** This field maintains a running list of everyone who has edited the article. The workflow logic automatically adds the *previous* `LastAuthor` to the `Contributors` list whenever a *different* user saves the article. This prevents duplicate entries while building a comprehensive history of all contributors.

This strategy ensures that even though the system uses a service account for operations, all user-driven modifications are accurately tracked and attributed to the correct individuals directly within the list item.

## 4. Detailed Architecture

### 4.1. Power App: The Trigger

The Power App's role is now simplified to data collection and triggering the workflow. The `OnSelect` properties of `btn_SaveDraft` and `btn_StartReview` will be completely replaced. The specific implementation for this is detailed in the following document:

*   **Calling Document:** [`ScreenBreakdownAndLogic.md`](../PowerApp_Standalone_DesignDoc/ScreenBreakdownAndLogic.md)

#### 4.1.1. Capturing the Load Timestamp (Concurrency Control)

To implement the timestamp-based concurrency check, a context variable `locLoadTimestamp` must be set whenever an article is loaded for viewing or editing.

*   **On the `OnSelect` property of your article gallery (`gal_KB`):**
    ```powerapps
    // When a user selects an item, set the selected item and record the time.
    Set(gblSelectedItem, ThisItem);
    UpdateContext({ locLoadTimestamp: Now() });
    ```

*   **On the `OnSelect` property of your "New" button:**
    ```powerapps
    // Add the locLoadTimestamp to your existing OnSelect logic
    NewForm(frm_ArticleContent);
    Set(gblSelectedItem, Blank());
    UpdateContext({ newMode: true, selectedTab: "KB Content", locLoadTimestamp: Now() });
    ```

This ensures that the `locLoadTimestamp` variable always holds the time the user *started* their session, which is crucial for the concurrency check.

#### 4.1.2. `OnSelect` Logic

The complete Power Fx formula and implementation details for the `OnSelect` property of the save buttons are maintained in the Power App's design document to ensure a single source of truth.

*   **Canonical Source:** [`ScreenBreakdownAndLogic.md`](../PowerApp_Standalone_DesignDoc/ScreenBreakdownAndLogic.md)

### 4.2. Power Automate Flow: `Orchestrate-GenerateAltTextAndSaveArticle`

This flow is the new heart of the save process.

*   **Trigger:** PowerApps (V2)
    *   **Input:** `jsonData` (Text) - Receives the single JSON string from the Power App.

**Execution Steps:**

1.  **Parse Input Data (`Parse JSON` action):**
        *   **Purpose:** This is the first and most critical step. It takes the single JSON text string from the Power App and converts it into a strongly-typed object with properties that can be used as dynamic content throughout the flow.
        *   **Content:** `triggerBody()['text']`
        *   **Schema:** This schema must match the JSON object being passed from the Power App. It has been updated to include the existing article identifiers for update scenarios.
            ```json
            {
                "type": "object",
                "properties": {
                    "itemID": { "type": "integer" },
                    "buttonPressed": { "type": "string" },
                    "isNewMode": { "type": "boolean" },
                    "loadTimestamp": { "type": "string", "format": "date-time" },
                    "currentUserEmail": { "type": "string" },
                    "isPrimary": { "type": ["boolean", "null"] },
                    "title": { "type": ["string", "null"] },
                    "overviewHTML": { "type": ["string", "null"] },
                    "articleHTML": { "type": ["string", "null"] },
                    "keywords": { "type": ["string", "null"] },
                    "internalNotesHTML": { "type": ["string", "null"] },
                    "metaTitle": { "type": ["string", "null"] },
                    "metaDescription": { "type": ["string", "null"] },
                    "reviewComments": { "type": ["string", "null"] },
                    "language": { "type": ["string", "null"] },
                    "solutionType": { "type": ["string", "null"] },
                    "authorRegion": { "type": ["string", "null"] },
                    "audience": { "type": ["string", "null"] },
                    "category": { "type": ["string", "null"] },
                    "productVersion": { "type": ["string", "null"] },
                    "productService": { "type": ["string", "null"] },
                    "source": { "type": ["string", "null"] },
                    "owningBusinessUnit": { "type": ["string", "null"] },
                    "assignedSME": { "type": ["string", "null"] },
                    "contributors": { "type": ["string", "null"] },
                    "previousLastAuthorEmail": { "type": ["string", "null"] },
                    "articleID": { "type": ["string", "null"] },
                    "canonicalArticleID": { "type": ["string", "null"] },
                    "articleVersion": { "type": ["number", "null"] },
                    "firstPublishedDate": { "type": ["string", "null"] },
                    "expirationDate": { "type": ["string", "null"] },
                    "publishOnDate": { "type": ["string", "null"] },
                    "contextSource": { "type": ["string", "null"] },
                    "sfdcArticleNumber": { "type": ["string", "null"] },
                    "legacyModifiedBy": { "type": ["string", "null"] },
                    "legacyContributors": { "type": ["string", "null"] },
                    "legacyAssignedSME": { "type": ["string", "null"] },
                    "legacyCreatedBy": { "type": ["string", "null"] }
                }
            }
            ```

2.  **Process Nested JSON from Power App (Scope):**
        *   **Purpose:** This scope isolates the logic required to parse the complex data types (arrays/objects) that the Power App stringifies before sending.
        *   **2.1. Parse `contributors` (`Parse JSON` action):**
            *   **Purpose:** To convert the stringified array of contributor user objects into a usable array of objects.
            *   **Content:** `body('Parse_Input_Data')?['contributors']`
            *   **Schema:**
                ```json
                {
                    "type": ["array", "null"],
                    "items": {
                        "type": "object",
                        "properties": {
                            "DisplayName": { "type": "string" },
                            "Email": { "type": "string" },
                            "Claims": { "type": "string" },
                            "Department": { "type": "string" },
                            "JobTitle": { "type": "string" },
                            "Picture": { "type": "string" }
                        }
                    }
                }
                ```
        *   **2.2. Parse `assignedSME` (`Parse JSON` action):**
            *   **Purpose:** To convert the stringified single user object into a usable object to reliably access its properties.
            *   **Content:** `body('Parse_Input_Data')?['assignedSME']`
            *   **Schema:**
                ```json
                {
                    "type": ["object", "null"],
                    "properties": {
                        "DisplayName": { "type": "string" },
                        "Email": { "type": "string" },
                        "Claims": { "type": "string" },
                        "Department": { "type": "string" },
                        "JobTitle": { "type": "string" },
                        "Picture": { "type": "string" }
                    }
                }
                ```
        *   **2.3. Parse `source` (`Parse JSON` action):**
            *   **Purpose:** To convert the stringified array of source choice objects into a usable array.
            *   **Content:** `body('Parse_Input_Data')?['source']`
            *   **Schema:**
                ```json
                {
                    "type": ["array", "null"],
                    "items": {
                        "type": "object",
                        "properties": { "Value": { "type": "string" } },
                        "required": [ "Value" ]
                    }
                }
                ```

3.  **Get Configuration from SharePoint (Scope):**
        *   **Purpose:** To retrieve dynamic configuration values, such as external endpoint URLs, from the `appConfiguration` SharePoint list. This avoids hardcoding values within the flow, making it more maintainable.
        *   **Action: `Get items` from SharePoint**
            *   **List Name:** `appConfiguration`
            *   **Filter Query:** `Title eq 'HTML_SANITIZER_URL'`
            *   **Top Count:** `1`
            *   **Note:** This action should be renamed to `Get_HTML_Sanitizer_URL_Config` for clarity.

4.  **Sanitize HTML Inputs (Scope):**
        *   **Purpose:** This scope calls the `html-sanitizer` Azure Function for each of the three rich text fields (`articleHTML`, `overviewHTML`, `internalNotesHTML`). This is a critical security and data integrity step that solves several complex issues simultaneously:
            1.  **Strips Invalid Characters:** Removes invisible XML control characters that break the downstream DITA conversion process.
            2.  **Removes Wrapper Tags:** Strips the extraneous `<div class=\"ExternalClass...\">` and `<p class=\"editor-paragraph\">` tags added by SharePoint and the Power Apps Rich Text Editor. This prevents the infinite nesting of tags with each save.
            3.  **Cleans Up Artifacts:** Removes empty `<p></p>` tags that are left behind as artifacts after stripping the invalid nested tags.
            4.  **Preserves Author Intent:** Intentionally preserves paragraph tags containing only a non-breaking space (`<p>&nbsp;</p>`), which is the standard way authors create blank lines in the editor.
        *   **Implementation Note:** The logic for items 2, 3, and 4 is handled entirely within the Node.js code of the Azure Function. The function relies on the default behavior of the `sanitize-html` library to strip un-allowed tags (like `div`) while keeping their content, and then uses a regular expression to clean up empty paragraph artifacts. No special configuration is needed in the HTTP actions below.
        *   **Configuration:** The actions inside this scope should be configured to run in parallel for efficiency.
        *   **4.1. Sanitize `articleHTML` (`HTTP` action):**
            *   **Method:** `POST`
            *   **URI:** `body('Get_HTML_Sanitizer_URL_Config')?['value']?[0]?['Value']`
            *   **Headers:** `Content-Type: application/json`
            *   **Body:**
                ```json
                {
                  "html": "@{body('Parse_Input_Data')?['articleHTML']}"
                }
                ```
            *   **Note:** This action should be renamed to `HTTP_-_Sanitize_articleHTML` for clarity.
        *   **4.2. Sanitize `overviewHTML` (`HTTP` action):**
            *   **Method:** `POST`
            *   **URI:** `body('Get_HTML_Sanitizer_URL_Config')?['value']?[0]?['Value']`
            *   **Headers:** `Content-Type: application/json`
            *   **Body:**
                ```json
                {
                  "html": "@{body('Parse_Input_Data')?['overviewHTML']}"
                }
                ```
            *   **Note:** This action should be renamed to `HTTP_-_Sanitize_overviewHTML` for clarity.
        *   **4.3. Sanitize `internalNotesHTML` (`HTTP` action):**
            *   **Method:** `POST`
            *   **URI:** `body('Get_HTML_Sanitizer_URL_Config')?['value']?[0]?['Value']`
            *   **Headers:** `Content-Type: application/json`
            *   **Body:**
                ```json
                {
                  "html": "@{body('Parse_Input_Data')?['internalNotesHTML']}"
                }
                ```
            *   **Note:** This action should be renamed to `HTTP_-_Sanitize_internalNotesHTML` for clarity.
        *   **4.4. Parse Sanitized `articleHTML` (`Parse JSON` action):**
            *   **Purpose:** To access the `cleanHtml` property from the sanitizer's response.
            *   **Content:** `body('HTTP_-_Sanitize_articleHTML')`
            *   **Schema:**
                ```json
                { "type": "object", "properties": { "cleanHtml": { "type": "string" } } }
                ```
        *   **4.5. Parse Sanitized `overviewHTML` (`Parse JSON` action):**
            *   **Purpose:** To access the `cleanHtml` property from the sanitizer's response.
            *   **Content:** `body('HTTP_-_Sanitize_overviewHTML')`
            *   **Schema:** (Same as above)
        *   **4.6. Parse Sanitized `internalNotesHTML` (`Parse JSON` action):**
            *   **Purpose:** To access the `cleanHtml` property from the sanitizer's response.
            *   **Content:** `body('HTTP_-_Sanitize_internalNotesHTML')`
            *   **Schema:** (Same as above)

5.  **Select contributor emails (`Select` action):**
        *   **Purpose:** To efficiently transform the array of contributor objects (from step 2.1) into a simple array of just their email addresses. This simplifies the logic for checking duplicates and constructing claims.
        *   **From:** `coalesce(body('Parse_contributors'), json('[]'))`
        *   **Note:** The `coalesce` function is critical here. It ensures that if the `Parse_contributors` step outputs `null` (because the input was empty), this step will receive an empty array `[]` instead of `null`, preventing a "BadRequest" error.
        *   **Map (Text Mode):** `item()?['Email']`

6.  **Initialize Variables:**
        *   **Purpose:** All variables used in the flow are initialized here for clarity and maintainability.
        *   `varFinalHTML` (String): `body('Parse_Sanitized_articleHTML')?['cleanHtml']`
        *   `varBase64Images` (Array): Leave empty.
        *   `varContributorEmails` (Array): Set to the **Output** of the `Select contributor emails` action.
        *   `varFinalContributors` (Array): Leave empty. This will be populated with claims objects.
        *   `newarticleid` (String): Initialize with an empty string: `''`.
        *   `newcanonicalarticleid` (String): Initialize with an empty string: `''`.
        *   `newarticleversion` (Integer): Initialize with the number `0`.
        *   `responseStatus` (String): Initialize as "Failure". This is a safeguard; it will be explicitly set to "Success" upon successful completion.
        *   `responseMessage` (String): Initialize as "An unknown error occurred during the save process."
        *   `responseItemID` (Integer): Initialize with the `itemID` from the `Parse_Input_Data` action. This ensures the ID is preserved even if the flow fails before it can be set.
        *   `isSaveConfirmed` (Boolean): Initialize to `false`. **Critical:** This variable controls the state confirmation polling loop. The flow will not proceed until this variable is explicitly set to `true`, guaranteeing that the SharePoint save operation has fully replicated before responding to the Power App.

7.  **Business Logic: Handle Author and Contributors (Scope):**
        *   **Purpose:** This scope manages the logic for accurately tracking all users who have edited an article. It uses a `Compose` action to safely handle potentially null input for the `previousLastAuthorEmail`.
        *   **7.1. Coalesce Previous Author Email (`Compose` action):**
            *   **Purpose:** This action takes the `previousLastAuthorEmail` (which can be `null` for new articles) and converts it into a guaranteed non-null value (an empty string `''`). This prevents downstream actions from failing.
            *   **Inputs:** `@coalesce(body('Parse_Input_Data')?['previousLastAuthorEmail'], '')`
        *   **7.2. Condition: Check if Previous Author should be added**
            *   **Condition:** This condition now safely checks if the coalesced email is not an empty string and is different from the current user.
            *   **Row 1:** `outputs('Coalesce_Previous_Author_Email')` | `is not equal to` | `''`
            *   **Row 2 (AND):** `outputs('Coalesce_Previous_Author_Email')` | `is not equal to` | `body('Parse_Input_Data')?['currentUserEmail']`
        *   **If Yes (Check for Duplicates):**
            *   **Condition:** Check if `varContributorEmails` array `contains` the output from the `Coalesce_Previous_Author_Email` action.
            *   **If No (Append previousLastAuthorEmail to Contributors):** Use the `Append to array variable` action to add the output from `Coalesce_Previous_Author_Email` to the `varContributorEmails` array.

8.  **Business Logic: Clean and Construct Final Contributor Objects (Scope):**
        *   **Purpose:** To create a clean, valid array of claims objects, ensuring no empty values are processed.
        *   **8.1. Filter out empty emails (`Filter array` action):**
            *   **Purpose:** This crucial step removes any blank or `null` entries from the `varContributorEmails` array. As observed, a simple check for an empty string (`''`) is not sufficient.
            *   **From:** `variables('varContributorEmails')`
            *   **Condition (Advanced Mode):** You must switch to "advanced mode" for the filter query and use the following expression. This correctly handles both empty strings and `null` values.
            *   **Expression:** `@not(empty(item()))`
        *   **8.2. Loop (`Apply to each`):** **This is a critical step.** The loop must iterate over the **output body** of the `Filter out empty emails` action from the previous step. Do **not** use the original `varContributorEmails` variable here, as that would re-introduce the empty values that were just filtered out.
        *   **Inside loop (Finalize contributors claims):** Use `Append to array variable` to add an object to `varFinalContributors`. The expression should use `item()` to refer to the current item in the loop.
            ```json
            { "Claims": "i:0#.f|membership|@{item()}" }
            ```

9.  **Business Logic: Handle New Item ID Generation (Scope):**
        *   **Purpose:** This scope runs the child flow to generate a new Article ID, but only for new articles.
        *   **Architectural Note:** This step has been refactored to call the `KB_ID_Generator_Child` flow directly, removing the redundant `Instant-GenerateNextArticleID` wrapper flow.
        *   **Condition:** Check if `isNewMode` from `Parse_Input_Data` is `true`.
        *   **If Yes (Run a Child Flow...):**
            *   **Action:** `Run a Child Flow`
            *   **Child Flow:** `KB_ID_Generator_Child`
            *   **Parameters:**
                *   `Mode`: `new`
                *   `CanonicalArticleId`: `' '` (single space)
                *   `Language`: `body('Parse_Input_Data')?['language']`
                *   `ArticleVersion`: `' '` (single space)
                *   `ParentItemID`: `0`
                *   `ArticlePayload`: `{}` (empty JSON object)
                *   **Note on Parameters:** The `CanonicalArticleId` and `ArticleVersion` fields are intentionally passed as a single space (`' '`) instead of a true empty string. This is a workaround for a Power Automate limitation where empty strings can be incorrectly handled. The `KB_ID_Generator_Child` flow is designed to `trim()` these inputs to correctly interpret them as empty.
            *   **Action:** `Set variable` for `newarticleid` with the `newarticleid` output from the `KB_ID_Generator_Child` step.
            *   **Action:** `Set variable` for `newcanonicalarticleid` with the `newcanonicalarticleid` output from the `KB_ID_Generator_Child` step.
            *   **Action:** `Set variable` for `newarticleversion` with the `newarticleversion` output from the `KB_ID_Generator_Child` step.

10. **Image Processing & `alt` Text Generation (Placeholder):**
        *   **Purpose:** This section is reserved for future AI image analysis.
        *   **Action:** This step must be **removed or disabled**. You correctly identified that this placeholder logic was overwriting the `varFinalHTML` variable, causing the article content to be blank.

11. **Error Handling and Response (`Try`, `Success`, `Catch` Scopes):**
        *   **Architectural Note:** This new structure, designed by you, is the most robust solution. It separates the success and failure logic into distinct, parallel scopes and uses a final response action configured to run after either path completes. This completely avoids all race conditions and ensures a reliable response.

        *   **11.1. Try (Scope):**
            *   **Purpose:** This scope contains only the core data persistence logic. If any action within it fails, execution immediately stops and moves to the `Catch` block.
            *   **Inside the Try Scope:**
                1.  **Condition: Check if `isNewMode` is `true`**
                2.  **If Yes (Create Path):**
                    *   **Action: `SharePoint - Create item`**
                    *   **Field Mappings:**
                        *   `Title`: `body('Parse_Input_Data')?['title']`
                        *   `field_5` (Overview): `body('Parse_Sanitized_overviewHTML')?['cleanHtml']`
                        *   `field_20` (Article Content): `variables('varFinalHTML')`
                        *   `field_14` (Keywords): `body('Parse_Input_Data')?['keywords']`
                        *   `InternalNotes`: `body('Parse_Sanitized_internalNotesHTML')?['cleanHtml']`
                        *   `MetaTitle`: `body('Parse_Input_Data')?['metaTitle']`
                        *   `MetaDescription`: `body('Parse_Input_Data')?['metaDescription']`

                    *   **State Confirmation Polling Loop (`Do until` action):**
                        *   **Purpose:** This is the implementation of the **Backend State Confirmation Pattern**. It solves the critical problem of SharePoint replication delay. After the `Create item` action is sent, this loop begins. It will continuously poll SharePoint until it receives confirmation that the new item has been successfully created and is retrievable. The flow will not proceed past this loop until the state is confirmed. This guarantees that when the flow finally responds to the Power App, the data is in a consistent and ready state, preventing UI refresh errors.
                        *   **Loop until:** `@equals(variables('isSaveConfirmed'), true)`
                        *   **Limit:** 60 retries with a timeout of 1 hour (PT1H). This provides a robust window for SharePoint to process the request.
                        *   **Inside the Loop:**
                            1.  **Action: `Get items` from SharePoint**
                                *   **Rename:** `Get_newly_created_article`
                                *   **Purpose:** To poll SharePoint for the existence of the item that was just created.
                                *   **List Name:** `Knowledge Base Articles`
                                *   **Filter Query:** `ArticleID eq '@{variables('newarticleid')}'`
                                *   **Top Count:** `1`
                            2.  **Action: `Condition - Check for new article`**
                                *   **Purpose:** To check if the `Get_newly_created_article` action returned any results.
                                *   **Condition:** `length(outputs('Get_newly_created_article')?['body/value'])` `is greater than` `0`
                                *   **If Yes:**
                                    *   **Action: `Set variable - isSaveConfirmed`**
                                        *   **Purpose:** The item has been found, confirming the save state. This action sets the `isSaveConfirmed` variable to `true`, which will terminate the `Do until` loop.
                                        *   **Name:** `isSaveConfirmed`
                                        *   **Value:** `true`
                                *   **If No:**
                                    *   **Action: `Delay`**
                                        *   **Purpose:** The item has not been found yet. This action pauses the flow for a few seconds before the loop runs again. This is essential to prevent the flow from hitting API throttling limits.
                                        *   **Count:** `2`
                                        *   **Unit:** `Seconds`

                    *   **Action: Set `responseItemID` variable**
                        *   **Value:** `body('Create_item')?['ID']`

                    *   **Action: `Do until`**
                        *   **Purpose:** To poll SharePoint and confirm the `Create item` operation has fully replicated before proceeding. This guarantees that the subsequent response to the Power App is based on a confirmed state.
                        *   **Loop until:** `length(body('Get_confirmation_item_-_Create')?['value'])` `is greater than` `0`
                        *   **Limit:** PT1M (1 minute timeout)
                        *   **Inside the Loop:**
                            1.  **Action: `Get items` from SharePoint**
                                *   **Rename:** `Get_confirmation_item_-_Create`
                                *   **List Name:** `Knowledge Base Articles`
                                *   **Filter Query:** `ArticleID eq '@{variables('newarticleid')}'`
                                *   **Top Count:** `1`
                            2.  **Action: `Delay`**
                                *   **Count:** `3`
                                *   **Unit:** `Seconds`
                                *   **Note:** This runs only if the `Get items` action returns 0 results.

                    *   **Action: Set `responseItemID` variable**
                        *   **Value:** `body('Create_item')?['ID']`

                3.  **If No (Update Path):**
                    *   **Condition: Concurrency Check**
                        *   **Purpose:** To prevent users from overwriting each other's work.
                        *   **Condition:** `body('Get_item')?['Modified']` `is greater than` `body('Parse_Input_Data')?['loadTimestamp']`
                    *   **If Yes (Save Conflict):**
                        *   **Action: Set `responseStatus` variable** to `Save Conflict`
                        *   **Action: Set `responseMessage` variable** to `It looks like someone else has updated this article since you opened it. Please refresh and try again.`
                    *   **If No (Proceed with Update):**
                        *   **Action: `SharePoint - Update item`**
                        *   **Field Mappings:** (Same as `Create item`, but using the `itemID` from the parsed JSON to identify the item to update)

                        *   **Action: `Do until`**
                            *   **Purpose:** To poll SharePoint and confirm the `Update item` operation has fully replicated.
                            *   **Loop until:** `length(body('Get_confirmation_item_-_Update')?['value'])` `is greater than` `0`
                            *   **Limit:** PT1M (1 minute timeout)
                            *   **Inside the Loop:**
                                1.  **Action: `Get items` from SharePoint**
                                    *   **Rename:** `Get_confirmation_item_-_Update`
                                    *   **List Name:** `Knowledge Base Articles`
                                    *   **Filter Query:** `ID eq '@{body('Parse_Input_Data')?['itemID']}' and Modified ge '@{utcNow()}'`
                                    *   **Note on Filter:** The `Modified ge '@{utcNow()}'` is a trick to confirm the update specifically. We are looking for the item whose modification timestamp is at or after the moment this flow started running.
                                    *   **Top Count:** `1`
                                2.  **Action: `Delay`**
                                    *   **Count:** `3`
                                    *   **Unit:** `Seconds`

            *   **Outside the `Try` Scope (in the `Success` parallel branch):**
                1.  **Action: Set `responseStatus` variable** to `Success`
                2.  **Action: Set `responseMessage` variable** to `Article saved successfully.`
                3.  **Action: Set `responseArticleID` variable** to `coalesce(variables('newarticleid'), body('Parse_Input_Data')?['articleID'])`
                4.  **Action: Set `responseCanonicalArticleID` variable** to `coalesce(variables('newcanonicalarticleid'), body('Parse_Input_Data')?['canonicalArticleID'])`
                5.  **Action: Set `responseArticleVersion` variable** to `coalesce(variables('newarticleversion'), body('Parse_Input_Data')?['articleVersion'])`
                        *   `field_10` (Review Comments): `body('Parse_Input_Data')?['reviewComments']`
                        *   `field_19` (Language): `body('Parse_Input_Data')?['language']`
                        *   `field_11` (Solution Type): `body('Parse_Input_Data')?['solutionType']`
                        *   `field_7` (Author Region): `body('Parse_Input_Data')?['authorRegion']`
                        *   `field_6` (Audience): `body('Parse_Input_Data')?['audience']`
                        *   `field_12` (Category): `body('Parse_Input_Data')?['category']`
                        *   `field_13` (Product Version): `body('Parse_Input_Data')?['productVersion']`
                        *   `Product_x002f_Service`: `body('Parse_Input_Data')?['productService']`
                        *   `isPrimary`: `body('Parse_Input_Data')?['isPrimary']`
                        *   `Source`: `coalesce(body('Parse_source'), json('[]'))`
                        *   `OwningBusinessUnit`: `body('Parse_Input_Data')?['owningBusinessUnit']`
                        *   `ContextSource`: `body('Parse_Input_Data')?['contextSource']`
                        *   `SFDC_x0020_Article_x0020_Number`: `body('Parse_Input_Data')?['sfdcArticleNumber']`
                        *   `SMEReviewerId`: `if(not(equals(body('Parse_assignedSME'), null)), body('Parse_assignedSME')?['Email'], null)`
                        *   `ContributorsId`: `variables('varFinalContributors')`
                        *   `LastAuthorId`: `body('Parse_Input_Data')?['currentUserEmail']`
                        *   `AssignedSMEEmail`: `if(not(equals(body('Parse_assignedSME'), null)), body('Parse_assignedSME')?['Email'], null)`
                        *   `lastAuthorEmail`: `body('Parse_Input_Data')?['currentUserEmail']`
                        *   `LegacyModifiedBy`: `body('Parse_Input_Data')?['legacyModifiedBy']`
                        *   `LegacyContributors`: `body('Parse_Input_Data')?['legacyContributors']`
                        *   `LegacyAssignedSME`: `body('Parse_Input_Data')?['legacyAssignedSME']`
                        *   `LegacyCreatedBy`: `body('Parse_Input_Data')?['legacyCreatedBy']`
                        *   `field_16` (Expiration Date): `if(empty(body('Parse_Input_Data')?['expirationDate']), json('null'), body('Parse_Input_Data')?['expirationDate'])`
                        *   `field_15` (Publish On Date): `if(empty(body('Parse_Input_Data')?['publishOnDate']), json('null'), body('Parse_Input_Data')?['publishOnDate'])`
                        *   `field_4` (Status): `if(equals(body('Parse_Input_Data')?['buttonPressed'], 'StartReview'), 'Ready for Review', 'Draft')`
                        *   `field_3` (Article ID): `variables('newarticleid')`
                        *   `CanonicalArticleID`: `variables('newcanonicalarticleid')`
                        *   `ArticleVersion`: `variables('newarticleversion')`
                        *   `FirstPublishedDate`: `if(empty(body('Parse_Input_Data')?['firstPublishedDate']), json('null'), body('Parse_Input_Data')?['firstPublishedDate'])`
                    *   **Action:** `Set variable` for `responseItemID` with the `ID` output from the `Create item` action.
                    *   **Action: Compose - Assemble Override Body (New)**
                        *   **Purpose:** To create a valid JSON object for the override request, allowing the Power Automate engine to handle character escaping correctly. This prevents "Invalid JSON" errors caused by special characters in the sanitized HTML.
                        *   **Inputs:**
                            ```json
                            {
                              "__metadata": {
                                "type": "SP.Data.Knowledge_x0020_Base_x0020_ArticlesListItem"
                              },
                              "field_5": "@{body('Parse_Sanitized_overviewHTML')?['cleanHtml']}",
                              "field_20": "@{variables('varFinalHTML')}",
                              "InternalNotes": "@{body('Parse_Sanitized_internalNotesHTML')?['cleanHtml']}"
                            }
                            ```
                    *   **Action: `Send an HTTP request to SharePoint` (Rich Text Override - New)**
                        *   **Purpose:** This action is the definitive fix for SharePoint incorrectly adding wrapper tags. It uses the SharePoint REST API to directly overwrite the specified fields with the clean, sanitized data.
                        *   **Site Address:** `[Your SharePoint Site]`
                        *   **Method:** `POST`
                        *   **Uri:** `_api/web/lists/getbytitle('Knowledge Base Articles')/items(@{outputs('Create_new_article')?['body/ID']})`
                        *   **Headers:**
                            ```json
                            {
                              "Content-Type": "application/json;odata=verbose",
                              "Accept": "application/json;odata=verbose",
                              "X-HTTP-Method": "MERGE",
                              "IF-MATCH": "*"
                            }
                            ```
                        *   **Body:** `outputs('Compose_-_Assemble_Override_Body_(New)')`
                    *   **Action: `Send an HTTP request to SharePoint` (Rich Text Override)**
                        *   **Purpose:** This action mirrors the fix in the update path. It runs *after* the `Create item` action and uses the SharePoint REST API to immediately overwrite the rich text fields with the clean, sanitized HTML. This is necessary because even when creating a new item, the standard `Create item` action can corrupt clean HTML if the target column is a Rich Text field. This ensures that new articles are stored correctly from the very beginning.
                        *   **Site Address:** `[Your SharePoint Site]`
                        *   **Method:** `POST`
                        *   **Uri:** `_api/web/lists/getbytitle('Knowledge Base Articles')/items(@{outputs('Create_item')?['body/ID']})`
                        *   **Headers:**
                            ```json
                            {
                              "Content-Type": "application/json;odata=verbose",
                              "Accept": "application/json;odata=verbose",
                              "X-HTTP-Method": "MERGE",
                              "IF-MATCH": "*"
                            }
                            ```
                        *   **Body:**
                            ```json
                            {
                              "__metadata": {
                                "type": "SP.Data.Knowledge_x0020_Base_x0020_ArticlesListItem"
                              },
                              "field_5": "@{body('Parse_Sanitized_overviewHTML')?['cleanHtml']}",
                              "field_20": "@{variables('varFinalHTML')}",
                              "InternalNotes": "@{body('Parse_Sanitized_internalNotesHTML')?['cleanHtml']}"
                            }
                            ```
                    *   **Action:** `Set variable` for `responseStatus` to "Success".
                    *   **Action:** `Set variable` for `responseMessage` to "Your new article has been created successfully."
                    *   **Action: Run a Child Flow (Log Audit Event - Create)**
                        *   **Purpose:** To log the successful creation of the article to the audit log.
                        *   **Child Flow:** `Instant - LogAuditEvent`
                        *   **Parameters:**
                            *   `action`: `Article Created`
                            *   `modifiedBy`: `body('Parse_Input_Data')?['currentUserEmail']`
                            *   `canonicalArticleId`: `variables('newcanonicalarticleid')`
                            *   `articleVersion`: `variables('newarticleversion')`
                            *   `details`: `User created a new article draft.`
                            *   `contentDiff`: `''`
                3.  **If No (Update Path):**
                    *   **1. Get Current Item Metadata:**
                        *   **Action:** `SharePoint - Get item`
                        *   **ID:** `body('Parse_Input_Data')?['itemID']`
                    *   **2. Concurrency Check (Condition):**
                        *   **Purpose:** This condition implements the user-proposed concurrency check. It compares the timestamp from when the app loaded the data against the item's last modified date in SharePoint.
                        *   **Condition:** `outputs('Get_Current_Item_Metadata')?['body/Modified']` is greater than `body('Parse_Input_Data')?['loadTimestamp']`
                        *   **If Yes (Conflict Found):**
                            *   **Action: Set `responseStatus` variable** to "Failure".
                            *   **Action: Set `responseMessage` variable** to "Save Conflict: This article was modified by another user after you opened it. Please refresh the app and try again."
                        *   **If No (Safe to Save):**
                            *   **Action: `SharePoint - Update item`**
                                *   **ID:** `body('Parse_Input_Data')?['itemID']`
                                *   **Field Mappings:** Use the same field mappings as the `Create item` action, with the following exceptions:
                                    *   `field_3` (Article ID): `body('Parse_Input_Data')?['articleID']`
                                    *   `CanonicalArticleID`: `body('Parse_Input_Data')?['canonicalArticleID']`
                                    *   `ArticleVersion`: `body('Parse_Input_Data')?['articleVersion']`
                            *   **Action: Compose - Assemble Override Body (Update)**
                                *   **Purpose:** To create a valid JSON object for the override request, allowing the Power Automate engine to handle character escaping correctly. This prevents "Invalid JSON" errors caused by special characters in the sanitized HTML.
                                *   **Inputs:**
                                    ```json
                                    {
                                      "__metadata": {
                                        "type": "SP.Data.Knowledge_x0020_Base_x0020_ArticlesListItem"
                                      },
                                      "field_5": "@{body('Parse_Sanitized_overviewHTML')?['cleanHtml']}",
                                      "field_20": "@{variables('varFinalHTML')}",
                                      "InternalNotes": "@{body('Parse_Sanitized_internalNotesHTML')?['cleanHtml']}"
                                    }
                                    ```
                            *   **Action: `Send an HTTP request to SharePoint` (Rich Text Override)**
                                *   **Purpose:** This action is the definitive fix for the SharePoint rich text issue. It uses the SharePoint REST API to directly overwrite the rich text fields with the clean, sanitized HTML.
                                *   **Site Address:** `[Your SharePoint Site]`
                                *   **Method:** `POST`
                                *   **Uri:** `_api/web/lists/getbytitle('Knowledge Base Articles')/items(@{body('Parse_Input_Data')?['itemID']})`
                                *   **Headers:**
                                    ```json
                                    {
                                      "Content-Type": "application/json;odata=verbose",
                                      "Accept": "application/json;odata=verbose",
                                      "X-HTTP-Method": "MERGE",
                                      "IF-MATCH": "*"
                                    }
                                    ```
                                *   **Body:** `outputs('Compose_-_Assemble_Override_Body_(Update)')`
                            *   **Action: Set `responseStatus` variable** to "Success".
                            *   **Action: Set `responseMessage` variable** to "Your changes have been saved successfully."
                           *   **Action: Run a Child Flow (Log Audit Event - Update)**
                                *   **Purpose:** To log the successful update of the article to the audit log.
                                *   **Child Flow:** `Instant - LogAuditEvent`
                                *   **Parameters:**
                                    *   `action`: `Article Updated`
                                    *   `modifiedBy`: `body('Parse_Input_Data')?['currentUserEmail']`
                                    *   `canonicalArticleId`: `body('Parse_Input_Data')?['canonicalArticleID']`
                                    *   `articleVersion`: `body('Parse_Input_Data')?['articleVersion']`
                                    *   `details`: `User saved changes to an existing article draft.`
                                    *   `contentDiff`: `''`

        *   **11.2. Catch (Scope):**
            *   **Purpose:** This scope runs only when an unexpected system error occurs inside the `Try` block (e.g., SharePoint is down). It will not run for handled business logic failures like a save conflict, as those paths now set their own response variables.
            *   **Configuration:** Configure the `Run after` for this scope to only execute if the `Try` scope `has failed`.
            *   **Inside the Catch Scope:**
                *   **Action 1: Set Failure Message**
                    *   **Action:** `Set variable`
                    *   **Name:** `responseMessage`
                    *   **Value:** `An unexpected error occurred during the save process. Please contact support. Error: @{result('Try')[0]?['error']?['message']}`
                *   **Action 2: Log System Error**
                    *   **Action:** `Run a Child Flow`
                    *   **Flow:** `Child Flow - LogSystemEvent`
                    *   **Parameters (Standardized Schema):**
                        *   `logLevel` (Text): `Error`
                        *   `source` (Text): `Orchestrate-GenerateAltTextAndSaveArticle`
                        *   `message` (Text): `variables('responseMessage')`
                        *   `context` (Text):
                            ```json
                            {
                              "itemID": "@{body('Parse_Input_Data')?['itemID']}",
                              "buttonPressed": "@{body('Parse_Input_Data')?['buttonPressed']}",
                              "isNewMode": "@{body('Parse_Input_Data')?['isNewMode']}",
                              "currentUserEmail": "@{body('Parse_Input_Data')?['currentUserEmail']}",
                              "canonicalArticleID": "@{body('Parse_Input_Data')?['canonicalArticleID']}",
                              "articleVersion": "@{body('Parse_Input_Data')?['articleVersion']}"
                            }
                            ```

        *   **11.3. Final Response (Guaranteed Execution):**
            *   **Purpose:** This single action, placed after the `Try` and `Catch` scopes, sends the final response back to the Power App.
            *   **Action:** `Respond to a PowerApp or flow`.
            *   **Configuration:** This is the most critical configuration. The `Respond` action must run after the `Catch` block, regardless of whether it was skipped (because `Try` succeeded) or ran successfully (because `Try` failed). This guarantees the `Respond` action always runs.
                *   Select the `Catch` scope as the only preceding action.
                *   Check the box for `is successful`.
                *   Check the box for `is skipped`.
            *   **Note:** This covers all possibilities. If `Try` succeeds, `Catch` is skipped, and the `Respond` action runs. If `Try` fails, `Catch` runs and succeeds, and the `Respond` action runs.
            *   **Outputs:**
                *   `status` (Text): `variables('responseStatus')`
                *   `message` (Text): `variables('responseMessage')`
                *   `itemID` (Number): `variables('responseItemID')`

## 5. Phased Implementation Plan

1.  **Phase 1 (Current):**
    *   Implement the full Power App and Power Automate changes as described above, but with the **placeholder** `alt` text logic.
    *   This allows the new architecture to be fully tested end-to-end.
2.  **Phase 2 (Future):**
    *   Set up the On-premises data gateway.
    *   Create a Custom Connector in Power Automate for the AI API that uses the gateway.
    *   Replace the placeholder `alt` text logic in the flow with the real HTTP call via the Custom Connector.

This detailed design ensures all business logic is preserved and provides a clear, maintainable, and scalable architecture for future enhancements.
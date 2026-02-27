# App Startup, Architecture, and UI Logic

The `App.OnStart` property is configured to handle incoming URL parameters, enabling deep linking directly to a specific article. This is the primary mechanism used by external systems (like Power Automate approval notifications) to direct users to the correct content.

```powerapps
// --- Create collections for text field autocomplete ---
ClearCollect(colCategories, Distinct('Knowledge Base Articles', Category));
ClearCollect(colProductVersions, Filter(Distinct('Knowledge Base Articles', 'Product Version'), !IsBlank(Value)));
// --- Load choices for Choice columns into local collections ---
ClearCollect(colSolutionTypes, Choices('Knowledge Base Articles'.'Solution Type'));
//ClearCollect(colLanguages, Choices('Knowledge Base Articles'.Language));
Set(gblIsAdmin, 'Util-CheckIfUserIsAdmin'.Run(User().Email).isadmin);

// 1. Create the final collection directly from the source list,
//    giving it the correct {Product: ...} schema.
ClearCollect(colMasterProducts,
    ForAll('Trend Naming Guidelines',
        {
            Product: field_1
        } 
    )
);

// 2. Add the custom "All" option.
Collect(colMasterProducts, {Product: "All products/services"});

Set(gblCurrentUser, Office365Users.MyProfileV2());

// Set the SharePoint domain root for resolving relative image URLs.
Set(gblSharePointDomain, "https://trendmicro.sharepoint.com");

// Set the base URL for the app, used for deep linking in approval emails.
// This should be updated for different environments (Dev, UAT, Prod).
Set(gblAppURL, "https://apps.powerapps.com/play/e/6a796a64-8b93-e3d8-9837-7d6a4b43508c/a/ff359c83-d62e-4b89-a659-6454df83cca1");


// --- Deep Linking Logic ---
// Check if an 'ArticleID' parameter is present in the URL
If(!IsBlank(Param("ArticleID")),
    // If it exists, look up the corresponding article in the main list.
    Set(
        gblSelectedItem,
        LookUp(
            'Knowledge Base Articles',
            field_3 = Param("ArticleID") && IsLatestVersion = true
        )
    );

    // Set a variable that will be used to pre-populate the search box,
    // effectively filtering the gallery to the deep-linked item.
    Set(gblSearchOnLoad, gblSelectedItem.CanonicalArticleID);

    // Set a flag to clear any other active filters on the gallery screen.
    Set(gblClearFiltersOnLoad, true);

    // Also set the concurrency timestamp for the loaded record.
    Set(locLoadTimestamp, Now());
);
```

**How It Works:**

1.  **`Param("ArticleID")`**: On app load, this function checks if an `ArticleID` parameter was included in the launch URL (e.g., `...&ArticleID=KA-00123`).
2.  **`LookUp(...)`**: If the parameter exists, a `LookUp` is performed against the `'Knowledge Base Articles'` data source to find the single record that matches the provided `ArticleID` (`field_3`) and is also marked as the latest version (`IsLatestVersion = true`).
3.  **`Set(gblSelectedItem, ...)`**: The found record is loaded into the `gblSelectedItem` global variable. The app's UI, particularly the main form, is already configured to automatically display the record stored in this variable.
4.  **`Set(locLoadTimestamp, Now())`**: Critically, the `locLoadTimestamp` global variable is also set. This ensures that the app's concurrency control mechanism functions correctly for an article loaded via a deep link, preventing a user from accidentally overwriting changes made while the approval notification was in transit.

---

## Application Architecture & Workflow Integration

The V3 architecture represents a fundamental shift from a monolithic, SharePoint-triggered approval system to a decoupled, event-driven model orchestrated directly by the Power App. This change enhances reliability, provides better real-time user feedback, and simplifies the backend logic.

The Power App is now the primary initiator of all key approval and lifecycle events.

### Core Approval Workflows

The old, single `KBApprovalProcessWorkflow` has been replaced by a suite of smaller, more focused flows that are called on-demand by the Power App.

*   **Start KB Article Approval (`Instant - Start KB Article Approval`):** When a user clicks "Start Review", the Power App first saves the draft and then explicitly calls this flow. This flow is responsible for setting the article's status to `Waiting for Reviewer` and posting the initial notification to the Teams channel for SME assignment.
    *   **See detailed design:** [`Instant - Start KB Article Approval`](../../power-automate-flows/flow-designs/Instant_-_Start_KB_Article_Approval.md)

*   **Manage SME Approval (`Instant - Manage SME Approval`):** This flow is triggered when an SME is assigned or re-assigned from the Power App UI. It handles the logic for updating the article's status to `In Review` and sending the approval request directly to the selected SME.
    *   **See detailed design:** [`Instant - Manage SME Approval`](../../power-automate-flows/flow-designs/Instant_-_Manage_SME_Approval.md)

### Supporting Workflows

*   **Scheduled Article Review Reminder (`Scheduled - Article Review Reminder`):** This is a background process that runs hourly. It is not called by the Power App but is a critical part of the overall approval ecosystem. It queries for articles that are stuck in either `Waiting for Reviewer` or `In Review` status for more than 24 hours and sends appropriate reminder notifications.
    *   **See detailed design:** [`Scheduled - Article Review Reminder`](../../power-automate-flows/flow-designs/Scheduled_-_Unassigned_Article_Reminder.md)

---

## Screen Breakdown & Logic

### Browse Screen (`scr_Article`)

This is the main entry point of the application.

*   **`OnVisible` Property:** This logic runs every time the screen becomes visible. It handles the cleanup for the deep link search functionality.
    ```powerapps
    // Check if any broad filters (like "My Articles") need to be cleared.
    If(gblClearFiltersOnLoad,
        Reset(lbx_FilterOptions);
        Set(gblClearFiltersOnLoad, false);
    );

    // After the search box has been populated by its Default property,
    // clear the global variable so it doesn't interfere with subsequent user searches.
    If(!IsBlank(gblSearchOnLoad), Set(gblSearchOnLoad, Blank()));

    // --- Other OnVisible Logic ---
    UpdateContext({ selectedTab: "KB Content" });
    ClearCollect(colSavedProducts,
        Filter(
            Split(gblSelectedItem.Product_x002f_Service, ";"),
            !IsBlank(ThisRecord.Value)
        )
    );

    UpdateContext({ startPostRefreshTimer: false });
    UpdateContext({ locIsHoveringNewButton: false });
    UpdateContext({
        showDialogConfirmButton: true,
        showDialogCancelButton: true
    });
    ```

*   **`txt_Search` (Text Input):**
    *   **`Default` Property:** This is the key to the deep link solution. It's bound to a global variable that is only set when the app opens from a deep link.
        ```powerapps
        gblSearchOnLoad
        ```

*   **`gal_Articles` (Gallery):**
    *   **`Items` Property (Dynamic Data Source):** The gallery's `Items` property is now back to its original, simple state. It dynamically switches between the active and archive lists and applies the standard filter and search logic. The deep link is handled by the `txt_Search` control, not by this formula.
        ```powerapps
        If(
            locIsArchiveView,
            // --- ARCHIVE VIEW ---
            SortByColumns(
                Filter(
                    'Knowledge Base Articles Archive',
                    IsLatestVersion = true &&
                    (
                        IsBlank(txt_Search.Text) ||
                        StartsWith(Title, txt_Search.Text) ||
                        StartsWith(CanonicalArticleID, txt_Search.Text) ||
                        StartsWith(AssignedSMEEmail, txt_Search.Text) ||
                        StartsWith(lastAuthorEmail, txt_Search.Text)
                    ) &&
                    // --- Delegable Filter Logic ---
                    (
                        lbx_FilterOptions.Selected.Value = "All items" ||
                        IsBlank(lbx_FilterOptions.Selected.Value) ||
                        (lbx_FilterOptions.Selected.Value = "My Articles" && lastAuthorEmail = User().Email) ||
                        (lbx_FilterOptions.Selected.Value = "Assigned to Me" && AssignedSMEEmail = User().Email) ||
                        (lbx_FilterOptions.Selected.Value = "Waiting for Reviewer" && field_4.Value = "Waiting for Reviewer")
                    )
                ),
                "Modified",
                SortOrder.Descending
            ),
            // --- ACTIVE VIEW ---
            SortByColumns(
                Filter(
                    'Knowledge Base Articles',
                    IsLatestVersion = true &&
                    (
                        IsBlank(txt_Search.Text) ||
                        StartsWith(Title, txt_Search.Text) ||
                        StartsWith(CanonicalArticleID, txt_Search.Text) ||
                        StartsWith(AssignedSMEEmail, txt_Search.Text) ||
                        StartsWith(lastAuthorEmail, txt_Search.Text)
                    ) &&
                    // --- Delegable Filter Logic ---
                    (
                        lbx_FilterOptions.Selected.Value = "All items" ||
                        IsBlank(lbx_FilterOptions.Selected.Value) ||
                        (lbx_FilterOptions.Selected.Value = "My Articles" && lastAuthorEmail = User().Email) ||
                        (lbx_FilterOptions.Selected.Value = "Assigned to Me" && AssignedSMEEmail = User().Email) ||
                        (lbx_FilterOptions.Selected.Value = "Waiting for Reviewer" && field_4.Value = "Waiting for Reviewer")
                    )
                ),
                "Modified",
                SortOrder.Descending
            )
        )
        ```
        *   **`IsLatestVersion = true`**: This is the primary filter. It ensures that only articles marked as the latest version are ever displayed in the gallery.
        *   **`StartsWith(Title, txt_Search.Text)`**: This provides the search functionality on the filtered list of latest versions.
    *   **`OnSelect` Property (Single-Screen App):** This action updates the app's state to show the selected record and, critically, captures the timestamp for the concurrency check.
        ```powerapps
        // Set the form to Edit mode to display the selected item.
        EditForm(frm_Article);

        // Update the global variable with the selected record.
        Set(gblSelectedItem, ThisItem);

        // Explicitly set the newMode flag to false.
        UpdateContext({ newMode: false });

        // Set the concurrency timestamp for the selected record.
        UpdateContext({ locLoadTimestamp: Now() });
        ```



#### Last Author & Contributor Logic (V2 Backend)

In the V2 architecture, the complex logic for managing the `LastAuthor` and `Contributors` fields has been moved from the Power App to the `Orchestrate-GenerateAltTextAndSaveArticle` Power Automate workflow.

The Power App is only responsible for sending the *currently selected* contributors. The workflow handles the business rules for preserving attribution history.

*   **Power App Responsibility:** Pass the `cbo_contributors.SelectedItems` collection in the JSON payload.
*   **Power Automate Responsibility:**
    1.  Receive the list of current contributors.
    2.  Look up the existing SharePoint item.
    3.  Compare the incoming `LastAuthor` (the current user) with the previously saved `LastAuthor`.
    4.  If they are different, add the previous `LastAuthor` to the list of contributors before saving.

#### Form Controls and Data Submission

This section details how the form and various controls interact to manage the app's state, whether creating a new article or editing an existing one.

*   **`frm_Article` (Form):**
    *   **`DataSource` Property:** `‘Knowledge Base Articles’`
    *   **`Item` Property:** This property is critical for both initial data loading and subsequent selections. It uses the `Coalesce` function to create a "waterfall" of choices, preventing the form from being empty on startup.
        ```powerapps
        // Use Coalesce to show the selected item, or fall back to the first gallery item.
        Coalesce(gblSelectedItem, First(gal_Articles.AllItems))
        ```
        *   **On Initial Load:** `gblSelectedItem` is blank, so `Coalesce` returns `First(gal_Articles.AllItems)`, automatically loading the first article as soon as the gallery has data.
        *   **On User Selection:** `gblSelectedItem` is populated by the gallery's `OnSelect` action, so `Coalesce` returns it immediately.
    *   **`OnSuccess` Property:** Obsolete in V2 architecture, as `SubmitForm()` is no longer used for saving article data.

*   **`btn_Save` (Button):**
    *   **Note:** The "Save Draft" and "Start Review" buttons have been consolidated into a single "Save" button. The logic to determine the correct status is now handled by a shared component variable.
    *   **`Visible` Property:** The button is only visible when the user is creating a new article or editing an existing article that is still in "Draft" status.
        ```powerapps
        frm_ArticleContent.Mode = FormMode.New || (gblSelectedItem.Status.Value = "Draft" && gblSelectedItem.IsLatestVersion)
        ```
    *   **`OnSelect` Property:** This is the primary formula for the V2 architecture. It constructs a JSON object with all form data and sends it to the `Orchestrate-GenerateAltTextAndSaveArticle` flow. It then waits for the response and notifies the user accordingly.

        *   **Flow Documentation:** For complete details on the backend workflow, see the [`Orchestrate-GenerateAltTextAndSaveArticle`](../../power-automate-flows/flow-designs/Orchestrate-GenerateAltTextAndSaveArticle.md) document.
        *   **`cmp_SaveWithStatus` Component:** The `cmp_SaveWithStatus.Status` variable referenced in the code is set by a shared component that contains the "Save" and "Submit" buttons. The logic for this component is detailed in the [`GenericUIComponents.md`](./GenericUIComponents.md) document.

        ```powerapps
        // --- OnSelect Logic for BOTH "Save Draft" and "Start Review" Buttons ---

        // Step 1: Set a local variable to identify which button was pressed.
        // This line should be placed just before the main logic block in each button's OnSelect property.
        // For btn_SaveDraft:   Set(locButtonPressed, "SaveDraft")
        // For btn_StartReview: Set(locButtonPressed, "StartReview")

        // Step 2: Show the reusable dialog as a non-interactive status indicator.
        UpdateContext({
            dialogTitle: "Processing Request",
            dialogMessage: "Saving article...",
            showDialogConfirmButton: false,
            showDialogCancelButton: false,
            showConfirmationDialog: true
        });

        // Step 3: Call the orchestrator flow to save the article.
        Set(
            gblFlowResult,
            'Orchestrate-GenerateAltTextAndSaveArticle'.Run(
                JSON(
                    {
                        // --- Item Metadata ---
                        itemID: If(frm_ArticleContent.Mode = FormMode.New, 0, gblSelectedItem.ID),
                        buttonPressed: "SaveDraft", // Explicitly set to SaveDraft for this stage
                        isNewMode: frm_ArticleContent.Mode = FormMode.New,
                        loadTimestamp: locLoadTimestamp, // Pass the session start time for concurrency check
                         
                        // --- Main Content Fields ---
                        title: dc_Title.Update,
                        overviewHTML: rte_overview.HtmlText,
                        articleHTML: Substitute(Substitute(Substitute(rte_articleContent.HtmlText, "<p>&nbsp;</p>", ""),"<p>&#160;</p>", ""),"<p></p>", ""),
                        keywords: dc_Keywords.Update,
                        internalNotesHTML: rte_internalNotes.HtmlText,
                        metaTitle: dc_MetaTitle.Update,
                        metaDescription: dc_MetaDescription.Update,
                        reviewComments: dc_reviewComments.Update,

                        // --- Choice & Lookup Fields ---
                        language: cbo_language.Selected.Value,
                        solutionType: cbo_solutionType.Selected.Value,
                        authorRegion: cbo_authorReg.Selected.Value,
                        audience: cbo_audience.Selected.Value,
                        category: Coalesce(cbo_category.Selected.Value, cbo_category.SearchText),
                        productVersion: Coalesce(cbo_productVersion.Selected.Value, cbo_productVersion.SearchText),
                        productService: Concat(cbo_productService.SelectedItems, Product, ";"),
                        isPrimary: isPrimary_DataCard1.Update,
                        source: If(
                            !IsEmpty(cbo_source.SelectedItems),
                            JSON(cbo_source.SelectedItems, JSONFormat.IncludeBinaryData),
                            !IsBlank(cbo_source.SearchText),
                            JSON(Table({Value: cbo_source.SearchText})),
                            "[]"
                        ),
                        owningBusinessUnit: cbo_OwningBusinessUnit.Selected.Value,

                        // --- Person & Helper Fields ---
                        assignedSME: JSON(cbo_assignedSME.Selected, JSONFormat.IncludeBinaryData),
                        contributors: JSON(cbo_contributors.SelectedItems, JSONFormat.IncludeBinaryData),
                        previousLastAuthorEmail: If(frm_ArticleContent.Mode = FormMode.New, "", gblSelectedItem.LastAuthor.Email),
                        currentUserEmail: User().Email,

                        // --- Existing IDs (for updates) ---
                        articleID: gblSelectedItem.field_3,
                        canonicalArticleID: gblSelectedItem.CanonicalArticleID,
                        articleVersion: gblSelectedItem.ArticleVersion,
                        firstPublishedDate: gblSelectedItem.FirstPublishedDate,
 
                        // --- Legacy & Other Fields ---
                        contextSource: dc_contextSource.Update,
                        sfdcArticleNumber: dc_sfdcArticleNumber.Update,
                        legacyModifiedBy: dc_legacyModifiedBy.Update,
                        legacyContributors: dc_legacyContributors.Update,
                        legacyAssignedSME: dc_legacyAssignedSME.Update,
                        legacyCreatedBy: dc_legacyCreatedBy.Update,
                        expirationDate: dc_expirationDate.Update,
                        publishOnDate: dc_publishOn.Update
                    },
                    JSONFormat.IncludeBinaryData
                )
            )
        );

        // Step 4: Check the result of the save operation.
        If(
            gblFlowResult.status = "Success",
            
            // --- SAVE SUCCESSFUL ---
            // 4a. Check which button was pressed to determine the next action.
            If(
                locButtonPressed = "StartReview",

                // --- "Start Review" was pressed ---
                // 4a-1. Update dialog and start the review flow.
                UpdateContext({ dialogMessage: "Starting review..." });
                Refresh('Knowledge Base Articles');
                Set(
                    gblReviewFlowResult,
                    'Instant-StartKBArticleApproval'.Run(gblFlowResult.itemid, gblAppURL)
                );

                // 4a-2. Check the result of the review flow.
                If(
                    gblReviewFlowResult.responsestatus = "Success",
                    // Review Start Success: Close dialog, notify, and navigate back.
                    UpdateContext({ showConfirmationDialog: false });
                    Notify(gblReviewFlowResult.responsemessage, NotificationType.Success, 4000);
                    Back(),
                    // Review Start Failure: Show error in dialog.
                    UpdateContext({
                        dialogMessage: "Error starting review: " & gblReviewFlowResult.responsemessage,
                        showDialogCancelButton: true
                    })
                ),

                // --- "Save Draft" was pressed ---
                // 4b. Refresh data, re-select the item to update the UI, close the dialog, and notify.
                Refresh('Knowledge Base Articles');
                Set(
                    gblSelectedItem,
                    LookUp('Knowledge Base Articles', ID = gblFlowResult.itemid)
                );
                EditForm(frm_ArticleContent); // Switch from New to Edit mode if a new item was created.
                UpdateContext({ showConfirmationDialog: false });
                Notify("Draft saved successfully.", NotificationType.Success, 2000);
            ),

            // --- SAVE FAILED ---
            // 4c. Update the dialog with the save error.
            UpdateContext({
                dialogMessage: "Error saving article: " & gblFlowResult.message,
                showDialogCancelButton: true
            })
        );
        ```

*   **`btn_New` (Button):**
    *   **`OnSelect` Property:** The "New" button clears the app's state, puts the form into `New` mode, and critically, sets the `locLoadTimestamp` for the new, unsaved article.
        ```powerapps
        // Put the form into New mode.
        NewForm(frm_Article);

        // Clear the global variable to remove the current selection.
        Set(gblSelectedItem, Blank());

        // Set the newMode flag for any dependent controls.
        UpdateContext({ newMode: true });

        // Set the concurrency timestamp for the new record.
        UpdateContext({ locLoadTimestamp: Now() });
        ```

*   **`btn_assignSME` (Button):**
    *   **Purpose:** This button provides a context-sensitive action for assigning or re-assigning a Subject Matter Expert (SME). Its visibility and behavior change based on the status of the selected article.
    *   **`Visible` Property:** The button only appears when an article is in a state that requires SME assignment or re-assignment, and only for the latest version of that article.
        ```powerapps
        (gblSelectedItem.Status.Value = "Waiting for Reviewer" || gblSelectedItem.Status.Value = "In Review") && gblSelectedItem.IsLatestVersion
        ```
    *   **`DisplayMode` Property:** The button is only enabled when the user is on the "Details" tab of the form, preventing changes while the user is focused on the main "KB Content" editor. This assumes a variable `selectedTab` is used to control tab visibility.
        ```powerapps
        If(selectedTab = "Details", DisplayMode.Edit, DisplayMode.Disabled)
        ```
    *   **`OnSelect` Property:** This formula no longer contains any direct business logic. Instead, it follows the established best practice of configuring and displaying the reusable confirmation dialog.
    
            *   **Component Documentation:** For complete details on the confirmation dialog and its variables, see the [`GenericUIComponents.md`](./GenericUIComponents.md) document.
            ```powerapps
            // Set the context variables to configure the generic confirmation dialog.
            UpdateContext({
                dialogTitle: "Confirm SME Assignment",
                dialogMessage: If(
                    gblSelectedItem.field_4.Value = "In Review",
                    "You are about to re-assign the SME for this article. This will cancel the current approval process and start a new one with the selected user. Do you want to continue?",
                    "You are about to assign an SME and start the review process. Do you want to continue?"
                ),
                dialogContinueAction: "Confirm",
                isSMEAssignAction: true, // Set the flag for the new action
                showConfirmationDialog: true // Show the dialog
            });


### Archive View Functionality

This section details the implementation of the read-only Archive View, which allows users to browse and view the history of archived articles without being able to edit them.

#### State Management

The entire feature is controlled by a single context variable, `locIsArchiveView`, which is toggled by an icon in the main action toolbar.

*   **`locIsArchiveView` (Context Variable):** A boolean that determines the current view. `false` (default) for the active articles list, `true` for the archive.

*   **`ico_ArchiveView` (Icon):**
    *   **`Icon` Property:** `Icon.History`
    *   **`OnSelect` Property:** Toggles the state variable.
        ```powerapps
        UpdateContext({ locIsArchiveView: !locIsArchiveView })
        ```
    *   **`Color` Property:** Provides a visual cue for the active state.
        ```powerapps
        If(locIsArchiveView, Color.Black, ColorValue("#e31717"))
        ```
    *   **`Tooltip` Property:** Provides clear instruction to the user.
        ```powerapps
        If(locIsArchiveView, "View Active Articles", "View Archived Articles")
        ```

#### Dynamic UI Elements

To provide a clear and consistent user experience, several key UI elements change dynamically based on the `locIsArchiveView` variable.

*   **Screen Title (`lbl_ScreenTitle`):
    *   **`Text` Property:**
        ```powerapps
        If(locIsArchiveView, "Knowledge Base Article Archives", "Knowledge Base Articles")
        ```

*   **Header Banner (`rec_HeaderBanner`):
    *   **`Fill` Property:** Changes the banner color to a neutral gray to indicate a different mode.
        ```powerapps
        If(locIsArchiveView, ColorValue("#4a4a4a"), ColorValue("#e31717"))
        ```

#### Read-Only Form View

To prevent edits in the archive view, the form's data cards are made read-only individually. This is superior to setting the entire form's mode, as it allows specific controls (like the version history button) to remain interactive.

*   **Pattern:** For each data card that should be read-only, its `DisplayMode` property is wrapped with a master `If` statement that checks `locIsArchiveView`.
*   **Example (`dc_Title` `DisplayMode`):** This example shows how the archive view rule is layered on top of existing logic.
    ```powerapps
    If(
        // Master Switch: If in archive view, ALWAYS be read-only.
        locIsArchiveView,
        DisplayMode.View,
        
        // Otherwise, apply the original logic for the active view.
        If(
            frm_ArticleContent.Mode = FormMode.New || (gblSelectedItem.field_4.Value = "Draft" && gblSelectedItem.IsLatestVersion),
            DisplayMode.Edit,
            DisplayMode.View
        )
    )
    ```

#### Dynamic Action Button Visibility (Spacer Pattern)

To hide action buttons like `+ New` in the archive view without causing the layout of the toolbar to shift, a "spacer" pattern is used.

*   **`con_newArticle` (Button Container):**
    *   **`Visible` Property:** The actual button is hidden when in archive view.
        ```powerapps
        !locIsArchiveView
        ```

*   **`lbl_newArticleSpacer` (Label Control):**
    *   **Purpose:** An invisible label that occupies the exact same space as the button.
    *   **`Width` Property:** `con_newArticle.Width`
    *   **`Visible` Property:** The spacer is made visible only when in archive view, perfectly preserving the layout.
        ```powerapps
        locIsArchiveView
        ```

#### Dynamic Version History

The version history gallery (`gal_VersionHistory`) is also made dynamic to show the correct history for the selected article, whether it's active or archived.

*   **`gal_VersionHistory` (Gallery):**
    *   **`Items` Property:**
        ```powerapps
        If(
            locIsArchiveView,
            // --- ARCHIVE VIEW ---
            SortByColumns(
                Filter(
                    'Knowledge Base Articles Archive',
                    CanonicalArticleID = gblSelectedItem.CanonicalArticleID
                ),
                "ArticleVersion",
                SortOrder.Descending
            ),
            // --- ACTIVE VIEW ---
            SortByColumns(
                Filter(
                    'Knowledge Base Articles',
                    CanonicalArticleID = gblSelectedItem.CanonicalArticleID
                ),
                "ArticleVersion",
                SortOrder.Descending
            )
    
        )
        ```
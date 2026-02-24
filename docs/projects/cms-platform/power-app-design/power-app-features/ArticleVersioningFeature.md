## Article Versioning Feature

This section details the complete UI implementation for the article versioning feature, which allows users to view historical versions of an article and create new drafts from them.

### 8.1. "View version history" Button

This button initiates the version history workflow.

*   **Control:** `Button`
*   **Name:** `btn_versionHistory`
*   **Text:** `"View version history"`
*   **`DisplayMode` Property:** The button is always visible but is only enabled if the selected article has a version history (i.e., its version number is 2 or higher). This provides a consistent UI while preventing users from clicking it when no action can be taken.
    ```powerapps
    If(gblSelectedItem.ArticleVersion >= 2, DisplayMode.Edit, DisplayMode.Disabled)
    ```
*   **`OnSelect` Property:** When clicked, this formula stores the currently selected item (which is the latest version) into a temporary variable for later use by the "Revert" function. It then sets a context variable to `true` to display the version history dialog.
    ```powerapps
    UpdateContext({
        locLatestVersionItem: gblSelectedItem,
        showVersionHistory: true
    })
    ```
*   **Layout & Positioning:**
    *   **Critical Requirement:** The button **must not** be placed inside the main form (`frm_ArticleContent`). If it is, its `DisplayMode` will be overridden by the form's `DisplayMode` (which is often `View`), making the button unclickable. It must be placed on the screen directly or within a container that is a sibling of the form.
    *   **Dynamic Positioning:** To ensure the button remains in the correct visual position relative to the "ArticleVersion" field even on a responsive screen, its `X` and `Y` properties are set with formulas that calculate the absolute position by adding the coordinates of parent containers.
        *   **`Y` Property:**
            ```powerapps
            // Start with the Y of the main content container
            con_kbContent.Y +
            // Add the Y of the form inside that container
            frm_ArticleContent.Y +
            // Add the Y of the datacard inside the form
            dc_articleVersion.Y
            ```
        *   **`X` Property:**
            ```powerapps
            // Start with the X of the main content container
            con_kbContent.X +
            // Add the X of the form inside that container
            frm_ArticleContent.X +
            // Add the X of the datacard inside the form
            dc_articleVersion.X +
            // Add the width of the label inside the datacard
            DataCardKey8.Width +
            // Add the width of the value control inside the datacard
            DataCardValue1.Width +
            // Add 30px for padding
            30
            ```

### 8.2. Version History Dialog

The dialog is a group of controls that overlay the main screen content.

*   **Implementation:** It consists of a semi-transparent `Rectangle` for the background, a `Container` for the dialog box itself, and a `Close` icon.
*   **`Visible` Property:** The `Visible` property of all these controls is set to the context variable `showVersionHistory`.
*   **Close Icon `OnSelect`:** The close icon sets the context variable back to false: `UpdateContext({ showVersionHistory: false })`.

### 8.3. Version History Gallery (`gal_VersionHistory`)

This gallery, placed inside the dialog container, lists all available versions of the selected article.

*   **`Items` Property:** The formula filters the entire `Knowledge Base Articles` list to find all items that share the same `CanonicalArticleID` as the currently selected article. It then sorts the results by `ArticleVersion` in descending order to show the newest versions first.
    ```powerapps
    SortByColumns(
        Filter(
            'Knowledge Base Articles',
            CanonicalArticleID = gblSelectedItem.CanonicalArticleID
        ),
        "ArticleVersion",
        SortOrder.Descending
    )
    ```
*   **Gallery Labels:** The labels inside the gallery template are configured to show relevant information for each version, such as the version number, status, and modification details.
    *   **Title Label `Text`:** `"Version " & ThisItem.ArticleVersion & " (" & ThisItem.Status.Value & ")"`
    *   **Subtitle Label `Text`:** `"Modified by " & ThisItem.LastAuthor.DisplayName & " on " & Text(ThisItem.Modified, DateTimeFormat.ShortDate)`

### 8.4. In-Form Preview and Revert Logic

This section describes the final, improved user experience for previewing and reverting to old versions.

*   **Caret Arrow (`NextArrow`) `OnSelect` Property:** When a user clicks the arrow for a historical version in the gallery, the app loads that version's data directly into the main form for an in-place preview.
    ```powerapps
    // Step 1: Update the main selected item variable to this historical version.
    Set(gblSelectedItem, ThisItem);

    // Step 2: Close the version history dialog.
    UpdateContext({ showVersionHistory: false })
    ```
    *   **How it Works:** The main form (`frm_ArticleContent`) is already bound to `gblSelectedItem`. By updating this variable, the form automatically refreshes to show the historical data. Because the form's `DisplayMode` logic checks `IsLatestVersion`, the form correctly enters `View` mode.

*   **"Revert to this version" Button (on Main Form):** A button is placed on the main form that only becomes visible when the user is previewing a historical version.
    *   **`Visible` Property:** `!gblSelectedItem.IsLatestVersion`
    *   **`OnSelect` Property:** This formula does **not** call the flow directly. Instead, it sets the context variables for the generic confirmation dialog and then displays it.
        ```powerapps
        UpdateContext({
            showConfirmationDialog: true,
            dialogTitle: "Revert to Version",
            dialogMessage: "Are you sure you want to create a new draft based on the content of this historical version (Version " & gblSelectedItem.ArticleVersion & ")?",
            dialogContinueAction: "Revert",
            // Set a flag to tell the dialog's confirm button which action to run
            isRevertAction: true
        })
        ```
    *   **Backend Logic:** The actual Power Automate flow is triggered by the confirmation button within the generic dialog.
        *   **Flow Name:** `Instant - Revert to Version`
        *   **Dialog Logic:** For details on the dialog's implementation, see the [Generic UI Components](./GenericUIComponents.md) document.
        *   **Flow Documentation:** For details on the backend workflow, see the [Instant - Revert to Version](../../power-automate-flows/flow-designs/Instant_-_Revert_to_Version.md) document.
    *   **State Management:** No manual reset is needed for the button's visibility. When the user selects a normal (latest) article from the main gallery, `gblSelectedItem.IsLatestVersion` becomes `true`, and the button's `Visible` formula automatically evaluates to `false`, hiding it.
    
    *   **"Create New Version" Button (on Main Form):** A button is placed on the main form that allows users to create a new draft from a published article.
        *   **`Visible` Property:** `gblSelectedItem.Status.Value = "Published" && gblSelectedItem.IsLatestVersion`
        *   **`OnSelect` Property:** This formula uses the same robust pattern as the Revert function to create the new version and refresh the UI in place, providing a seamless user experience.
            ```powerapps
            // --- Create New Version Action ---
            // This logic provides a seamless, in-app navigation experience.
        
            // **Power Automate Prerequisite:**
            // 1. Add a "Respond to a PowerApp or flow" action at the end of the flow.
            // 2. Add a Text Output and name it `Result`.
            // 3. Set its value to "Success".
        
            // **Power App Logic:**
            // Run the flow and CAPTURE its response to force the app to wait.
            UpdateContext({
                locFlowResult: 'Instant-CreateNewArticleVersion'.Run(gblSelectedItem.ID, User().Email)
            });
        
            // Now that the flow has finished, refresh the data source.
            Refresh('Knowledge Base Articles');
        
            // Look up the newly created draft.
            Set(
                gblSelectedItem,
                LookUp(
                    'Knowledge Base Articles',
                    CanonicalArticleID = gblSelectedItem.CanonicalArticleID && IsLatestVersion = true
                )
            );
        
            // Force the form to clear its cache and reload with the new data.
            ResetForm(frm_ArticleContent);
            EditForm(frm_ArticleContent);
        
            // Switch to the main content tab.
            UpdateContext({selectedTab: "KB Content"});
            ```
        *   **Backend Logic:** This action directly calls the Power Automate flow.
            *   **Flow Name:** `Instant-CreateNewArticleVersion`
            *   **Flow Documentation:** For details on the backend workflow, see the [Instant - Create New Article Version](../../power-automate-flows/flow-designs/Instant_-_Create_New_Article_Version.md) document.
    
    *   **"Discard Draft" Button (on Main Form):** A button that allows users to delete a draft version.
        *   **`Visible` Property:** `gblSelectedItem.Status.Value = "Draft" && gblSelectedItem.IsLatestVersion`
        *   **`OnSelect` Property:** This formula does not call the flow directly. Instead, it populates the context variables for the generic confirmation dialog to ensure the user confirms this destructive action.
            ```powerapps
            UpdateContext({
                showConfirmationDialog: true,
                dialogTitle: "Discard Draft",
                dialogMessage: "Are you sure you want to discard this draft? This action cannot be undone.",
                dialogContinueAction: "Discard",
                // Set a flag to tell the dialog's confirm button which action to run
                isDiscardAction: true
            })
            ```
        *   **Backend Logic:** The actual Power Automate flow is triggered by the confirmation button within the generic dialog.
            *   **Flow Name:** `Instant - Discard Article Draft`
            *   **Dialog Logic:** For details on the dialog's implementation, see the [Generic UI Components](./GenericUIComponents.md) document.
            *   **Flow Documentation:** For details on the backend workflow, see the [Instant - Discard Article Draft](../../power-automate-flows/flow-designs/Instant_-_Discard_Article_Draft.md) document.

*   **"Archive Article" Button (on Main Form):** A button that allows users to instantly archive a published article.
    *   **`Visible` Property:** `gblSelectedItem.Status.Value = "Published" && gblSelectedItem.IsLatestVersion`
    *   **`OnSelect` Property:** This formula populates the context variables for the generic confirmation dialog to ensure the user confirms this significant action.
        ```powerapps
        UpdateContext({
            showConfirmationDialog: true,
            dialogTitle: "Archive Article",
            dialogMessage: "Are you sure you want to archive this article? This will remove the article and its entire version history from the active list and move it to the archive. This action cannot be undone.",
            dialogContinueAction: "Archive",
            // Set a flag to tell the dialog's confirm button which action to run
            isExpireAction: true
        })
        ```
    *   **Backend Logic:** The actual Power Automate flow is triggered by the confirmation button within the generic dialog.
        *   **Flow Name:** `Instant - Expire Single KB Article v2`
        *   **Dialog Logic:** For details on the dialog's implementation, see the [Generic UI Components](./GenericUIComponents.md) document.
        *   **Flow Documentation:** For details on the backend workflow, see the [Instant - Expire Single KB Article v2](../../power-automate-flows/flow-designs/Instant_-_Expire_Single_KB_Article_v2.md) document.
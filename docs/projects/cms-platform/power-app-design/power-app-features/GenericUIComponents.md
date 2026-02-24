## Generic UI Components

### 1.1. Reusable Confirmation Dialog

To provide a consistent user experience for significant actions, a reusable confirmation dialog has been implemented.

*   **Implementation:** The dialog is built using a nested structure of standard containers. Its height is calculated dynamically based on the content of the message label.
    *   **`con_confirmationDialog` (Container):** The main parent container for the entire dialog.
    *   **`con_confirmTitleBar` (Container):** Holds the title label (`lbl_dialogTitle`) and cancel icon (`ico_cancelConfirmationDialog`).
    *   **`con_confirmBody` (Container):** Holds the main message label (`lbl_dialogMessage`).
    *   **`con_dialogButtons` (Container):** Holds the "Confirm" (`btn_dialogConfirm`) and "Cancel" (`btn_dialogCancel`) buttons.
*   **Dynamic Height Formulas:**
    *   The message label (`lbl_dialogMessage`) must have its `AutoHeight` property set to `true`.
    *   The height of the body container is then set relative to the message label, with added padding:
        *   `con_confirmBody.Height`: `lbl_dialogMessage.Height + 100`
    *   The height of the main dialog container is the sum of its children:
        *   `con_confirmationDialog.Height`: `con_confirmTitleBar.Height + con_confirmBody.Height + con_dialogButtons.Height`
*   **Self-Sizing Button Width:**
    *   To ensure buttons can accommodate dynamic text (e.g., "Revert", "Save and Continue") while maintaining a minimum size, a formula-based approach is used for the `Width` property. This is a best practice that avoids text being cut off.
    *   **Control:** `btn_dialogConfirm`, `btn_dialogCancel`
    *   **Property:** `Width`
    *   **Formula:**
        ```powerapps
        Max(130, (Len(Self.Text) * 8) + 40)
        ```
    *   **How it Works:**
        *   `Len(Self.Text) * 8`: Calculates an approximate text width. The multiplier (`8`) can be adjusted based on the font family and size to fine-tune the fit.
        *   `+ 40`: Adds horizontal padding (e.g., 20px on each side).
        *   `Max(130, ...)`: Enforces a minimum width of 130px, allowing the button to grow if the text requires more space, but preventing it from becoming too small for short text like "OK".
*   **`Visible` Property:** The `Visible` property of the parent container (`con_confirmationDialog`) and a background overlay rectangle is bound to a single context variable: `showConfirmationDialog`.

#### Context Variables

The dialog is controlled by a set of context variables that must be set before showing it:

*   `showConfirmationDialog` (Boolean): Set to `true` to show the dialog, `false` to hide it.
*   `dialogTitle` (String): The text to display in the dialog's title bar.
*   `dialogMessage` (String): The main body text of the dialog, explaining the action.
*   `dialogContinueAction` (String): The text for the "Confirm" button (e.g., "Revert", "Delete").
*   `isProcessingAction` (Boolean): A flag set to `true` while the backend operation is running. This is used to show a "Processing..." message and disable buttons.
*   `showDialogConfirmButton` (Boolean): Explicitly controls the visibility of the confirmation button.
*   `showDialogCancelButton` (Boolean): Explicitly controls the visibility of the cancel/close button.
*   `isRevertAction` (Boolean): A flag to indicate that the confirmation action is for a revert.
*   `isDiscardAction` (Boolean): A flag to indicate that the confirmation action is to discard a draft.
*   `isExpireAction` (Boolean): A flag to indicate that the confirmation action is to expire a published article.
*   `isReactivateAction` (Boolean): A flag to indicate that the confirmation action is to reactivate an archived article.
*   `isSMEAssignAction` (Boolean): A flag to indicate that the confirmation action is to assign or re-assign an SME.
*   `locLatestVersionItem` (Record): A record variable that holds the full item of the version to be made the new latest version. This is set by the button that triggers the revert action.

#### Control Properties

*   **Title Label (`lbl_dialogTitle`):**
    *   `Text` Property: `dialogTitle`
*   **Message Label (`lbl_dialogMessage`):**
    *   `Text` Property: `If(isProcessingAction, "Processing...", dialogMessage)`
    *   **Cancel Button (`btn_dialogCancel`):**
        *   `DisplayMode` Property: `If(isProcessingAction, DisplayMode.Disabled, DisplayMode.Edit)`
        *   `Visible` Property: `showDialogCancelButton`
        *   `OnSelect` Property: `UpdateContext({ showConfirmationDialog: false, isRevertAction: false, isDiscardAction: false, isExpireAction: false, isSMEAssignAction: false, isProcessingAction: false })`
    *   **Cancel Icon (`ico_cancelConfirmationDialog`):**
        *   `DisplayMode` Property: `If(isProcessingAction, DisplayMode.Disabled, DisplayMode.Edit)`
        *   `OnSelect` Property: `Select(btn_dialogCancel)`
        *   **Note:** This is a best practice for code reuse. The icon programmatically "presses" the main cancel button. This ensures that if the cancel logic ever changes, it only needs to be updated in one place (the button).
    *   **Confirm Button (`btn_dialogConfirm`):**
        *   `Text` Property: `dialogContinueAction`
        *   `DisplayMode` Property: `If(isProcessingAction, DisplayMode.Disabled, DisplayMode.Edit)`
        *   `Visible` Property: `showDialogConfirmButton`
        *   `OnSelect` Property: This formula provides user feedback by showing a "Processing..." state and then executes the correct backend logic based on which action flag has been set. The code below is the exact implementation from the Power App.
                     *   **UI Trigger:** For details on the buttons that set these flags, see the [Article Versioning Feature](./ArticleVersioningFeature.md) document.
                     ```powerapps
                    // Step 1: Set the "Processing" state.
                    // This changes the dialog text and disables the buttons to prevent duplicate clicks.
                    UpdateContext({ isProcessingAction: true });
            
                    // Step 2: Check which action flag is set and execute the corresponding logic.
                    If(
                        isRevertAction,
                        // --- Revert Action (with response handling) ---

                        // 1. Run the flow and store its JSON response.
                        UpdateContext({ locFlowResult: 'Instant-ReverttoVersion'.Run(gblSelectedItem.ID, locLatestVersionItem.ID, User().Email) });

                        // 2. Check the response status from the flow.
                        If(
                            locFlowResult.responsestatus = "Success",
                            // --- SUCCESS PATH ---
                            // 3a. Notify the user of success.
                            Notify(locFlowResult.responsemessage, NotificationType.Success);
                            // 4a. Refresh the data source.
                            Refresh('Knowledge Base Articles');
                            // 5a. Set the global selected item to the new draft identified by the flow's response.
                            Set(
                                gblSelectedItem,
                                LookUp(
                                    'Knowledge Base Articles',
                                    CanonicalArticleID = locFlowResult.canonicalid && IsLatestVersion = true
                                )
                            );
                            // 6a. Reset the form to show the new draft.
                            ResetForm(frm_ArticleContent);
                            EditForm(frm_ArticleContent),

                            // --- FAILURE PATH ---
                            // 3b. Notify the user of the specific error from the flow.
                            Notify(locFlowResult.responsemessage, NotificationType.Error, 10000)
                        )
                    );
            
                    If(
                        isDiscardAction,
                        // --- Discard Draft Action (with response handling) ---

                        // 1. Store the Canonical ID for lookup after refresh.
                        UpdateContext({ locCanonicalIDToKeep: gblSelectedItem.CanonicalArticleID });

                        // 2. Run the flow and store its response.
                        UpdateContext({
                            locDiscardResult: 'Instant-DiscardArticleDraft'.Run(
                                gblSelectedItem.ID,
                                gblSelectedItem.CanonicalArticleID,
                                gblSelectedItem.ArticleVersion,
                                User().Email
                            )
                        });

                        // 3. Check the flow's response and act accordingly.
                        If(
                            locDiscardResult.status = "Success",
                            // --- SUCCESS PATH ---
                            Notify(locDiscardResult.message, NotificationType.Success, 3000);
                            Refresh('Knowledge Base Articles');
                            Set(
                                gblSelectedItem,
                                LookUp(
                                    'Knowledge Base Articles',
                                    CanonicalArticleID = locCanonicalIDToKeep && IsLatestVersion = true
                                )
                            );
                            ResetForm(frm_ArticleContent);
                            EditForm(frm_ArticleContent),

                            // --- FAILURE PATH ---
                            Notify(locDiscardResult.message, NotificationType.Error, 10000)
                        )
                    );
        
                    If(
                        isExpireAction,
                        // --- Expire Article Action Logic ---
        
                        // 1. Run the flow and store the result in a local variable.
                        UpdateContext({
                            locExpireResult: 'Instant-ExpireSingleKBArticlev2'.Run(gblSelectedItem.ID, User().Email)
                        });
        
                        // 2. Check the 'responsestatus' field from the flow's output.
                        If(
                            locExpireResult.responsestatus = "Success",
        
                            // 3. If successful, refresh data and reset the UI.
                            Notify(locExpireResult.responsemessage, NotificationType.Success);
                            Refresh('Knowledge Base Articles');
                            Set(gblSelectedItem, First(gal_Articles.AllItems));
                            ResetForm(frm_ArticleContent);
                            EditForm(frm_ArticleContent),
        
                            // 4. If it failed, show an error notification with the message from the flow.
                            Notify(locExpireResult.responsemessage, NotificationType.Error)
                        )
                    );
        
                    If(
                        isReactivateAction,
                        // --- Reactivate Article Action ---
                        UpdateContext({locIsProcessing: true});
                        Set(gblReactivateResult, 'Instant-ReactivateArchivedArticle'.Run(gblSelectedItem.CanonicalArticleID, User().Email));
                        UpdateContext({locIsProcessing: false, locIsDialogVisible: false, isReactivateAction: false});
                        
                        If(gblReactivateResult.result = "Success",
                            // On Success: Notify user and navigate to the new draft
                            Notify("Article and its full history have been restored. A new draft has been created.", NotificationType.Success, 4000);
                            Set(gblSelectedItem, LookUp('Knowledge Base Articles', CanonicalArticleID=gblSelectedItem.CanonicalArticleID && IsLatestVersion=true));
                            UpdateContext({locIsArchiveView: false}); // Switch back to the Active view
                            ResetForm(frm_ArticleContent);
                            EditForm(frm_ArticleContent);
                        ,
                            // On Error: Notify user of the failure
                            Notify(gblReactivateResult.message, NotificationType.Error)
                        )
                    );

                    If(
                        isSMEAssignAction,
                        // --- Assign SME Action (V2 - Centralized Logic) ---

                        // 1. Run the flow, passing the item ID, the new SME's email, and the app's base URL.
                        // The flow is now responsible for the entire transaction.
                        UpdateContext({
                            locFlowResult: 'Instant-ManageSMEApproval'.Run(
                                gblSelectedItem.ID,
                                cbo_assignedSME.Selected.Email,
                                gblAppURL, // Pass the app's base URL for deep linking in the approval email.
                                User().Email
                            )
                        });

                        // 2. Check the flow's response and notify the user.
                        If(
                            locFlowResult.responsestatus = "Success",
                            Notify(locFlowResult.responsemessage, NotificationType.Success, 4000),
                            Notify(locFlowResult.responsemessage, NotificationType.Error, 10000)
                        );

                        // 3. Refresh the data source to get the updated status from the flow.
                        Refresh('Knowledge Base Articles');
                    );
            
                    // Step 3: Once all actions are complete, hide the dialog and reset all state variables.
                    UpdateContext({
                        showConfirmationDialog: false,
                        isProcessingAction: false,
                        isRevertAction: false,
                        isDiscardAction: false,
                        isExpireAction: false,
                        isReactivateAction: false,
                        isSMEAssignAction: false
                    });
                     ```
        *   **Developer's Note on Architectural Consistency:**
            *   The code above now demonstrates a consistent architectural pattern. The `Revert`, `Discard`, `Expire`, and `Reactivate` actions all correctly follow the application's core V2 architecture: they call a flow, wait for a structured response (`status` and `message`), and then update the UI based on that response. This is robust, reliable, and provides a consistent experience for the user and developer.

        *   **Flow Documentation:**
            *   [Instant - Revert to Version](../../power-automate-flows/flow-designs/Instant_-_Revert_to_Version.md)
            *   [Instant - Discard Article Draft](../../power-automate-flows/flow-designs/Instant_-_Discard_Article_Draft.md)
            *   [Instant - Expire Single KB Article v2](../../power-automate-flows/flow-designs/Instant_-_Expire_Single_KB_Article_v2.md)
            *   [Instant - Reactivate Archived Article](../../power-automate-flows/flow-designs/Instant_-_Reactivate_Archived_Article.md)

## 10. Component Usage

The components and logic described in this document are referenced and used in the following parts of the application:

*   **Screen & Form Logic:** For details on how these components are integrated into the main edit screen, see the [`ScreenBreakdownAndLogic.md`](./ScreenBreakdownAndLogic.md) document.
*   **Article Versioning:** The confirmation dialog is triggered by buttons described in the [`ArticleVersioningFeature.md`](./ArticleVersioningFeature.md) document.
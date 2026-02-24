# UI/UX Best Practices

## Consistent Read-Only Visuals

To provide a clear and consistent user experience, all input fields should visually indicate whether they are editable or read-only. The default appearance for controls in "View" mode is inconsistent. The following pattern standardizes this behavior by applying a light grey background to all read-only fields.

### The Two-Step Implementation Pattern

For every input control within a data card, two properties must be set correctly:

1.  **`DisplayMode` Property (The Inheritance Step):** This is the most critical step. The control's `DisplayMode` must be set to inherit from its parent data card. This ensures it respects the central logic that determines editability.
    *   **Property:** `DisplayMode`
    *   **Formula:** `Parent.DisplayMode`
    *   *Note: When adding new controls to a card, this often defaults to `DisplayMode.Edit` and must be manually corrected for this pattern to work.*

2.  **`Fill` Property (The Visual Step):** Once the `DisplayMode` is correctly inherited, use a formula on the `Fill` property to create the consistent visual style.

### Formulas by Control Type

*   **Standard Controls (TextBox, ComboBox, DatePicker, etc.):**
    *   **Control:** The input control itself.
    *   **Property:** `Fill`
    *   **Formula:**
        ```powerapps
        If(Self.DisplayMode = DisplayMode.Edit, Color.White, RGBA(244, 244, 244, 1))
        ```

## Handling Blank Dates

To ensure a clean UI, empty date fields should display a placeholder value instead of being blank. The most efficient way to achieve this is by using the `InputTextPlaceholder` property of the Date Picker control.

*   **Goal:** Display `"--"` when a date field (like "First Published") is empty.
*   **Control:** The Date Picker control itself.
*   **Property:** `InputTextPlaceholder`
*   **Value:** `"--"`

This property automatically displays the placeholder text whenever the control's value is blank, requiring no complex `If` statements.

*   **Rich Text Editors:**
    *   **Note:** The Rich Text Editor control does not have a `Fill` property. Instead, apply the fill to its parent data card.
    *   **Control:** The Data Card (e.g., `dc_ArticleContent`, `dc_Overview`).
    *   **Property:** `Fill`
    *   **Formula:**
        ```powerapps
        If(Self.DisplayMode = DisplayMode.Edit, Color.White, RGBA(244, 244, 244, 1))
        ```
    *   **Critical Bug Workaround:** The Rich Text Editor control may fail to respect the `Parent.DisplayMode` inheritance and get "stuck" in View mode. To fix this, the `DisplayMode` logic must be applied **directly** to the Rich Text Editor control itself, instead of relying on `Parent.DisplayMode`.
    *   **Control:** The Rich Text Editor (e.g., `rte_overview`).
    *   **Property:** `DisplayMode`
    *   **Formula:**
        ```powerapps
        // This is the final, correct formula that also checks the version.
        If(
            frm_ArticleContent.Mode = FormMode.New || (gblSelectedItem.Status.Value = "Draft" && gblSelectedItem.IsLatestVersion),
            DisplayMode.Edit,
            DisplayMode.View
        )
        ```

## Spacing Items in Modern Containers

To create consistent spacing between controls inside a modern **Horizontal** or **Vertical container** (e.g., adding a gap between buttons), the container's `Gap` property should be used.

*   **Control:** The parent container itself (e.g., a Horizontal container holding two buttons).
*   **Property:** `Gap`
*   **Value:** A number representing the pixels of space to add between each child control (e.g., `10` or `20`).

This is the recommended best practice as it keeps layout logic on the parent container and automatically adjusts as controls are added or removed.

## Selective Read-Only Data Cards

When a form needs to be mostly read-only but still allow interaction with specific controls (e.g., a button within a single data card), setting the entire form's mode to `View` is not suitable, as it disables all child controls.

The correct pattern is to keep the form in `Edit` mode and control the `DisplayMode` of each individual data card that needs to be read-only. This is achieved by wrapping the card's existing `DisplayMode` logic within a higher-priority `If` statement that acts as a master switch.

*   **Scenario:** Make a form read-only when viewing an archived article (`locIsArchiveView` is true), but keep a button in one data card clickable.
*   **Control:** All data cards that need to be read-only (e.g., `dc_Title`).
*   **Property:** `DisplayMode`
*   **Formula Pattern:**
    ```powerapps
    If(
        // Master Switch: If in archive view, ALWAYS be read-only.
        locIsArchiveView,
        DisplayMode.View,
        
        // Otherwise, apply the original, complex logic for the active view.
        // (This is the pre-existing formula for the DisplayMode property)
        If(
            frm_ArticleContent.Mode = FormMode.New || (gblSelectedItem.field_4.Value = "Draft" && gblSelectedItem.IsLatestVersion),
            DisplayMode.Edit,
            DisplayMode.View
        )
    )
    ```

*   **Developer's Note on Logical Names:** The formula uses `gblSelectedItem.field_4.Value` instead of the display name `gblSelectedItem.Status.Value`. This is intentional. Using logical field names (`field_1`, `field_2`, etc.) is a best practice in this app to prevent formulas from breaking if the underlying SharePoint list is ever replaced or its column display names are changed. While less readable, it provides crucial long-term stability.

By applying this pattern to all data cards except the one containing the interactive button, the form becomes selectively read-only.

*   **Flow Context:** The `locIsArchiveView` variable is set to `true` when the user navigates to the "Archived History" view for an article. The gallery in this view is populated by the results of the **`GetArchivedVersionHistory`** flow, which specifically retrieves items from the secondary `Archived Knowledge Base Articles` SharePoint list. This is why a master switch is required to enforce a read-only state, as the form's standard logic is designed for the primary `Knowledge Base Articles` list.

## Preserving Layout When Hiding Controls

When an item inside a horizontal or vertical layout container has its `Visible` property set to `false`, the container collapses the space, causing other controls in the container to shift their position. This is often undesirable, especially in a toolbar.

The best practice to avoid this is the **"Spacer" pattern**. Instead of making the control invisible, you swap its visibility with an invisible placeholder control that has the exact same dimensions.

*   **Scenario:** Hiding a `+ New` button in a toolbar when in archive view, without causing the other toolbar icons to move.

1.  **Add a Spacer Control:**
    *   Inside the layout container, add a `Label` control next to the button you intend to hide.
    *   Set its `Text` to `""`.

2.  **Configure the Spacer's Properties:**
    *   **`Width` Property:** Set it to be identical to the button's width (e.g., `con_newArticle.Width`).
    *   **`Visible` Property:** Make the spacer visible only when the button should be hidden.
        ```powerapps
        locIsArchiveView
        ```

3.  **Configure the Button's `Visible` Property:**
    *   Set the button's visibility to be the opposite of the spacer's.
        ```powerapps
        !locIsArchiveView
        ```

This pattern ensures that one of the two controls is always visible but invisible, perfectly preserving the layout at all times.

## Indicating a Processing State for Flow-Driven Actions

When a user clicks a button that triggers a Power Automate flow (e.g., "Revert," "Discard Draft," "Expire"), the app must provide clear visual feedback that a background process has been initiated. This prevents the user from clicking the button multiple times and makes the app feel more responsive.

The standard pattern for this is to use a context variable (e.g., `isProcessingAction`) to temporarily disable the interactive controls and display a "Processing..." message.

*   **Scenario:** A user clicks the "Confirm" button in a dialog to trigger a flow.
*   **Implementation:** The `OnSelect` property of the button should follow this three-step pattern:

1.  **Set Processing State:** Immediately set a variable like `isProcessingAction` to `true`. This variable is used to change the text of a label to "Processing..." and disable the dialog's buttons.
2.  **Execute Flow:** Call the Power Automate flow using the `.Run()` method.
3.  **Reset State:** After the flow returns and all subsequent UI logic (like `Refresh()` and `ResetForm()`) is complete, set `isProcessingAction` back to `false` and hide the dialog.

*   **Canonical Example:** This pattern is implemented in the [Reusable Confirmation Dialog](./GenericUIComponents.md)**. The `OnSelect` property of the `btn_dialogConfirm` button demonstrates the exact Power Fx code for setting the state, executing the flow based on action-specific flags (`isRevertAction`, `isDiscardAction`, etc.), and resetting the state upon completion.
## Advanced Troubleshooting

This section documents critical, non-obvious issues encountered during development and their definitive solutions.

### 12.2. Stale Power Automate Flow Connections

This is a severe and difficult-to-diagnose bug within the Power Apps studio.

*   **Developer's Note:** This issue, which requires cloning the flow, is distinct from the more common `InvokerConnectionOverrideFailed` error. For that error, see the guide on [Fixing the InvokerConnectionOverrideFailed Error](./TroubleshootingAndKeyFixes.md#117-fixing-the-invokerconnectionoverridefailed-error).

*   **The Symptom:** After modifying the trigger of a Power Automate flow (e.g., adding, removing, or renaming a parameter), the Power App's formula bar will give contradictory error messages.
    *   First, it may show `Invalid argument type (Record). Expecting a Text value instead.` when using comma-separated arguments.
    *   After changing to the record syntax (`.Run({param: value})`), it will show `Invalid number of arguments.`
    *   This loop can persist even after removing/re-adding the flow or restarting the app.

*   **The Root Cause:** The Power App maintains a cached, stale, or corrupted reference to the flow's signature. It is no longer certain what inputs the flow expects, leading to the conflicting errors.

*   **The Definitive Solution: Clone the Flow**
    1.  **Do not trust the error messages.** They are misleading.
    2.  In Power Automate, use **"Save As"** to create a clone of the problematic flow (e.g., `MyFlow_V2`).
    3.  Ensure the new cloned flow is **turned on**.
    4.  In the Power App, go to the Data panel, **"Remove"** the old flow completely.
    5.  **"+ Add data"** and add the new `_V2` flow.
    6.  Update the formula in the app to call the new `_V2` flow. Use the modern **record syntax** (`.Run({param1: value1, param2: value2})`) as a fresh connection will expect this.

*   **Permissions Side-Effect:** After cloning, the new flow may retain the connection references of the original owner. This can cause a `ConnectionAuthorizationFailed` error. To fix this, the flow owner must edit the flow's **"Run only users"** settings and change the connection from "Provided by run-only user" to the specific, embedded service account connection.

### 12.3. The "Optional" Parameter Bug in Power Automate Triggers

This is the final piece of the puzzle for resolving flow connection issues. Even after cloning a flow, the app may still send `null` values for parameters.

*   **The Symptom:** A flow call from the Power App fails. When checking the flow's run history, you see that an input parameter (e.g., `ItemID`) is `null`, even though you are certain the app is providing a valid value. The formula in the app appears correct.

*   **The Root Cause:** When a parameter in a Power Automate V2 trigger ("Ask in PowerApps") is left as "Optional" (the default), the connection contract between the app and the flow can become ambiguous. The app may fail to correctly pass the value, especially if the connection has been previously corrupted or is being re-established.

*   **The Definitive Solution: Make Parameters "Required"**
    1.  In the Power Automate editor, open the trigger action (the "PowerApps (V2)" card).
    2.  For each input parameter, click the `...` menu and select **"Make the field required"**.
    3.  Save the flow.
    4.  Return to the Power App. The formula calling the flow may now show an error. This is a **good sign**, as it means the app has finally recognized the new, stricter signature of the flow.
    5.  You may need to re-enter the formula. The app should now correctly map the arguments. In our case, this forced the app to accept the simple comma-separated syntax for the main save flow: `'Orchestrate-GenerateAltTextAndSaveArticle'.Run(locArticleJSON)`.

    This simple change solidifies the contract between the app and the flow, removing ambiguity and ensuring that values are passed correctly.

### 12.4. Resolving Relative Image URLs for Display

A common issue is that images processed and stored by the Power Automate flow do not display when an article is loaded in the Power App's Rich Text Editor.

*   **The Symptom:** The Rich Text Editor shows broken image icons instead of the actual images, even though the links are valid in SharePoint.

*   **The Root Cause:** The `Orchestrate-GenerateAltTextAndSaveArticle` flow saves image URLs as **relative paths** to the SharePoint server (e.g., `<img src="/sites/TrendVisionPulse/Article%20Images/image.png">`). The Power App, being an external application, cannot resolve these relative paths. It requires a full, **absolute URL** (e.g., `https://trendmicro.sharepoint.com/sites/.../image.png`).

*   **The Solution: Dynamic URL Substitution**
    1.  **Store the Domain in `App.OnStart`:** To make the solution maintainable, the SharePoint domain is stored in a global variable when the app starts. This avoids hardcoding the URL in multiple places.
        *Control: `App` | Property: `OnStart`*
        ```powerapps
        // Add this line to your OnStart
        Set(gblSharePointDomain, "https://trendmicro.sharepoint.com")
        ```

    2.  **Modify the Rich Text Editor's `Default` Property:** The `Default` property of the Rich Text Editor control (`rte_articleContent`) is modified to dynamically replace the start of any relative URL with the full domain.
        *Control: `rte_articleContent` | Property: `Default`*
        ```powerapps
        // Replaces src="/ with src="https://domain.com/
        Substitute(
            Parent.Default,
            "src=""/",
            "src=""" & gblSharePointDomain & "/"
        )
        ```
    *   **How it Works:**
        *   `Parent.Default` gets the raw HTML content for the article from the form's data card.
        *   `Substitute()` finds all occurrences of the string `src="/`.
        *   It replaces them with the string `src="` followed by the value of `gblSharePointDomain` and a closing `/`.
        *   This transforms the relative URL into an absolute URL that the Rich Text Editor can correctly render.

### 12.5. Setting Default Values for New Items

To improve user experience and ensure data consistency, several fields in the form are pre-populated with default values when a user creates a new article.

*   **The Goal:** When `frm_ArticleContent.Mode` is `FormMode.New`, specific fields should have pre-set values. When the form is in `FormMode.Edit`, the fields must show the values saved in SharePoint.

*   **The Pattern:** The correct way to implement this is by setting the `Default` property on the **control inside the data card** (e.g., the Dropdown, Date Picker, or Text Input). The formula uses a simple `If` condition:
    ```powerapps
    If(frm_ArticleContent.Mode = FormMode.New, [Default Value], ThisItem.[FieldName])
    ```
    *   `If(frm_ArticleContent.Mode = FormMode.New, ...)`: This checks if the form is creating a new item.
    *   `[Default Value]`: This is the value to set for a new item. For Choice columns, this must be a record: `{ Value: "ChoiceText" }`.
    *   `ThisItem.[FieldName]`: This is the crucial "else" condition. `ThisItem` refers to the form's current record. This ensures that when editing an existing article, the control shows the value that is already saved for that item.

*   **Final Implemented Formulas:**

    *   **Language (`dc_Language`):**
        ```powerapps
        If(frm_ArticleContent.Mode = FormMode.New, { Value: "en-us" }, ThisItem.Language)
        ```
    *   **Audience (`dc_Audience`):**
        ```powerapps
        If(frm_ArticleContent.Mode = FormMode.New, { Value: "Internal" }, ThisItem.Audience)
        ```
    *   **Author Region (`dc_AuthorRegion`):**
        ```powerapps
        If(frm_ArticleContent.Mode = FormMode.New, { Value: "Philippines" }, ThisItem.'Author Region')
        ```
    *   **Product/Service (`dc_productService`):** This field required extensive troubleshooting. The final solution recognizes that this is **not a Lookup field**, but a **Text field** in SharePoint used to store multiple selections separated by a semicolon (`;`). The control is a multi-select ComboBox.

        *   **Core Principle:** The default value logic must reside in the `DefaultSelectedItems` property of the ComboBox control itself. The `Default` property of the parent Data Card (`dc_productService`) must be left blank.

        *   **Data Source (`App.OnStart`):** The ComboBox's `Items` property is a collection named `colMasterProducts`. For the default logic to work, this collection must be built with a schema that matches the ComboBox's expectations. The `App.OnStart` formula was corrected to build this collection with a `{Product: "..."}` schema, which avoids all previous data type mismatch errors.
            ```powerapps
            // In App.OnStart:
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
            ```

        *   **Final `DefaultSelectedItems` Formula:** The logic is handled entirely within the ComboBox's `DefaultSelectedItems` property. It uses an `If` statement to provide a default value for new items, while using the original parsing logic for existing items.
            ```powerapps
            // On the ComboBox control inside the data card
            If(
                frm_ArticleContent.Mode = FormMode.New,
                // For a new item, return a table containing the default record
                Table({Product: "All products/services"}),
                
                // For an existing item, use the original parsing logic
                ForAll(
                    Split(ThisItem.'Product/Service', ";"),
                    If(!IsBlank(Value), {Product: Value})
                )
            )
            ```
    *   **Publish On (`dc_publishOn`):**
        ```powerapps
        If(frm_ArticleContent.Mode = FormMode.New, Now(), ThisItem.'Publish On')
        ```
    *   **Expiration Date (`dc_expirationDate`):**
        ```powerapps
        If(frm_ArticleContent.Mode = FormMode.New, DateAdd(Today(), 5, TimeUnit.Years), ThisItem.'Expiration Date')
        ```
    *   **IsLatestVersion (`dc_IsLatestVersion`):**
        ```powerapps
        If(frm_ArticleContent.Mode = FormMode.New, true, ThisItem.IsLatestVersion)
        ```
    *   **IsPrimary (`dc_IsPrimary`):**
        ```powerapps
        If(frm_ArticleContent.Mode = FormMode.New, true, ThisItem.IsPrimary)
        ```
    *   **Status (`dc_Status`):** The Status field is intentionally left blank on a new form. In the V2 architecture, its default value is set on the backend by the **`Orchestrate-GenerateAltTextAndSaveArticle`** flow. The Power App includes a `saveMode` parameter in the JSON it sends to the flow. If `saveMode` is `"Draft"`, the flow sets the SharePoint item's status to "Draft". This ensures the status is only applied upon a successful save operation and centralizes the core business logic in the backend workflow.

### 12.6. Debugging the `Choices()` Function

A perplexing issue can arise where a Choice column's dropdown in Power Apps shows values that are not in the column's predefined settings in SharePoint.

*   **The Symptom:** A ComboBox whose `Items` property is set to `Choices([@DataSource].MyChoiceColumn)` displays extra, incorrect values. In our case, the 'Author Region' dropdown was showing values from the 'Audience' column ("Internal", "Public").

*   **The Root Cause: "Allow 'Fill-in' choices" in SharePoint.** This was not a Power Apps bug, but a data integrity issue. The SharePoint column was configured with "Allow 'Fill-in' choices" set to "Yes". During early API testing, incorrect data was written to this column. The `Choices()` function in Power Apps was correctly reporting **all unique values ever entered into that column**, including the polluted data.

*   **The Definitive Solution: Clean the Data and Settings**
    1.  **Clean the Data:** Manually edit the SharePoint list to remove all incorrect entries from the Choice column.
    2.  **Change the Setting:** In the SharePoint column's settings, change "Allow 'Fill-in' choices" to **"No"**. This prevents the issue from happening again.
    3.  **Refresh the Connection:** Back in the Power App, refresh the data source connection to ensure the app pulls the clean choice list. In extreme cases, removing and re-adding the data source may be necessary.

    Once the data and settings in SharePoint were corrected, the `Choices()` function in Power Apps immediately began returning the correct, clean list of options.
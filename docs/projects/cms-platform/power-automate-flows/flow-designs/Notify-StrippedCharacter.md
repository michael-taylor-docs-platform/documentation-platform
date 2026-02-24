# Design Document: HTTP - Stripped Character Notification

**Version: 3.0**

## 1. Executive Summary

This document outlines the architecture for the **HTTP - Stripped Character Notification** Power Automate flow. This flow operates asynchronously, triggered by the `html-sanitizer` Azure Function. Its primary purpose is to create a continuous improvement feedback loop by notifying administrators when the sanitizer encounters and strips previously unknown characters from knowledge base article content.

The flow is designed for performance and maintainability. It runs decoupled from the main article-saving process to ensure no impact on user experience. Configuration is externalized to a central SharePoint list, allowing administrators to manage notification settings without modifying the flow itself.

## 2. Architectural Diagram

```mermaid
graph TD
    subgraph "Azure Function"
        A[html-sanitizer] -- "Async HTTP POST<br><i>{ strippedChars: [...] }</i>" --> B{HTTP Request URL};
    end

    subgraph "Power Automate Flow"
        B -- "Trigger" --> C[SP Get items from 'App Configuration' list];
        C --> D[Filter for Email Config];
        C --> E[Filter for Exclusion List Config];
        D --> F[Initialize varNotificationEmail];
        E --> G[Initialize varExclusionList];
        
        subgraph "Main Processing"
            F & G --> H[Initialize varCharsToNotify (Array)];
            H --> I[Apply to each: `triggerBody()?['strippedChars']`];
            
            subgraph "For Each Character"
                I --> J{Condition: Is character in exclusion list?};
                J -- "No" --> K[Append character to `varCharsToNotify`];
                J -- "Yes" --> L[Do Nothing];
            end

            K --> M[End Loop];
            L --> M;

            M --> N{Condition: Is `varCharsToNotify` not empty?};
            N -- "Yes" --> O[Send Email Notification];
            N -- "No" --> P[End];
            O --> P;
        end
    end
```

## 3. Detailed Flow Logic

This flow is triggered by an HTTP request and uses a SharePoint list for configuration.

1.  **Trigger:** `When a HTTP request is received`
    *   **HTTP POST URL:** This URL is generated upon the first save of the flow and must be configured as the `NOTIFICATION_FLOW_URL` environment variable in the `html-sanitizer` Azure Function App.
    *   **Request Body JSON Schema:**
        ```json
        {
            "type": "object",
            "properties": {
                "strippedChars": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            }
        }
        ```

2.  **Action: Get items (SharePoint)**
    *   **Action Name:** `SP Get Config from App Configuration`
    *   **Site Address:** Select the SharePoint site where the list was created.
    *   **List Name:** `App Configuration`
    *   **Filter Query:** `Title eq 'CHAR_NOTIFICATION_EMAIL' or Title eq 'CHAR_EXCLUSION_LIST' or Title eq 'DEV_CONTACT_EMAIL'`
    *   **Top Count:** `3`

3.  **Action: Filter array**
    *   **Action Name:** `Filter for Email Config`
    *   **From:** `outputs('SP_Get_Config_from_App_Configuration')?['body/value']`
    *   **Condition:** `item()?['Title']` is equal to `CHAR_NOTIFICATION_EMAIL`

4.  **Action: Filter array**
    *   **Action Name:** `Filter for Exclusion List Config`
    *   **From:** `outputs('SP_Get_Config_from_App_Configuration')?['body/value']`
    *   **Condition:** `item()?['Title']` is equal to `CHAR_EXCLUSION_LIST`

5.  **Action: Initialize variable - `varNotificationEmail`**
    *   **Name:** `varNotificationEmail`
    *   **Type:** `String`
    *   **Value:** `body('Filter_for_Email_Config')?[0]?['Value']`

6.  **Action: Initialize variable - `varExclusionList`**
    *   **Name:** `varExclusionList`
    *   **Type:** `Array`
    *   **Value:** `split(replace(coalesce(body('Filter_for_Exclusion_List_Config')?[0]?['Value'], ''), ' ', ''), ',')`
    *   *Note: This splits the comma-separated string from SharePoint into an array. It also removes spaces to make the list more forgiving.*

7.  **Action: Filter array**
    *   **Action Name:** `Filter for Dev Contact Config`
    *   **From:** `outputs('SP_Get_Config_from_App_Configuration')?['body/value']`
    *   **Condition:** `item()?['Title']` is equal to `DEV_CONTACT_EMAIL`

8.  **Action: Initialize variable - `varDevContactEmail`**
    *   **Name:** `varDevContactEmail`
    *   **Type:** `String`
    *   **Value:** `coalesce(body('Filter_for_Dev_Contact_Config')?[0]?['Value'], 'dev-team@example.com')`
    *   *Note: `coalesce` provides a fallback email if the SharePoint item is missing.*

9.  **Action: Initialize variable - `varCharsToNotify`**
    *   **Name:** `varCharsToNotify`
    *   **Type:** `Array`
    *   **Value:** `[]`

10. **Action: Apply to each - `triggerBody()?['strippedChars']`**
    *   **Action Name:** `For Each Stripped Character`
    *   **Inside the loop:**
        1.  **Action: Condition**
            *   **Action Name:** `Is character in exclusion list?`
            *   **Condition:** `contains(variables('varExclusionList'), item())` is equal to `false`
            *   **If Yes (character is NOT in exclusion list):**
                *   **Action: Append to array variable**
                    *   **Name:** `varCharsToNotify`
                    *   **Value:** `item()`
            *   **If No:**
                *   (Do nothing)

11. **Action: Condition**
    *   **Action Name:** `Check if notification is needed`
    *   **Configure run after:** `For Each Stripped Character` has succeeded.
    *   **Condition:** `empty(variables('varCharsToNotify'))` is equal to `false`
    *   **If Yes (there are new, non-excluded characters):**
        1.  **Action: Send an email (V2)**
            *   **To:** `variables('varNotificationEmail')`
            *   **Subject:** `Action Required: New Invalid Characters Detected in KB Content`
            *   **Body:** (See HTML in Appendix A)
    *   **If No:**
        *   The flow terminates.

---

## 4. Configuration (SharePoint List)

The flow is configured via a SharePoint list named **`App Configuration`**. This list should be hidden from site navigation.

*   **Columns:**
    *   `Title` (Internal Name: `Title`) - Single line of text
    *   `Value` - Single line of text
*   **Required Items:**

| Title | Value | Description |
| :--- | :--- | :--- |
| `CHAR_NOTIFICATION_EMAIL` | `your-admin-email@example.com` | The email address or group that will receive the notification. |
| `CHAR_EXCLUSION_LIST` | `U+001E,U+001F` | A **comma-separated** list of Unicode strings (e.g., `U+001E`) to ignore. Spaces are ignored. |
| `DEV_CONTACT_EMAIL`   | `dev-team@example.com` | The email address for the development team contact. |

---

## 5. Appendix

### Appendix A: Notification Email Body

```html
<div style="font-family: Arial, sans-serif; font-size: 14px;">
    <p>Hello,</p>
    <p>The automated HTML sanitization service has detected and removed the following new character(s) from knowledge base article content:</p>
    <p style="background-color: #f0f0f0; border: 1px solid #cccccc; padding: 10px; font-family: Consolas, monospace; font-size: 16px;">
        <b>@{join(variables('varCharsToNotify'), '<br>')}</b>
    </p>
    <hr>
    <h3>Next Steps</h3>
    <p>Please review the character(s) above and decide on the appropriate action:</p>
    <ol>
        <li>
            <b>If the character should be permanently ignored (stripped without notification):</b>
            <ol>
                <li>Navigate to the <a href="https://trendmicro.sharepoint.com/sites/TrendVisionPulse/Lists/appConfiguration/AllItems.aspx">App Configuration List</a>.</li>
                <li>Find the item where the `Title` is <b>CHAR_EXCLUSION_LIST</b>.</li>
                <li>Click <b>Edit</b>.</li>
                <li>Copy the Unicode string from the list above and append it to the `Value` field, ensuring it is separated by a comma.</li>
                <li><b>Example:</b> If the current value is `U+001E` and the new character is `U+001F`, the new value should be `U+001E,U+001F`.</li>
                <li>Click <b>Save</b>.</li>
            </ol>
        </li>
        <li>
            <b>If the character should be converted to a different, valid character (e.g., converting ‘ to '):</b>
            <ul>
                <li>Contact <a href="mailto:@{variables('varDevContactEmail')}">@{variables('varDevContactEmail')}</a> to have them update the substitution map in the `html-sanitizer` Azure Function.</li>
            </ul>
        </li>
    </ol>
    <p>Taking action will prevent future notifications for these specific characters and help maintain content quality.</p>
    <p>Thank you,<br>
    The Knowledge Base System</p>
</div>
```

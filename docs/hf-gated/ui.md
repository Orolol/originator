# UI behaviour: screens, controls, states, side effects

"Faithful" means **behaviour, not pixels**: the same controls, state transitions, enabled/disabled
states, messages and requests fired (see [docs/assignement.md](../assignement.md)). Visual styling is
irrelevant.

Evidence levels here:
- [OBS]: captured from live HTML by `harness/kb/probe.py` (anonymous only, so far);
- [DOC-IMG]: official documentation screenshots (linked below; they may predate the current UI);
- [DOC]: documentation prose;
- **TO RECORD**: needs a logged-in session (owner account + requester account) through the bridge or
  a manual capture. These items are the P1 open questions.

**Recording constraint [OBS 2026-10-05]:** HF's HTML pages ignore `Authorization: Bearer` (the gate
component renders `isLoggedIn: false` even with a valid token). API state changes (`ask-access`,
`handle`, `grant`…) can be scripted with tokens, but the logged-in **screens** can only be captured
in a browser where the account owner logged in themselves. Agents must not type HF passwords.

Doc screenshots (light mode), base
`https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/hub/`:
`models-gated-disabled.png`, `models-gated-enabled.png`, `models-gated-manual-approval.png`,
`models-gated-enabled-pending-users.png`, `models-gated-user-side.png`.

---

## A. Requester: the gate box on the model page (`/{ns}/{repo}`)

The box sits above the model card. Files, the card and discussions remain browsable (ACC-4).

### A1. Anonymous visitor [OBS]

In visible order:
1. Heading: `You need to agree to share your contact information to access this model`, or
   `extra_gated_heading`.
2. Sub-line: `This repository is publicly accessible, but you have to accept the conditions to access
   its files and content.` The second clause is bold in the screenshot [DOC-IMG]. It is **replaced** by
   `extra_gated_description` when set.
3. The rendered `extra_gated_prompt`, if any.
4. `Log in` or `Sign Up` `to review the conditions and access this model content.`
5. **No form fields** in the server-rendered HTML for anonymous visitors (the checkbox label is absent).

### A2. Logged in, no request (and after `reset`) [DOC-IMG] [DOC], TO RECORD details

From the dataset-side screenshot (the model version says "model"):
1. Heading, as in A1.
2. Sub-line, as in A1.
3. The prompt, then the extra fields (`extra_gated_fields`, in YAML order [Q-11]).
4. `By agreeing you accept to share your contact information (email and username) with the
   repository authors.`
5. Primary button `Agree and send request to access repo` (or `extra_gated_button_content`) and a
   `Cancel` button.

TO RECORD: whether the default button label differs in auto mode; client-side validation (required
fields, unchecked checkbox) and its messages; what `Cancel` does; the redirect after submit (the spec
says `303` to the repo page).

### A3. Pending (manual mode), TO RECORD

Expected: a message that the request was submitted and awaits review. The API-side equivalent is
`Your request to access model {id} is awaiting a review from the repo authors.` [OBS-3P]. The page
wording is not yet recorded. Is there a requester-side "cancel request" control? The spec has a
self-cancel endpoint [Q-3].

### A4. Accepted, TO RECORD

Expected: a "you have been granted access" banner, with files downloadable.

### A5. Rejected [DOC], TO RECORD details

The API side is recorded: `403 GatedRepo` "Your request to access model {id} has been rejected by the
repo's authors.", with no reason [OBS 2026-10-05]. Our UI shows the docs' page text below.

`Your request to access this repo has been rejected by the repo's authors.` plus the
`rejectionReason` when one was given. No form, since the user cannot request again.

### A6. Reset [DOC] [OBS 2026-10-05 API side]

The API says `…has been reset by the repo's authors. Visit https://huggingface.co/{id} to submit a new request.`
Our UI shows the consent form again (A2) and was checked live: submit → 303 → pending.

On the next visit the user is prompted to agree and submit again, presumably screen A2. Is the
`resetReason` shown on the page, or only in the email? [Q-11]

---

## B. Owner: settings page (`/{ns}/{repo}/settings`), section "Gated user access" [DOC-IMG]

### B1. Disabled (`gated == false`)

- Title `Gated user access` with an ⓘ tooltip.
- `Access requests are currently [disabled] for this model.`
- `When enabled, users must share their contact information (email and username) and agree to your
  terms and conditions (if any) in order to access this model. You can download the list of users
  who have accepted and had access at any time.`
- Button, top right: `Enable Access requests`. Clicking it → `gated = "auto"` (CFG-1).

### B2. Enabled, automatic approval

- Badge becomes `[enabled]`; the button becomes `Disable Access requests` (→ `gated = false`).
- Row: `New requests:` select `Automatic approval` | `Manual review` → `gated = "auto" | "manual"`.
- `Review access requests (N)` button, which opens modal C. Whether **N** counts pending requests or
  all requests is TO RECORD [Q-13].
- `Download user access report` button → `GET /{id}/user-access-report` (file download, REP-1).

### B3. Enabled, manual review

Everything in B2, plus:
- `Add access` button → user search, then grant (`POST …/grant`).
- `Notifications frequency ⓘ` select: `Once a day` (= `bulk`) | real-time (label TO RECORD).
- `Notifications email ⓘ` text input, placeholder `example@example.com`. Empty → default recipients.

### B4. Org-owned repos [DOC]

An extra checkbox: `Also gate access for members of {org}` → `orgMembersGated`.

TO RECORD for all of B: does each control save immediately (one `PUT /settings` per change) or is
there a save button? Are there confirmations (for example, on disable)? What does the email field
show on validation errors? Which controls are disabled for read-role members? [Q-12]

---

## C. Owner: "Manage access requests" modal [DOC-IMG] [DOC]

- Title `Manage access requests` and a close ×.
- Tabs with counts: `pending (n)`, `accepted (n)`, `rejected (n)`. Whether the UI has a `reset` tab is
  TO RECORD (the API has a `reset` list) [Q-13].
- One row per request: avatar, **username (link)**, `·` email, `·` relative time
  (`less than a minute ago`), then the actions on the right.

| Tab | Row actions | Effect | Evidence |
|---|---|---|---|
| pending | `Accept`, `Reject` | → accepted / rejected | [DOC] [DOC-IMG] |
| accepted | `Reject`, `Cancel` | → rejected / back to pending | [DOC] |
| rejected | TO RECORD (the API allows → accepted and → pending) | | [CLIENT] |

TO RECORD: how the form answers (`fields`) are displayed; the rejection-reason input (a modal on
Reject?); reset as a UI action; search box (`q`), pagination ("load more"?), multi-select or bulk
actions (the `batch` endpoint suggests they exist); confirmations; how counts and tabs refresh after
an action.

---

## D. Side-effect matrix (what the clone UI must fire)

**Verified for our UI on 2026-10-05.** A live walkthrough through the bridge clicked each row below.
Each fired exactly the listed request, and each got `200`/`303` from huggingface.co:
`observations/2026-10-05-ui-walkthrough.md`, 13 writes. This proves *our* UI fires these requests; that
*HF's own* UI fires the same ones is still TO RECORD (it needs a browser session on huggingface.co).

| User action | Request | Then on screen |
|---|---|---|
| Enable access requests | `PUT /api/models/{id}/settings {gated:"auto"}` | B1 → B2 |
| Disable access requests | `PUT … {gated:false}` | B2/B3 → B1 |
| Change "New requests" select | `PUT … {gated:"auto"\|"manual"}` | B2 ⇄ B3 |
| Change notifications frequency / email | `PUT … {gatedNotificationsMode / gatedNotificationsEmail}` | TO RECORD |
| Add access → pick user | `POST …/user-access-request/grant {user}` | user appears in accepted |
| Accept / Reject / Cancel in the modal | `POST …/user-access-request/handle {user, status[, rejectionReason]}` | row moves tab; counts update |
| Download report | `GET /{id}/user-access-report` | browser download |
| Requester submits the form | `POST /{id}/ask-access` (fields) → 303 → repo page | A2 → A3 (manual) or A4 (auto) |

## E. Recording checklist (needs two real accounts and a sandbox repo)

1. Owner: settings states B1 → B2 → B3 → back, capturing each `PUT` payload and response.
2. Requester on a manual repo with every field type: A2 (validation), submit (capture the `ask-access`
   request, its encoding and the redirect), A3.
3. Owner: modal C at each step (pending → accept → cancel → reject with reason → accept → reset).
   Capture the payloads and the requester-side page after each step (A4, A5, A6).
4. Auto repo: submit, A4 immediately; owner cancels → pending tab non-empty in auto mode (REV-4).
5. Report download after each phase: format and fields.
6. Content-route errors for the requester in every state: `resolve`, `auth-check`, status code and
   `X-Error-Message` [Q-8].

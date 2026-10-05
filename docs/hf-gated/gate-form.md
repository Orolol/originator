# Gate form: card metadata → consent form

The owner configures what the requester sees and answers through **YAML front matter in the repo's
`README.md`**, not through the settings API. The clone seeds this as `cardData` on the repo
fixture; editing it is out of slice (it is a commit).

## 1. Metadata keys

| Key | Type | Effect | Evidence |
|---|---|---|---|
| `extra_gated_prompt` | markdown string | Text shown in the gate box, typically the licence. Rendered to sanitised HTML. | [DOC] [OBS] |
| `extra_gated_fields` | map `label → field spec` | Extra inputs. The **label is both the visible text and the key** in the stored `fields` answers. | [DOC] [SPEC] |
| `extra_gated_heading` | string | Replaces the default heading. | [DOC] [OBS] |
| `extra_gated_description` | markdown string | Replaces the default sub-line "This repository is publicly accessible, but you have to accept the conditions to access its files and content." | [DOC] [OBS] |
| `extra_gated_button_content` | string | Replaces the submit button label. | [DOC] [OBS] |
| `extra_gated_eu_disallowed` | bool | Blocks users located in the EU by IP. Only works if the repo is gated. Out of slice. | [DOC] |

## 2. Field specs

A field spec is either a bare type string or `{type: …}`. [DOC] [JS]

| Type | Input | Notes | Evidence |
|---|---|---|---|
| `text` | single-line text | | [DOC] |
| `checkbox` | checkbox | Usually "I agree…" lines; whether checking is mandatory is [Q-16] | [DOC] |
| `date_picker` | date picker | stored format [Q-15] | [DOC] |
| `country` | dropdown, ISO 3166-1 alpha-2 list | stored as code or name [Q-15] | [DOC] |
| `select` | dropdown; `options: [string \| {label, value}]` | stored value vs label [Q-15] | [DOC] [JS] |
| `ip_location` | **undocumented**; probably no input, with the server recording the requester's IP-based location | used live by `meta-llama/Llama-3.2-1B` (`geo: ip_location`) | [JS] [OBS] [Q-15] |

Answers are stored as `fields: {label: string}`; every value is a string. [SPEC]

## 3. How metadata reaches the page (observed props)

Repo pages are server-rendered Svelte. The gate box is a component `data-target="RepoGatedModal"`
whose JSON `data-props` were captured anonymously. [OBS], in
[observations/2026-10-05-anonymous-probes.md](observations/2026-10-05-anonymous-probes.md):

| Prop | Source | Present when |
|---|---|---|
| `gated` | repo setting (`"auto"` / `"manual"`) | always |
| `isLoggedIn` | session | always |
| `repoId`, `repoType` | repo | always |
| `additionalMessage` `{contents, html, classNames}` | `extra_gated_prompt` (markdown + sanitised HTML) | prompt set |
| `additionalFields` | `extra_gated_fields`, verbatim | fields set |
| `customHeading` | `extra_gated_heading` | heading set |
| `customDescription` `{contents, html, classNames}` | `extra_gated_description` | description set |
| `accessButtonString` | `extra_gated_button_content` | button set |
| `isGoogleGemma` | special-cased repos (true on `google/gemma-2-2b`) | always; quirk, out of slice |
| `requiresPaidPlan` | unknown | always; out of slice |

Logged-in props (request status, rejection reason, user email…) have not been recorded yet [Q-11].

## 4. Live examples (2026-10-05)

| Repo | Mode | Customisation |
|---|---|---|
| `bigcode/starcoder` | auto | prompt + 1 checkbox; default heading, description and button |
| `meta-llama/Llama-3.2-1B` | manual | long licence prompt, custom description, button `Submit`; fields: `text`×3, `date_picker`, `country`, `select`, `ip_location`, `checkbox` |
| `google/gemma-2-2b` | manual | custom heading `Access Gemma on Hugging Face`, button `Acknowledge license`, prompt says "Requests are processed immediately" (the owner auto-accepts through the API) |
| `mistralai/Mistral-7B-v0.1` | **not gated** | leftover `extra_gated_description`, ignored (CFG-5) |

These are good **seed fixtures**: one auto repo with a single checkbox, one manual repo using every
field type, one with custom heading and button, and one non-gated repo carrying stale metadata.

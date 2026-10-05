# Probe results: harness/kb/probes/hf-gated-anonymous.json

Recorded 2026-10-05T13:33:43Z by `harness/kb/probe.py` (no cookies, redirects not followed; `as` = identity used, secrets and e-mails redacted).
Regenerate with the command in the script docstring. Do not hand-edit: re-run instead.

| id | as | request | status | X-Error-Code | X-Error-Message / Location / body excerpt | note |
|---|---|---|---|---|---|---|
| meta-manual | anonymous | `GET /api/models/meta-llama/Llama-3.2-1B?expand[]=gated` | 200 |  | {"_id":"66eaebb25fcdca258b9576cb","id":"meta-llama/Llama-3.2-1B","gated":"manual"} | repo metadata stays public; gated=manual |
| meta-auto | anonymous | `GET /api/models/bigcode/starcoder?expand[]=gated` | 200 |  | {"_id":"644677e41173e85ac7f10745","id":"bigcode/starcoder","gated":"auto"} | gated=auto |
| meta-not-gated | anonymous | `GET /api/models/mistralai/Mistral-7B-v0.1?expand[]=gated` | 200 |  | {"_id":"650aedb6238a644cb93a52c3","id":"mistralai/Mistral-7B-v0.1","gated":false} | gated=false although card keeps an extra_gated_description |
| info-revision | anonymous | `GET /api/models/meta-llama/Llama-3.2-1B/revision/main` | 200 |  | {"_id":"66eaebb25fcdca258b9576cb","id":"meta-llama/Llama-3.2-1B","private":false,"pipeline | full model info is public |
| tree | anonymous | `GET /api/models/meta-llama/Llama-3.2-1B/tree/main` | 200 |  | [{"type":"directory","oid":"43407f64fdf0c27f09292520c4ebed5326ad6b4f","size":0,"path":"ori | file listing (paths, sizes, oids) is public |
| page | anonymous | `GET /meta-llama/Llama-3.2-1B` | 200 |  |  | model page renders |
| page-tree | anonymous | `GET /meta-llama/Llama-3.2-1B/tree/main` | 200 |  |  | files tab renders |
| discussions-page | anonymous | `GET /meta-llama/Llama-3.2-1B/discussions` | 200 |  |  | community tab readable |
| discussions-api | anonymous | `GET /api/models/meta-llama/Llama-3.2-1B/discussions` | 200 |  | {"discussions":[{"num":379,"author":{"_id":"67fd1aa0b80d3058701dfa63","avatarUrl":"/avatar | community API readable |
| resolve-config-manual | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/config.json` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | gated file |
| resolve-config-auto | anonymous | `GET /bigcode/starcoder/resolve/main/config.json` | 401 | GatedRepo | Access to model bigcode/starcoder is restricted. You must have access to it and be authenticated to access it. Please log in. | same answer in auto mode |
| head-config-auto | anonymous | `HEAD /bigcode/starcoder/resolve/main/config.json` | 401 | GatedRepo | Access to model bigcode/starcoder is restricted. You must have access to it and be authenticated to access it. Please log in. | HEAD behaves like GET |
| resolve-gitattributes | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/.gitattributes` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | .gitattributes is gated |
| resolve-subdir | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/original/params.json` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | subdirectory file gated |
| resolve-use-policy | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/USE_POLICY.md` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | other .md files gated |
| allow-readme | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/README.md` | 200 |  | --- language: - en - de - fr - it - pt - hi - es - th library_name: transformers pipeline_ | allowlisted |
| allow-readme-auto | anonymous | `GET /bigcode/starcoder/resolve/main/README.md` | 200 |  | --- pipeline_tag: text-generation inference: true widget: - text: 'def print_hello_world() | allowlisted in auto mode too |
| allow-license-txt | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/LICENSE.txt` | 200 |  | LLAMA 3.2 COMMUNITY LICENSE AGREEMENT Llama 3.2 Version Release Date: September 25, 2024   | allowlisted |
| allow-license-missing | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/LICENSE` | 404 | EntryNotFound | Entry not found | allowlisted path, file absent -> 404 not 401 |
| allow-license-md-missing | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/LICENSE.md` | 404 | EntryNotFound | Entry not found | allowlisted path, file absent |
| deny-readme-lower | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/readme.md` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | allowlist is case-sensitive |
| deny-readme-upper-ext | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/README.MD` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | case-sensitive extension |
| deny-readme-txt | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/README.txt` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | only README.md |
| deny-readme-noext | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/README` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | only README.md |
| deny-license-rst | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/LICENSE.rst` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | only none/.md/.txt |
| deny-license-lower | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/license.txt` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | case-sensitive |
| deny-licence | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/LICENCE` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | British spelling not allowlisted |
| deny-copying | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/COPYING` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | not allowlisted |
| deny-subdir-readme | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/original/README.md` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | root only |
| deny-subdir-license | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/original/LICENSE.txt` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | root only |
| raw-readme | anonymous | `GET /meta-llama/Llama-3.2-1B/raw/main/README.md` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | /raw/ is gated even for README.md |
| blob-config | anonymous | `GET /meta-llama/Llama-3.2-1B/blob/main/config.json` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | /blob/ page gated |
| gate-before-entry | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/main/does-not-exist.bin` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | gate checked before file existence |
| gate-before-revision | anonymous | `GET /meta-llama/Llama-3.2-1B/resolve/nonexistent-branch/config.json` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | gate checked before revision existence |
| missing-repo-resolve | anonymous | `GET /someone-xyz123/definitely-not-a-repo/resolve/main/config.json` | 401 |  | Invalid username or password. | comparison: unknown repo, anonymous |
| auth-check-gated | anonymous | `GET /api/models/meta-llama/Llama-3.2-1B/auth-check` | 401 | GatedRepo | Access to model meta-llama/Llama-3.2-1B is restricted. You must have access to it and be authenticated to access it. Please log in. | JSON error body |
| auth-check-public | anonymous | `GET /api/models/openai-community/gpt2/auth-check` | 200 |  | OK | comparison: public repo |
| auth-check-missing | anonymous | `GET /api/models/someone-xyz123/definitely-not-a-repo/auth-check` | 401 |  | Invalid username or password. | comparison: unknown repo |
| owner-list-anon | anonymous | `GET /api/models/meta-llama/Llama-3.2-1B/user-access-request/pending` | 401 |  | Invalid username or password. | owner endpoint, anonymous |
| owner-list-not-gated-anon | anonymous | `GET /api/models/openai-community/gpt2/user-access-request/pending` | 401 |  | Invalid username or password. | owner endpoint on non-gated repo, anonymous: auth checked first |
| report-anon | anonymous | `GET /meta-llama/Llama-3.2-1B/user-access-report` | 401 |  | Invalid username or password. | access report, anonymous |
| gate-props-auto | anonymous | `GET /bigcode/starcoder` | 200 |  |  | gate component props, default texts |
| gate-props-manual-custom | anonymous | `GET /meta-llama/Llama-3.2-1B` | 200 |  |  | custom description + button, all field types |
| gate-props-heading | anonymous | `GET /google/gemma-2-2b` | 200 |  |  | custom heading + button |

## Extracted component props

### gate-props-auto

```json
{
 "additionalFields": {
  "I accept the above license agreement, and will use the Model complying with the set of use restrictions and sharing requirements": "checkbox"
 },
 "additionalMessage": {
  "contents": "## Model License Agreement\nPlease read the BigCode [OpenRAIL-M license](https://huggingface.co/spaces/bigcode/bigcode-model-license-agreement) agreement before accepting it.\n  ",
  "html": "<h2>Model License Agreement</h2>\n<p>Please read the BigCode <a href=\"https://huggingface.co/spaces/bigcode/bigcode-model-license-agreement\" rel=\"nofollow\">OpenRAIL-M license</a> agreement before accep…[+16 chars]",
  "classNames": "hf-sanitized hf-sanitized-vVSXW-lqd4_dlOvnEcMNB"
 },
 "gated": "auto",
 "isLoggedIn": false,
 "repoId": "bigcode/starcoder",
 "repoType": "model",
 "isGoogleGemma": false,
 "requiresPaidPlan": false
}
```

### gate-props-manual-custom

```json
{
 "accessButtonString": "Submit",
 "additionalFields": {
  "First Name": "text",
  "Last Name": "text",
  "Date of birth": "date_picker",
  "Country": "country",
  "Affiliation": "text",
  "Job title": {
   "type": "select",
   "options": [
    "Student",
    "Research Graduate",
    "AI researcher",
    "AI developer/engineer",
    "Reporter",
    "Other"
   ]
  },
  "geo": "ip_location",
  "By clicking Submit below I accept the terms of the license and acknowledge that the information I provide will be collected stored processed and shared in accordance with the Meta Privacy Policy": "checkbox"
 },
 "additionalMessage": {
  "contents": "### LLAMA 3.2 COMMUNITY LICENSE AGREEMENT\n\nLlama 3.2 Version Release Date: September 25, 2024\n\n“Agreement” means the terms and conditions for use, reproduction, distribution  and modification of the L…[+13342 chars]",
  "html": "<h3>LLAMA 3.2 COMMUNITY LICENSE AGREEMENT</h3>\n<p>Llama 3.2 Version Release Date: September 25, 2024</p>\n<p>“Agreement” means the terms and conditions for use, reproduction, distribution  and modifica…[+14211 chars]",
  "classNames": "hf-sanitized hf-sanitized-7Jvr1Unnh6hKfRAZjUuyk"
 },
 "customDescription": {
  "contents": "The information you provide will be collected, stored, processed and shared in accordance with the [Meta Privacy Policy](https://www.facebook.com/privacy/policy/).",
  "html": "<p>The information you provide will be collected, stored, processed and shared in accordance with the <a href=\"https://www.facebook.com/privacy/policy/\" rel=\"nofollow\">Meta Privacy Policy</a>.</p>\n",
  "classNames": "hf-sanitized hf-sanitized-F00iADv2EESOL-SL9P8TB"
 },
 "gated": "manual",
 "isLoggedIn": false,
 "repoId": "meta-llama/Llama-3.2-1B",
 "repoType": "model",
 "isGoogleGemma": false,
 "requiresPaidPlan": false
}
```

### gate-props-heading

```json
{
 "accessButtonString": "Acknowledge license",
 "additionalMessage": {
  "contents": "To access Gemma on Hugging Face, you’re required to review and agree to Google’s usage license. To do this, please ensure you’re logged in to Hugging Face and click below. Requests are processed immed…[+7 chars]",
  "html": "<p>To access Gemma on Hugging Face, you’re required to review and agree to Google’s usage license. To do this, please ensure you’re logged in to Hugging Face and click below. Requests are processed im…[+15 chars]",
  "classNames": "hf-sanitized hf-sanitized-dlY0fv1NfWtSnvxJ1XVYK"
 },
 "customHeading": "Access Gemma on Hugging Face",
 "gated": "manual",
 "isLoggedIn": false,
 "repoId": "google/gemma-2-2b",
 "repoType": "model",
 "isGoogleGemma": true,
 "requiresPaidPlan": false
}
```


## Extracted visible text (one line per text node)

### gate-props-auto

1. You need to agree to share your contact information to access this model
2. This repository is publicly accessible, but
3. you have to accept the conditions to access its files and content
4. .
5. Model License Agreement
6. Please read the BigCode
7. OpenRAIL-M license
8. agreement before accepting it.
9. Log in
10. or
11. Sign Up
12. to review the conditions and access this model content.

### gate-props-manual-custom

1. You need to agree to share your contact information to access this model
2. The information you provide will be collected, stored, processed and shared in accordance with the
3. Meta Privacy Policy
4. .
5. LLAMA 3.2 COMMUNITY LICENSE AGREEMENT
6. Llama 3.2 Version Release Date: September 25, 2024

### gate-props-heading

1. Access Gemma on Hugging Face
2. This repository is publicly accessible, but
3. you have to accept the conditions to access its files and content
4. .
5. To access Gemma on Hugging Face, you’re required to review and agree to Google’s usage license. To do this, please ensure you’re logged in to Hugging Face and click below. Requests are processed immed…[+7 chars]
6. Log in
7. or
8. Sign Up
9. to review the conditions and access this model content.


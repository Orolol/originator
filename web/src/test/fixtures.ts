// Card metadata fixtures (docs/hf-gated/gate-form.md §3–4, observations/2026-10-05-anonymous-probes.md).

/** `meta-llama/Llama-3.2-1B` (manual): every documented field type, custom description and button. */
export const LLAMA_CARD = {
  extra_gated_prompt: "### LLAMA 3.2 COMMUNITY LICENSE AGREEMENT\n\nLlama 3.2 Version Release Date: September 25, 2024",
  extra_gated_description:
    "The information you provide will be collected, stored, processed and shared in accordance with the [Meta Privacy Policy](https://www.facebook.com/privacy/policy/).",
  extra_gated_button_content: "Submit",
  extra_gated_fields: {
    "First Name": "text",
    "Last Name": "text",
    "Date of birth": "date_picker",
    Country: "country",
    Affiliation: "text",
    "Job title": {
      type: "select",
      options: ["Student", "Research Graduate", "AI researcher", "AI developer/engineer", "Reporter", "Other"],
    },
    geo: "ip_location",
    "By clicking Submit below I accept the terms of the license and acknowledge that the information I provide will be collected stored processed and shared in accordance with the Meta Privacy Policy":
      "checkbox",
  },
};

/** `bigcode/starcoder` (auto): prompt + one checkbox, default heading, description and button. */
export const STARCODER_CARD = {
  extra_gated_prompt:
    "## Model License Agreement\nPlease read the BigCode [OpenRAIL-M license](https://huggingface.co/spaces/bigcode/bigcode-model-license-agreement) agreement before accepting it.\n  ",
  extra_gated_fields: {
    "I accept the above license agreement, and will use the Model complying with the set of use restrictions and sharing requirements":
      "checkbox",
  },
};

/** `google/gemma-2-2b`: custom heading and button. */
export const GEMMA_CARD = {
  extra_gated_heading: "Access Gemma on Hugging Face",
  extra_gated_button_content: "Acknowledge license",
  extra_gated_prompt: "To access Gemma on Hugging Face, you’re required to review and agree to Google’s usage license.",
};

/** A distinct 24-hex `_id` per username (TestingBOrig keeps its real one). */
export function userId(user: string): string {
  if (user === "TestingBOrig") return "6ac3a4b8792f9017b6cb67ec";
  return [...user].map((c) => c.charCodeAt(0).toString(16)).join("").padEnd(24, "0").slice(0, 24);
}

/** Owner list item as observed on the sandbox (api.md §2), with an extra `fields` map. */
export function accessRequest(user: string, status: string, fields?: Record<string, string>) {
  return {
    user: {
      _id: userId(user),
      avatarUrl: "/avatars/x.svg",
      isPro: false,
      fullname: user,
      user,
      type: "user",
      verifiedOrgNames: [],
      email: `${user.toLowerCase()}@example.com`,
    },
    timestamp: new Date().toISOString(),
    status,
    ...(fields ? { fields } : {}),
  };
}

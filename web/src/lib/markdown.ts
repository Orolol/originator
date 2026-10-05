// `extra_gated_prompt` / `extra_gated_description` are markdown rendered to sanitised HTML
// (gate-form.md §3). markdown-it with `html: false` escapes raw HTML and rejects unsafe link
// schemes, which is the sanitisation we need for card metadata.
import MarkdownIt from "markdown-it";

const md = new MarkdownIt({ html: false, linkify: false });

export function renderMarkdown(source: string): string {
  return md.render(source);
}

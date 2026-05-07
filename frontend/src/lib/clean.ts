/**
 * Light cosmetic cleanup for analyst output.
 *
 * Different LLM providers default to different markdown habits — Claude
 * loves `## headers`, GPT loves `**bold**`, NVIDIA NIM models often emit
 * blank section dividers. The persona prompt now asks them not to, but we
 * still strip leftovers at render time so a misbehaving model can't
 * uglify the UI. Conservative on purpose — we only touch syntax that's
 * unambiguously markdown formatting, never punctuation that could be
 * meaningful (e.g. `5*5` is left alone).
 */
export function cleanAgentText(raw: string): string {
  if (!raw) return raw;
  let s = raw;

  // Strip paired bold markers: **xxx** → xxx
  s = s.replace(/\*\*([^*\n]+?)\*\*/g, "$1");
  // Strip paired __italic__ → italic   (rare but happens)
  s = s.replace(/__([^_\n]+?)__/g, "$1");
  // Strip leading-of-line markdown headers: '## foo' → 'foo'
  s = s.replace(/^\s*#{1,6}[ \t]+/gm, "");
  // Strip stray code-fence lines (```python / ```)
  s = s.replace(/^```\w*\s*$/gm, "");
  // Collapse 3+ consecutive newlines into 2 (no big visual gaps)
  s = s.replace(/\n{3,}/g, "\n\n");

  return s.trim();
}

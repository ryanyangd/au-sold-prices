export interface Segment {
  text: string;
  match: boolean;
}

/** Splits `text` into segments, flagging substrings matching any whitespace-separated query token (case-insensitive). */
export function highlightSegments(text: string, query: string): Segment[] {
  const tokens = query
    .toLowerCase()
    .split(/[\s,]+/)
    .filter(Boolean);
  if (tokens.length === 0 || !text) return [{ text, match: false }];

  const lower = text.toLowerCase();
  const flags = new Array<boolean>(text.length).fill(false);
  for (const token of tokens) {
    let from = 0;
    for (;;) {
      const idx = lower.indexOf(token, from);
      if (idx === -1) break;
      for (let i = idx; i < idx + token.length; i++) flags[i] = true;
      from = idx + token.length;
    }
  }

  const out: Segment[] = [];
  let start = 0;
  for (let i = 1; i <= text.length; i++) {
    if (i === text.length || flags[i] !== flags[start]) {
      out.push({ text: text.slice(start, i), match: Boolean(flags[start]) });
      start = i;
    }
  }
  return out;
}

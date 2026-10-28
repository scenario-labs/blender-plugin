// SPDX-FileCopyrightText: 2026 Scenario Inc.
// SPDX-License-Identifier: GPL-3.0-or-later
// @ts-check
// Search the handbook in the page itself: no service, no library, no index file.
// The handbook template inlines this file, so the standalone handbook searches
// offline too. Node loads the same file for the unit tests in tests/site/.

/**
 * @typedef {{id: string, title: string, trail: string, text: string}} Section
 * @typedef {{text: string, match: boolean}} Segment
 * @typedef {{section: Section, score: number, title: Segment[], snippet: Segment[]}} Result
 */

const WORD = /[\p{L}\p{N}]+/gu;
// A title match outranks the text, which outranks the parent section's title.
const WEIGHTS = { title: 3, text: 1, trail: 0.5 };
const SNIPPET_BEFORE = 60;
const SNIPPET_LENGTH = 160;
// Closeness at or below this came from a typo, not the letters as typed.
const TYPO = 0.4;
// English endings, longest first; "ies"/"ied" become "y" so "query" meets
// "queries". A bare "y" is not stripped: "ready" is not a form of "read".
const ENDINGS = [
  ["ations", ""],
  ["ation", ""],
  ["ions", ""],
  ["ion", ""],
  ["ings", ""],
  ["ing", ""],
  ["ies", "y"],
  ["ied", "y"],
  ["ers", ""],
  ["er", ""],
  ["ed", ""],
  ["es", ""],
  ["s", ""],
  ["e", ""],
];
const MIN_STEM = 4;

/** @param {string} text */
function normalize(text) {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

/** @param {string} text */
function words(text) {
  return normalize(text).match(WORD) ?? [];
}

/**
 * Edit distance with adjacent transpositions, stopping once it exceeds `limit`.
 * @param {string} a
 * @param {string} b
 * @param {number} limit
 */
function distance(a, b, limit) {
  if (Math.abs(a.length - b.length) > limit) return limit + 1;
  /** @type {number[][]} */
  const rows = [];
  for (let i = 0; i <= a.length; i++) {
    rows.push([i]);
    for (let j = 1; j <= b.length; j++) {
      if (i === 0) {
        rows[0].push(j);
        continue;
      }
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      let value = Math.min(rows[i - 1][j] + 1, rows[i][j - 1] + 1, rows[i - 1][j - 1] + cost);
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
        value = Math.min(value, rows[i - 2][j - 2] + 1);
      }
      rows[i].push(value);
    }
    if (i > 0 && Math.min(...rows[i]) > limit) return limit + 1;
  }
  return rows[a.length][b.length];
}

/**
 * The word and every stem of MIN_STEM letters or more left by dropping one of its endings.
 * @param {string} word
 */
function stems(word) {
  const found = [word];
  for (const [ending, replacement] of ENDINGS) {
    if (!word.endsWith(ending)) continue;
    const stem = word.slice(0, -ending.length) + replacement;
    if (stem.length >= MIN_STEM) found.push(stem);
  }
  return found;
}

/**
 * Whether two words are forms of one word: "agents" and "agent", "queries" and "query".
 * @param {string} term
 * @param {string} word
 */
function shareStem(term, word) {
  const termStems = new Set(stems(term));
  return stems(word).some((stem) => termStems.has(stem));
}

/**
 * How well one query term matches one word, from 0 (not at all) to 1 (exactly).
 * @param {string} term
 * @param {string} word
 */
function closeness(term, word) {
  if (word === term) return 1;
  if (word.startsWith(term)) return 0.75;
  if (shareStem(term, word)) return 0.6;
  if (term.length >= 3 && word.includes(term)) return 0.5;
  // Typos only count in words of five letters or more, judged by the word in
  // the guide: "imge" is one letter short of "image".
  const allowed = term.length >= 4 && word.length >= 5 ? (word.length >= 9 ? 2 : 1) : 0;
  if (allowed && distance(term, word, allowed) <= allowed) return 0.4;
  // A typo while the word is still being typed: compare with its start.
  const partial = term.length >= 9 ? 2 : term.length >= 5 ? 1 : 0;
  if (partial && word.length > term.length && distance(term, word.slice(0, term.length), partial) <= partial) {
    return 0.35;
  }
  return 0;
}

/**
 * The best match of a term among unique words, with the words it matched,
 * counting either only typo matches or only typo-free ones.
 * @param {string} term
 * @param {Set<string>} candidates
 * @param {boolean} typo
 */
function best(term, candidates, typo) {
  let score = 0;
  /** @type {Set<string>} */
  const matched = new Set();
  for (const word of candidates) {
    const value = closeness(term, word);
    if (value === 0 || value <= TYPO !== typo) continue;
    matched.add(word);
    score = Math.max(score, value);
  }
  return { score, matched };
}

/**
 * A term's best weighted match in a section among its typo or typo-free
 * matches, with the title and text words matched; undefined when none.
 * @param {string} term
 * @param {{title: Set<string>, text: Set<string>, trail: Set<string>}} fields
 * @param {boolean} typo
 */
function bestField(term, fields, typo) {
  let score = 0;
  /** @type {{title: Set<string>, text: Set<string>}} */
  const matched = { title: new Set(), text: new Set() };
  for (const field of /** @type {const} */ (["title", "text", "trail"])) {
    const found = best(term, fields[field], typo);
    score = Math.max(score, found.score * WEIGHTS[field]);
    if (field !== "trail") matched[field] = found.matched;
  }
  return score > 0 ? { score, matched } : undefined;
}

/**
 * Split text into plain and matched segments, merging neighbours of one kind.
 * @param {string} text
 * @param {Set<string>} matched normalized words to highlight
 * @param {number} start
 * @param {number} end
 * @returns {Segment[]}
 */
function segments(text, matched, start = 0, end = text.length) {
  /** @type {Segment[]} */
  const parts = [];
  /** @param {string} piece @param {boolean} match */
  const push = (piece, match) => {
    if (!piece) return;
    const last = parts[parts.length - 1];
    if (last && last.match === match) last.text += piece;
    else parts.push({ text: piece, match });
  };
  let cursor = start;
  for (const token of text.slice(start, end).matchAll(WORD)) {
    const at = start + (token.index ?? 0);
    if (!matched.has(normalize(token[0]))) continue;
    push(text.slice(cursor, at), false);
    push(token[0], true);
    cursor = at + token[0].length;
  }
  push(text.slice(cursor, end), false);
  return parts;
}

/**
 * Up to SNIPPET_LENGTH characters of the text around its first matched word.
 * @param {string} text
 * @param {Set<string>} matched
 * @returns {Segment[]}
 */
function snippet(text, matched) {
  let first = 0;
  for (const token of text.matchAll(WORD)) {
    if (matched.has(normalize(token[0]))) {
      first = token.index ?? 0;
      break;
    }
  }
  let start = Math.max(0, first - SNIPPET_BEFORE);
  if (start > 0) start = text.indexOf(" ", start) + 1 || start;
  let end = Math.min(text.length, start + SNIPPET_LENGTH);
  if (end < text.length) end = text.lastIndexOf(" ", end) > first ? text.lastIndexOf(" ", end) : end;
  const parts = segments(text, matched, start, end);
  if (start > 0) parts.unshift({ text: "…", match: false });
  if (end < text.length) parts.push({ text: "…", match: false });
  return parts;
}

/**
 * Rank sections for a query. Every query word must match the section somewhere.
 * A word counts a typo only when nothing in the section matches it without one,
 * and only the words of the kind that scored it are highlighted. Sections with
 * fewer typos rank first, so an exact word in the text beats a typo in a title.
 * @param {Section[]} sections
 * @param {string} query
 * @param {number} [limit]
 * @returns {Result[]}
 */
function search(sections, query, limit = 8) {
  const terms = [...new Set(words(query))];
  if (!terms.length) return [];
  /** @type {{result: Result, typos: number}[]} */
  const ranked = [];
  for (const section of sections) {
    const fields = {
      title: new Set(words(section.title)),
      text: new Set(words(section.text)),
      trail: new Set(words(section.trail)),
    };
    let total = 0;
    let typos = 0;
    /** @type {{title: Set<string>, text: Set<string>}} */
    const highlight = { title: new Set(), text: new Set() };
    for (const term of terms) {
      const exact = bestField(term, fields, false);
      const match = exact ?? bestField(term, fields, true);
      if (!match) {
        total = 0;
        break;
      }
      if (!exact) typos += 1;
      total += match.score;
      for (const word of match.matched.title) highlight.title.add(word);
      for (const word of match.matched.text) highlight.text.add(word);
    }
    if (total > 0) {
      ranked.push({
        typos,
        result: {
          section,
          score: total,
          title: segments(section.title, highlight.title),
          snippet: snippet(section.text, highlight.text),
        },
      });
    }
  }
  // Array.prototype.sort is stable: equal ranks keep the handbook's order.
  return ranked
    .sort((a, b) => a.typos - b.typos || b.result.score - a.result.score)
    .slice(0, limit)
    .map(({ result }) => result);
}

/**
 * Read the handbook's sections: each heading with an id and the text after it.
 * @param {Element} article
 * @returns {Section[]}
 */
function collect(article) {
  /** @type {Section[]} */
  const sections = [];
  let parent = "";
  /** @type {Section | undefined} */
  let current;
  for (const node of article.children) {
    const level = /^H([1-3])$/.exec(node.tagName)?.[1];
    if (level && node.id) {
      const title = (node.textContent ?? "").trim();
      if (level !== "3") parent = level === "2" ? title : "";
      current = { id: node.id, title, trail: level === "3" ? parent : "", text: "" };
      sections.push(current);
    } else if (current) {
      current.text += ` ${node.textContent ?? ""}`;
    }
  }
  for (const section of sections) section.text = section.text.replace(/\s+/g, " ").trim();
  return sections;
}

/**
 * @param {Document} document
 * @param {HTMLElement} parent
 * @param {Segment[]} parts
 */
function fill(document, parent, parts) {
  for (const part of parts) {
    if (part.match) {
      const mark = document.createElement("mark");
      mark.textContent = part.text;
      parent.append(mark);
    } else {
      parent.append(part.text);
    }
  }
}

/** @param {Document} document */
function attach(document) {
  const input = /** @type {HTMLInputElement | null} */ (document.getElementById("search-input"));
  const panel = document.getElementById("search-panel");
  const list = document.getElementById("search-results");
  const status = document.getElementById("search-status");
  const article = document.querySelector(".handbook");
  if (!input || !panel || !list || !status || !article) return;
  const sections = collect(article);
  /** @type {HTMLAnchorElement[]} */
  let links = [];
  let active = -1;

  /** @param {boolean} open */
  const show = (open) => {
    panel.hidden = !open;
    input.setAttribute("aria-expanded", String(open && links.length > 0));
  };
  /** @param {number} index */
  const select = (index) => {
    links.forEach((link, at) => link.parentElement?.setAttribute("aria-selected", String(at === index)));
    active = index;
    if (index >= 0) {
      input.setAttribute("aria-activedescendant", links[index].parentElement?.id ?? "");
      links[index].scrollIntoView({ block: "nearest" });
    } else {
      input.removeAttribute("aria-activedescendant");
    }
  };
  const update = () => {
    const query = input.value.trim();
    const results = search(sections, query);
    list.replaceChildren();
    links = results.map((result, index) => {
      const item = document.createElement("li");
      item.id = `search-result-${index}`;
      item.setAttribute("role", "option");
      const link = document.createElement("a");
      link.href = `#${result.section.id}`;
      link.tabIndex = -1;
      if (result.section.trail) {
        const trail = document.createElement("span");
        trail.className = "search-trail";
        trail.textContent = result.section.trail;
        link.append(trail);
      }
      const title = document.createElement("span");
      title.className = "search-title";
      fill(document, title, result.title);
      const text = document.createElement("span");
      text.className = "search-snippet";
      fill(document, text, result.snippet);
      link.append(title, text);
      item.append(link);
      list.append(item);
      return link;
    });
    status.textContent = !query
      ? ""
      : results.length
        ? `${results.length} section${results.length === 1 ? "" : "s"}`
        : `No section matches “${query}”`;
    select(links.length ? 0 : -1);
    show(Boolean(query));
  };
  // Closing forgets the results, so Enter and the arrows cannot act on hidden ones.
  const close = () => {
    list.replaceChildren();
    links = [];
    status.textContent = "";
    show(false);
    select(-1);
  };
  /** @param {number} index */
  const go = (index) => {
    const link = links[index];
    if (!link) return;
    close();
    input.blur();
    link.click();
  };

  input.addEventListener("input", update);
  input.addEventListener("focus", () => {
    if (input.value.trim()) update();
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!links.length) return;
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      select((active + step + links.length) % links.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      go(Math.max(active, 0));
    } else if (event.key === "Escape") {
      if (!panel.hidden) close();
      else {
        input.value = "";
        input.blur();
      }
    }
  });
  list.addEventListener("click", (event) => {
    if (event.target instanceof Element && event.target.closest("a")) close();
  });
  document.addEventListener("click", (event) => {
    if (event.target instanceof Node && !input.closest(".search")?.contains(event.target)) close();
  });
  document.addEventListener("keydown", (event) => {
    const target = /** @type {HTMLElement | null} */ (event.target instanceof HTMLElement ? event.target : null);
    const typing = target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName));
    if ((event.key === "k" && (event.metaKey || event.ctrlKey)) || (event.key === "/" && !typing)) {
      event.preventDefault();
      input.focus();
      input.select();
    }
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { search, collect, normalize, attach };
} else if (typeof document !== "undefined") {
  attach(document);
}

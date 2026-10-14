// SPDX-FileCopyrightText: 2026 Scenario Inc.
// SPDX-License-Identifier: GPL-3.0-or-later
// Run with: node --test tests/site/
import assert from "node:assert/strict";
import { test } from "node:test";

import handbook from "../../docs/handbook-search.js";

const { search } = handbook;

const SECTIONS = [
  { id: "install", title: "Install", trail: "", text: "Turn on Allow Online Access, then add the remote repository." },
  { id: "updates", title: "Updates", trail: "Install", text: "Blender offers each new release; check for updates in Get Extensions." },
  { id: "materials", title: "Materials", trail: "Lanes", text: "Generate PBR texture sets and apply them to a mesh material slot." },
  { id: "costs", title: "Costs", trail: "", text: "Every estimate is shown in Creative Units before you install nothing or spend." },
  { id: "3d", title: "3D", trail: "Lanes", text: "Génération of meshes from an image or a prompt." },
];

const ids = (query: string, limit?: number) => search(SECTIONS, query, limit).map((result) => result.section.id);

test("finds nothing for an empty query", () => {
  assert.deepEqual(ids(""), []);
  assert.deepEqual(ids("   "), []);
});

test("ranks a title match above the text, and the text above the parent title", () => {
  assert.deepEqual(ids("install"), ["install", "costs", "updates"]);
  assert.deepEqual(ids("install updates"), ["updates"]);
});

test("matches the start of a word while typing", () => {
  assert.deepEqual(ids("mater"), ["materials"]);
});

test("tolerates a typo in a longer word", () => {
  assert.deepEqual(ids("matreials"), ["materials"]);
  assert.deepEqual(ids("repostory"), ["install"]);
});

test("ranks a misspelt start of a title word above the same typo in the text", () => {
  const sections = [
    { id: "intro", title: "What it does", trail: "", text: "Apply a material to the mesh." },
    { id: "materials", title: "Materials", trail: "Lanes", text: "Texture sets for a slot." },
  ];

  assert.deepEqual(
    search(sections, "matreial").map((result) => result.section.id),
    ["materials", "intro"],
  );
});

test("does not guess typos in short words", () => {
  assert.deepEqual(ids("cist"), []);
});

test("requires every word of the query", () => {
  assert.deepEqual(ids("texture mesh"), ["materials"]);
  assert.deepEqual(ids("texture repository"), []);
});

test("ignores case and accents", () => {
  assert.deepEqual(ids("GENERATION"), ["3d"]);
  assert.deepEqual(ids("3d"), ["3d"]);
});

test("returns at most the requested number of results", () => {
  assert.equal(ids("e", 2).length, 2);
});

test("highlights matched words in a snippet that preserves the original text", () => {
  const [result] = search(SECTIONS, "texture slot");

  const text = result.snippet.map((segment) => segment.text).join("");
  assert.ok(SECTIONS[2].text.includes(text.replace(/^…|…$/g, "")));
  assert.deepEqual(
    result.snippet.filter((segment) => segment.match).map((segment) => segment.text),
    ["texture", "slot"],
  );
});

test("highlights the matched part of the title", () => {
  const [result] = search(SECTIONS, "upd");

  assert.deepEqual(result.title, [{ text: "Updates", match: true }]);
});

test("shortens a long text around the first match", () => {
  const long = { id: "long", title: "Long", trail: "", text: `${"filler ".repeat(40)}needle ${"filler ".repeat(40)}` };

  const [result] = search([long], "needle");
  const text = result.snippet.map((segment) => segment.text).join("");

  assert.ok(text.startsWith("…") && text.endsWith("…"));
  assert.ok(text.length < 200);
  assert.ok(text.includes("needle"));
});

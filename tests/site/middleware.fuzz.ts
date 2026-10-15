// SPDX-FileCopyrightText: 2026 Scenario Inc.
// SPDX-License-Identifier: GPL-3.0-or-later
// Property-based tests (fuzzing) for the download-count middleware, which reads
// untrusted paths and headers. fast-check generates the requests and shrinks any
// failure to the smallest one. Run from the repository root: pnpm exec vitest run
import { fc, test } from "@fast-check/vitest";
import { afterAll, beforeAll, expect, vi } from "vitest";

import middleware from "../../tools/site_proxy/middleware.ts";

const SITE = "https://blender.scenario.com";
const PAGES = "https://pages.test";
const POSTHOG = "https://posthog.test";
const PUBLISHED = ["0.10.0", "0.11.0"];
const ARCHIVE = /^\/repo\/scenario-(\d+\.\d+\.\d+)\.zip$/;
const CLIENTS = ["blender", "browser", "tool", "bot", "other"];
const BLENDER_FIELDS = ["blender_version", "os", "arch", "blender_cycle"];
const FIELDS = ["plugin", "extension_version", "client", "country", "$process_person_profile", "$geoip_disable"];

type Event = { api_key: string; event: string; distinct_id: string; properties: Record<string, unknown> };

let fetched: string[] = [];
let events: Event[] = [];

beforeAll(() => {
  vi.stubEnv("POSTHOG_PROJECT_TOKEN", "phc_fuzz");
  vi.stubEnv("POSTHOG_HOST", POSTHOG);
  vi.stubEnv("SITE_ORIGIN", PAGES);
  // Stand-ins for GitHub Pages and PostHog; assertions run after the request,
  // because the middleware catches anything thrown here.
  vi.stubGlobal("fetch", async (input: string | URL | Request, init?: RequestInit) => {
    const url = String(input);
    fetched.push(url);
    if (url === `${PAGES}/repo/index.json`) {
      return Response.json({ data: PUBLISHED.map((version) => ({ id: "scenario", version })) });
    }
    events.push(JSON.parse(String(init?.body)));
    return new Response(null, { status: 200 });
  });
});

afterAll(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

async function visit(request: Request): Promise<Event[]> {
  fetched = [];
  events = [];
  const pending: Promise<unknown>[] = [];
  expect(middleware(request, { waitUntil: (promise) => pending.push(promise) })).toBeUndefined();
  await Promise.all(pending);
  return events;
}

// Any value a header can carry: Latin-1 without control characters.
const headerValue = fc.string({ unit: fc.integer({ min: 0x20, max: 0xff }).map((code) => String.fromCharCode(code)) });
const version = fc.tuple(fc.nat(20), fc.nat(20), fc.nat(20)).map((parts) => parts.join("."));
const token = fc.stringMatching(/^[A-Za-z0-9_.-]{1,12}$/);
const blenderAgent = fc
  .tuple(version, fc.option(fc.tuple(token, token, fc.stringMatching(/^[a-z]{1,8}$/))), headerValue)
  .map(([v, platform, rest]) => `Blender/${v}${platform ? ` (${platform[0]} ${platform[1]}; cycle=${platform[2]})` : ""}${rest}`);
const userAgent = fc.option(
  fc.oneof(
    headerValue,
    blenderAgent,
    fc.constantFrom("curl/8.7.1", "Mozilla/5.0 (compatible; Googlebot/2.1)", "Mozilla/5.0 (X11) Firefox/140.0"),
  ),
  { nil: undefined },
);
// Near misses of the two counted paths, any web path, and arbitrary Unicode.
const fragment = fc.constantFrom("scenario-", "0", "1", "10", ".", ".zip", "zip", "/", "..", "%2e", "%2F", "%00", "?", "#", "index.json", "-", "repo/", " ", "é");
// A counted path with fragments inserted at one of its seams.
const nearMiss = fc
  .tuple(
    fc.oneof(
      version.map((v) => ["/repo/", "scenario-", v, ".zip"]),
      fc.constant(["/repo/", "index", ".json"]),
    ),
    fc.array(fragment, { minLength: 1, maxLength: 3 }),
    fc.nat(3),
  )
  .map(([parts, extra, at]) => {
    const seam = 1 + (at % parts.length);
    return [...parts.slice(0, seam), ...extra, ...parts.slice(seam)].join("");
  });
// Weighted toward counted requests, so that near misses meet a GET without a range.
const path = fc.oneof(
  { weight: 4, arbitrary: nearMiss },
  { weight: 1, arbitrary: fc.array(fragment, { maxLength: 12 }).map((parts) => `/repo/${parts.join("")}`) },
  { weight: 1, arbitrary: fc.webPath() },
  { weight: 1, arbitrary: fc.string({ unit: "grapheme" }).map((text) => `/repo/${text}`) },
  { weight: 1, arbitrary: version.map((v) => `/repo/scenario-${v}.zip`) },
  { weight: 1, arbitrary: fc.constant("/repo/index.json") },
);
const method = fc.oneof(
  { weight: 3, arbitrary: fc.constant("GET") },
  { weight: 1, arbitrary: fc.constantFrom("get", "HEAD", "POST", "PUT", "DELETE", "OPTIONS", "PATCH") },
);
const range = fc.option(fc.oneof(headerValue, fc.constantFrom("bytes=0-", "bytes=0-99", "bytes=1-", "bytes=1048576-")), {
  nil: undefined,
  freq: 2,
});
const country = fc.option(fc.oneof(headerValue, fc.stringMatching(/^[A-Z]{2}$/)), { nil: undefined, freq: 2 });

function request(m: string, p: string, headers: Record<string, string | undefined>): Request {
  const present = Object.entries(headers).filter((entry): entry is [string, string] => entry[1] !== undefined);
  return new Request(`${SITE}${p}`, { method: m, headers: present });
}

test.prop([method, path, userAgent, range, country], { numRuns: 1000 })(
  "never fails a request and reaches only GitHub Pages and PostHog",
  async (m, p, agent, r, c) => {
    await visit(request(m, p, { "user-agent": agent, range: r, "x-vercel-ip-country": c }));

    for (const url of fetched) expect([`${PAGES}/repo/index.json`, `${POSTHOG}/i/v0/e/`]).toContain(url);
    expect(events.length).toBeLessThanOrEqual(1);
  },
);

test.prop([method, path, range], { numRuns: 1000 })(
  "counts only a first-byte GET of the repository index or a release ZIP",
  async (m, p, r) => {
    const req = request(m, p, { range: r });
    const pathname = new URL(req.url).pathname;
    const rangeHeader = req.headers.get("range");
    const fromStart = !rangeHeader || rangeHeader.startsWith("bytes=0-");
    const expected =
      req.method !== "GET" || !fromStart
        ? undefined
        : pathname === "/repo/index.json"
          ? "repository_checked"
          : ARCHIVE.test(pathname)
            ? "extension_downloaded"
            : undefined;

    const sent = await visit(req);

    expect(sent.map((event) => event.event)).toEqual(expected ? [expected] : []);
  },
);

test.prop([fc.oneof(version.map((v) => `/repo/scenario-${v}.zip`), fc.constant("/repo/index.json")), userAgent, country], {
  numRuns: 1000,
})("sends only the documented anonymous fields", async (p, agent, c) => {
  const [event] = await visit(request("GET", p, { "user-agent": agent, "x-vercel-ip-country": c }));
  const { properties } = event;

  expect(Object.keys(event).sort()).toEqual(["api_key", "distinct_id", "event", "properties"]);
  expect(event.api_key).toBe("phc_fuzz");
  expect(event.distinct_id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
  for (const key of Object.keys(properties)) expect([...FIELDS, ...BLENDER_FIELDS]).toContain(key);
  expect(properties.plugin).toBe("blender");
  expect(CLIENTS).toContain(properties.client);
  expect(properties.$process_person_profile).toBe(false);
  expect(properties.$geoip_disable).toBe(true);
  if ("country" in properties) expect(properties.country).toMatch(/^[A-Z]{2}$/);
  if (properties.client !== "blender") for (const key of BLENDER_FIELDS) expect(properties).not.toHaveProperty(key);
  // A ZIP name keeps its version only when the repository index lists it.
  const archive = ARCHIVE.exec(p);
  if (archive) expect(properties.extension_version).toBe(PUBLISHED.includes(archive[1]) ? archive[1] : "unknown");
  else expect(properties).not.toHaveProperty("extension_version");
});

test.prop([version, token, token, fc.stringMatching(/^[a-z]{1,8}$/)], { numRuns: 500 })(
  "reads the version and platform from any Blender user agent",
  async (v, os, arch, cycle) => {
    const agent = `Blender/${v} (${os} ${arch}; cycle=${cycle})`;

    const [event] = await visit(request("GET", "/repo/index.json", { "user-agent": agent }));

    expect(event.properties).toMatchObject({ client: "blender", blender_version: v, os, arch, blender_cycle: cycle });
  },
);

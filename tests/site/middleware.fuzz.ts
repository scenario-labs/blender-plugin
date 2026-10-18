// SPDX-FileCopyrightText: 2026 Scenario Inc.
// SPDX-License-Identifier: GPL-3.0-or-later
// Property-based tests (fuzzing) for the download-count middleware and the
// telemetry relay, which read untrusted paths, headers and bodies. fast-check
// generates the requests and shrinks any failure to the smallest one. Run from
// the repository root: pnpm exec vitest run
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
// The API survey that receives feedback: a 5-point rating, then two open questions.
const SURVEY = {
  id: "0190f3c4-5c1e-7000-8000-00000000b1e0",
  name: "Blender feedback",
  current_iteration: 2,
  questions: [
    { id: "rating", type: "rating", question: "Rate", scale: 5 },
    { id: "improve", type: "open", question: "Improve?" },
    { id: "email", type: "open", question: "Email?" },
  ],
};

type Event = { api_key: string; event: string; distinct_id: string; properties: Record<string, unknown> };

let fetched: string[] = [];
let events: Event[] = [];
// Requests sent to PostHog, with their address.
let posts: { url: string; body: Record<string, unknown> }[] = [];

beforeAll(() => {
  vi.stubEnv("POSTHOG_PROJECT_TOKEN", "phc_fuzz");
  vi.stubEnv("POSTHOG_HOST", POSTHOG);
  vi.stubEnv("SITE_ORIGIN", PAGES);
  vi.stubEnv("POSTHOG_FEEDBACK_SURVEY_ID", SURVEY.id);
  // Stand-ins for GitHub Pages and PostHog; assertions run after the request,
  // because the middleware catches anything thrown here.
  vi.stubGlobal("fetch", async (input: string | URL | Request, init?: RequestInit) => {
    const url = String(input);
    fetched.push(url);
    if (url === `${PAGES}/repo/index.json`) {
      return Response.json({ data: PUBLISHED.map((version) => ({ id: "scenario", version })) });
    }
    if (url === `${POSTHOG}/api/surveys/?token=phc_fuzz`) return Response.json({ surveys: [SURVEY] });
    const body = JSON.parse(String(init?.body));
    events.push(body);
    posts.push({ url, body });
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

// The telemetry relay. Its allowlist, written out from the extension contract (#128).
const INSTALL = "0123456789abcdef0123456789abcdef";
const OPERATOR = /^scenario\.[a-z0-9_]{1,64}$/;
const ERROR_TYPE = /^[A-Za-z_][A-Za-z0-9_]{0,63}$/;
const MCP_CLIENT = /^[A-Za-z0-9][A-Za-z0-9._ -]{0,63}$/;
const MCP_CLIENT_VERSION = /^[A-Za-z0-9][A-Za-z0-9._+-]{0,31}$/;
const MCP_TOOL = /^[a-z][a-z0-9_]{0,63}$/;
const VERSION = /^\d+\.\d+\.\d+$/;
const HEX_ID = /^[0-9a-f]{32}$/;
const DAY_MS = 24 * 3600_000;
const ANONYMOUS = { plugin: "blender", source: "extension", $process_person_profile: false, $geoip_disable: true };
const MCP_SERVER = { $mcp_server_name: "Scenario for Blender", $mcp_source: "scenario_blender" };
const OUTCOMES: Record<string, string[]> = {
  operator_used: ["finished", "cancelled", "error"],
  mcp_tool_called: ["ok", "error", "timeout"],
};
// Each event's properties and whether a value is valid for it, given the others.
const ALLOWED: Record<string, Record<string, (value: unknown, properties: Record<string, unknown>) => boolean>> = {
  extension_started: {},
  operator_used: {
    operator: (value) => typeof value === "string" && OPERATOR.test(value),
    outcome: (value) => OUTCOMES.operator_used.includes(value as string),
    error_type: (value, p) => p.outcome === "error" && typeof value === "string" && ERROR_TYPE.test(value),
  },
  mcp_client_connected: {
    client: (value) => typeof value === "string" && MCP_CLIENT.test(value),
    client_version: (value) => typeof value === "string" && MCP_CLIENT_VERSION.test(value),
  },
  mcp_tool_called: {
    tool: (value) => typeof value === "string" && MCP_TOOL.test(value),
    outcome: (value) => OUTCOMES.mcp_tool_called.includes(value as string),
    duration_ms: (value) => Number.isInteger(value) && (value as number) >= 0 && (value as number) <= 3600_000,
    client: (value) => typeof value === "string" && MCP_CLIENT.test(value),
  },
};
const REQUIRED: Record<string, string[]> = {
  extension_started: [],
  operator_used: ["operator", "outcome"],
  mcp_client_connected: ["client"],
  mcp_tool_called: ["tool", "outcome", "duration_ms"],
};
const CONTEXT_VALID: Record<string, (value: unknown) => boolean> = {
  extension_version: (value) => typeof value === "string" && VERSION.test(value),
  blender_version: (value) => typeof value === "string" && VERSION.test(value),
  os: (value) => ["macos", "windows", "linux", "other"].includes(value as string),
  arch: (value) => ["arm64", "x64", "other"].includes(value as string),
};
const ERRORS = [
  "bad_request",
  "method_not_allowed",
  "not_found",
  "rate_limited",
  "too_large",
  "unavailable",
  "unsupported_media_type",
  "upstream",
];

type Reply = { status: number; body: Record<string, unknown> };
type Item = { event: string; distinct_id: string; timestamp: string; properties: Record<string, unknown> };
type Sample = { event: string; timestamp: string; properties: Record<string, unknown> };

let address = 0;

async function relay(method: string, path: string, headers: Record<string, string | undefined>, body?: string) {
  fetched = [];
  events = [];
  posts = [];
  // A new address for every request, so that the rate limit never interferes.
  const all = { "x-real-ip": `10.${++address >> 16}.${(address >> 8) & 255}.${address & 255}`, ...headers };
  const present = Object.entries(all).filter((entry): entry is [string, string] => entry[1] !== undefined);
  const bodyless = ["GET", "HEAD"].includes(method.toUpperCase());
  const request = new Request(`${SITE}${path}`, { method, headers: present, body: bodyless ? undefined : body });
  const pending: Promise<unknown>[] = [];
  const response = await middleware(request, { waitUntil: (promise) => pending.push(promise) });
  await Promise.all(pending);
  // A path such as /telemetry/.. resolves outside the relay, which Vercel's matcher skips too.
  const { pathname } = new URL(request.url);
  if (pathname !== "/telemetry" && !pathname.startsWith("/telemetry/")) {
    expect(response).toBeUndefined();
    return undefined;
  }
  expect(response).toBeInstanceOf(Response);
  const answer = response as Response;
  expect(answer.headers.get("content-type")).toBe("application/json");
  expect(answer.headers.get("cache-control")).toBe("no-store");
  return { status: answer.status, body: (await answer.json()) as Record<string, unknown> } satisfies Reply;
}

const JSON_HEADERS = { "content-type": "application/json", "user-agent": "ScenarioBlender/0.11.0" };
const postEvents = async (body: unknown) =>
  (await relay("POST", "/telemetry/v1/events", JSON_HEADERS, JSON.stringify(body))) as Reply;
const postFeedback = async (body: unknown) =>
  (await relay("POST", "/telemetry/v1/feedback", JSON_HEADERS, JSON.stringify(body))) as Reply;
const forwarded = () => posts.flatMap(({ url, body }) => (url === `${POSTHOG}/batch/` ? (body.batch as Item[]) : []));

/** The event and properties PostHog receives for an allowed event, from the contract. */
function expectedUsage(sample: Sample, context: Record<string, unknown>) {
  const p = sample.properties;
  const server: Record<string, unknown> = { ...MCP_SERVER };
  if ("extension_version" in context) server.$mcp_server_version = context.extension_version;
  const shared = { ...context, ...ANONYMOUS };
  switch (sample.event) {
    case "mcp_client_connected": {
      const properties = { ...server, $mcp_client_name: p.client, ...shared };
      if ("client_version" in p) Object.assign(properties, { $mcp_client_version: p.client_version });
      return { event: "$mcp_initialize", properties };
    }
    case "mcp_tool_called": {
      const properties: Record<string, unknown> = {
        ...server,
        $mcp_tool_name: p.tool,
        $mcp_is_error: p.outcome !== "ok",
        $mcp_duration_ms: p.duration_ms,
        outcome: p.outcome,
        ...shared,
      };
      if (p.outcome === "timeout") properties.$mcp_error_type = "timeout";
      if ("client" in p) properties.$mcp_client_name = p.client;
      return { event: "$mcp_tool_call", properties };
    }
    default:
      return { event: sample.event, properties: { ...p, ...shared } };
  }
}

// Events the contract allows, with timestamps a minute inside the accepted window.
const recent = fc.integer({ min: -7 * DAY_MS + 60_000, max: 3600_000 - 60_000 });
const sampleProperties: Record<string, fc.Arbitrary<Record<string, unknown>>> = {
  extension_started: fc.constant({}),
  operator_used: fc.oneof(
    fc.record({ operator: fc.stringMatching(OPERATOR), outcome: fc.constantFrom("finished", "cancelled", "error") }),
    fc.record({
      operator: fc.stringMatching(OPERATOR),
      outcome: fc.constant("error"),
      error_type: fc.stringMatching(ERROR_TYPE),
    }),
  ),
  mcp_client_connected: fc.record(
    { client: fc.stringMatching(MCP_CLIENT), client_version: fc.stringMatching(MCP_CLIENT_VERSION) },
    { requiredKeys: ["client"] },
  ),
  mcp_tool_called: fc.record(
    {
      tool: fc.stringMatching(MCP_TOOL),
      outcome: fc.constantFrom("ok", "error", "timeout"),
      duration_ms: fc.integer({ min: 0, max: 3600_000 }),
      client: fc.stringMatching(MCP_CLIENT),
    },
    { requiredKeys: ["tool", "outcome", "duration_ms"] },
  ),
};
const validSample: fc.Arbitrary<Sample> = fc
  .tuple(fc.constantFrom(...Object.keys(ALLOWED)), recent)
  .chain(([event, offset]) =>
    sampleProperties[event].map((properties) => ({
      event,
      timestamp: new Date(Date.now() + offset).toISOString(),
      properties,
    })),
  );
const notAllowedValue = fc.oneof(fc.string(), fc.jsonValue(), fc.constant(null), fc.integer(), fc.double());
const unknownKey = (event: string) => fc.string().filter((key) => !(key in ALLOWED[event]));

// One change the allowlist refuses, applied to an allowed event.
const invalidSample: fc.Arbitrary<unknown> = validSample.chain((sample) => {
  const keys = Object.keys(sample.properties);
  const mutations: fc.Arbitrary<unknown>[] = [
    fc
      .string()
      .filter((name) => !(name in ALLOWED))
      .map((event) => ({ ...sample, event })),
    fc
      .oneof(
        fc
          .integer({ min: 60_000, max: 365 * DAY_MS })
          .map((late) => new Date(Date.now() - 7 * DAY_MS - late).toISOString()),
        fc
          .integer({ min: 60_000, max: 365 * DAY_MS })
          .map((early) => new Date(Date.now() + 3600_000 + early).toISOString()),
        fc.string().filter((text) => Number.isNaN(Date.parse(text))),
        fc.integer(),
        fc.constant(null),
      )
      .map((timestamp) => ({ ...sample, timestamp })),
    fc.tuple(unknownKey(sample.event), fc.jsonValue()).map(([key, value]) => ({
      ...sample,
      properties: { ...sample.properties, [key]: value },
    })),
    fc
      .oneof(fc.array(fc.jsonValue()), fc.string(), fc.constant(null), fc.integer())
      .map((properties) => ({ ...sample, properties })),
    fc
      .tuple(fc.constantFrom("distinct_id", "uuid", "$set", "api_key"), fc.jsonValue())
      .map(([key, value]) => ({ ...sample, [key]: value })),
    fc.constantFrom(sample.event, sample.timestamp, null, 42, [sample]),
  ];
  if (keys.length > 0) {
    // A value the contract refuses for one of the event's properties.
    mutations.push(
      fc
        .constantFrom(...keys)
        .chain((key) =>
          notAllowedValue
            .filter((value) => !ALLOWED[sample.event][key](value, { ...sample.properties, [key]: value }))
            .map((value) => ({ ...sample, properties: { ...sample.properties, [key]: value } })),
        ),
    );
  }
  const required = REQUIRED[sample.event];
  if (required.length > 0) {
    mutations.push(
      fc.constantFrom(...required).map((key) => {
        const { [key]: _removed, ...properties } = sample.properties;
        return { ...sample, properties };
      }),
    );
  }
  if (sample.event === "operator_used" && sample.properties.outcome !== "error") {
    mutations.push(fc.constant({ ...sample, properties: { ...sample.properties, error_type: "ValueError" } }));
  }
  return fc.oneof(...mutations);
});
// A context whose fields are each valid, invalid or absent, among unknown ones.
const contextField = (valid: fc.Arbitrary<string>) => fc.option(fc.oneof(valid, notAllowedValue), { nil: undefined });
const context = fc.oneof(
  {
    weight: 4,
    arbitrary: fc.record({
      extension_version: contextField(fc.stringMatching(VERSION)),
      blender_version: contextField(fc.stringMatching(VERSION)),
      os: contextField(fc.constantFrom("macos", "windows", "linux", "other", "Darwin")),
      arch: contextField(fc.constantFrom("arm64", "x64", "other", "x86_64")),
      user: fc.option(fc.string(), { nil: undefined }),
    }),
  },
  { weight: 1, arbitrary: notAllowedValue },
);

function validContext(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return {};
  const fields = Object.entries(value).filter(
    ([key, field]) => Object.hasOwn(CONTEXT_VALID, key) && CONTEXT_VALID[key](field),
  );
  return Object.fromEntries(fields);
}

const methodOrPost = fc.oneof(
  { weight: 4, arbitrary: fc.constant("POST") },
  { weight: 1, arbitrary: fc.constantFrom("GET", "HEAD", "PUT", "DELETE", "OPTIONS", "PATCH", "post") },
);
const telemetryPath = fc.oneof(
  { weight: 4, arbitrary: fc.constantFrom("/telemetry/v1/events", "/telemetry/v1/feedback") },
  { weight: 1, arbitrary: fc.array(fragment, { maxLength: 6 }).map((parts) => `/telemetry/${parts.join("")}`) },
  { weight: 1, arbitrary: fc.webPath().map((rest) => `/telemetry${rest}`) },
);
const contentType = fc.option(
  fc.oneof(
    { weight: 4, arbitrary: fc.constantFrom("application/json", "application/json; charset=utf-8") },
    { weight: 1, arbitrary: headerValue },
  ),
  { nil: undefined, freq: 8 },
);
const extensionAgent = fc.option(
  fc.oneof({ weight: 4, arbitrary: fc.constant("ScenarioBlender/0.11.0") }, { weight: 1, arbitrary: headerValue }),
  { nil: undefined, freq: 8 },
);
const anyBody = fc.oneof(
  fc.string(),
  fc.json(),
  fc
    .record({
      install_id: fc.constant(INSTALL),
      context,
      events: fc.array(fc.oneof(validSample, invalidSample, fc.jsonValue()), { maxLength: 4 }),
    })
    .map((body) => JSON.stringify(body)),
  fc
    .record(
      { submission_id: fc.constant(INSTALL), rating: fc.jsonValue(), message: fc.jsonValue(), email: fc.jsonValue() },
      { requiredKeys: [] },
    )
    .map((body) => JSON.stringify(body)),
);

test.prop([methodOrPost, telemetryPath, contentType, extensionAgent, anyBody], { numRuns: 1000 })(
  "answers every telemetry request itself, with a fixed reply that repeats nothing the client sent",
  async (m, p, type, agent, body) => {
    const reply = await relay(m, p, { "content-type": type, "user-agent": agent }, body);
    if (!reply) return;

    expect([202, 400, 404, 405, 413, 415, 429, 502, 503]).toContain(reply.status);
    const keys = Object.keys(reply.body).sort();
    if (keys.length === 1 && keys[0] === "error") expect(ERRORS).toContain(reply.body.error);
    else if (keys.length === 1) expect(reply.body).toEqual({ ok: true });
    else {
      expect(keys).toEqual(["accepted", "dropped"]);
      expect(Number.isInteger(reply.body.accepted) && Number.isInteger(reply.body.dropped)).toBe(true);
    }
    // Never GitHub Pages: only PostHog's batch, survey and capture endpoints.
    for (const url of fetched) {
      expect([`${POSTHOG}/batch/`, `${POSTHOG}/api/surveys/?token=phc_fuzz`, `${POSTHOG}/i/v0/e/`]).toContain(url);
    }
    for (const item of forwarded()) {
      expect(["extension_started", "operator_used", "$mcp_initialize", "$mcp_tool_call"]).toContain(item.event);
    }
  },
);

test.prop([fc.array(fc.tuple(fc.boolean(), validSample, invalidSample), { minLength: 1, maxLength: 20 }), context], {
  numRuns: 500,
})("forwards exactly the allowed events, with only their allowed properties", async (picks, rawContext) => {
  const samples = picks.map(([valid, good, bad]) => (valid ? good : bad));
  const valid = picks.filter(([isValid]) => isValid).map(([, good]) => good);

  const reply = await postEvents({ install_id: INSTALL, context: rawContext, events: samples });

  expect(reply).toEqual({ status: 202, body: { accepted: valid.length, dropped: samples.length - valid.length } });
  const sent = forwarded();
  const platform = validContext(rawContext);
  expect(sent).toEqual(
    valid.map((sample) => ({
      ...expectedUsage(sample, platform),
      distinct_id: INSTALL,
      timestamp: new Date(sample.timestamp).toISOString(),
    })),
  );
  expect(posts.length).toBe(valid.length > 0 ? 1 : 0);
});

// Feedback the contract accepts, and the same with one refused change.
const message = fc.string({ minLength: 1, maxLength: 200 }).filter((text) => text.trim().length > 0);
const email = fc
  .emailAddress()
  .filter((address) => address.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(address));
const validFeedback = fc
  .record(
    {
      submission_id: fc.stringMatching(HEX_ID),
      install_id: fc.stringMatching(HEX_ID),
      context,
      rating: fc.integer({ min: 1, max: 5 }),
      message,
      email,
    },
    { requiredKeys: ["submission_id"] },
  )
  .filter((body) => "rating" in body || "message" in body);
const invalidFeedback = validFeedback.chain((body) =>
  fc.oneof(
    fc
      .tuple(
        fc
          .string()
          .filter((key) => !["submission_id", "install_id", "context", "rating", "message", "email"].includes(key)),
        fc.jsonValue(),
      )
      .map(([key, value]) => ({ ...body, [key]: value })),
    notAllowedValue
      .filter((value) => typeof value !== "string" || !HEX_ID.test(value))
      .map((submission_id) => ({ ...body, submission_id })),
    notAllowedValue
      .filter((value) => typeof value !== "string" || !HEX_ID.test(value))
      .map((install_id) => ({ ...body, install_id })),
    notAllowedValue
      .filter((value) => !(Number.isInteger(value) && (value as number) >= 1 && (value as number) <= 5))
      .map((rating) => ({ ...body, rating })),
    notAllowedValue
      .filter((value) => typeof value !== "string" || value.trim().length === 0)
      .map((text) => ({ ...body, message: text })),
    notAllowedValue
      .filter((value) => typeof value !== "string" || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value))
      .map((text) => ({ ...body, email: text })),
    fc.constant({ submission_id: body.submission_id, email: "a@b.co" }),
  ),
);

test.prop([fc.boolean(), validFeedback, invalidFeedback], { numRuns: 500 })(
  "sends feedback only in the allowed shape, as answers to the survey's questions",
  async (isValid, good, bad) => {
    const reply = await postFeedback(isValid ? good : bad);

    const sent = posts.filter(({ url }) => url === `${POSTHOG}/i/v0/e/`).map((post) => post.body);
    if (!isValid) {
      expect(reply).toEqual({ status: 400, body: { error: "bad_request" } });
      expect(sent).toEqual([]);
      return;
    }
    expect(reply).toEqual({ status: 202, body: { ok: true } });
    const answers: Record<string, string> = {};
    if (good.rating !== undefined) answers.$survey_response_rating = String(good.rating);
    if (good.message !== undefined) answers.$survey_response_improve = good.message.trim();
    if (good.email !== undefined) answers.$survey_response_email = good.email;
    expect(sent).toEqual([
      {
        api_key: "phc_fuzz",
        event: "survey sent",
        distinct_id: good.install_id ?? good.submission_id,
        properties: {
          ...answers,
          $survey_id: SURVEY.id,
          $survey_name: SURVEY.name,
          $survey_questions: SURVEY.questions.map(({ id, question }) => ({ id, question })),
          $survey_submission_id: good.submission_id,
          $survey_completed: true,
          $survey_iteration: SURVEY.current_iteration,
          ...validContext(good.context),
          ...ANONYMOUS,
        },
      },
    ]);
  },
);

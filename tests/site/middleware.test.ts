// SPDX-FileCopyrightText: 2026 Scenario Inc.
// SPDX-License-Identifier: GPL-3.0-or-later
// Run from the repository root: node --test tests/site/middleware.test.ts
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { createServer, type IncomingMessage, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { after, before, beforeEach, describe, test } from "node:test";

import middleware, { config, ORIGIN, rememberedClients } from "../../tools/site_proxy/middleware.ts";

const BLENDER = "Blender/5.0.1 (Darwin arm64; cycle=release)";
const BROWSER = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Firefox/140.0";

type Captured = { path: string; body: Record<string, unknown> };
type Index = { status: number; versions: string[] };

let server: Server;
let base: string;
let received: Captured[] = [];
let respond: (request: IncomingMessage, reply: (status: number) => void) => void;
// Repository indexes served by the stand-in for GitHub Pages, one per test origin.
const indexes = new Map<string, Index>();
// The running surveys the stand-in for PostHog lists, after a delay (never when
// infinite), and the reads of that list.
let surveyList: { status: number; body: unknown };
let surveyDelay = 0;
let surveyReads: string[] = [];
const indexReads = new Map<string, number>();
let origins = 0;

function read(request: IncomingMessage): Promise<string> {
  return new Promise((resolve) => {
    let text = "";
    request.on("data", (chunk) => (text += chunk));
    request.on("end", () => resolve(text));
  });
}

before(async () => {
  server = createServer(async (request, response) => {
    const path = request.url ?? "";
    const prefix = path.replace(/\/repo\/index\.json$/, "");
    if (request.method === "GET" && indexes.has(prefix)) {
      indexReads.set(prefix, (indexReads.get(prefix) ?? 0) + 1);
      const index = indexes.get(prefix) as Index;
      const data = index.versions.map((version) => ({ id: "scenario", version }));
      response.writeHead(index.status, { "content-type": "application/json" }).end(JSON.stringify({ data }));
      return;
    }
    if (request.method === "GET" && path.startsWith("/api/surveys/")) {
      surveyReads.push(path);
      const { status, body } = surveyList;
      const answer = () => response.writeHead(status, { "content-type": "application/json" }).end(JSON.stringify(body));
      if (Number.isFinite(surveyDelay)) setTimeout(answer, surveyDelay);
      return;
    }
    received.push({ path, body: JSON.parse(await read(request)) });
    respond(request, (status) => response.writeHead(status).end());
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  process.env.POSTHOG_HOST = base;
});

after(() => {
  server.closeAllConnections();
  server.close();
});

// Point the middleware at a new origin, so its cached index starts empty.
function publish(versions: string[], status = 200) {
  const prefix = `/pages-${++origins}`;
  indexes.set(prefix, { status, versions });
  process.env.SITE_ORIGIN = base + prefix;
  return prefix;
}

beforeEach(() => {
  received = [];
  respond = (_request, reply) => reply(200);
  process.env.POSTHOG_PROJECT_TOKEN = "phc_test";
  publish(["0.10.0", "0.11.0"]);
});

async function visit(path: string, headers: Record<string, string> = {}, method = "GET") {
  const pending: Promise<unknown>[] = [];
  const result = middleware(new Request(`https://blender.scenario.com${path}`, { method, headers }), {
    waitUntil: (promise) => pending.push(promise),
  });
  await Promise.all(pending);
  return result;
}

const versionOf = (index: number) => (received[index].body.properties as Record<string, unknown>).extension_version;

test("runs only for the repository directory and the telemetry relay", () => {
  assert.deepEqual(config.matcher, ["/repo/:path*", "/telemetry/:path*"]);
  assert.equal(config.runtime, "nodejs");
});

test("records a Blender download with its plugin, versions, platform and country only", async () => {
  const result = await visit("/repo/scenario-0.10.0.zip", { "user-agent": BLENDER, "x-vercel-ip-country": "FR" });

  assert.equal(result, undefined);
  assert.equal(received.length, 1);
  const [{ path, body }] = received;
  assert.equal(path, "/i/v0/e/");
  assert.equal(body.api_key, "phc_test");
  assert.equal(body.event, "extension_downloaded");
  assert.match(String(body.distinct_id), /^[0-9a-f-]{36}$/);
  assert.deepEqual(body.properties, {
    plugin: "blender",
    extension_version: "0.10.0",
    client: "blender",
    blender_version: "5.0.1",
    os: "Darwin",
    arch: "arm64",
    blender_cycle: "release",
    country: "FR",
    $process_person_profile: false,
    $geoip_disable: true,
  });
});

test("uses a new anonymous identifier for every request", async () => {
  await visit("/repo/scenario-0.10.0.zip", { "user-agent": BLENDER });
  await visit("/repo/scenario-0.10.0.zip", { "user-agent": BLENDER });

  assert.equal(received.length, 2);
  assert.notEqual(received[0].body.distinct_id, received[1].body.distinct_id);
});

test("deploys only the middleware and its routing", () => {
  // Vercel serves any other file in the project directory instead of forwarding
  // that path, and a Git deployment applies .vercelignore from the repository root.
  assert.deepEqual(readdirSync("tools/site_proxy").sort(), ["middleware.ts", "vercel.json"]);
});

test("forwards to the same GitHub Pages address as vercel.json", () => {
  // Run from the repository root, as CI does.
  const settings = JSON.parse(readFileSync("tools/site_proxy/vercel.json", "utf8"));

  assert.equal(settings.rewrites.at(-1).destination, `${ORIGIN}/$1`);
});

test("serves the analytics script at the handbook's own path", () => {
  // Blocker lists (EasyPrivacy) block /_vercel/insights/script.js, not the endpoints it reports to;
  // vercel.json reaches /_vercel/ paths only through a full URL: a bare path falls through to Pages.
  const settings = JSON.parse(readFileSync("tools/site_proxy/vercel.json", "utf8"));
  const page = readFileSync("docs/handbook-template.html", "utf8");
  const src = /<script defer src="([^"]+)"><\/script>/.exec(page)?.[1];

  assert.deepEqual(settings.rewrites[0], {
    source: src,
    destination: "https://blender.scenario.com/_vercel/insights/script.js",
  });
});

test("records a version missing from the repository index as unknown", async () => {
  await visit("/repo/scenario-9.9.9.zip", { "user-agent": BLENDER });

  assert.equal(received.length, 1);
  assert.equal(versionOf(0), "unknown");
});

test("records the version as unknown when the repository index cannot be read", async () => {
  publish(["0.10.0"], 503);

  await visit("/repo/scenario-0.10.0.zip", { "user-agent": BLENDER });

  assert.equal(received.length, 1);
  assert.equal(versionOf(0), "unknown");
});

test("reads the repository index once for several downloads", async () => {
  const prefix = publish(["0.10.0", "0.11.0"]);

  await visit("/repo/scenario-0.10.0.zip", { "user-agent": BLENDER });
  await visit("/repo/scenario-0.11.0.zip", { "user-agent": BLENDER });
  await visit("/repo/scenario-0.10.0.zip", { "user-agent": BROWSER });

  assert.equal(indexReads.get(prefix), 1);
  assert.deepEqual([versionOf(0), versionOf(1), versionOf(2)], ["0.10.0", "0.11.0", "0.10.0"]);
});

test("reads the index again for an unseen version once a minute has passed", async (t) => {
  t.mock.timers.enable({ apis: ["Date"], now: 0 });
  const prefix = publish(["0.10.0"]);
  await visit("/repo/scenario-0.10.0.zip", { "user-agent": BLENDER });
  (indexes.get(prefix) as Index).versions.push("0.12.0");

  t.mock.timers.tick(30_000);
  await visit("/repo/scenario-0.12.0.zip", { "user-agent": BLENDER });
  t.mock.timers.tick(31_000);
  await visit("/repo/scenario-0.12.0.zip", { "user-agent": BLENDER });

  assert.equal(indexReads.get(prefix), 2);
  assert.deepEqual([versionOf(1), versionOf(2)], ["unknown", "0.12.0"]);
});

test("records a repository check from Blender", async () => {
  await visit("/repo/index.json?platform=macos-arm64&blender_version=5.0.1", { "user-agent": BLENDER });

  assert.equal(received.length, 1);
  assert.equal(received[0].body.event, "repository_checked");
  assert.deepEqual(received[0].body.properties, {
    plugin: "blender",
    client: "blender",
    blender_version: "5.0.1",
    os: "Darwin",
    arch: "arm64",
    blender_cycle: "release",
    $process_person_profile: false,
    $geoip_disable: true,
  });
});

test("records a browser download without Blender details", async () => {
  await visit("/repo/scenario-0.10.0.zip", { "user-agent": BROWSER, "x-vercel-ip-country": "not a code" });

  assert.equal(received.length, 1);
  assert.deepEqual(received[0].body.properties, {
    plugin: "blender",
    extension_version: "0.10.0",
    client: "browser",
    $process_person_profile: false,
    $geoip_disable: true,
  });
});

test("sorts other clients into crawlers, scripts, browsers and the rest", async () => {
  const cases: [string, string][] = [
    ["Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", "bot"],
    ["Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)", "bot"],
    ["facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)", "bot"],
    ["Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/141.0 Safari/537.36", "bot"],
    ["Scenario-Blender-LinkCheck lychee/0.24.2", "bot"],
    ["curl/8.7.1", "tool"],
    ["Wget/1.21.4", "tool"],
    ["python-requests/2.32.3", "tool"],
    ["Go-http-client/2.0", "tool"],
    ["", "tool"],
    ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36", "browser"],
    ["SomethingElse/1.0", "other"],
  ];

  for (const [agent, client] of cases) {
    received = [];
    await visit("/repo/scenario-0.10.0.zip", agent ? { "user-agent": agent } : {});

    assert.equal((received[0].body.properties as Record<string, unknown>).client, client, agent || "(no User-Agent)");
  }
});

test("ignores other repository files, HEAD requests and resumed downloads", async () => {
  await visit("/repo/");
  await visit("/repo/inventory.json");
  await visit("/repo/scenario-0.10.0.zip.sha256");
  await visit("/repo/scenario-0.10.0.zip", { "user-agent": BLENDER }, "HEAD");
  await visit("/repo/scenario-0.10.0.zip", { "user-agent": BROWSER, range: "bytes=1048576-" });

  assert.deepEqual(received, []);
});

test("counts a download that requests its range from the first byte", async () => {
  await visit("/repo/scenario-0.10.0.zip", { "user-agent": BROWSER, range: "bytes=0-" });

  assert.equal(received.length, 1);
});

test("records nothing without a project token", async () => {
  delete process.env.POSTHOG_PROJECT_TOKEN;

  assert.equal(await visit("/repo/scenario-0.10.0.zip", { "user-agent": BLENDER }), undefined);
  assert.deepEqual(received, []);
});

test("never fails the download when the analytics service rejects the event", async () => {
  respond = (_request, reply) => reply(500);

  assert.equal(await visit("/repo/scenario-0.10.0.zip", { "user-agent": BLENDER }), undefined);
  assert.equal(received.length, 1);
});

test("gives up on an analytics service that does not answer", async () => {
  respond = () => {};
  const started = Date.now();

  assert.equal(await visit("/repo/scenario-0.10.0.zip", { "user-agent": BLENDER }), undefined);
  assert.equal(received.length, 1);
  assert.ok(Date.now() - started < 5000);
});

// The telemetry relay: opt-in usage events and user-sent feedback from the extension.
const AGENT = "ScenarioBlender/0.11.0";
const INSTALL = "0123456789abcdef0123456789abcdef";
const SUBMISSION = "fedcba9876543210fedcba9876543210";
const SURVEY = "0190f3c4-5c1e-7000-8000-00000000b1e0";
const CONTEXT = { extension_version: "0.11.0", blender_version: "5.0.1", os: "macos", arch: "arm64" };
const ANONYMOUS = { plugin: "blender", source: "extension", $process_person_profile: false, $geoip_disable: true };
const MCP_SERVER = { $mcp_server_name: "Scenario for Blender", $mcp_source: "posthog_mcp_analytics" };
const QUESTIONS = [
  { id: "q-rating", type: "rating", question: "How would you rate Scenario for Blender?", scale: 5, display: "number" },
  { id: "q-improve", type: "open", question: "What should we improve?" },
  { id: "q-email", type: "open", question: "Email, if you would like a reply (optional)" },
];
const SURVEY_QUESTIONS = QUESTIONS.map(({ id, question }) => ({ id, question }));

type Reply = { status: number; headers: Headers; body: Record<string, unknown> };
type Sent = { event: string; distinct_id: string; timestamp: string; properties: Record<string, unknown> };
// An undefined value leaves that header out.
type HeaderValues = Record<string, string | undefined>;

let address = "";
let clients = 0;
let tokens = 0;

// A new client address, so that no request inherits another test's rate limit.
function newAddress() {
  address = `2001:db8:${(++clients).toString(16)}::1`;
}

beforeEach(() => {
  newAddress();
  surveyReads = [];
  surveyDelay = 0;
  launch();
  process.env.POSTHOG_FEEDBACK_SURVEY_ID = SURVEY;
});

/** Lists the feedback survey among PostHog's running surveys. */
function launch(questions: unknown[] = QUESTIONS, extra: Record<string, unknown> = {}) {
  const survey = {
    id: SURVEY,
    name: "Blender feedback",
    type: "api",
    questions,
    start_date: "2026-10-18T09:00:00Z",
    end_date: null,
    current_iteration: null,
    ...extra,
  };
  surveyList = { status: 200, body: { surveys: [{ id: "another", name: "Another", questions: [] }, survey] } };
}

/** A new project token, so that the survey cache starts empty. */
function newToken(): string {
  const token = `phc_feedback_${++tokens}`;
  process.env.POSTHOG_PROJECT_TOKEN = token;
  return token;
}

async function post(path: string, body: unknown, headers: HeaderValues = {}, method = "POST"): Promise<Reply> {
  const all = { "content-type": "application/json", "user-agent": AGENT, "x-real-ip": address, ...headers };
  const present = Object.entries(all).filter((entry): entry is [string, string] => entry[1] !== undefined);
  const init: RequestInit = { method, headers: present };
  if (method !== "GET" && method !== "HEAD") {
    init.body =
      typeof body === "string"
        ? body
        : body instanceof Uint8Array
          ? (body as Uint8Array<ArrayBuffer>)
          : JSON.stringify(body);
  }
  const pending: Promise<unknown>[] = [];
  const response = await middleware(new Request(`https://blender.scenario.com${path}`, init), {
    waitUntil: (promise) => pending.push(promise),
  });
  await Promise.all(pending);
  assert.ok(response, "a telemetry request gets the relay's own response");
  assert.equal(response.headers.get("content-type"), "application/json");
  assert.equal(response.headers.get("cache-control"), "no-store");
  return {
    status: response.status,
    headers: response.headers,
    body: (await response.json()) as Record<string, unknown>,
  };
}

const sendEvents = (events: unknown[], extra: Record<string, unknown> = {}, headers: HeaderValues = {}) =>
  post("/telemetry/v1/events", { install_id: INSTALL, context: CONTEXT, events, ...extra }, headers);
const sendFeedback = (body: Record<string, unknown>, headers: HeaderValues = {}) =>
  post("/telemetry/v1/feedback", { submission_id: SUBMISSION, ...body }, headers);
const batch = () => (received[0]?.body.batch ?? []) as Sent[];
const at = (offset = 0) => new Date(Date.now() + offset).toISOString();

describe("usage events", () => {
  test("relays the allowed events to PostHog's batch endpoint", async () => {
    const timestamp = at(-60_000);
    const result = await sendEvents(
      [
        { event: "extension_started", timestamp, properties: {} },
        { event: "extension_started", timestamp },
        {
          event: "operator_used",
          timestamp,
          properties: { operator: "scenario.generate", outcome: "error", error_type: "TimeoutError" },
        },
        { event: "operator_used", timestamp, properties: { operator: "scenario.capture_view", outcome: "cancelled" } },
      ],
      {},
      { "x-vercel-ip-country": "FR" },
    );

    assert.equal(result.status, 202);
    assert.deepEqual(result.body, { accepted: 4, dropped: 0 });
    assert.equal(received.length, 1);
    assert.equal(received[0].path, "/batch/");
    const properties = { ...CONTEXT, ...ANONYMOUS, country: "FR" };
    assert.deepEqual(received[0].body, {
      api_key: "phc_test",
      batch: [
        { event: "extension_started", distinct_id: INSTALL, timestamp, properties },
        { event: "extension_started", distinct_id: INSTALL, timestamp, properties },
        {
          event: "operator_used",
          distinct_id: INSTALL,
          timestamp,
          properties: { operator: "scenario.generate", outcome: "error", error_type: "TimeoutError", ...properties },
        },
        {
          event: "operator_used",
          distinct_id: INSTALL,
          timestamp,
          properties: { operator: "scenario.capture_view", outcome: "cancelled", ...properties },
        },
      ],
    });
  });

  test("forwards MCP events under PostHog's MCP analytics names", async () => {
    const timestamp = at();
    await sendEvents([
      {
        event: "mcp_client_connected",
        timestamp,
        properties: { client: "Claude Code", client_version: "2.1.0+build.7" },
      },
      { event: "mcp_client_connected", timestamp, properties: { client: "cursor-vscode" } },
      {
        event: "mcp_tool_called",
        timestamp,
        properties: { tool: "capture_views", outcome: "timeout", duration_ms: 3600000, client: "Claude Code" },
      },
      { event: "mcp_tool_called", timestamp, properties: { tool: "get_scene_info", outcome: "ok", duration_ms: 0 } },
      { event: "mcp_tool_called", timestamp, properties: { tool: "generate", outcome: "error", duration_ms: 1520 } },
    ]);

    const server = { ...MCP_SERVER, $mcp_server_version: "0.11.0" };
    const shared = { ...CONTEXT, ...ANONYMOUS };
    assert.deepEqual(
      batch().map(({ event, properties }) => ({ event, properties })),
      [
        {
          event: "$mcp_initialize",
          properties: { ...server, $mcp_client_name: "Claude Code", $mcp_client_version: "2.1.0+build.7", ...shared },
        },
        { event: "$mcp_initialize", properties: { ...server, $mcp_client_name: "cursor-vscode", ...shared } },
        {
          event: "$mcp_tool_call",
          properties: {
            ...server,
            $mcp_tool_name: "capture_views",
            $mcp_is_error: true,
            $mcp_error_type: "timeout",
            $mcp_duration_ms: 3600000,
            $mcp_client_name: "Claude Code",
            outcome: "timeout",
            ...shared,
          },
        },
        {
          event: "$mcp_tool_call",
          properties: {
            ...server,
            $mcp_tool_name: "get_scene_info",
            $mcp_is_error: false,
            $mcp_duration_ms: 0,
            outcome: "ok",
            ...shared,
          },
        },
        {
          event: "$mcp_tool_call",
          properties: {
            ...server,
            $mcp_tool_name: "generate",
            $mcp_is_error: true,
            $mcp_duration_ms: 1520,
            outcome: "error",
            ...shared,
          },
        },
      ],
    );
  });

  test("drops each event that breaks the allowlist and forwards the rest", async () => {
    const timestamp = at();
    const invalid: unknown[] = [
      { event: "page_viewed", timestamp, properties: {} },
      { event: "mcp_tool_call", timestamp, properties: { tool: "generate", outcome: "ok", duration_ms: 1 } },
      { event: "extension_started", timestamp, properties: { prompt: "a red car" } },
      { event: "extension_started", timestamp, properties: [] },
      { event: "extension_started", timestamp, properties: null },
      { event: "extension_started", timestamp, properties: {}, distinct_id: "someone" },
      { event: "extension_started" },
      { event: "operator_used", timestamp, properties: { operator: "object.delete", outcome: "finished" } },
      { event: "operator_used", timestamp, properties: { operator: "scenario.Generate", outcome: "finished" } },
      {
        event: "operator_used",
        timestamp,
        properties: { operator: `scenario.${"a".repeat(65)}`, outcome: "finished" },
      },
      { event: "operator_used", timestamp, properties: { operator: "scenario.generate", outcome: "done" } },
      { event: "operator_used", timestamp, properties: { operator: "scenario.generate" } },
      {
        event: "operator_used",
        timestamp,
        properties: { operator: "scenario.generate", outcome: "finished", error_type: "ValueError" },
      },
      {
        event: "operator_used",
        timestamp,
        properties: { operator: "scenario.generate", outcome: "error", error_type: "Bad error: C:\\temp" },
      },
      {
        event: "operator_used",
        timestamp,
        properties: { operator: "scenario.generate", outcome: "error", error_type: 3 },
      },
      {
        event: "operator_used",
        timestamp,
        properties: { operator: "scenario.generate", outcome: "finished", object: "Cube" },
      },
      { event: "mcp_client_connected", timestamp, properties: {} },
      { event: "mcp_client_connected", timestamp, properties: { client: " leading space" } },
      { event: "mcp_client_connected", timestamp, properties: { client: "a".repeat(65) } },
      { event: "mcp_client_connected", timestamp, properties: { client: "Claude", client_version: "1.0 beta" } },
      { event: "mcp_client_connected", timestamp, properties: { client: "Claude", client_version: null } },
      { event: "mcp_tool_called", timestamp, properties: { tool: "Generate", outcome: "ok", duration_ms: 1 } },
      { event: "mcp_tool_called", timestamp, properties: { tool: "generate", outcome: "failed", duration_ms: 1 } },
      { event: "mcp_tool_called", timestamp, properties: { tool: "generate", outcome: "ok", duration_ms: 1.5 } },
      { event: "mcp_tool_called", timestamp, properties: { tool: "generate", outcome: "ok", duration_ms: -1 } },
      { event: "mcp_tool_called", timestamp, properties: { tool: "generate", outcome: "ok", duration_ms: 3600001 } },
      { event: "mcp_tool_called", timestamp, properties: { tool: "generate", outcome: "ok", duration_ms: "12" } },
      { event: "mcp_tool_called", timestamp, properties: { tool: "generate", outcome: "ok" } },
      {
        event: "mcp_tool_called",
        timestamp,
        properties: { tool: "generate", outcome: "ok", duration_ms: 1, client: "" },
      },
      {
        event: "mcp_tool_called",
        timestamp,
        properties: { tool: "generate", outcome: "ok", duration_ms: 1, arguments: { prompt: "a red car" } },
      },
      "extension_started",
      null,
      [],
    ];

    const result = await sendEvents([...invalid, { event: "extension_started", timestamp }]);

    assert.equal(result.status, 202);
    assert.deepEqual(result.body, { accepted: 1, dropped: invalid.length });
    assert.deepEqual(
      batch().map(({ event }) => event),
      ["extension_started"],
    );
  });

  test("accepts timestamps from seven days ago to one hour ahead", async (t) => {
    const now = Date.parse("2026-10-18T12:00:00.000Z");
    t.mock.timers.enable({ apis: ["Date"], now });
    const accepted = [
      "2026-10-11T12:00:00Z",
      "2026-10-18T13:00:00.000Z",
      "2026-10-18T14:00:00+02:00",
      "2026-10-18T11:59:59.123456Z",
      "2026-10-18T07:30:00-04:30",
    ];
    const dropped = [
      "2026-10-11T11:59:59.999Z",
      "2026-10-18T13:00:00.001Z",
      "2026-10-18T12:00:00",
      "2026-10-18 12:00:00Z",
      "2026-10-18T12:00Z",
      "2026-10-18T12:00:00+0200",
      "2026-10-18T24:00:00Z",
      "2026-02-30T12:00:00Z",
      "2026-10-18t12:00:00z",
      "yesterday",
      now,
    ];

    const result = await sendEvents(
      [...accepted, ...dropped].map((timestamp) => ({ event: "extension_started", timestamp })),
    );

    assert.deepEqual(result.body, { accepted: accepted.length, dropped: dropped.length });
    assert.deepEqual(
      batch().map(({ timestamp }) => timestamp),
      [
        "2026-10-11T12:00:00.000Z",
        "2026-10-18T13:00:00.000Z",
        "2026-10-18T12:00:00.000Z",
        "2026-10-18T11:59:59.123Z",
        "2026-10-18T12:00:00.000Z",
      ],
    );
  });

  test("leaves out invalid or unknown context fields without refusing the events", async () => {
    const event = {
      event: "mcp_tool_called",
      timestamp: at(),
      properties: { tool: "generate", outcome: "ok", duration_ms: 5 },
    };

    const result = await sendEvents([event], {
      context: { extension_version: "0.11", blender_version: "5.0.1", os: "Darwin", arch: "x64", user: "someone" },
    });
    await sendEvents([event], { context: "macos" });
    await sendEvents([event], { context: null });

    assert.deepEqual(result.body, { accepted: 1, dropped: 0 });
    const [first, second, third] = received.map(({ body }) => (body.batch as Sent[])[0].properties);
    // Without a valid extension version, the MCP server version is left out too.
    assert.deepEqual(first, {
      ...MCP_SERVER,
      $mcp_tool_name: "generate",
      $mcp_is_error: false,
      $mcp_duration_ms: 5,
      outcome: "ok",
      blender_version: "5.0.1",
      arch: "x64",
      ...ANONYMOUS,
    });
    for (const properties of [second, third]) {
      for (const key of ["extension_version", "blender_version", "os", "arch", "$mcp_server_version"]) {
        assert.ok(!(key in properties), key);
      }
    }
  });

  test("answers 202 and forwards nothing when every event is dropped", async () => {
    const result = await sendEvents([
      { event: "unknown", timestamp: at() },
      { event: "extension_started", timestamp: "now" },
    ]);

    assert.equal(result.status, 202);
    assert.deepEqual(result.body, { accepted: 0, dropped: 2 });
    assert.deepEqual(received, []);
  });

  test("refuses a malformed batch", async () => {
    const event = { event: "extension_started", timestamp: at() };
    // A valid batch but for one byte that is not UTF-8, in a field that would only be left out.
    const invalidUtf8 = new TextEncoder().encode(
      JSON.stringify({ install_id: INSTALL, context: { os: "#" }, events: [event] }),
    );
    invalidUtf8[invalidUtf8.indexOf(0x23)] = 0xff;
    const bodies: unknown[] = [
      { context: CONTEXT, events: [event] },
      { install_id: INSTALL.toUpperCase(), events: [event] },
      { install_id: INSTALL.slice(1), events: [event] },
      { install_id: 12, events: [event] },
      { install_id: INSTALL },
      { install_id: INSTALL, events: [] },
      { install_id: INSTALL, events: Array.from({ length: 101 }, () => event) },
      { install_id: INSTALL, events: { 0: event } },
      { install_id: INSTALL, events: [event], api_key: "phc_other" },
      [{ install_id: INSTALL, events: [event] }],
      "null",
      "{",
      "",
      invalidUtf8,
    ];

    for (const body of bodies) {
      const result = await post("/telemetry/v1/events", body);

      assert.equal(result.status, 400, JSON.stringify(body));
      assert.deepEqual(result.body, { error: "bad_request" });
    }
    assert.deepEqual(received, []);
  });

  test("forwards up to 100 events in one batch", async () => {
    const result = await sendEvents(
      Array.from({ length: 100 }, () => ({ event: "extension_started", timestamp: at() })),
    );

    assert.deepEqual(result.body, { accepted: 100, dropped: 0 });
    assert.equal(batch().length, 100);
  });

  test("keeps answering 202 when PostHog rejects or ignores the batch", async (t) => {
    const warn = t.mock.method(console, "warn", () => {});
    respond = (_request, reply) => reply(500);

    const result = await sendEvents([{ event: "extension_started", timestamp: at() }]);

    assert.equal(result.status, 202);
    assert.equal(received.length, 1);
    // The log names the failure only: never the address or anything the client sent.
    const logged = warn.mock.calls.map((call) => String(call.arguments[0]));
    assert.deepEqual(logged, ["Usage events not relayed: HTTP 500"]);
  });

  test("treats __proto__ keys as unknown keys, never as a prototype", async () => {
    const timestamp = at();
    const tool = `"tool":"generate","outcome":"ok","duration_ms":5`;
    const event = (rest: string) => `{"event":${rest},"timestamp":"${timestamp}"`;
    const top = `{"install_id":"${INSTALL}","events":[${event(`"extension_started"`)}}],"__proto__":{}}`;
    const nested = `{"install_id":"${INSTALL}",
      "context":{"__proto__":{"os":"macos","extension_version":"9.9.9"},"arch":"x64"},
      "events":[
        ${event(`"mcp_tool_called","properties":{${tool}}`)}},
        ${event(`"extension_started","properties":{"__proto__":{}}`)}},
        ${event(`"operator_used","properties":{"__proto__":{"operator":"scenario.generate","outcome":"finished"}}`)}},
        ${event(`"operator_used","properties":{"operator":"scenario.generate","outcome":"error","__proto__":{"error_type":"E"}}`)}},
        ${event(`"extension_started","__proto__":{}`)}}
      ]}`;

    const refused = await post("/telemetry/v1/events", top);
    const result = await post("/telemetry/v1/events", nested);

    assert.equal(refused.status, 400);
    assert.deepEqual(result.body, { accepted: 1, dropped: 4 });
    assert.deepEqual(batch()[0].properties, {
      ...MCP_SERVER,
      $mcp_tool_name: "generate",
      $mcp_is_error: false,
      $mcp_duration_ms: 5,
      outcome: "ok",
      arch: "x64",
      ...ANONYMOUS,
    });
  });
});

describe("relay requests", () => {
  test("answers unknown telemetry paths itself with 404", async () => {
    for (const path of [
      "/telemetry",
      "/telemetry/",
      "/telemetry/v1",
      "/telemetry/v2/events",
      "/telemetry/v1/events/",
      "/telemetry/v1/Events",
    ]) {
      const result = await post(path, {}, {}, "GET");

      assert.equal(result.status, 404, path);
      assert.deepEqual(result.body, { error: "not_found" });
    }
    assert.deepEqual(received, []);
  });

  test("accepts only POST", async () => {
    for (const method of ["GET", "HEAD", "PUT", "OPTIONS", "DELETE"]) {
      for (const path of ["/telemetry/v1/events", "/telemetry/v1/feedback"]) {
        const result = await post(path, {}, {}, method);

        assert.equal(result.status, 405, `${method} ${path}`);
        assert.equal(result.headers.get("allow"), "POST");
        assert.deepEqual(result.body, { error: "method_not_allowed" });
      }
    }
  });

  test("accepts only JSON, optionally in UTF-8", async () => {
    const events = { install_id: INSTALL, events: [{ event: "extension_started", timestamp: at() }] };
    for (const type of [
      "text/plain",
      "application/x-www-form-urlencoded",
      "application/json; charset=latin-1",
      "application/jsonx",
      undefined,
    ]) {
      const result = await post("/telemetry/v1/events", events, { "content-type": type });

      assert.equal(result.status, 415, type);
      assert.deepEqual(result.body, { error: "unsupported_media_type" });
    }
    for (const type of ["application/json; charset=utf-8", "Application/JSON;charset=UTF-8"]) {
      assert.equal((await post("/telemetry/v1/events", events, { "content-type": type })).status, 202, type);
    }
  });

  test("accepts only the extension's User-Agent", async () => {
    for (const agent of [
      undefined,
      "",
      "Blender/5.0.1 (Darwin arm64; cycle=release)",
      "curl/8.7.1",
      "scenarioblender/0.11.0",
    ]) {
      const result = await post("/telemetry/v1/events", {}, { "user-agent": agent });

      assert.equal(result.status, 400, agent);
      assert.deepEqual(result.body, { error: "bad_request" });
    }
  });

  test("refuses a body over 64 KiB before or while reading it", async () => {
    const declared = await post("/telemetry/v1/events", "{}", { "content-length": String(64 * 1024 + 1) });
    const streamed = await post("/telemetry/v1/events", `{"padding": "${"x".repeat(64 * 1024)}"}`);
    const event = { event: "extension_started", timestamp: at() };
    const json = JSON.stringify({ install_id: INSTALL, events: [event] });
    const fits = await post("/telemetry/v1/events", json + " ".repeat(64 * 1024 - json.length));

    assert.deepEqual([declared.status, streamed.status, fits.status], [413, 413, 202]);
    assert.deepEqual(declared.body, { error: "too_large" });
    assert.deepEqual(streamed.body, { error: "too_large" });
  });

  test("limits each address to 60 event batches a minute, over a sliding window", async (t) => {
    t.mock.timers.enable({ apis: ["Date"], now: Date.parse("2026-10-18T12:00:00Z") });
    const events = [{ event: "extension_started", timestamp: at() }];
    const statuses = async (count: number, headers: HeaderValues = {}) => {
      const result: number[] = [];
      for (let i = 0; i < count; i += 1) result.push((await sendEvents(events, {}, headers)).status);
      return result;
    };

    assert.deepEqual(await statuses(60), Array(60).fill(202));
    const limited = await sendEvents(events);
    assert.equal(limited.status, 429);
    assert.deepEqual(limited.body, { error: "rate_limited" });
    // Another address, the first entry of x-forwarded-for when x-real-ip is absent, is not limited.
    assert.deepEqual(await statuses(1, { "x-real-ip": undefined, "x-forwarded-for": "203.0.113.9, 10.0.0.1" }), [202]);
    t.mock.timers.tick(60_000);
    // The previous minute still counts in full at the start of the next one.
    assert.equal((await sendEvents(events)).status, 429);
    t.mock.timers.tick(30_000);
    assert.deepEqual(await statuses(31), [...Array(30).fill(202), 429]);
    t.mock.timers.tick(120_000);
    assert.equal((await sendEvents(events)).status, 202);
  });

  test("limits each address to 5 feedback messages a minute", async (t) => {
    t.mock.timers.enable({ apis: ["Date"], now: Date.parse("2026-10-18T12:00:00Z") });
    newToken();
    const statuses: number[] = [];
    for (let i = 0; i < 6; i += 1) statuses.push((await sendFeedback({ rating: 5 })).status);

    assert.deepEqual(statuses, [202, 202, 202, 202, 202, 429]);
    // Events have their own budget.
    assert.equal((await sendEvents([{ event: "extension_started", timestamp: at() }])).status, 202);
  });

  test("is unavailable without a project token", async () => {
    delete process.env.POSTHOG_PROJECT_TOKEN;

    const events = await sendEvents([{ event: "extension_started", timestamp: at() }]);
    const feedback = await sendFeedback({ rating: 5 });

    assert.deepEqual([events.status, feedback.status], [503, 503]);
    assert.deepEqual(events.body, { error: "unavailable" });
    assert.deepEqual(received, []);
    assert.deepEqual(surveyReads, []);
  });

  test("never counts a telemetry request as a download", async () => {
    await sendEvents([{ event: "extension_started", timestamp: at() }]);

    assert.deepEqual(
      received.map(({ path }) => path),
      ["/batch/"],
    );
  });

  /** The status of a request from one address with no project token: 503 when admitted, 429 when limited. */
  async function admitted(endpoint: "events" | "feedback", headers: HeaderValues): Promise<number> {
    delete process.env.POSTHOG_PROJECT_TOKEN;
    return (await post(`/telemetry/v1/${endpoint}`, {}, headers)).status;
  }

  test("limits an IPv6 /64 prefix as one address, whatever its written form", async () => {
    const statuses: number[] = [];
    for (let i = 1; i <= 70; i += 1) {
      const host = i.toString(16);
      const forms = [
        `2001:db8:ffff:1::${host}`,
        `2001:0DB8:FFFF:0001:0000:0000:0000:${host}`,
        `[2001:db8:ffff:1::${host}]`,
        `2001:db8:ffff:1:${host}::`,
        `2001:db8:ffff:1::${host}%eth0`,
      ];
      statuses.push(await admitted("events", { "x-real-ip": forms[i % forms.length] }));
    }

    assert.deepEqual(statuses, [...Array(60).fill(503), ...Array(10).fill(429)]);
    assert.equal(await admitted("events", { "x-real-ip": "2001:db8:ffff:2::1" }), 503);
  });

  test("limits an IPv4-mapped IPv6 address as its IPv4 address", async () => {
    const statuses: number[] = [];
    for (const ip of ["192.0.2.7", "192.0.2.7", "192.0.2.7", "::ffff:192.0.2.7", "::FFFF:c000:207"]) {
      statuses.push(await admitted("feedback", { "x-real-ip": ip }));
    }

    assert.deepEqual(statuses, Array(5).fill(503));
    assert.equal(await admitted("feedback", { "x-real-ip": "0:0:0:0:0:ffff:192.0.2.7" }), 429);
    assert.equal(await admitted("feedback", { "x-real-ip": "::ffff:192.0.2.8" }), 503);
  });

  test("keys the limit by x-real-ip before x-forwarded-for", async () => {
    const statuses: number[] = [];
    for (let i = 0; i < 6; i += 1) {
      const forwarded = i < 5 ? "198.51.100.1" : "198.51.100.2";
      statuses.push(await admitted("feedback", { "x-real-ip": "198.51.100.9", "x-forwarded-for": forwarded }));
    }

    assert.deepEqual(statuses, [...Array(5).fill(503), 429]);
    assert.equal(
      await admitted("feedback", { "x-real-ip": undefined, "x-forwarded-for": "198.51.100.1, 10.0.0.1" }),
      503,
    );
  });

  test("forgets addresses idle for two minutes", async (t) => {
    t.mock.timers.enable({ apis: ["Date"], now: Date.parse("2026-10-20T00:00:00Z") });
    for (const ip of ["192.0.2.21", "192.0.2.22", "192.0.2.23"]) await admitted("events", { "x-real-ip": ip });
    assert.ok(rememberedClients() >= 3);

    t.mock.timers.tick(120_000);
    await admitted("events", { "x-real-ip": "192.0.2.24" });

    assert.equal(rememberedClients(), 1);
  });

  test("remembers at most 10,000 addresses, forgetting the least recent first", async (t) => {
    t.mock.timers.enable({ apis: ["Date"], now: Date.parse("2026-10-21T00:00:00Z") });
    const first = { "x-real-ip": "192.0.2.30" };
    const statuses: number[] = [];
    for (let i = 0; i < 61; i += 1) statuses.push(await admitted("events", first));
    assert.deepEqual(statuses.slice(59), [503, 429]);
    assert.equal(rememberedClients(), 1);

    for (let i = 0; i < 10_000; i += 1) {
      await admitted("events", { "x-real-ip": `10.${i >> 16}.${(i >> 8) & 255}.${i & 255}` });
    }

    assert.equal(rememberedClients(), 10_000);
    assert.equal(await admitted("events", first), 503);
  });
});

describe("feedback", () => {
  test("sends feedback as a response to the API survey", async () => {
    const token = newToken();

    const result = await sendFeedback(
      {
        install_id: INSTALL,
        context: CONTEXT,
        rating: 4,
        message: "  Add a batch mode.\n",
        email: "artist@example.com",
      },
      { "x-vercel-ip-country": "JP" },
    );

    assert.equal(result.status, 202);
    assert.deepEqual(result.body, { ok: true });
    assert.deepEqual(surveyReads, [`/api/surveys/?token=${token}`]);
    assert.equal(received.length, 1);
    assert.equal(received[0].path, "/i/v0/e/");
    assert.deepEqual(received[0].body, {
      api_key: token,
      event: "survey sent",
      distinct_id: INSTALL,
      properties: {
        "$survey_response_q-rating": "4",
        "$survey_response_q-improve": "Add a batch mode.",
        "$survey_response_q-email": "artist@example.com",
        $survey_id: SURVEY,
        $survey_name: "Blender feedback",
        $survey_questions: SURVEY_QUESTIONS,
        $survey_submission_id: SUBMISSION,
        $survey_completed: true,
        ...CONTEXT,
        ...ANONYMOUS,
        country: "JP",
      },
    });
  });

  test("identifies feedback by its submission without usage sharing, and sends the survey iteration", async () => {
    newToken();
    launch(QUESTIONS, { current_iteration: 3 });

    await sendFeedback({ message: "Thanks" });

    const { distinct_id: distinctId, properties } = received[0].body as {
      distinct_id: string;
      properties: Record<string, unknown>;
    };
    assert.equal(distinctId, SUBMISSION);
    assert.equal(properties.$survey_iteration, 3);
    assert.equal(properties["$survey_response_q-improve"], "Thanks");
    assert.ok(!("$survey_response_q-rating" in properties));
    assert.ok(!("$survey_response_q-email" in properties));
  });

  test("maps the rating to the first 5-point question and the texts to the first two open questions", async () => {
    newToken();
    launch([
      { id: "first-open", type: "open", question: "Improve?" },
      { id: "ten", type: "rating", question: "Recommend?", scale: 10 },
      { id: "choice", type: "single_choice", question: "Which?", choices: ["a", "b"] },
      { id: "five", type: "rating", question: "Rate", scale: 5 },
      { id: "second-five", type: "rating", question: "Rate again", scale: 5 },
      { id: "second-open", type: "open", question: "Email?" },
      { id: "third-open", type: "open", question: "Anything else?" },
    ]);

    await sendFeedback({ rating: 2, message: "Slow", email: "a@b.co" });

    const properties = (received[0].body as { properties: Record<string, unknown> }).properties;
    const answers = Object.fromEntries(
      Object.entries(properties).filter(([key]) => key.startsWith("$survey_response_")),
    );
    assert.deepEqual(answers, {
      $survey_response_five: "2",
      "$survey_response_first-open": "Slow",
      "$survey_response_second-open": "a@b.co",
    });
    assert.equal((properties.$survey_questions as unknown[]).length, 7);
  });

  test("drops an answer whose question the survey lacks", async () => {
    newToken();
    launch([{ id: "only-rating", type: "rating", question: "Rate", scale: 5 }]);

    const result = await sendFeedback({ rating: 5, message: "Great", email: "a@b.co" });

    assert.equal(result.status, 202);
    const properties = (received[0].body as { properties: Record<string, unknown> }).properties;
    assert.deepEqual(
      Object.keys(properties).filter((key) => key.startsWith("$survey_response_")),
      ["$survey_response_only-rating"],
    );
  });

  test("is unavailable when no answer maps to the survey", async () => {
    newToken();
    launch([
      { id: "open", type: "open", question: "Improve?" },
      { id: "seven", type: "rating", question: "Rate", scale: 7 },
      { type: "rating", question: "No ID", scale: 5 },
    ]);

    const result = await sendFeedback({ rating: 5 });

    assert.equal(result.status, 503);
    assert.deepEqual(result.body, { error: "unavailable" });
    assert.deepEqual(received, []);
  });

  test("is unavailable without the survey setting or while the survey is not running", async () => {
    newToken();
    delete process.env.POSTHOG_FEEDBACK_SURVEY_ID;
    const unset = await sendFeedback({ rating: 5 });
    process.env.POSTHOG_FEEDBACK_SURVEY_ID = SURVEY;
    surveyList = { status: 200, body: { surveys: [{ id: "another", name: "Another", questions: QUESTIONS }] } };
    const stopped = await sendFeedback({ rating: 5 });
    newToken();
    surveyList = { status: 500, body: {} };
    const unreadable = await sendFeedback({ rating: 5 });
    newToken();
    surveyList = { status: 200, body: [] };
    const malformed = await sendFeedback({ rating: 5 });

    assert.deepEqual([unset.status, stopped.status, unreadable.status, malformed.status], [503, 503, 503, 503]);
    assert.deepEqual(received, []);
  });

  test("reads the survey once every five minutes and keeps it when PostHog cannot list it", async (t) => {
    t.mock.timers.enable({ apis: ["Date"], now: Date.parse("2026-10-18T12:00:00Z") });
    newToken();

    await sendFeedback({ rating: 5 });
    t.mock.timers.tick(299_000);
    await sendFeedback({ rating: 4 });
    assert.equal(surveyReads.length, 1);

    t.mock.timers.tick(1_000);
    surveyList = { status: 502, body: {} };
    const kept = await sendFeedback({ rating: 3 });

    assert.equal(surveyReads.length, 2);
    assert.equal(kept.status, 202);
    assert.equal(received.length, 3);
  });

  test("refuses malformed feedback", async () => {
    newToken();
    const bodies: Record<string, unknown>[] = [
      { submission_id: undefined, rating: 5 },
      { submission_id: SUBMISSION.toUpperCase(), rating: 5 },
      { install_id: "abc", rating: 5 },
      { install_id: null, rating: 5 },
      { rating: 0 },
      { rating: 6 },
      { rating: 4.5 },
      { rating: "4" },
      { message: "" },
      { message: " \n\t " },
      { message: "x".repeat(5001) },
      { message: ["hello"] },
      { rating: 5, email: "not an address" },
      { rating: 5, email: "a@b" },
      { rating: 5, email: `${"a".repeat(245)}@example.com` },
      { rating: 5, email: 12 },
      { email: "a@b.co" },
      { context: CONTEXT },
      { rating: 5, name: "Someone" },
    ];

    for (const body of bodies) {
      newAddress();
      const result = await post("/telemetry/v1/feedback", { submission_id: SUBMISSION, ...body });

      assert.equal(result.status, 400, JSON.stringify(body));
      assert.deepEqual(result.body, { error: "bad_request" });
    }
    assert.deepEqual(received, []);
    assert.deepEqual(surveyReads, []);
  });

  test("accepts a message of up to 5000 code points with a non-blank character, and sends it trimmed", async () => {
    newToken();
    const emoji = "\u{1F600}";
    const messages = [emoji.repeat(5000), `${" ".repeat(4999)}x`, ` ${"x".repeat(5000)}`, emoji.repeat(5001)];
    const statuses: number[] = [];
    for (const message of messages) {
      newAddress();
      statuses.push((await sendFeedback({ message })).status);
    }

    assert.deepEqual(statuses, [202, 202, 400, 400]);
    const sent = received.map(({ body }) => (body.properties as Record<string, unknown>)["$survey_response_q-improve"]);
    assert.deepEqual(sent, [emoji.repeat(5000), "x"]);
  });

  test("tells the extension when PostHog rejects the feedback", async (t) => {
    const warn = t.mock.method(console, "warn", () => {});
    newToken();
    respond = (_request, reply) => reply(500);

    const result = await sendFeedback({ rating: 1, message: "Crashes on start", email: "a@b.co" });

    assert.equal(result.status, 502);
    assert.deepEqual(result.body, { error: "upstream" });
    const logged = warn.mock.calls.map((call) => String(call.arguments[0]));
    assert.deepEqual(logged, ["Feedback not relayed: HTTP 500"]);
  });

  test("answers within four seconds when PostHog is slow to list surveys and then does not answer", async (t) => {
    t.mock.method(console, "warn", () => {});
    newToken();
    surveyDelay = 1500;
    respond = () => {};
    const started = performance.now();

    const result = await sendFeedback({ rating: 3 });

    // The capture gets what remains of the deadline, not a timeout of its own.
    const elapsed = performance.now() - started;
    assert.equal(result.status, 502);
    assert.ok(elapsed >= 3500 && elapsed < 4400, `${elapsed} ms`);
  });

  test("gives up on a survey list that does not arrive after two seconds", async (t) => {
    t.mock.method(console, "warn", () => {});
    newToken();
    surveyDelay = Infinity;
    const started = performance.now();

    const result = await sendFeedback({ rating: 3 });

    const elapsed = performance.now() - started;
    assert.equal(result.status, 503);
    assert.ok(elapsed >= 1900 && elapsed < 3000, `${elapsed} ms`);
    assert.deepEqual(received, []);
  });

  test("is unavailable while the survey is a draft or stopped, even if PostHog lists it", async () => {
    const statuses: number[] = [];
    for (const dates of [
      { start_date: null },
      { start_date: "" },
      { start_date: undefined, end_date: undefined },
      { end_date: "2026-10-18T10:00:00Z" },
    ]) {
      newToken();
      newAddress();
      launch(QUESTIONS, dates);
      statuses.push((await sendFeedback({ rating: 5 })).status);
    }
    newToken();
    launch(QUESTIONS, { end_date: undefined });
    statuses.push((await sendFeedback({ rating: 5 })).status);

    assert.deepEqual(statuses, [503, 503, 503, 503, 202]);
    assert.equal(received.length, 1);
  });

  test("remembers a failed survey read for 30 seconds when it has nothing to fall back on", async (t) => {
    t.mock.method(console, "warn", () => {});
    t.mock.timers.enable({ apis: ["Date"], now: Date.parse("2026-10-18T12:00:00Z") });
    newToken();
    surveyList = { status: 500, body: {} };
    const statuses: number[] = [];
    const send = async () => {
      newAddress();
      statuses.push((await sendFeedback({ rating: 4 })).status);
    };

    await send();
    launch();
    t.mock.timers.tick(29_000);
    await send();
    assert.equal(surveyReads.length, 1);
    t.mock.timers.tick(1_000);
    await send();

    assert.deepEqual(statuses, [503, 503, 202]);
    assert.equal(surveyReads.length, 2);
  });

  test("keeps at most 16 survey lists, forgetting the oldest", async () => {
    const tokens = Array.from({ length: 17 }, () => newToken());
    const send = async (token: string) => {
      process.env.POSTHOG_PROJECT_TOKEN = token;
      newAddress();
      assert.equal((await sendFeedback({ rating: 5 })).status, 202);
    };

    for (const token of tokens.slice(0, 16)) await send(token);
    await send(tokens[0]);
    assert.equal(surveyReads.length, 16);
    await send(tokens[16]);
    await send(tokens[0]);

    assert.equal(surveyReads.length, 18);
    assert.equal(surveyReads.at(-1), `/api/surveys/?token=${tokens[0]}`);
  });

  test("refuses a __proto__ key at the top level", async () => {
    newToken();

    const result = await post("/telemetry/v1/feedback", `{"submission_id":"${SUBMISSION}","rating":5,"__proto__":{}}`);

    assert.equal(result.status, 400);
  });
});

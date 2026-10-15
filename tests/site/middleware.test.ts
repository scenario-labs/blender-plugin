// SPDX-FileCopyrightText: 2026 Scenario Inc.
// SPDX-License-Identifier: GPL-3.0-or-later
// Run from the repository root: node --test tests/site/middleware.test.ts
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { createServer, type IncomingMessage, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { after, before, beforeEach, test } from "node:test";

import middleware, { config, ORIGIN } from "../../tools/site_proxy/middleware.ts";

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

test("runs only for the repository directory", () => {
  assert.equal(config.matcher, "/repo/:path*");
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

  assert.equal(settings.rewrites[0].destination, `${ORIGIN}/$1`);
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

test("records other clients without Blender details", async () => {
  await visit("/repo/scenario-0.10.0.zip", { "user-agent": BROWSER, "x-vercel-ip-country": "not a code" });

  assert.equal(received.length, 1);
  assert.deepEqual(received[0].body.properties, {
    plugin: "blender",
    extension_version: "0.10.0",
    client: "other",
    $process_person_profile: false,
    $geoip_disable: true,
  });
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

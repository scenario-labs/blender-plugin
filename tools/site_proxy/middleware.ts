// SPDX-FileCopyrightText: 2026 Scenario Inc.
// SPDX-License-Identifier: GPL-3.0-or-later
// Counts extension downloads and repository checks on blender.scenario.com.
// It runs before vercel.json forwards the request to GitHub Pages and never
// changes the response: the event is sent after the request continues, and
// any failure only loses that count. Nothing identifies the visitor: no IP
// address, no stable identifier, only the fields built below. A ZIP keeps its
// version only when the repository index lists it; any other name, which
// Pages cannot serve, counts as "unknown".
//
// It also relays the extension's opt-in usage events and the feedback a user
// sends, under /telemetry/v1/. Those requests get their own answer and never
// reach Pages. The relay holds the PostHog token and forwards only the shapes
// allowed below; no response or log repeats what the client sent or names its
// address.

export const config = { matcher: ["/repo/:path*", "/telemetry/:path*"], runtime: "nodejs" };
// The GitHub Pages copy of the site: vercel.json forwards every request there.
export const ORIGIN = "https://scenario-labs.github.io/blender-plugin";

interface RequestContext {
  waitUntil(promise: Promise<unknown>): void;
}

// Blender's extension manager sends "Blender/5.0.1 (Darwin arm64; cycle=release)".
const BLENDER = /^Blender\/(\d+\.\d+\.\d+)(?: \(([^ ;)]+) ([^ ;)]+); cycle=([a-z]+)\))?/;
// Crawlers, link checkers and previews, matched before browsers because many
// announce themselves as "Mozilla/5.0 (compatible; ...bot...)".
const BOT = /bot|crawl|spider|slurp|facebookexternalhit|preview|lychee|linkcheck|headless|lighthouse/i;
// Scripts and command-line tools; an empty User-Agent counts as one too.
const TOOL = /^(curl|wget|python|go-http-client|node|undici|axios|okhttp|java|libwww|httpie|aiohttp)|powershell/i;
const ARCHIVE = /^\/repo\/scenario-(\d+\.\d+\.\d+)\.zip$/;
const TIMEOUT_MS = 2000;
// Published versions are cached; an unseen version rereads at most once a minute.
const INDEX_TTL_MS = 5 * 60_000;
const INDEX_RETRY_MS = 60_000;
const published = new Map<string, { versions: Set<string>; at: number }>();

// Read through globalThis: Vercel type-checks this file without Node's types.
function env(name: string): string | undefined {
  return (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env?.[name];
}

function postHogHost(): string {
  return env("POSTHOG_HOST") || "https://us.i.posthog.com";
}

/** Who made a request that is not Blender: a crawler, a script, a browser or something else. */
function classify(agent: string): string {
  if (BOT.test(agent)) return "bot";
  if (!agent || TOOL.test(agent)) return "tool";
  if (agent.startsWith("Mozilla/")) return "browser";
  return "other";
}

function describe(request: Request): { event: string; properties: Record<string, unknown> } | undefined {
  if (request.method !== "GET") return undefined;
  // A resumed download already counted when it started.
  const range = request.headers.get("range");
  if (range && !range.startsWith("bytes=0-")) return undefined;

  const path = new URL(request.url).pathname;
  // The PostHog project is shared with other Scenario plugins.
  const properties: Record<string, unknown> = { plugin: "blender" };
  let event: string;
  const archive = ARCHIVE.exec(path);
  if (archive) {
    event = "extension_downloaded";
    properties.extension_version = archive[1];
  } else if (path === "/repo/index.json") {
    event = "repository_checked";
  } else {
    return undefined;
  }

  const agent = request.headers.get("user-agent") ?? "";
  const blender = BLENDER.exec(agent);
  properties.client = blender ? "blender" : classify(agent);
  if (blender) {
    properties.blender_version = blender[1];
    if (blender[2]) {
      properties.os = blender[2];
      properties.arch = blender[3];
      properties.blender_cycle = blender[4];
    }
  }
  const country = request.headers.get("x-vercel-ip-country") ?? "";
  if (/^[A-Z]{2}$/.test(country)) properties.country = country;
  // Anonymous events: no person profile, and no location from the proxy's own address.
  properties.$process_person_profile = false;
  properties.$geoip_disable = true;
  return { event, properties };
}

async function isPublished(version: string): Promise<boolean> {
  // Read the index from Pages directly: through this site it would count itself.
  const origin = env("SITE_ORIGIN") || ORIGIN;
  const now = Date.now();
  const cached = published.get(origin);
  const age = cached ? now - cached.at : Infinity;
  if (cached && age < INDEX_TTL_MS && (cached.versions.has(version) || age < INDEX_RETRY_MS)) {
    return cached.versions.has(version);
  }
  let versions = cached?.versions ?? new Set<string>();
  try {
    const response = await fetch(`${origin}/repo/index.json`, { signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (response.ok) {
      const index = (await response.json()) as { data?: { version?: unknown }[] };
      versions = new Set((index.data ?? []).map((item) => String(item.version)));
    }
  } catch {
    // Keep the last versions read; an unreadable index only makes this count unknown.
  }
  published.set(origin, { versions, at: now });
  return versions.has(version);
}

async function send(token: string, event: string, properties: Record<string, unknown>): Promise<void> {
  if (event === "extension_downloaded" && !(await isPublished(String(properties.extension_version)))) {
    properties.extension_version = "unknown";
  }
  try {
    const response = await fetch(`${postHogHost()}/i/v0/e/`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ api_key: token, event, distinct_id: crypto.randomUUID(), properties }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (!response.ok) console.warn(`Download count not recorded: HTTP ${response.status}`);
  } catch (error) {
    console.warn(`Download count not recorded: ${(error as Error).name}`);
  }
}

// Telemetry relay. The extension's request shapes are a contract (#128): change
// them only together with the extension.
type Json = Record<string, unknown>;
type Properties = Record<string, string | number | boolean>;
type Endpoint = "events" | "feedback";
type Usage = { event: string; properties: Properties };

const MAX_BODY = 64 * 1024;
// Feedback answers within one deadline, before the extension's own timeout. The
// survey read gets the usual timeout, the capture what remains, but never less
// than its floor.
const FEEDBACK_DEADLINE_MS = 4000;
const MIN_CAPTURE_MS = 500;
// Per instance and per client address; a Vercel Firewall rule is the durable limit.
const RATE_LIMITS: Record<Endpoint, number> = { events: 60, feedback: 5 };
const RATE_WINDOW_MS = 60_000;
const MAX_CLIENTS = 10_000;
// An event may wait in the extension's queue, but not for long, and clocks drift.
const MAX_EVENT_AGE_MS = 7 * 24 * 3600_000;
const MAX_EVENT_AHEAD_MS = 3600_000;
const SURVEY_TTL_MS = 5 * 60_000;
// A failed read with nothing to fall back on is retried after this long.
const SURVEY_RETRY_MS = 30_000;
const MAX_SURVEY_SOURCES = 16;

const JSON_TYPE = /^application\/json\s*(?:;\s*charset="?utf-8"?\s*)?$/i;
const HEX_ID = /^[0-9a-f]{32}$/;
const VERSION = /^\d+\.\d+\.\d+$/;
const OPERATOR = /^scenario\.[a-z0-9_]{1,64}$/;
const ERROR_TYPE = /^[A-Za-z_][A-Za-z0-9_]{0,63}$/;
const MCP_CLIENT = /^[A-Za-z0-9][A-Za-z0-9._ -]{0,63}$/;
const MCP_CLIENT_VERSION = /^[A-Za-z0-9][A-Za-z0-9._+-]{0,31}$/;
const MCP_TOOL = /^[a-z][a-z0-9_]{0,63}$/;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const TIMESTAMP =
  /^(\d{4})-(\d{2})-(\d{2})T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,9})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/;
// PostHog's MCP analytics read these names and properties.
const MCP_SERVER = { $mcp_server_name: "Scenario for Blender", $mcp_source: "scenario_blender" };

interface RateWindow {
  start: number;
  count: number;
  previous: number;
}
interface SurveyQuestion {
  id?: string;
  type?: string;
  question: string;
  scale?: number;
}
interface Survey {
  id: string;
  name: string;
  iteration?: number;
  questions: SurveyQuestion[];
}
interface Feedback {
  submissionId: string;
  installId?: string;
  context: Properties;
  rating?: number;
  message?: string;
  email?: string;
}

// Least recently seen first, so the oldest entries are the first to go.
const rateWindows = new Map<string, RateWindow>();
// Surveys read per host and token; none when the last read failed.
const surveySources = new Map<string, { surveys?: Map<string, Survey>; at: number }>();

function isObject(value: unknown): value is Json {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function has(object: Json, key: string): boolean {
  return Object.hasOwn(object, key);
}

function hasOnly(object: Json, keys: readonly string[]): boolean {
  return Object.keys(object).every((key) => keys.includes(key));
}

function matches(value: unknown, pattern: RegExp): value is string {
  return typeof value === "string" && pattern.test(value);
}

function oneOf<T extends string>(value: unknown, options: readonly T[]): value is T {
  return typeof value === "string" && (options as readonly string[]).includes(value);
}

/** Length in code points, as the extension's Python counts it. */
function characters(text: string): number {
  let count = 0;
  for (const _ of text) count += 1;
  return count;
}

function reply(status: number, body: Json, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store", ...headers },
  });
}

function refuse(status: number, error: string, headers?: Record<string, string>): Response {
  return reply(status, { error }, headers);
}

/** The eight groups of an IPv6 address, or undefined for any other text. */
function ipv6Groups(text: string): number[] | undefined {
  // An embedded IPv4 tail, as in ::ffff:192.0.2.1, is the last two groups.
  const v4 = /^(.*:)(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(text);
  let hex = text;
  if (v4) {
    const bytes = v4.slice(2).map(Number);
    if (bytes.some((byte) => byte > 255)) return undefined;
    hex = `${v4[1]}${((bytes[0] << 8) | bytes[1]).toString(16)}:${((bytes[2] << 8) | bytes[3]).toString(16)}`;
  }
  const halves = hex.split("::");
  if (halves.length > 2) return undefined;
  const [left, right] = halves.map((half) => (half === "" ? [] : half.split(":")));
  // "::" stands for at least one zero group.
  const zeros = right ? 8 - left.length - right.length : 0;
  const groups = [...left, ...Array<string>(Math.max(zeros, 0)).fill("0"), ...(right ?? [])];
  if (groups.length !== 8 || (right && zeros < 1)) return undefined;
  if (!groups.every((group) => /^[0-9a-f]{1,4}$/.test(group))) return undefined;
  return groups.map((group) => parseInt(group, 16));
}

/**
 * The rate-limit key of the client's address, kept only in memory: an IPv4
 * address as is, an IPv6 address by its /64 prefix, which one host can rotate
 * through freely.
 */
function clientKey(request: Request): string {
  const forwarded = request.headers.get("x-forwarded-for")?.split(",", 1)[0];
  const address = (request.headers.get("x-real-ip") || forwarded || "").trim().slice(0, 64);
  // Without brackets or a zone, as in [fe80::1%eth0].
  const bare = address.replace(/^\[(.*)\]$/, "$1").split("%", 1)[0];
  const groups = bare.includes(":") ? ipv6Groups(bare.toLowerCase()) : undefined;
  if (!groups) return address;
  if (groups.slice(0, 5).every((group) => group === 0) && groups[5] === 0xffff) {
    return [groups[6] >> 8, groups[6] & 255, groups[7] >> 8, groups[7] & 255].join(".");
  }
  const prefix = groups.slice(0, 4).map((group) => group.toString(16));
  return `${prefix.join(":")}::/64`;
}

/** How many client keys the rate limit remembers, for tests. */
export function rememberedClients(): number {
  return rateWindows.size;
}

/** A sliding-window counter per endpoint and address, in this instance's memory only. */
function admit(endpoint: Endpoint, address: string): boolean {
  const now = Date.now();
  const key = `${endpoint} ${address}`;
  let window = rateWindows.get(key);
  rateWindows.delete(key);
  if (!window || now < window.start || now - window.start >= 2 * RATE_WINDOW_MS) {
    window = { start: now, count: 0, previous: 0 };
  } else if (now - window.start >= RATE_WINDOW_MS) {
    window = { start: window.start + RATE_WINDOW_MS, count: 0, previous: window.count };
  }
  const recent = window.previous * (1 - (now - window.start) / RATE_WINDOW_MS) + window.count;
  const allowed = recent < RATE_LIMITS[endpoint];
  if (allowed) window.count += 1;
  rateWindows.set(key, window);
  // Forget idle clients, and the least recent ones beyond the cap.
  for (const [other, entry] of rateWindows) {
    if (rateWindows.size <= MAX_CLIENTS && now - entry.start < 2 * RATE_WINDOW_MS) break;
    rateWindows.delete(other);
  }
  return allowed;
}

/** The body as text, or undefined when it exceeds the cap; reading stops there. */
async function readBody(request: Request): Promise<string | undefined> {
  const reader = request.body?.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  while (reader) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > MAX_BODY) {
      await reader.cancel();
      return undefined;
    }
    chunks.push(value);
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  // Invalid UTF-8 throws, and the caller refuses it with the malformed JSON.
  return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
}

function parseObject(text: string): Json | undefined {
  try {
    const value: unknown = JSON.parse(text);
    return isObject(value) ? value : undefined;
  } catch {
    return undefined;
  }
}

/** The validated platform fields; an invalid or unknown field is left out, never refused. */
function readContext(value: unknown): Properties {
  const context: Properties = {};
  if (!isObject(value)) return context;
  if (matches(value.extension_version, VERSION)) context.extension_version = value.extension_version;
  if (matches(value.blender_version, VERSION)) context.blender_version = value.blender_version;
  if (oneOf(value.os, ["macos", "windows", "linux", "other"])) context.os = value.os;
  if (oneOf(value.arch, ["arm64", "x64", "other"])) context.arch = value.arch;
  return context;
}

/** Properties every relayed event carries: anonymous, without a person profile or GeoIP. */
function anonymous(request: Request): Properties {
  const properties: Properties = { plugin: "blender", source: "extension" };
  const country = request.headers.get("x-vercel-ip-country") ?? "";
  if (/^[A-Z]{2}$/.test(country)) properties.country = country;
  properties.$process_person_profile = false;
  properties.$geoip_disable = true;
  return properties;
}

/** Milliseconds for an ISO 8601 timestamp with a zone, or undefined for anything else. */
function instant(value: unknown): number | undefined {
  const match = typeof value === "string" ? TIMESTAMP.exec(value) : null;
  if (!match) return undefined;
  const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])];
  // Date.parse accepts days such as February 30.
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return undefined;
  const time = Date.parse(match[0]);
  return Number.isFinite(time) ? time : undefined;
}

/** An allowed event under its PostHog name, or undefined when anything about it is not allowed. */
function usageEvent(name: unknown, p: Json, context: Properties): Usage | undefined {
  const server: Properties = { ...MCP_SERVER };
  if (context.extension_version) server.$mcp_server_version = context.extension_version;
  switch (name) {
    case "extension_started":
      return Object.keys(p).length === 0 ? { event: name, properties: {} } : undefined;
    case "operator_used": {
      if (!hasOnly(p, ["operator", "outcome", "error_type"]) || !matches(p.operator, OPERATOR)) return undefined;
      if (!oneOf(p.outcome, ["finished", "cancelled", "error"])) return undefined;
      const properties: Properties = { operator: p.operator, outcome: p.outcome };
      if (has(p, "error_type")) {
        if (p.outcome !== "error" || !matches(p.error_type, ERROR_TYPE)) return undefined;
        properties.error_type = p.error_type;
      }
      return { event: name, properties };
    }
    case "mcp_client_connected": {
      if (!hasOnly(p, ["client", "client_version"]) || !matches(p.client, MCP_CLIENT)) return undefined;
      const properties: Properties = { ...server, $mcp_client_name: p.client };
      if (has(p, "client_version")) {
        if (!matches(p.client_version, MCP_CLIENT_VERSION)) return undefined;
        properties.$mcp_client_version = p.client_version;
      }
      return { event: "$mcp_initialize", properties };
    }
    case "mcp_tool_called": {
      if (!hasOnly(p, ["tool", "outcome", "duration_ms", "client"]) || !matches(p.tool, MCP_TOOL)) return undefined;
      if (!oneOf(p.outcome, ["ok", "error", "timeout"])) return undefined;
      const duration = p.duration_ms;
      if (typeof duration !== "number" || !Number.isInteger(duration) || duration < 0 || duration > 3600_000) {
        return undefined;
      }
      const properties: Properties = {
        ...server,
        $mcp_tool_name: p.tool,
        $mcp_is_error: p.outcome !== "ok",
        $mcp_duration_ms: duration,
        outcome: p.outcome,
      };
      if (p.outcome === "timeout") properties.$mcp_error_type = "timeout";
      if (has(p, "client")) {
        if (!matches(p.client, MCP_CLIENT)) return undefined;
        properties.$mcp_client_name = p.client;
      }
      return { event: "$mcp_tool_call", properties };
    }
    default:
      return undefined;
  }
}

function readEvent(item: unknown, now: number, context: Properties): (Usage & { timestamp: string }) | undefined {
  if (!isObject(item) || !hasOnly(item, ["event", "timestamp", "properties"])) return undefined;
  const at = instant(item.timestamp);
  if (at === undefined || at < now - MAX_EVENT_AGE_MS || at > now + MAX_EVENT_AHEAD_MS) return undefined;
  const properties = has(item, "properties") ? item.properties : {};
  if (!isObject(properties)) return undefined;
  const usage = usageEvent(item.event, properties, context);
  return usage && { event: usage.event, timestamp: new Date(at).toISOString(), properties: usage.properties };
}

async function forwardEvents(token: string, batch: Json[]): Promise<void> {
  try {
    const response = await fetch(`${postHogHost()}/batch/`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ api_key: token, batch }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (!response.ok) console.warn(`Usage events not relayed: HTTP ${response.status}`);
  } catch (error) {
    console.warn(`Usage events not relayed: ${(error as Error).name}`);
  }
}

/** Validates each event on its own, answers at once and forwards the valid ones afterwards. */
function relayEvents(request: Request, body: Json, token: string, context: RequestContext): Response {
  const { install_id: installId, events } = body;
  if (!hasOnly(body, ["install_id", "context", "events"]) || !matches(installId, HEX_ID)) {
    return refuse(400, "bad_request");
  }
  if (!Array.isArray(events) || events.length < 1 || events.length > 100) return refuse(400, "bad_request");
  const platform = readContext(body.context);
  const shared = { ...platform, ...anonymous(request) };
  const now = Date.now();
  const batch: Json[] = [];
  for (const item of events) {
    const event = readEvent(item, now, platform);
    if (event) {
      const properties = { ...event.properties, ...shared };
      batch.push({ event: event.event, distinct_id: installId, timestamp: event.timestamp, properties });
    }
  }
  if (batch.length > 0) context.waitUntil(forwardEvents(token, batch));
  return reply(202, { accepted: batch.length, dropped: events.length - batch.length });
}

function readFeedback(body: Json): Feedback | undefined {
  if (!hasOnly(body, ["submission_id", "install_id", "context", "rating", "message", "email"])) return undefined;
  const { submission_id: submissionId, install_id: installId, rating, message, email } = body;
  if (!matches(submissionId, HEX_ID)) return undefined;
  const feedback: Feedback = { submissionId, context: readContext(body.context) };
  if (has(body, "install_id")) {
    if (!matches(installId, HEX_ID)) return undefined;
    feedback.installId = installId;
  }
  if (has(body, "rating")) {
    if (typeof rating !== "number" || !Number.isInteger(rating) || rating < 1 || rating > 5) return undefined;
    feedback.rating = rating;
  }
  if (has(body, "message")) {
    if (typeof message !== "string" || characters(message) > 5000) return undefined;
    const text = message.trim();
    if (text.length === 0) return undefined;
    feedback.message = text;
  }
  if (has(body, "email")) {
    if (typeof email !== "string" || characters(email) > 254 || !EMAIL.test(email)) return undefined;
    feedback.email = email;
  }
  return feedback.rating === undefined && feedback.message === undefined ? undefined : feedback;
}

/** The fields of PostHog's running surveys this relay reads, by survey ID. */
function readSurveys(value: unknown): Map<string, Survey> | undefined {
  if (!isObject(value) || !Array.isArray(value.surveys)) return undefined;
  const surveys = new Map<string, Survey>();
  for (const item of value.surveys) {
    if (!isObject(item) || typeof item.id !== "string") continue;
    const questions = (Array.isArray(item.questions) ? item.questions : []).filter(isObject).map((q) => ({
      id: typeof q.id === "string" ? q.id : undefined,
      type: typeof q.type === "string" ? q.type : undefined,
      question: typeof q.question === "string" ? q.question : "",
      scale: typeof q.scale === "number" ? q.scale : undefined,
    }));
    const iteration = typeof item.current_iteration === "number" ? item.current_iteration : undefined;
    surveys.set(item.id, { id: item.id, name: typeof item.name === "string" ? item.name : "", iteration, questions });
  }
  return surveys;
}

/** Running surveys, cached; a failed read keeps the last ones read, or is itself remembered. */
async function runningSurveys(host: string, token: string): Promise<Map<string, Survey> | undefined> {
  const key = `${host} ${token}`;
  const cached = surveySources.get(key);
  const now = Date.now();
  if (cached && now - cached.at < (cached.surveys ? SURVEY_TTL_MS : SURVEY_RETRY_MS)) return cached.surveys;
  let surveys: Map<string, Survey> | undefined;
  try {
    const response = await fetch(`${host}/api/surveys/?token=${encodeURIComponent(token)}`, {
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    surveys = response.ok ? readSurveys(await response.json()) : undefined;
    const reason = response.ok ? "unexpected body" : `HTTP ${response.status}`;
    if (!surveys) console.warn(`Feedback survey not read: ${reason}`);
  } catch (error) {
    console.warn(`Feedback survey not read: ${(error as Error).name}`);
  }
  surveys ??= cached?.surveys;
  surveySources.delete(key);
  surveySources.set(key, { surveys, at: now });
  for (const other of surveySources.keys()) {
    if (surveySources.size <= MAX_SURVEY_SOURCES) break;
    surveySources.delete(other);
  }
  return surveys;
}

/** Answers keyed by question: the 1 to 5 rating, then the first and second open questions. */
function surveyAnswers(survey: Survey, feedback: Feedback): Properties {
  const open = survey.questions.filter((question) => question.type === "open");
  const rating = survey.questions.find((question) => question.type === "rating" && question.scale === 5);
  const pairs: [SurveyQuestion | undefined, string | undefined][] = [
    [rating, feedback.rating === undefined ? undefined : String(feedback.rating)],
    [open[0], feedback.message],
    [open[1], feedback.email],
  ];
  const answers: Properties = {};
  for (const [question, answer] of pairs) {
    if (question?.id && answer !== undefined) answers[`$survey_response_${question.id}`] = answer;
  }
  return answers;
}

/** Sends the feedback as a response to the configured API survey and waits for PostHog. */
async function relayFeedback(
  request: Request,
  body: Json,
  token: string,
  surveyId: string,
  started: number,
): Promise<Response> {
  const feedback = readFeedback(body);
  if (!feedback) return refuse(400, "bad_request");
  const host = postHogHost();
  // A survey that is not launched, or is stopped, is not among the running ones.
  const survey = (await runningSurveys(host, token))?.get(surveyId);
  const answers = survey ? surveyAnswers(survey, feedback) : {};
  if (!survey || Object.keys(answers).length === 0) return refuse(503, "unavailable");
  const properties = {
    ...answers,
    $survey_id: survey.id,
    $survey_name: survey.name,
    $survey_questions: survey.questions.map(({ id, question }) => ({ id, question })),
    $survey_submission_id: feedback.submissionId,
    $survey_completed: true,
    ...(survey.iteration === undefined ? {} : { $survey_iteration: survey.iteration }),
    ...feedback.context,
    ...anonymous(request),
  };
  const distinctId = feedback.installId ?? feedback.submissionId;
  // What remains of the deadline, in whole milliseconds as AbortSignal.timeout requires.
  const remaining = Math.round(FEEDBACK_DEADLINE_MS - (performance.now() - started));
  try {
    const response = await fetch(`${host}/i/v0/e/`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ api_key: token, event: "survey sent", distinct_id: distinctId, properties }),
      signal: AbortSignal.timeout(Math.max(MIN_CAPTURE_MS, remaining)),
    });
    if (response.ok) return reply(202, { ok: true });
    console.warn(`Feedback not relayed: HTTP ${response.status}`);
  } catch (error) {
    console.warn(`Feedback not relayed: ${(error as Error).name}`);
  }
  return refuse(502, "upstream");
}

/** Answers every /telemetry/ request itself; cheap checks run before the body is read. */
async function relay(request: Request, path: string, context: RequestContext): Promise<Response> {
  const started = performance.now();
  const endpoint =
    path === "/telemetry/v1/events" ? "events" : path === "/telemetry/v1/feedback" ? "feedback" : undefined;
  if (!endpoint) return refuse(404, "not_found");
  if (request.method !== "POST") return refuse(405, "method_not_allowed", { allow: "POST" });
  // Any other type also makes a browser send a preflight, which gets no CORS headers.
  if (!JSON_TYPE.test(request.headers.get("content-type") ?? "")) return refuse(415, "unsupported_media_type");
  if (!(request.headers.get("user-agent") ?? "").startsWith("ScenarioBlender/")) return refuse(400, "bad_request");
  if (!admit(endpoint, clientKey(request))) return refuse(429, "rate_limited");
  const token = env("POSTHOG_PROJECT_TOKEN");
  const surveyId = env("POSTHOG_FEEDBACK_SURVEY_ID") ?? "";
  if (!token || (endpoint === "feedback" && !surveyId)) return refuse(503, "unavailable");
  if (Number(request.headers.get("content-length")) > MAX_BODY) return refuse(413, "too_large");
  let text: string | undefined;
  try {
    text = await readBody(request);
  } catch {
    return refuse(400, "bad_request");
  }
  if (text === undefined) return refuse(413, "too_large");
  const body = parseObject(text);
  if (!body) return refuse(400, "bad_request");
  if (endpoint === "events") return relayEvents(request, body, token, context);
  return relayFeedback(request, body, token, surveyId, started);
}

export default function middleware(request: Request, context: RequestContext): Promise<Response> | undefined {
  const path = new URL(request.url).pathname;
  if (path === "/telemetry" || path.startsWith("/telemetry/")) return relay(request, path, context);
  const token = env("POSTHOG_PROJECT_TOKEN");
  const described = token ? describe(request) : undefined;
  if (token && described) context.waitUntil(send(token, described.event, described.properties));
  return undefined;
}

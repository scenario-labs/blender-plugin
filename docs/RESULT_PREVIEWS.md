# Saved-result previews

[`result_previews`](../scenario/core/jobs/result_previews.py) and
[`preview_scheduler`](../scenario/core/jobs/preview_scheduler.py) prepare small
previews of downloaded saved results for the shared runtime. They are bpy-free.
Previews are read-only: they never submit, spend, apply, resolve a scene origin or
write the job store. This runtime layer has no user interface or local MCP tool
yet. Audio envelopes are decoded in an owned offline Blender process, described
below. Blender-side image decoding, display, playback and waveform drawing are
follow-up work under [#189](https://github.com/scenario-labs/blender-plugin/issues/189)
and [#66](https://github.com/scenario-labs/blender-plugin/issues/66).

## Sources by result type

Only results with a saved download receipt are previewed, in the states `ready`,
`applying`, `apply_failed` and `applied`. An interrupted application is allowed
because previews never touch the scene. The saved manifest's MIME type selects
the source:

| Saved result | Still | Other renditions |
| --- | --- | --- |
| PNG, JPEG, WebP and OpenEXR images | Local decode request for the verified result | None |
| Video | Server `thumbnail` | Server `preview` clip, only when requested |
| 3D models, except MTL material libraries | Server `thumbnail` | Server `preview` turntable clip, only when requested |
| WAV, MP3, OGG, FLAC, M4A and AAC audio | Server `thumbnail` when offered | Local RMS envelope from decoded samples |
| Anything else | Unsupported | None |

Image previews use the verified local bytes, not CDN transformation parameters,
which are undocumented CDN behavior.

## Server stills and clips

Metadata uses the selected SDK 2.2.0 through the shared
[adapter](../scenario/core/api/sdk_adapter.py):
`assets.with_raw_response.get_bulk` for every batch, a single asset included, in
chunks of 100 identities (the SDK documents a 200-identity limit). It carries the
selected project, uses the client's `max_retries=0` and checks online access
before each request. One batch reads its metadata once. The published wheel's
`types/asset_get_bulk_response.py`, like `types/asset_retrieve_response.py`,
documents the optional `thumbnail` and `preview` objects, each with an `assetId`
and a signed `url`; see the
[asset retrieval contract](https://docs.scenario.com/api/python/resources/assets/methods/retrieve).
The record must match the saved asset identity and MIME type. Signed URLs stay in
memory and are never written, logged or returned in errors.

Using one method for every batch size gives an absent asset one meaning. An
asset the server omits, for example one deleted after the job, is treated like
a preview that has not appeared yet: it is polled within the window, then marked
`missing`. A failed or malformed response, including an unrequested record,
remains a read failure, described under the polling window.

Bytes use the existing [signed result transfer](RESULT_TRANSFERS.md) with the same
configured storage hosts, redirect rules and online-access predicate, and smaller
caps: 8 MiB for a still and 64 MiB for a clip. The content, not the URL or a
declared type, must be PNG, JPEG or WebP for a still and MP4 or WebM for a clip.
Blender will decode stills on its main thread, so the byte cap alone does not
bound decode memory. A still must also declare at most 4096 pixels per side in
its PNG `IHDR` chunk, JPEG start-of-frame segment or WebP `VP8`, `VP8L` or
`VP8X` header; the checked dimensions are stored in its sidecar.

A failed transfer is not a final answer: storage may not serve a new preview on
its first request, for example by redirecting to another host. Any failure of
the transfer itself leaves the rendition `pending` for the
[polling window](#polling-window): a redirect to another host or a host outside
the policy, a connection error or timeout, a status other than 200 such as a
5xx, and a chunked, incomplete or oversized body. The downloader still makes one
attempt per call and follows only the same bounded same-host redirects, and
each attempt stays within its byte cap. Bytes that arrive but no longer match
their download receipt, are not a supported format, or lack bounded dimensions,
and a metadata mismatch, fail the rendition at once. Either way the reason is
sanitized and nothing is cached.

Server previews are bound to the saved asset identity and receipt digest. Their
bytes are produced by the service, not derived from the saved file, so they are
not a content attestation of the result.

## Polling window

Server previews can appear minutes after a result is saved. The scheduler polls
missing ones on the preview lane with backoff delays of 5, 10, 20, 40 and then
60 seconds. The window measures 300 seconds of online polling: it opens at the
first online poll and the last poll lands at its end. If no preview appeared,
the cache records a `missing` marker for that receipt and later requests show it
without polling again. An explicit `retry` clears the marker and opens a new
window. Requesting a rendition the result did not have yet, such as a clip after
its still, also opens a new window and restarts the backoff for that result, so
the clip is not judged by a window the still already used. Renditions still
polling share the new window, including one whose final poll is already on the
lane: if that poll leaves it `missing` or `failed`, it polls again in the new
window when the batch returns. That forced poll clears the `missing` marker the
final poll wrote, and any older marker of the requested rendition. A failed
download in that final poll is polled again too, because its outcome does not
show whether the window's end caused it.

A retry queues every rendition of the result at once, except unsupported ones
and previews the lane is already decoding or publishing, such as an audio
envelope whose offline decode is running. It withdraws their outstanding decode
requests, including an envelope still waiting for room on the lane, so the
snapshot it returns and later `status` reads report the retry rather than the
old outcome. When that result's batch is already on the lane, the forced fetch
waits for it. The pump that collects the batch applies its late outcome and
queues the renditions again in the same call, so that outcome is never reported
as settled and cannot undo the retry.

Without online access, renditions report `offline` and are checked every five
seconds. An offline poll pauses the window, keeping the time already used since
it opened, and the next online poll resumes it instead of starting a new one. A
transfer stopped because online access was turned off also reports `offline`.
Metadata read failures and transfers that did not complete stay `pending` with
the same backoff and become `failed` at the window's end, as do repeated lane
task failures. A transfer that keeps failing therefore makes at most nine
attempts in one window. Unlike `missing`, `failed` writes no marker. No result
state is persisted in `jobs.sqlite3`: the window starts in memory, and the
`missing` marker is what prevents a new window after a restart.

The backoff applies only to `pending` and `offline` renditions. A rendition
that was not sent with a batch, because the decode limit below held it back or
because it was requested while the batch ran, stays `queued` and goes with the
next pump.

## Local images and audio

For an image still or an audio envelope, the lane copies the saved file into a
new private `work/preview-*` directory of the cache, rehashing it against its
receipt while copying, and checks the copy's container signature. The copy has
a canonical name, never the provider's file name. Sources are capped at 128 MiB
for images and 256 MiB for audio. The scheduler keeps at most four such decode
requests outstanding, including running audio decodes, and fails a request that
waits 120 seconds for a decoder.

Blender decodes an image request later on its main thread: it writes a PNG of
at most 256 pixels per side to the request's `output`. Publication checks the
PNG signature, header checksum, dimensions and a 4 MiB size limit before caching
it. Every finished or discarded request removes its private copy.

## Offline audio envelopes

Blender's audio module holds Python's global interpreter lock for an entire
decode. Measured on macOS arm64 with Blender 5.0.1, 5.1.2 and 5.2.1, decoding ten
minutes of MP3, Ogg Vorbis or AAC stereo on a worker thread paused the main
thread for 0.4 to 0.55 seconds. An audio request is therefore decoded by
[`audio_decode`](../scenario/core/jobs/audio_decode.py) in a separate Blender
process, never on a thread of the user's Blender. The scheduler queues one lane
command per request as soon as the batch returns it; audio requests are never
listed by `decode_requests`, which is for Blender's main thread.

The lane starts the session's Blender executable with `--offline-mode`,
`--factory-startup`, `--disable-autoexec`, `--background` and `-noaudio`, a new
disposable profile and temporary directory, and the environment that local
capture uses, without `SCENARIO_`, `BLENDER_`, `PYTHON` or proxy variables.
The standalone [`waveform_worker.py`](../scenario/blender/waveform_worker.py)
does not load the extension. Blender's audio module and its ffmpeg readers decode
the private copy from its start, without seeking: WAV, MP3, Ogg, FLAC, M4A and
AAC are the accepted saved types. Numpy then writes one sum of squares and one
peak of samples clamped to full scale per 10 ms block, and a header with the
sample rate, channel count and frame count. Failures use a fixed vocabulary:
unreadable, unsupported rate or channels, no samples, too long or non-finite
samples. The process's log is never read and is removed with its directory.

[`EnvelopeBuilder`](../scenario/core/audio_waveform.py) checks each block against
its frame count before folding the blocks into 256 RMS and peak bins: finite
values, peaks within full scale and a root mean square no louder than its peak.
Envelopes accept up to 600 seconds, eight channels and 192 kHz. The child holds
at most 64 Mi decoded samples, which covers ten minutes of 48 kHz stereo; longer,
faster or wider audio fails instead of being truncated. A decode times out after
60 seconds. Cancellation, retirement and the timeout terminate the child, which
is killed if it has not exited three seconds later. Only a child still running at
the deadline reports a timeout; one that exits with a failure keeps the reason it
reported, however long it took. The envelope is cached as a sidecar keyed by
the saved receipt, so a later session reads it without decoding again.

The session builds the decoder specification on Blender's main thread from
`bpy.app.binary_path` and the installed worker. Without a usable executable,
for example when Blender runs as a Python module, envelopes fail with an explicit
reason instead of waiting. A failed decode caches nothing; Retry decodes again.

## Cache

The runtime passes `cache/result-previews` under Blender's extension user
directory. If that directory cannot be created, the session still runs jobs and
`result_previews` reports that previews are not configured. Entries live in
`v1/<scope digest>/<key digest>/`; the scope digest matches the saved result
partition and the key also binds the request, asset, MIME type and receipt
digest and size. Another credential, project, request or byte content therefore
never shares an entry. Stills and clips have a data file and a JSON sidecar
holding digests, sizes, dimensions and the server preview asset ID, never a URL,
credential or prompt. Envelopes and `missing` markers are sidecars only.

Like saved results, the paths the cache returns, including decode requests,
use the canonical spelling of its root: on Windows, the extended-length `\\?\`
namespace. Compare them with that canonical root, not with the configured one.
Work directories are built on that root and take only their name from
`mkdtemp`, which normalizes the path it returns on Python 3.12 and later.

Reads accept only a regular, nonsymlink file whose size, digest and signature
match its sidecar; anything else is a cache miss. Publication never replaces a
valid entry. At most every ten minutes the lane removes abandoned work
directories older than a day and evicts the least recently used entries beyond
512 MiB, keeping entries used in the last minute. That pass normally starts a
preview batch. Once every rendition has settled no batch comes, so when previews
were written since the last pass, the scheduler queues a maintenance-only lane
command on the same ten-minute cadence. It reads no job record and makes no
network request, and it evicts only beyond the budget. A cache that writes took
past 512 MiB is therefore brought back toward it within about ten minutes of the
previous pass, whether or not more previews are requested. A ready status can
outlive its evicted file; an explicit retry reads or fetches it again. Only
removed bytes count toward the budget: an entry the system refuses to delete,
such as a file another process holds open on Windows, leaves the next oldest
entry to go instead and is tried again on the next pass. The cache is safe to delete, even
while Blender runs: each lane command recreates the root as a private directory
when its parent still exists.

## Lane and ownership

`JobWorkers` owns one dedicated `ScenarioPreview` thread with its own bounded
queue of eight tasks and per-task cancellation. Preview polling, copies and
downloads therefore never occupy the job workers used by remote refresh, result
downloads and submissions, and never use the single local media slot.
Deactivation cancels queued previews and signals the running one. A storage
transfer stops at its next permission check once signaled, before publishing
anything; an audio decode terminates its child within about 0.1 seconds, or kills
it after three more; an SDK metadata read cannot be interrupted and finishes or
times out under the client policy. An audio decode occupies the lane for its
duration, so later server polls wait behind it: 0.65 to 0.9 seconds for a
one-second file and about 1.7 seconds for ten minutes on macOS arm64, at most
the 60-second timeout. `JobWorkers.previews_idle` reports when no preview
command is queued or running. Shutdown joins the lane with the other workers.

`ResultPreviewScheduler` runs on its owner thread, normally Blender's main
thread, and performs no network I/O or preview cache work. `request` reads saved
receipts from the local job store, and `release` removes leftover private copies
after the lane stops. `request`, `retry`, `status`, `decode_requests`,
`finish_decode` and `discard_decode` are its interface; status snapshots are
immutable and safe to read while drawing. It sends at most one batch of up to 32
assets at a time.

`JobSession(preview_root=...)` exposes it as `result_previews` while the session
is active. The session's existing maintenance timer, and `reap_retired` in
headless loops, call `service_previews`. Deactivation closes the scheduler. The
timer shuts a retired session down only once its preview lane is idle, so an
in-flight preview read never blocks Blender's main thread; the session stays
registered until then. Shutdown removes remaining private copies after the
workers stop. Extension disable or exit still joins any running preview command.
See the [job context contract](BLENDER_JOB_CONTEXT.md#saved-result-preview-ownership).

## Boundaries

These are offline contracts with synthetic SDK and storage fixtures. Which asset
kinds receive server thumbnails or previews, their sizes and dimensions, signed
URL lifetime and hosts, where a first request may redirect, their timing after a
job succeeds, and how `get_bulk` reports a deleted asset are not established by
live evidence. The installed-ZIP native tests decode synthetic WAV, MP3, Ogg,
FLAC, Matroska AAC and MP4 AAC files in the offline child and exercise its
failures, cancellation and timeout. They passed on Blender 5.0.1, 5.1.2 and 5.2.1
locally on macOS arm64 and in hosted CI on Linux x64 and Windows x64 runners.
Provider audio files, child start-up time and antivirus behavior on real Windows
and Linux desktops, macOS x64 and sandboxed Blender packages are not covered.
The timing figures above are macOS arm64 measurements only. Blender-side image
decoding, the user interface, MCP parity and native desktop acceptance remain
open under #189, #65 and #66.

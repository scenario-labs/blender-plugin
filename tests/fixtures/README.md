# Test fixtures

## Inventory

These fixtures support offline parsing, payload and result tests. Recording dates
below come from the commits that first added each file, not a recent API refresh.

| Path | Contents and source | Recorded |
| --- | --- | --- |
| `models/*.json` | Eighteen model records from `GET /models/{id}` | 2026-08-28 and 2026-08-29 |
| `models_list_page1.json` | Five public models from `GET /models?privacy=public&pageSize=5` | 2026-08-28 |
| `patina-copper-512/model_record.json` | Model record from `GET /models/model_patina-material` | 2026-08-28 |
| `patina-copper-512/dryrun_response.json` | Estimate from `POST /models/model_patina-material/inferences?dryRun=true` | 2026-08-28 |
| `patina-copper-512/job.json` | Patina job response from `GET /jobs/{jobId}` | 2026-08-28 |
| `patina-copper-512/*.png` | Six maps from that job; `manifest.json` maps asset IDs, types, files and sizes | 2026-08-28 |
| `smoke/playblast_72f.mp4` | Blender viewport playblast used by the opt-in video smoke script | 2026-08-28 |

## Provenance and rights

The JSON records and Patina maps are captured Scenario API responses and outputs.
The playblast is a Blender capture. Git history records their addition, but does
not establish which legal entity owned the generating account or media rights.
Maintainer confirmation of those rights and the final media licence/provenance
statement remain tracked in [#9](https://github.com/scenario-labs/blender-plugin/issues/9).
Do not infer an assignment or change an existing licence from this inventory.
No `PROVENANCE.json` has been generated for a new recording run.

## Generated audio fixtures

Audio waveform tests generate their own PCM sample bytes at runtime in
`tests/unit/test_audio_waveform.py` and `tests/blender/test_audio_preview.py`.
Those synthetic signals contain no provider output, recording or third-party
media; they are first-party GPL test code and leave no committed audio files.
They cover 8/16/24/32-bit mono/stereo and malformed, missing, oversized and
unsupported input. Human listening acceptance remains separate under #68.

## Synthetic video fixture

`synthetic/video-six-frames.mp4` is a first-party test clip containing six solid
32-by-32 blue-gray picture frames at 24 fps, with no audio or provider content.
It is licensed GPL-3.0-or-later with the test code. Native movie-strip tests use
it to exercise Blender's bundled decoder without needing an external encoder.
It was generated locally with this ffmpeg command; the tests do not run it:

```sh
ffmpeg -f lavfi -i color=c=0x6b88a4:s=32x32:r=24 -frames:v 6 -an \
  -c:v mpeg4 -q:v 5 -fflags +bitexact -flags:v +bitexact -map_metadata -1 \
  tests/fixtures/synthetic/video-six-frames.mp4
```

The adjacent `synthetic/audio-silence.mp3`, `audio-silence.ogg` and
`video-six-frames.webm` are also first-party GPL-3.0-or-later test media. They
contain one second of generated silence or the same six solid-color frames,
with no recording or provider output. Native saved-result tests decode each
format using Blender. Reproduce them with:

```sh
ffmpeg -f lavfi -i anullsrc=r=8000:cl=mono -t 1 -c:a libmp3lame -b:a 32k \
  -map_metadata -1 tests/fixtures/synthetic/audio-silence.mp3
ffmpeg -f lavfi -i anullsrc=r=8000:cl=mono -t 1 -c:a libvorbis \
  -map_metadata -1 tests/fixtures/synthetic/audio-silence.ogg
ffmpeg -f lavfi -i color=c=0x6b88a4:s=32x32:r=24 -frames:v 6 -an \
  -c:v libvpx-vp9 -map_metadata -1 tests/fixtures/synthetic/video-six-frames.webm
```

## Synthetic Film review media

`synthetic/film-four-seconds.mp4` and `film-four-seconds-audio.mp4` are
first-party GPL-3.0-or-later fixtures: four seconds of 32x32 generated color at
24 fps, respectively silent and with a generated 440 Hz tone. They contain no
recording or provider output. Native Film tests use their actual bundled-decoder
frames/sound to verify trims, independent copies and muted-master assembly.
The tests do not invoke the external encoder. Reproduce with:

```sh
ffmpeg -f lavfi -i color=c=0x6b88a4:s=32x32:r=24 -t 4 -an \
  -c:v mpeg4 -q:v 5 -fflags +bitexact -flags:v +bitexact -map_metadata -1 \
  tests/fixtures/synthetic/film-four-seconds.mp4
ffmpeg -f lavfi -i color=c=0x6b88a4:s=32x32:r=24 \
  -f lavfi -i sine=frequency=440:sample_rate=48000:duration=4 -t 4 \
  -c:v mpeg4 -q:v 5 -c:a aac -b:a 32k -fflags +bitexact \
  -flags:v +bitexact -flags:a +bitexact -map_metadata -1 \
  tests/fixtures/synthetic/film-four-seconds-audio.mp4
```

## Synthetic progressive JPEG panorama

`synthetic/panorama-progressive.jpg` is a first-party GPL-3.0-or-later fixture:
a 32x16 progressive JPEG with four flat 16x8 color blocks (red and green above,
blue and yellow below), 4:4:4 sampling and ten scans. It contains no recording,
provider output or EXIF metadata. Unit tests check that the JPEG preflight
accepts it and rejects comment floods inserted into it. Native World tests check
that Blender decodes this progressive frame with its expected colors, that scan
and comment floods built from it are rejected before decoding, and that comments
up to the segment limit decode to the same pixels. Reproduce it with the locked
Pillow 12.3.0 development dependency; the tests do not run this command:

```sh
uv run --locked python -c 'from PIL import Image
image = Image.new("RGB", (32, 16))
colors = ((200, 40, 40), (40, 200, 40), (40, 40, 200), (200, 200, 40))
image.putdata([colors[(y // 8) * 2 + x // 16] for y in range(16) for x in range(32)])
image.save("tests/fixtures/synthetic/panorama-progressive.jpg",
           quality=95, subsampling=0, progressive=True)'
```

## Identifiers and URLs

The recorder replaces string-valued account fields `userId`, `authorId`,
`createdBy`, `ownerId`, `projectId` and `teamId` with stable synthetic placeholders.
It replaces HTTP URLs whose query contains `Key-Pair-Id`, `Policy`, `Signature`,
`X-Amz-Signature` or `X-Amz-Credential` with `https://cdn.example/FIXTURE`, including
case variants and percent-encoded query names. Treat signed URLs as credentials.
This is a targeted sanitizer, not a guarantee that arbitrary response fields or
free text contain no sensitive data. Inspect proposed fixture diffs before commit.

Asset, job, model and collection identifiers, ordinary documentation URLs and
schema values stay intact. Non-string account fields remain inspectable rather
than being coerced, since they may be schema definitions or malformed responses.
Offline [hygiene tests](../unit/test_fixture_hygiene.py) check every committed JSON
file without printing the rejected values.

## Local cleanup and recording

This command uses no credentials and makes no API calls:

```sh
uv run --locked --no-env-file python tools/record_fixtures.py --scrub-existing
```

It preserves compact versus indented JSON and a final newline where present;
unchanged files are not rewritten. Invalid JSON stops cleanup before any file is
written. The cleanup command does not refresh API records or download media.
It skips dot-prefixed directories, including private recorder staging left by an
interrupted process; those files are not part of the published fixture inventory.

The normal recorder uses the shared SDK adapter and the pinned SDK's public
`models.with_raw_response.retrieve/list` methods. It reads all eighteen model
records named in `MODEL_IDS` and one public page of five models, using the
explicit test credential pair and optional project from the environment. It
reconstructs each detail's `model` wrapper around the adapter's complete model
record; unrelated top-level detail metadata is not recorded. The list page
retains its wrapper, unknown fields and next-page cursor. No speculative
pagination parameter, generation request or media download is performed.

Every required read must succeed before local files change. A missing or failed
model stops the run rather than silently retaining a stale record. Sanitized
files are staged, then replaced individually; `PROVENANCE.json` is published
last with the UTC recording date, SDK version, recorder path, scrub policy and
written-file/endpoint map. It records no account identity or ownership assertion.
A failed publication may leave some complete new fixtures, but removes the prior
provenance first so it cannot claim the partial set is a successful refresh.
Inspect the diff and retry the explicit read command if needed. Temporary staging
is cleaned when the process exits normally, including handled failures; an abrupt
process kill can leave a `.recording-*` directory to inspect and remove. These
staging directories are ignored by Git and excluded from offline cleanup and
fixture hygiene checks; a later cleanup cannot publish or legitimize their files.

No fixture refresh or provenance file is included in this change. Real endpoint
acceptance and maintainer confirmation of media rights remain under #9.

Live recording requires explicitly selected test credentials and authorization;
see [contributor configuration](../../CONTRIBUTING.md#environment-variables).
The default test suite needs neither credentials nor a Scenario account.

## Synthetic static GLB

`synthetic/static-triangle.glb` is first-party GPL-3.0-or-later test data:
a parent node, one translated triangle, three positions and UV pairs, and one
material with a generated solid-color 2-by-2 RGBA PNG embedded in the GLB buffer.
Its asset copyright metadata records Scenario Inc. It contains no recording,
provider output, external URI, animation or rig. Pure preflight tests mutate its
JSON to check unsupported contracts; native tests exercise actual import,
hierarchy, packed textures, cursor placement, rollback and durable recovery.

The native update probe stages
these exact bytes and compares their captured-source metadata and generation
bindings before and after upgrade/restart. Packages exposing Film upload storage
also bind this same imported fixture to a saved production/task and preserve that
separate association. This does not establish live provider
behavior or in-place application acceptance.

## Schema 9 job store

`synthetic/jobs-schema9.sql` is first-party GPL-3.0-or-later test data: the SQL
dump of a shared job database written by the schema 9 storage code of commit
`b57c398f`, the last main revision before schema 10, followed by that database's
application ID and schema version pragmas. The repository does not commit database
files, so tests rebuild the database from this reviewable text. It holds fifteen
jobs in two synthetic credential scopes, covering every job state except the
transient `downloading` and `applying`, the model, workflow, prompt and translate
operations, partial and complete receipts, a
texture role, a captured mesh binding, local application claims including an
unfinished one, a Film task, a Film upload association and an adopted cloud
record. All identities, hashes and receipts are synthetic; there are no result
files, credentials, prompts or signed URLs. The
[schema 10 upgrade tests](../unit/test_job_store_schema10.py) and the
installed-ZIP store test rebuild a fresh database for each case. Reproduce the
dump with that commit's own storage code and compare it with the committed file:

```sh
git archive b57c398f scenario | tar -x -C /path/to/empty-directory
uv run --locked --no-env-file python tools/make_job_store_fixture.py \
  --source /path/to/empty-directory --output /path/to/new/jobs-schema9.sql
cmp /path/to/new/jobs-schema9.sql tests/fixtures/synthetic/jobs-schema9.sql
```

The tool never overwrites a file: `--output` must name a new `.sql` path, so delete
the committed fixture first only when intentionally replacing it. It refuses any
source whose store is not schema 9, imports nothing from the current checkout and
writes the database only to a temporary directory. The dump records rows, schema
and index definitions, not SQLite page layout, which the upgrade does not depend on.

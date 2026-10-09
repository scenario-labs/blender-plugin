# Test fixtures

## Inventory

These fixtures support offline parsing, payload and result tests. Recording dates
below come from the commits that first added each file, not a recent API refresh.

| Path | Contents and source | Recorded |
| --- | --- | --- |
| `models/*.json` | Nineteen model records from `GET /models/{id}` | 2026-08-28 and 2026-08-29; Seedance 2.0 Mini 2026-10-10 |
| `models_list_page1.json` | Five public models from `GET /models?privacy=public&pageSize=5` | 2026-08-28 |
| `models/trained/bases/*.json` | Five public LoRA-capable base model records from `GET /models/{id}`; see [trained-model contracts](#trained-model-contracts) | 2026-10-09 |
| `models/trained/public/*.json` | Routing-field projections of six public Scenario LoRA and composition records from `GET /models/{id}` | 2026-10-09 |
| `models/trained/contracts.json` | Catalog and bulk-read observations, composition concept reads, 21 `dryRun=true` probe replies and 8 production-path quotes for trained-model routes | 2026-10-09 |
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

Audio waveform tests generate their own signals at runtime. The unit tests
`tests/unit/test_audio_waveform.py` and `test_audio_decode.py` use synthetic
sample lists. The native `tests/blender/test_audio_preview.py` and
`test_result_previews.py` write 16-bit PCM WAV tones, and
`tests/blender/test_waveform_worker.py` writes WAV, MP3, Ogg Vorbis, FLAC and
Matroska AAC tones with Blender's audio module. The waveform decoder tests also
read the documented synthetic `audio-silence.mp3`, `audio-silence.ogg` and
`film-four-seconds-audio.mp4`, copying the latter as an M4A. Those signals
contain no provider output, recording or third-party media; they are
first-party GPL test code and leave no new committed audio files. They cover
PCM and compressed, mono and stereo, silent, undecodable, too long, canceled and
timed-out input. Human listening acceptance remains separate under #68.

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

## Synthetic rendered reference image

`synthetic/reference-toadstool-512.png` is a first-party GPL-3.0-or-later
fixture: a 512x512 8-bit RGB render of a red toadstool with white spots, standing
on a green base with pebbles, in front of a plain blue-gray backdrop. It contains
no recording, provider output, external asset or PNG metadata. Smoke plans can
name it as an explicitly authorized
[reference input](../smoke/README.md#committed-reference-image).

[The committed script](../../tools/render_reference_fixture.py) builds the scene
from code in an empty factory scene, placing the spots and pebbles with seed 40.
It renders with Workbench: Studio lighting, object colors, eight-sample
anti-aliasing, no shadows or cavity, the Standard view transform and no dither.
It then decodes Blender's PNG output and writes a canonical PNG holding only
IHDR, one IDAT and IEND, with every row unfiltered. It refuses to run outside
background Blender 5.1.2. The file was generated with Blender 5.1.2 on macOS
arm64 (Metal GPU backend) through the isolated command wrapper, which owns a
fresh offline profile. The tests do not run this command:

```sh
uv run --locked --no-env-file python tools/blender_env.py run --blender /path/to/blender-5.1.2 -- \
  --background --factory-startup --python-exit-code 1 \
  --python tools/render_reference_fixture.py -- write tests/fixtures/synthetic/reference-toadstool-512.png
```

| Digest | SHA-256 |
| --- | --- |
| File bytes | `b70e8debff0ba0fc7dd8823a9a38229600e3fd7b8f22a1a32c490b4310182e02` |
| Decoded RGB pixels, top row first | `5ec27e71b80a93737e51e354eac42d1341d0737d90f0cede8f4a8dcd269e4a71` |

To check a fresh render against the committed pixels without rewriting the file:

```sh
uv run --locked --no-env-file python tools/blender_env.py run --blender /path/to/blender-5.1.2 -- \
  --background --factory-startup --python-exit-code 1 \
  --python tools/render_reference_fixture.py -- check tests/fixtures/synthetic/reference-toadstool-512.png
```

`check` prints the pixel digest, the number of differing pixels and the largest
channel difference. It fails when that difference exceeds `--tolerance`, which
defaults to 0 (exact pixels). On macOS arm64, repeated `write` runs produced
identical bytes and `check` reported no differing pixel. A scratch copy without
the version guard also reproduced the same pixels with Blender 5.0.1 and 5.2.1 on
that machine; this is an observation, not a supported way to regenerate.

The pixel digest is the reproducibility contract. The compressed bytes also
depend on the zlib bundled with Blender. Other GPUs, drivers and operating
systems were not checked, and their Workbench rasterization or anti-aliasing may
differ slightly. Accept a nonzero `--tolerance` only after inspecting the
reported difference. A changed scene needs a regenerated file with new digests,
tests and evidence, not a wider tolerance.

[Offline unit tests](../unit/test_reference_fixture.py) pin both digests, the
size and the chunk layout. They check that Pillow reads the same pixels, that
the object stays inside a plain backdrop border, and that the PNG helpers
reverse every row filter and reject malformed or unsupported files. They also
validate the smoke guide's example plan against this file and stage it through
the shared upload staging with the documented digest. They do not render,
upload or contact Scenario. Live upload acceptance and paid generation with this
image remain separate checks under
[#40](https://github.com/scenario-labs/blender-plugin/issues/40).

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
`models.with_raw_response.retrieve/list` methods. It reads all nineteen model
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

No full fixture refresh or provenance file has been committed. The Seedance 2.0
Mini record was added alone on 2026-10-10: one detail read through the same
adapter `model` read and `write_fixture` scrub, without regenerating the other
records, the list page or `PROVENANCE.json`. Its public schema keeps a
first-frame rule naming a last-frame input that the schema does not declare.
Real endpoint acceptance and maintainer confirmation of media rights remain
under #9.

Live recording requires explicitly selected test credentials and authorization;
see [contributor configuration](../../CONTRIBUTING.md#environment-variables).
The default test suite needs neither credentials nor a Scenario account.

## Trained-model contracts

`models/trained/` records how the service treats trained models. A separate
recorder writes it with reads and `dryRun=true` quotes only, never a submission:

```sh
uv run --locked --env-file .env.local python tools/capture_trained_contracts.py
```

It reads the selected scope's private trained list, the public catalog, five
fixed LoRA-capable base models, six fixed public Scenario LoRAs and compositions,
their bulk summaries, each composition concept and one image of the scope. It
then sends the dry runs listed in its `CASES` and quotes each accepted base-model
route again through `SDKAdapter.estimate_model`. A fixed public model missing
from the public catalog, a server error or any other failed read stops the run;
a 4xx dry-run reply is recorded as evidence. The whole directory is staged and
replaced in one step, so a failed run leaves the previous fixtures in place. If
the replacement fails and moving the previous directory back fails too, the
recorder keeps its `.recording-*` staging directory, which then holds the only
previous copy, and prints where it is.

What is written:

- `bases/`: complete base records, scrubbed like the records above. Random
  model and asset identifiers that are not in the public catalog, such as
  example asset IDs, also become `FIXTURE` placeholders.
- `public/`: projections of public trained records. They keep only the routing
  fields (`id`, `type`, `privacy`, `status`, `custom`, `capabilities`,
  `compliantModelIds`, `concepts`, `parentModelId`) plus `observedFields`, the
  field names of the full record. Training parameters, which can hold signed
  storage URLs and internal paths, are dropped. A parent or concept ID that is
  not in the public catalog becomes a placeholder.
- `contracts.json`: the recording date, SDK version and whether a project
  override was set, never the project itself; the public type counts and
  whether list, bulk and detail records carry `inputs` or `uiConfig`;
  readability and type of each composition concept; every dry-run request
  body, HTTP status and the reply's exact quote fields or rejection reason; and
  the route decision derived from those statuses.

Private records are never written. For the private list the recorder keeps
only whether it is empty and, per REST type, schema presence and dry-run
statuses, with no reason text, since a reason could name a private model. The
selected project, the scope's asset IDs and private record IDs are replaced
wherever they occur; the reference image used for image-to-image quotes is
written as `asset_FIXTUREREFERENCE00000000`. A final check refuses to write
anything if one of those private values remains. The
[offline contract tests](../unit/test_trained_contracts.py) pin the captured
shapes; the [recorder tests](../unit/test_capture_trained_contracts.py) exercise
the real SDK and adapter against a synthetic service. The captured results and
what they mean for routing are summarized in
[SDK contracts](../../docs/SDK_ADOPTION.md#trained-model-rest-contracts).

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
`b57c398f`, a schema 9 main revision, followed by that database's
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

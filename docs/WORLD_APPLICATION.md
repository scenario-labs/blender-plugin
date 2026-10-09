# Local panorama World application

`scenario.blender.world_application.apply_world(scene, filepath, *, expected_receipt=None, media_type=None)` is a synchronous,
main-thread primitive for an explicitly selected scene. It creates a packed image
and a separate World with an equirectangular Environment Texture → Background →
World Output graph. The original World, including its nodes and other scene users,
is untouched. The returned session-local handle can restore that exact original
World. A scene with no original World restores to `None`.

## Accepted local files

The filename is not trusted as a format declaration. The bounded core preflight
checks actual signatures and dimensions before Blender decodes a private snapshot
of the same bytes. Blender's decoded format and dimensions must agree. The image
is packed before scene assignment; deleting the source file afterward is safe.
Temporary copies live under the extension's user directory, not its installation.

For a downloaded result, supply its saved `DownloadedResult` as
`expected_receipt`. The source basename, byte count and SHA256 must match before
container parsing, image decoding or World allocation. Larger files report the
panorama byte limit before receipt comparison. Verification applies to the exact
bounded byte snapshot passed to Blender, so replacing the source path
after that read cannot change the decoded image. Missing, changed or mismatched
data fails locally and preserves the original World; it never triggers another
download or generation. Ordinary explicit local-file callers can omit the receipt.

A saved result also supplies its server-declared `media_type`. It must be one of
`image/png`, `image/jpeg`, `image/exr`, `image/x-exr` or `image/aces`, and must
name the container the preflight actually finds; `image/aces` must be OpenEXR.
Any other type is rejected before the file is opened, and a mismatch is rejected
before decoding. This keeps the confirmation's declared format truthful.

A receipt describes bytes, not authoritative job ownership or a current Blender
target. The caller must obtain it from the selected scoped job, preserve its
private storage, and validate the original file/scene/revision before application.
The optional byte check does not claim a durable application transaction.
The explicit [JobSession World command](BLENDER_JOB_CONTEXT.md#explicit-saved-result-world-application)
adds owned verification, original-context checks and a durable claim around this
primitive for one selected saved result.

- RGB/RGBA PNG with 8- or 16-bit samples. CRCs and chunk boundaries are checked;
  animated PNG and HDR metadata (`cICP`, `mDCV`, `cLLI`) are rejected. A maximum
  of 4,096 total chunks, including IHDR, IDAT and IEND, bounds per-chunk preflight
  work independently of file size and pixel dimensions. Files above this
  application limit are rejected before decoding; it is not a PNG format limit.
- Baseline, extended-sequential or progressive Huffman JPEG with 8-bit samples
  and three color components. Lossless, hierarchical, arithmetic-coded, 12-bit,
  grayscale and CMYK files are rejected. A maximum of 4,096 marker segments up
  to the first scan bounds header work. The file must end with its end-of-image
  marker, because libjpeg would otherwise conceal a truncated scan with gray
  pixels. Blender must decode it as a JPEG image with its default sRGB color space.
- Single-part, non-deep OpenEXR version 2 scanline files (compression types 0–9), with matching data
  and display windows. Explicit cubemap metadata is rejected. Blender must decode
  the result as a floating-point image.
- All formats require a 2:1 aspect ratio, minimum 4×2, at most 32 megapixels and 128 MiB
  on disk. EXR header scanning is limited to 1 MiB; the expected scanline table, block
  coordinates and complete nonoverlapping byte extents are checked before decode. Non-regular files are rejected;
  POSIX FIFOs are opened without waiting for a writer.

The parser follows the [OpenEXR file layout](https://openexr.com/en/latest/OpenEXRFileLayout.html)
(version/flags and null-terminated attribute headers),
[PNG specification](https://www.w3.org/TR/png-3/) (signature, IHDR, CRC and chunks)
and [ITU-T T.81](https://www.w3.org/Graphics/JPEG/itu-t81.pdf) Annex B
(marker segments and the frame header).
The parser checks structural completeness, not compressed-payload integrity; the
optional receipt check above binds the source bytes separately. This preflight is
not another image decoder: Blender's decoder remains authoritative.
The byte/pixel limits bound input and decoded dimensions, not decoder CPU time.
Radiance HDR, WebP, tiled/layered/multipart/deep EXR and other formats remain unsupported.

The JPEG check reads only what must be known before Blender allocates pixels.
A few kilobytes of JPEG can declare billions of pixels, and Blender exposes no
header-only dimension query, so the marker walk stops at the first scan after
reading the frame header. Quantization and Huffman tables, entropy-coded data,
color transforms, ICC profiles and EXIF metadata are left to Blender. Blender
5.0, 5.1 and 5.2 ignore EXIF orientation, so a JPEG is applied in its stored
pixel order.

### OpenEXR color primaries

The optional OpenEXR `chromaticities` attribute is read during the same bounded
header scan. Without it, or with Rec.709 primaries, Blender's own color space
choice applies unchanged. ACES AP0 primaries with the ACES white point select
Blender's `ACES2065-1` color space; Blender 5.0, 5.1 and 5.2 already make that
choice while decoding, and the primitive assigns it explicitly if a decoder does
not. Other primaries, such as ACEScg AP1 or Rec.2020, and malformed attributes
are rejected before decoding: those Blender versions decode them as linear
Rec.709, which would tint the lighting. The `image/aces` media type is a server
label; only the declared primaries select the color space. Image import and
material maps keep their previous handling of EXR primaries.

`PanoramaInfo.hdr_capable` describes accepted floating-point OpenEXR capability.
It does not assert measured dynamic range. Accepted PNG and JPEG are treated as LDR.
`PanoramaInfo.chromaticities` reports `None`, `rec709` or `aces_ap0` for panoramas.
A 2:1 image alone proves neither equirectangular content nor seamless edges/poles;
the caller explicitly selects that projection. Cloud generation must separately
establish a supported model/output contract and validate live results.

## Restore and failure ownership

`handle.restore()` returns `True` once and `False` on an already restored handle.
It requires the original live scene, the applied World still assigned there, the
original World still available, and unchanged owned World/image settings. A changed
node graph, socket value, mapping/image-user setting, World setting, image color
space, dirty pixel buffer or changed packed bytes refuses restoration. This conservative fingerprint
excludes the large image pixel array (dirty state and the bounded packed-byte
digest guard content edits). It also includes writable UI properties such as node positions/names; preserve edits
or restore manually when it refuses. It never searches by scene or World name.

Restore preserves the applied World/image if another scene or material has acquired
users. Unused owned data is removed best effort. Preparation/decoding failures
clean up owned data and preserve the previous scene assignment; cleanup failures
may leave orphan data but cannot unlink another user's data. The original World
is not given a fake user: manually purging it makes later restoration unavailable.

Handles contain live RNA references and are not serializable history records.
Discard them after file load, undo or extension shutdown. Invalidated/removed
references fail closed. This primitive creates no undo entry. Operators offering Blender global undo
must own its transaction and invalidate handles when undo changes ownership.
The saved-result operator below offers explicit guarded restoration, without
a global undo transaction. Async jobs must validate captured file, scene, target and revision
before calling this function; selecting an active scene is not such validation.

## Validation and remaining integration

Unit tests exercise bounded malformed-container rejection, JPEG coding and
segment limits, and OpenEXR primaries classification. Installed-ZIP native
fixtures generate small PNG, JPEG and floating EXR files locally and test explicit
scene application, graph/packing, shared users, restoration, edited/deleted data,
thread rejection, corrupt/truncated files, saved-receipt and media-type mismatches,
source replacement after snapshotting and rollback after decode. Directly written
EXR fixtures declare Rec.709, ACES AP0 or ACEScg AP1 primaries; the AP0 case
checks the `ACES2065-1` color space, its pixel conversion and the restore guard
on a color space edit. Another native case shows Blender ignoring EXIF
orientation. They make no Scenario service calls.

This is a partial slice of #98 and #65. Optional JobSession integration now binds
verified downloads to guarded durable World application. SDK model validation,
estimate/confirmation, production storage policy, global undo operators,
seam/pole quality and authorized live generation remain separate integration work.

## Saved-result UI and MCP approval

For a downloaded PNG, JPEG or OpenEXR result (media type `image/png`,
`image/jpeg`, `image/exr`, `image/x-exr` or `image/aces`),
**Set panorama as World (N)** captures the selected scene revision and current
World for explicit confirmation. The confirmation and MCP `format` field state
the selected asset's declared format: PNG or JPEG as LDR, or OpenEXR as a float
container whose ACES AP0 primaries use `ACES2065-1`.
MCP uses `prepare_result_application` with `purpose: world` and a selected
`asset_id`, followed by the same `apply_result_application` command after approval.
Inspection and the confirmation dialog do not read media or contact Scenario.
The existing worker verifies receipts, then `apply_recovered_world` rechecks the
approved destination and saves the recovered application claim before mutation.
The primitive still verifies the actual panorama bytes, packs the image and
preserves the previous World. An unrelated ordinary image fails locally without
replacing anything. No automatic download or generation retry follows failure.

The action is offered by supported image media type, not a claim that every
image is panoramic. The confirmation explicitly chooses equirectangular use;
actual 2:1 dimensions and supported container checks occur during application.
PNG and JPEG remain LDR, and an accepted EXR does not prove measured HDR range or
seamless content. Known application failure, including a media type that does not
match the actual container, is reported with panorama requirements and keeps the
local retry state. Server-declared panorama projection is not shown: the saved
job does not yet persist it.

A successful World assignment exposes **Restore previous World** in the same
session. MCP prepares `purpose: restore_world` without an asset ID, shows the
scene and current World, then consumes the approval through
`apply_result_application`. Restoration checks the captured destination plus
the primitive's exact ownership/fingerprint guards. A replaced/edited World or
image refuses restoration and preserves user changes. The original World is not
mutated. Successful restoration leaves the job `applied`; it does not rewind the
claim or permit generation/application replay. A pending persistence receipt must
be saved before restoration is offered, and retry never repeats World assignment.

This path accepts `ready` or confirmed `apply_failed` jobs under the original
claim. Already `applied` images, including automatic Image imports, use a separate
durable local claim after fresh approval. Interrupted local claims block further
reuse. Restoration covers the most recent World assignment for this job in each
destination scene in the current file session. Reusing a panorama in another
scene preserves the earlier scene's restore handle; restore each scene separately
after selecting and reviewing it. Handles use scene identities owned by this
session, independently of ordinary edit/render origin revisions. Renaming a
scene preserves restoration while deleting it and creating another with the
same name does not transfer authority. Retrying a persistence receipt keeps
its original destination even if another scene is
active. Previous owned Worlds remain subject to normal Blender save/purge rules;
these handles are not a persistent undo history.
Undo/Redo invalidates live scene ownership and retires restoration handles,
as do session retirement/restart and file load. Deleted or retired destinations
do not offer restoration, and maintenance removes their handles without touching
stale Blender data. Manually select a retained World in Blender when needed.
No global undo transaction, cloud panorama preset, seam/pole acceptance or
completion of #98 is claimed.

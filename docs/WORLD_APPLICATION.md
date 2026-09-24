# Local panorama World application

`scenario.blender.world_application.apply_world(scene, filepath, *, expected_receipt=None)` is a synchronous,
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
container parsing, image decoding or World allocation. Verification applies to
the exact bounded byte snapshot passed to Blender, so replacing the source path
after that read cannot change the decoded image. Missing, changed or mismatched
data fails locally and preserves the original World; it never triggers another
download or generation. Ordinary explicit local-file callers can omit the receipt.

A receipt describes bytes, not authoritative job ownership or a current Blender
target. The caller must obtain it from the selected scoped job, preserve its
private storage, and validate the original file/scene/revision before application.
The optional byte check does not claim a durable application transaction.

- RGB/RGBA PNG with 8- or 16-bit samples. CRCs and chunk boundaries are checked;
  animated PNG and HDR metadata (`cICP`, `mDCV`, `cLLI`) are rejected. A maximum
  of 4,096 total chunks, including IHDR, IDAT and IEND, bounds per-chunk preflight
  work independently of file size and pixel dimensions. Files above this
  application limit are rejected before decoding; it is not a PNG format limit.
- Single-part, non-deep OpenEXR version 2 scanline files (compression types 0–9), with matching data
  and display windows. Explicit cubemap metadata is rejected. Blender must decode
  the result as a floating-point image.
- Both require a 2:1 aspect ratio, minimum 4×2, at most 32 megapixels and 128 MiB
  on disk. EXR header scanning is limited to 1 MiB; the expected scanline table, block
  coordinates and complete nonoverlapping byte extents are checked before decode. Non-regular files are rejected;
  POSIX FIFOs are opened without waiting for a writer.

The parser follows the [OpenEXR file layout](https://openexr.com/en/latest/OpenEXRFileLayout.html)
(version/flags and null-terminated attribute headers) and
[PNG specification](https://www.w3.org/TR/png-3/) (signature, IHDR, CRC and chunks).
The parser checks structural completeness, not compressed-payload integrity; the
optional receipt check above binds the source bytes separately. This preflight is
not another image decoder: Blender's decoder remains authoritative.
The byte/pixel limits bound input and decoded dimensions, not decoder CPU time.
JPEG, Radiance HDR, tiled/layered/multipart/deep EXR and other formats remain unsupported.

`PanoramaInfo.hdr_capable` describes accepted floating-point OpenEXR capability.
It does not assert measured dynamic range. Ordinary accepted PNG is treated as LDR.
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
references fail closed. This primitive creates no undo entry. A future user-facing
operator must own the undo transaction and invalidate handles when undo changes
ownership. Async jobs must validate captured file, scene, target and revision
before calling this function; selecting an active scene is not such validation.

## Validation and remaining integration

Unit tests exercise bounded malformed-container rejection. Installed-ZIP native
fixtures generate small PNG and floating EXR files locally and test explicit
scene application, graph/packing, shared users, restoration, edited/deleted data,
thread rejection, corrupt/truncated files, saved-receipt mismatches, source
replacement after snapshotting and rollback after decode. They make no
Scenario service calls.

This is a partial slice of #98 and #65. SDK model validation, estimate/confirmation,
job completion guards, trusted downloads, history/Set as World UI, undo operators,
seam/pole quality and authorized live generation remain separate integration work.

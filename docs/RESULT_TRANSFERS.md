# Signed result downloads

`scenario.core.jobs.transfers` provides a synchronous, bpy-free storage primitive
for application-owned workers. It does not contact Scenario API endpoints;
those remain the shared SDK adapter's responsibility. SDK 2.2.0 returns storage
URLs but does not transfer their bytes. This module uses Python's HTTPS transport
and the already bundled certifi certificate authorities, adding no dependency.

## Trust and boundaries

The caller supplies a `StoragePolicy` containing exact, reviewed HTTPS storage
hostnames. There is deliberately no default allowlist: deriving the policy from
an incoming URL defeats the check. Hosts and their DNS infrastructure must be
trusted. The policy rejects alternate ports, user credentials, fragments,
non-ASCII URLs, control characters and backslashes. Wildcards, IP literals and
local hostnames cannot be configured. IDN names must use their explicit ASCII
representation. This is a host policy, not a defense against compromised trusted
DNS or hosts.

The downloader sends only a GET, identity encoding and connection-close header.
It has no Scenario credentials, cookie jar, netrc, proxy configuration, automatic
retry or URL logging. At most two HTTP 301/302/303/307/308 redirects may be
followed. Each Location must be an absolute HTTPS URL that passes the original
storage policy and keeps the original hostname; relative URLs, cross-host hops
(including another configured host), loops and malformed destinations are
rejected. Each hop uses a fresh credential-free connection, the same total
deadline and a fresh online-permission check. Redirect bodies are not read and
responses/connections are closed before continuing. Final size/digest checks
and atomic publication are unchanged. This accommodates same-host CDN delivery
redirects without retrying generation or deriving new trusted hosts. TLS verifies the hostname and bundled certificate
authorities; ambient certificate/key-log environment variables are ignored.
Status 200 is required. Content and transfer encodings are rejected; compressed
or chunked responses require a separately reviewed transport contract.
Exceptions exposed to callers and successful receipts omit the URL and response
body. Caller instrumentation must also avoid logging the input URL or locals.

The caller must provide an online-access predicate reflecting Blender's actual
permission. Permission is checked before connecting, sending and reading, and
before publishing. Revocation cannot undo a socket operation already in progress.
Byte limits cover streams both with and without Content-Length. A socket timeout
bounds inactivity; an overall elapsed budget is checked between operations and
reads. OS DNS resolution and blocking header/TLS operations are not interruptible
by that elapsed-budget check; worker shutdown must account for this limitation.

## Output and recovery

The root must already exist, be an absolute path without symlink components, and
remain privately owned with trusted ancestors for the whole operation. Blender
integration must create it under `bpy.utils.extension_path_user`; the primitive
never chooses an installed-extension or shared temporary directory. Names are
portable basenames, not paths. After validating the original root, Windows storage
operations use its extended-length drive or UNC path so scoped directories and
staging files can exceed legacy Win32 path limits. Verification can return that
extended path; this does not establish compatibility with a later Blender importer.
The directory layout and receipt names are unchanged.
The supplied root must already be accessible in its supplied path notation;
conversion protects descendants and does not repair an inaccessible root.
Win32 device paths are rejected instead of being reinterpreted as UNC roots.
Staging uses a private temporary subdirectory and
0600 file; completed bytes are fsynced before atomic, non-overwriting hard-link
publication in the same filesystem. A filesystem without hard-link support fails
closed. Directory metadata durability after sudden power loss is not guaranteed.

An optional expected byte count and SHA256 are checked before publication. The
returned immutable `DownloadedResult(name, size, sha256)` contains no URL. The
[job store](JOB_STORAGE.md) can persist this receipt; `verify_download` rehashes it
before explicit recovery or Blender application. Verification accepts only a
regular nonsymlink file with the saved size/digest, enforces a byte cap and checks
for changes during reading. It does not repair files or make service calls.
On Windows Python 3.12+, descriptor and path queries can give `ctime` different
meanings. Verification compares their creation timestamps while retaining the
descriptor's before/after metadata-change check, identity, size, mode and digest
checks. Other platforms retain their metadata-change timestamp comparison.
The caller must retain exclusive ownership of the private directory through
application; verification does not lock the file against later replacement.
A computed hash without a trusted expected digest proves local consistency, not
remote content authenticity. Existing files and symlinks are never replaced,
including competing publication from another worker.

Cleanup is attempted for ordinary failures and control exceptions. Once the
verified file is published, ordinary staging/response/connection cleanup failures
do not replace its successful receipt with a failed-transfer error. Control
exceptions still propagate. After cleanup failure or process death,
`.scenario-download-*` directories may remain. Once all the application's
transfer workers have stopped, recovery may remove those unreferenced staging
directories and explicitly retry a download using a freshly retrieved URL.
Never infer a finished job from a partial file or resubmit generation to repair
missing downloads. A crash between publication and receipt persistence requires
explicit file verification and reconciliation by the caller.

## Active Image delivery

The runtime configures the selected `JobSession` with a private `shared-results`
directory below extension user state and an exact HTTPS host policy:
`cdn.cloud.scenario.com`, documented in Scenario's
[CDN guide](https://docs.scenario.com/get-started/documentation/content-delivery-network-cdn),
and `cdn.scenario.com`, used by the official
[asset retrieval guide](https://docs.scenario.com/get-started/content/retrieve-asset-url-by-asset-id).
The policy never derives hosts from incoming URLs. Download permission uses the
catalog's worker-safe online-access event, including credential retirement.

Active Image UI/MCP jobs use SDK `jobs.retrieve` and `assets.retrieve` through the
shared adapter, then this credential-free downloader. The main-thread pump verifies
receipts before importing supported PNG/OpenEXR snapshots. Transfer and application
failures stop the pipeline and preserve saved results; they cannot repeat the paid
submission. Synthetic native tests exercise the real downloader with mocked HTTPS
bytes, exact saved digests, packed images, stale origins and failed transfers.
They do not establish live CDN or provider format acceptance.

## Integration still required

Other generation lanes remain unintegrated. Explicit recovered Image application
uses a separately approved destination and reverified local receipts.
Image UI/MCP controls can resume downloads and reconcile interrupted receipts;
neither action grants permission to import into a restarted scene.
The [coordinator](JOB_COORDINATOR.md#result-retrieval-and-download-commands)
now orchestrates saved manifests/receipts and retrieves fresh URLs for explicit
download retries through the SDK. Explicit interrupted-download recovery now verifies committed receipts under a
cooperating cross-process lock; unreceipted files and staging cleanup still need
separate review. Those commands must bind the trusted asset response and
receipt to the original account/project/job/target. Live signed-storage acceptance
and supported OS/filesystem behavior remain separate from offline contracts.

SDK identifier-validation failures in result metadata retrieval become sanitized
`ResultError` exceptions without changing the saved manifest or starting downloads.


## Full prompt text

`ResultDownloader.download(max_bytes=...)` can impose a smaller per-request cap;
it cannot expand the configured storage policy. Prompt result recovery uses a
64 KiB cap for full text assets when their preview is incomplete, with exact
expected size and post-download digest verification. The cap applies to headers
and streamed bodies even without Content-Length. Each read owns private temporary
staging beneath the configured result root and removes it on success or failure.
The strings are returned to the caller; no local prompt cache or automatic paid
fallback is created. A process crash can leave private temporary staging for
later cleanup, as with other interrupted transfers.

[Model text recovery](JOB_COORDINATOR.md#model-text-recovery) uses the same
reader for one explicitly selected output. SDK 2.2.0 exposes text classification
as top-level `kind`, separately from `mimeType`; the old nested `type.kind` shape
does not qualify. An explicit `properties.hasFullPreview=true` permits the whole
preview; otherwise a bounded full-body read must succeed. There is no fallback
to a truncated prefix. Integral numeric byte counts are normalized to integers
before transfer. This reader returns text and leaves scene application to its
caller; it does not adopt the prototype Blockout path on its own.

## Texture result semantics

The selected SDK 2.2.0's public `assets.with_raw_response.retrieve` response keeps
`mimeType` separate from `metadata.type`. The
[asset retrieval contract](https://docs.scenario.com/api/python/resources/assets/methods/retrieve)
names both fields. The shared adapter already preserves that response; no new
endpoint, raw fallback or service request is needed.

`result_metadata.texture_role` keeps only documented image texture categories:
base texture, albedo, normal, smoothness, roughness (3D map), metallic, height,
ambient occlusion and edge. These are semantic labels, not a complete PBR material
or a guarantee about channel layout, normal convention, seamlessness or color
space. MIME continues to select file handling and Blender validates actual bytes.
Missing, malformed or unknown optional metadata stays unclassified. A nonimage
file, including an archive with a texture label, never gets an image texture role.

The immutable manifest persists only this allowlisted role, not the raw metadata.
Known roles are rechecked when refreshing an unfinished asset's download URL;
a changed role stops before transfer. Old/unclassified manifests keep an unknown
role without blocking otherwise matching downloads or inferring a new role.
Receipt verification after restart does not contact Scenario to enrich metadata.

This is a prerequisite for explicit material application under #65/#68. It does
not assign materials or choose between multiple texture sets/variants. A later
material approval must select unambiguous assets and the intended mesh targets;
role preservation alone does not authorize a scene mutation.

## Declared HDR originals and 360 projection

SDK 2.2.0 documents that an HDRi skybox asset exposes a JPEG preview as `url` and
its OpenEXR file as `originalFileUrl`, labelled by `originalMimeType`. When an
image asset declares `image/x-exr` or `image/aces` there, the manifest records
`source: original`, that media type, an `.exr` local name and an unknown expected
size: originals publish no size metadata. The download fetches `originalFileUrl`
through the same storage policy, online check, redirect rules and atomic
publication, with a 128 MiB cap matching the World file limit instead of a size
match. The receipt digest then binds the saved bytes. Radiance (`.hdr`), mesh,
splat, audio and video originals keep the asset's own file and size.

A declared EXR original without a usable `originalFileUrl` fails before any
manifest is saved, so a retry can still choose the original; the JPEG preview is
never saved in its place. Refreshing an unfinished download reuses the saved
manifest's choice. A saved original whose declaration or destination later
disappears, changes to another format or loses its projection stops before
transfer with `download_failed`. Manifests saved before
[schema 10](JOB_STORAGE.md#schema-10-declared-originals-and-lane-defaults) keep
downloading the file they recorded, even if Scenario now declares an original.

`result_metadata.panorama_projection` reports `equirectangular` only when an image
asset's `metadata.type` is `skybox-base-360`, `upscale-skybox` or `skybox-hdri`.
Filenames, dimensions, models and `skybox-3d` never set it, and an unclassified
saved result is never relabelled later, as for texture roles. The projection and
EXR container are labels for later review; Blender must still decode the file,
the World preflight still checks its 2:1 shape and no dynamic range is measured.
Existing image and World actions accept `image/x-exr` but not yet `image/aces`;
an ACES-labelled original stays saved for inspection until World application
accepts that label. The offline and installed-ZIP tests use mocked storage
responses. A live HDRi run must still confirm `metadata.type`, the original's
host, size and color labelling before the release freezes this behavior. An
`originalFileUrl` host outside the storage policy makes each such job end in
`download_failed`, where earlier builds saved the JPEG preview; that needs a
reviewed storage policy change, never a host derived from another URL.

## Local Film media measurement

`ResultCommands.measure_media` selects exactly one asset from a current verified
saved result, then measures a private copy bound to its saved receipt. It rechecks
the saved record after inspection. This is a worker-side read with no metadata
refresh, download, repair or scene application. A missing or changed saved file
fails before a composition draft can be prepared; source bytes are preserved.
See [Film media limits](FILM_PLAN.md#verified-media-preparation), including the
optional installed ffprobe and metadata-only timing guarantee.

## Legacy OBJ and MTL byte counts

Asset ingestion can rewrite OBJ material-library names and MTL texture names
without updating `properties.size`. For exactly `model/obj` and `model/mtl`,
result recovery treats that size as advisory. It still checks the selected
scope, asset identity, success status, MIME type and any expected SHA-256.
Only a size change may differ from the saved manifest; other metadata checks
are unchanged. No API write, production backfill or generation is required.

The storage call explicitly enables this exception and requires a numeric
`Content-Length` within the configured byte cap. The complete streamed body
must match that header before atomic publication. Missing lengths, truncated
bodies, encoded responses, disallowed destinations, permission revocation,
timeouts and digest mismatches still fail. Other MIME types retain the exact
metadata-size requirement. This is a transport-completeness check, not a remote
cryptographic content attestation: the asset retrieval response supplies no
expected content digest. The computed SHA-256 protects subsequent local reads.

After verification, the store atomically saves the actual size in the local
OBJ/MTL manifest together with its immutable receipt. Existing failed jobs use
the same resume command, retain completed receipts and cannot resubmit. The
remote asset and stored bytes are unchanged. A crash between file publication
and receipt persistence still requires explicit interrupted-transfer recovery.

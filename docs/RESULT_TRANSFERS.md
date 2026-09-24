# Signed result downloads

`scenario.core.jobs.transfers` provides a synchronous, bpy-free storage primitive
for application-owned workers. It does not contact Scenario API endpoints;
those remain the shared SDK adapter's responsibility. SDK 2.1.0 returns storage
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
It has no Scenario credentials, cookie jar, netrc, proxy configuration, redirects,
automatic retry or URL logging. TLS verifies the hostname and bundled certificate
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
portable basenames, not paths. Staging uses a private temporary subdirectory and
0600 file; completed bytes are fsynced before atomic, non-overwriting hard-link
publication in the same filesystem. A filesystem without hard-link support fails
closed. Directory metadata durability after sudden power loss is not guaranteed.

An optional expected byte count and SHA256 are checked before publication. The
returned immutable `DownloadedResult(name, size, sha256)` contains no URL. The
[job store](JOB_STORAGE.md) can persist this receipt; `verify_download` rehashes it
before explicit recovery or Blender application. Verification accepts only a
regular nonsymlink file with the saved size/digest, enforces a byte cap and checks
for changes during reading. It does not repair files or make service calls.
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

## Integration still required

This change supplies the independently testable transport. It does not configure
production storage hosts, implement multipart uploads, wire UI/MCP commands or
import results into Blender. The [coordinator](JOB_COORDINATOR.md#result-retrieval-and-download-commands)
now orchestrates saved manifests/receipts and retrieves fresh URLs for explicit
download retries through the SDK. Interrupted-worker reconciliation remains
separate. Those commands must bind the trusted asset response and
receipt to the original account/project/job/target. Live signed-storage acceptance
and supported OS/filesystem behavior remain separate from offline contracts.

SDK identifier-validation failures in result metadata retrieval become sanitized
`ResultError` exceptions without changing the saved manifest or starting downloads.

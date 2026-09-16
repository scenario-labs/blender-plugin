# SDK runtime bundle

The extension bundles SDK **2.1.0** and its pinned runtime dependency closure.
[scenario/sdk-wheel-lock.json](../scenario/sdk-wheel-lock.json) records exact
artifact URLs, SHA-256 digests and license-member digests. Every selected wheel
also appears in [uv.lock](../uv.lock); an offline test rejects version, artifact
or dependency-closure drift. Developer-only packages are excluded.

## Targets

The manifest lists one universal bundle containing pure Python wheels and the
following `pydantic-core` binary wheels:

| Blender runtime | CPython ABI | Wheel platforms |
| --- | --- | --- |
| 5.0 | cp311 | Linux x64 (manylinux2014), Windows x64, macOS arm64, macOS x64 |
| 5.1 / 5.2 | cp313 | Linux x64 (manylinux2014), Windows x64, macOS arm64, macOS x64 |

These are package targets. Passing validation on a platform does not prove
native execution there. The native CI matrix exercises Linux x64 on Blender
5.0.1, 5.1.2 and 5.2.1; macOS/Windows execution evidence must be recorded
separately. No Linux arm64 or Windows arm64 binary is included.

Blender's extension manager selects and installs compatible wheels into its
extension `site-packages`. See the official
[wheel documentation](https://docs.blender.org/manual/en/5.2/advanced/extensions/python_wheels.html).
The extension does not run pip, extract binary dependencies itself, modify
`sys.path`, or depend on the developer's `.venv` at runtime.

## Build and verification

Use the canonical `make build`, `make install` and `make test-blender` commands.
The release workflow uses the same [tools/build.py](../tools/build.py) entry
point. [tools/wheel_bundle.py](../tools/wheel_bundle.py):

1. Checks manifest/lock agreement and retrieves missing artifacts into the
   ignored `.blender/wheels/` cache. Downloads use the pinned PyPI file URLs,
   never package names resolved to latest versions. This build preparation can
   use the network; native test processes remain under the offline socket guard.
   Transient transport failures and HTTP 408/429/500/502/503/504 receive at most
   three attempts, with 1- and 2-second delays. Other HTTP errors and hash
   mismatches are not retried.
2. Verifies SHA-256 on every cache reuse. Downloads use private temporary paths
   and atomic replacement; a missing/corrupt artifact cannot yield a partial ZIP.
3. Copies source to a fresh build staging directory and adds only the locked
   wheels. The checkout and Blender's normal user profile are unchanged.
   Staging lives in the run's temporary directory: successful cleanup removes
   it while retaining logs and the ZIP. Failed runs and `--keep-profile` native
   runs retain it for diagnosis.
4. Preserves all recorded license texts inside the wheels and copies them
   verbatim into `licenses/dependencies/` in the extension. Filenames include a
   content digest so duplicate notices can be shared without overwriting
   different notices.
5. Checks the candidate ZIP against its own lock and verifies every wheel and
   notice before Blender validation/installation. A supplied ZIP is not compared
   against a different checkout's SDK version.

Archive inspection and bundle verification reject more than 10,000 entries,
members larger than 64 MiB, or more than 256 MiB of declared expanded content
per archive before reading payloads. The same checks apply to nested wheels;
manifest/lock files and individual license notices are limited to 1 MiB.
Downloads and cached wheel reads are bounded at 64 MiB. These resource limits
are independent of the candidate's own lock and hashes.

`prepare_source(..., offline=True)` permits cache-only staging and fails on a
missing/corrupt wheel. The source manifest names staged wheel paths, so a direct
`blender --command extension build --source-dir scenario` is no longer the
supported build path. Use the shared tool to include the actual dependencies.

The installed-ZIP native suite imports every runtime dependency, verifies its
version and imported source bytes against the bundled wheel, and verifies the
loaded `pydantic-core` binary against the appropriate wheel. It exercises
Pydantic validation and the real SDK via `httpx.MockTransport`: online permission,
catalog reads, exact estimates, selected Bearer headers and single-attempt
failures. `tests.json` records the verified versions, Python version and native
wheel identity under `sdk_bundle`. These are offline runtime checks, not live
Scenario endpoint or OAuth-token acceptance.

The test runs in a fresh profile. Interactions with another extension's already
loaded dependency versions need separate acceptance; do not infer that behavior
from a successful isolated installation.

## Notices and upgrades

| Dependency | Pinned version | License |
| --- | --- | --- |
| scenario-sdk | 2.1.0 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |
| distro | 1.9.0 | Apache-2.0 |
| h11 | 0.16.0 | MIT |
| httpcore | 1.0.9 | BSD-3-Clause |
| httpx | 0.28.1 | BSD-3-Clause |
| idna | 3.19 | BSD-3-Clause |
| pydantic | 2.13.5 | MIT |
| pydantic-core | 2.46.5 | MIT |
| sniffio | 1.3.1 | MIT OR Apache-2.0 |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.4 | MIT |

License expressions summarize inspected wheel metadata; the included license
texts and original copyright notices remain authoritative.

For an upgrade, inspect the exact SDK release and run its dependency contracts
first. Update the uv pin/lock intentionally, select the complete runtime closure
and CPython/platform artifacts from that lock, then inspect each exact wheel's
metadata and notice files. Update `sdk-wheel-lock.json` and the manifest together;
retain original notices and review any changed license. Run the offline bundle
contracts and the actual native matrix. Do not mark a platform accepted because
a wheel filename exists or because a host Python import succeeds.

# Browser vendor software notices

These files cover the unmodified pinned browser bundles in `web/vendor/`. These are licensed software components, separate from the project-authored educational materials. Preserve this entire directory with the published site.

| Package | Version | License | Full notices |
| --- | --- | --- | --- |
| geotiff | 2.1.3 | MIT | [LICENSE](geotiff-2.1.3/LICENSE) |
| proj4 | 2.12.1 | MIT | [LICENSE.md](proj4-2.12.1/LICENSE.md); [EMBEDDED-NOTICES.txt](proj4-2.12.1/EMBEDDED-NOTICES.txt) |
| @babel/runtime | 7.15.4 | MIT | [LICENSE](babel-runtime-7.15.4/LICENSE) |
| regenerator-runtime | 0.13.9 | MIT | [LICENSE](regenerator-runtime-0.13.9/LICENSE); [EMBEDDED-NOTICES.txt](regenerator-runtime-0.13.9/EMBEDDED-NOTICES.txt) |
| @petamoriken/float16 | 3.4.7 | MIT | [LICENSE](petamoriken-float16-3.4.7/LICENSE) |
| xml-utils | 1.0.2 | CC0-1.0 | [LICENSE](xml-utils-1.0.2/LICENSE) |
| quick-lru | 6.1.1 | MIT | [license](quick-lru-6.1.1/license) |
| pako | 2.0.4 | (MIT AND Zlib) | [LICENSE](pako-2.0.4/LICENSE); [EMBEDDED-NOTICES.txt](pako-2.0.4/EMBEDDED-NOTICES.txt) |
| lerc | 3.0.0 | Apache-2.0 | [EMBEDDED-NOTICES.txt](lerc-3.0.0/EMBEDDED-NOTICES.txt); [Full Apache 2.0 license](Apache-2.0.txt) |
| zstddec | 0.1.0 | MIT AND BSD-3-Clause | [LICENSE](zstddec-0.1.0/LICENSE); [EMBEDDED-NOTICES.txt](zstddec-0.1.0/EMBEDDED-NOTICES.txt) |
| web-worker | 1.2.0 | Apache-2.0 | [LICENSE](web-worker-1.2.0/LICENSE); [EMBEDDED-NOTICES.txt](web-worker-1.2.0/EMBEDDED-NOTICES.txt) |
| mgrs | 1.0.0 | MIT | [license.md](mgrs-1.0.0/license.md) |
| wkt-parser | 1.3.3 | MIT | [LICENSE.md](wkt-parser-1.3.3/LICENSE.md) |

Proj4 also includes the Equal Earth projection, copyright 2018 Bernie Jenny, Monash University, Melbourne, Australia, under Apache-2.0. Its original notice is retained in `proj4-2.12.1/EMBEDDED-NOTICES.txt`; the complete Apache license is `Apache-2.0.txt`.

The LERC 3.0.0 npm tarball omits a standalone license file. Its original Esri copyright/contributor notices and explicit Apache-2.0 declaration are retained in `lerc-3.0.0/EMBEDDED-NOTICES.txt`, accompanied by the complete canonical Apache-2.0 license.

GeoTIFF dependency versions were obtained from the official v2.1.3 release lockfile and confirmed against every bundled dependency source in its official source map. Proj4 dependency versions follow its official v2.12.1 release lockfile. `parse-headers` is declared by GeoTIFF but does not occur in its browser bundle source map and is not redistributed here.

The source map annotation in the unchanged upstream GeoTIFF bundle is retained; the optional developer source map is not distributed. Runtime use does not require it.

See [manifest.json](manifest.json) for official npm tarball URLs, integrity values, SHA-256 hashes, exact release lockfile identities, retained license files and source-match evidence. No agency material or dataset is included in these vendor files.

Verification: both expected browser globals loaded in a Node.js v24.19.0 VM with browser capabilities stubbed; an original 2x2 TIFF encode/decode and WGS84/UTM18N round trip passed. This is not a full browser CORS, worker, or live-acquisition test.

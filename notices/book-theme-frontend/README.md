# Book theme frontend software notices

This directory accompanies the pinned MyST Book theme software used to publish the OneHealth Book. Preserve the entire directory in the published site. It contains legal notices, source facts, hashes, and license-reference texts; it does not import agency educational material.

## Pinned provenance

- Build artifacts: [`myst-templates/book-theme`](https://github.com/myst-templates/book-theme/tree/23f2df5493e23dfb1d9433c8aa64c87beb4232a3), commit `23f2df5493e23dfb1d9433c8aa64c87beb4232a3`.
- The artifact commit identifies source revision `1c3581d`; its canonical source is [`jupyter-book/myst-theme@1c3581dbd0fd268709656304f4ff7677c3f350a3`](https://github.com/jupyter-book/myst-theme/tree/1c3581dbd0fd268709656304f4ff7677c3f350a3).
- [Exact source Bun lockfile](source-bun.lock) and [original theme license](THEME-LICENSE) are retained. The artifact?s npm lockfile covers server dependencies and was not used as evidence of frontend versions.
- [manifest.json](manifest.json) records official npm tarball URLs, locked versions, npm integrity values, tarball and notice SHA-256 hashes, package-specific coverage, and the frontend source-bundle inventory.

## Publication exclusion

The root build deliberately excludes the unused optional payload `public/build/_shared/plotly-PQJCFEUX.js` from the published Book. The lazy renderer and CSS remain so normal page initialization continues to work. This Book uses static Matplotlib figures; the project-authored interactive visualizations do not use Plotly. The root build verifies the excluded payload is absent and checks the Book for failed requests.

The conservative source inventory includes `@mapbox/jsonlint-lines-primitives@2.0.2`, whose package provides no verified permission grant. Its original npm metadata, source identity, and exclusion decision are recorded as facts only. No README or implementation text from that unlicensed package is copied here. Its later `2.0.3` release has an MIT license, but that fact is not treated as permission for locked `2.0.2`. The ambiguous legacy parser closure is outside the published runtime scope through the optional-payload exclusion.

## Notice coverage

- **415** distinct locked production package/version pairs were collected from the dependency closure of the **35** components named by preserved bundled-license headers. All npm integrity checks passed.
- **390** packages have original npm legal files, full legal grants extracted verbatim from package source/README, or exact upstream license files at the npm git revision or package release tag.
- **24** legacy packages explicitly declare an SPDX license but omit its standalone text. Their original legal declarations and author credits are retained alongside clearly labeled [full standard-license references](standard-license-references/). These references are not misrepresented as package-shipped copyright notices, and missing copyright statements were not invented.
- **1** permission-unverified legacy package is handled through the publication exclusion above.
- **21** original bundled legal-header blocks/files are retained under `embedded/`, including nested Plotly, JSPM, DOCX, React, Mermaid, and Lumino notices. Their preservation does not imply that excluded Plotly code is distributed.

This is a conservative source-lock notice inventory, not a byte-exact bill of materials for every tree-shaken frontend chunk. It includes some packages not proven to be present in the browser payload and excludes dev, peer-only, optional-only, and type-definition dependencies. Components without retained headers may require separate identification; this index does not claim that a declared dependency is necessarily shipped. The exact scope and limits are recorded in the manifest.

## Components identified by bundled headers

The following links lead to the full notice files retained for each identified component. Multiple locked versions are preserved where the source lock contains more than one instance.

| Component | Locked version(s) | Notice directory |
| --- | --- | --- |
| @babel/runtime | 7.29.7 | [7.29.7](packages/babel__runtime@7.29.7/source.json) |
| @jspm/core | 2.1.0 | [2.1.0](packages/jspm__core@2.1.0/source.json) |
| @lumino/commands | 1.21.1, 2.3.3 | [1.21.1](packages/lumino__commands@1.21.1/source.json); [2.3.3](packages/lumino__commands@2.3.3/source.json) |
| @lumino/disposable | 1.10.4, 2.1.5 | [1.10.4](packages/lumino__disposable@1.10.4/source.json); [2.1.5](packages/lumino__disposable@2.1.5/source.json) |
| @lumino/messaging | 1.10.3, 2.0.4 | [1.10.3](packages/lumino__messaging@1.10.3/source.json); [2.0.4](packages/lumino__messaging@2.0.4/source.json) |
| @lumino/virtualdom | 1.14.3, 2.0.4 | [1.14.3](packages/lumino__virtualdom@1.14.3/source.json); [2.0.4](packages/lumino__virtualdom@2.0.4/source.json) |
| @lumino/widgets | 1.37.2, 2.8.0 | [1.37.2](packages/lumino__widgets@1.37.2/source.json); [2.8.0](packages/lumino__widgets@2.8.0/source.json) |
| @mermaid-js/parser | 1.1.1 | [1.1.1](packages/mermaid-js__parser@1.1.1/source.json) |
| @remix-run/react | 1.17.1 | [1.17.1](packages/remix-run__react@1.17.1/source.json) |
| @remix-run/router | 1.6.3 | [1.6.3](packages/remix-run__router@1.6.3/source.json) |
| classnames | 2.5.1 | [2.5.1](packages/classnames@2.5.1/source.json) |
| cytoscape | 3.34.0 | [3.34.0](packages/cytoscape@3.34.0/source.json) |
| docx | 7.8.2 | [7.8.2](packages/docx@7.8.2/source.json) |
| dompurify | 3.4.8 | [3.4.8](packages/dompurify@3.4.8/source.json) |
| he | 1.2.0 | [1.2.0](packages/he@1.2.0/source.json) |
| is-buffer | 2.0.5 | [2.0.5](packages/is-buffer@2.0.5/source.json) |
| is-plain-object | 5.0.0 | [5.0.0](packages/is-plain-object@5.0.0/source.json) |
| jquery | 3.7.1 | [3.7.1](packages/jquery@3.7.1/source.json) |
| js-yaml | 3.14.2, 4.2.0 | [3.14.2](packages/js-yaml@3.14.2/source.json); [4.2.0](packages/js-yaml@4.2.0/source.json) |
| lodash-es | 4.18.1 | [4.18.1](packages/lodash-es@4.18.1/source.json) |
| markdown-it-myst | 1.0.18 | [1.0.18](packages/markdown-it-myst@1.0.18/source.json) |
| mermaid | 11.15.0 | [11.15.0](packages/mermaid@11.15.0/source.json) |
| plotly.js | 2.35.3 | [2.35.3](packages/plotly.js@2.35.3/source.json) |
| prismjs | 1.27.0, 1.30.0 | [1.27.0](packages/prismjs@1.27.0/source.json); [1.30.0](packages/prismjs@1.30.0/source.json) |
| react | 19.2.7 | [19.2.7](packages/react@19.2.7/source.json) |
| react-dom | 19.2.7 | [19.2.7](packages/react-dom@19.2.7/source.json) |
| react-highlight-words | 0.20.0 | [0.20.0](packages/react-highlight-words@0.20.0/source.json) |
| react-is | 16.13.1, 17.0.2, 18.3.1 | [16.13.1](packages/react-is@16.13.1/source.json); [17.0.2](packages/react-is@17.0.2/source.json); [18.3.1](packages/react-is@18.3.1/source.json) |
| react-router | 6.13.0 | [6.13.0](packages/react-router@6.13.0/source.json) |
| react-router-dom | 6.13.0 | [6.13.0](packages/react-router-dom@6.13.0/source.json) |
| sax | 1.6.0 | [1.6.0](packages/sax@1.6.0/source.json) |
| scheduler | 0.27.0 | [0.27.0](packages/scheduler@0.27.0/source.json) |
| tabbable | 5.3.3 | [5.3.3](packages/tabbable@5.3.3/source.json) |
| tslib | 1.14.1, 2.8.1 | [1.14.1](packages/tslib@1.14.1/source.json); [2.8.1](packages/tslib@2.8.1/source.json) |
| use-sync-external-store | 1.6.0 | [1.6.0](packages/use-sync-external-store@1.6.0/source.json) |

## Legal-file interpretation

Each package?s `source.json` identifies its license, creators where supplied, provenance, retained legal files, and evidence limitations. Original `LICENSE`, `NOTICE`, `COPYRIGHT`, and other legal files were copied unchanged from their recorded source. Complete compound and alternative licenses are retained when supplied. This collection does not replace those terms or relicense third-party software.

Supplementary reference texts for explicitly declared licenses are taken unchanged from the SPDX License List Data project and distinguished from original package legal files. No inferred successor license is used to declare the excluded legacy parser licensed.

## Validation

All 472 recorded legal/provenance hash entries were verified. No npm download or integrity errors occurred. The pinned theme, application code, and build code were not modified by this notice audit. Final asset exclusion and browser verification are performed by the root build.

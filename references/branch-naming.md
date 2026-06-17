# Branch Naming Conventions

## Upstream (Intel)

All repos use the same pattern:
```
releases/YEAR/MINOR
```
Example: `releases/2026/2`

## Midstream (OpenDataHub)

### openvino_model_server
```
YEAR.MINOR-release
```
Example: `2026.2-release`

### openvino, openvino.genai, openvino_tokenizers
```
releases/YEAR/MINOR
```
Example: `releases/2026/2` (same as upstream)

### Special branches
- `stable` — always-latest synced release for ODH consumption
- `patches` — branch containing patch files (not code)

## Downstream (RHDS)

```
rhoai-RHOAI_VERSION
```
Example: `rhoai-2.19`

## PR Branch Naming (Your Fork)

| Purpose | Pattern |
|---------|---------|
| Mirror creation | (API-created, no PR needed) |
| OWNERS push | `add-owners-YEAR.MINOR` |
| Patches | `apply-patches-YEAR.MINOR` |
| Stable sync | `sync-stable-YEAR.MINOR` |
| RHOAI sync | `sync-rhoai-RHOAI_VERSION` |
| Cherry-pick | `cp-SHA8-to-BRANCH` |
| CVE rebuild | `cve-rebuild-BRANCH-DATE` |

## Version Format

Always `YEAR.MINOR` (e.g., `2026.2`). No patch level — OVMS uses major.minor only.

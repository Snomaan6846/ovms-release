# OVMS Release Workflow

## Overview

The OVMS release process syncs upstream Intel releases of OpenVINO Model Server into the Red Hat OpenDataHub and RHOAI ecosystems. It follows an 8-phase linear pipeline with human-in-loop checkpoints.

## Phase Summary

| Phase | Name | Action | Human Gate? |
|-------|------|--------|-------------|
| 0 | Pre-flight | Intelligence gathering, prerequisites | No |
| 1 | Mirror | Create release branches in 4 ODH repos | Yes (confirm) |
| 2 | OWNERS | Push OWNERS file via PR | Yes (PR merge) |
| 3 | ARG Review | Diff Dockerfile ARGs between versions | Yes (review) |
| 4 | CI Config | Generate openshift/release prow config | Yes (PR merge) |
| 5 | Patches | Apply patches to release branch | Yes (PR merge) |
| 5.5 | Image Check | Verify ODH image build passes | Yes (wait for CI) |
| 5.7 | E2E (Release) | Optional E2E validation | Yes (opt-in) |
| 6 | Sync Stable | Tree transplant merge to stable | Yes (PR merge) |
| 6.5 | E2E (Stable) | Optional E2E validation | Yes (opt-in) |
| 7 | Sync RHOAI | Sync stable to rhoai branch | Yes (PR merge) |
| 8 | RHDS Verify | Confirm downstream sync + image | Yes (verify) |

## Key Invariants

1. **PR-Only** — No direct pushes to midstream/downstream
2. **State Tracked** — All phases persist to `release-state.yaml`
3. **Idempotent** — Each phase can be re-run safely
4. **Protected Files** — `.tekton/` and `.github/workflows/` preserved during tree transplant
5. **Mirror Points** — Upstream SHAs tagged for auditability

## Repositories Involved

### Upstream (Intel)
- `openvinotoolkit/model_server`
- `openvinotoolkit/openvino`
- `openvinotoolkit/openvino.genai`
- `openvinotoolkit/openvino_tokenizers`

### Midstream (ODH)
- `opendatahub-io/openvino_model_server`
- `opendatahub-io/openvino`
- `opendatahub-io/openvino.genai`
- `opendatahub-io/openvino_tokenizers`

### Downstream (RHDS)
- `red-hat-data-services/openvino_model_server`

## Branching Convention

See [branch-naming.md](./branch-naming.md) for details.

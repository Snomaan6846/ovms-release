# Troubleshooting

## Patch Application Failures

**Symptom**: `apply-patches.sh` reports `FAILED` for one or more patches.

**Cause**: Upstream changed the files that patches target (context mismatch).

**Fix**:
1. Run `/ovms-release-patch <version>` to diagnose
2. Manually recreate the patch:
   ```bash
   git switch midstream/<release-branch>
   # Make the desired change
   git diff HEAD -- <file> > /tmp/regenerated-<patch-name>
   ```
3. Push regenerated patch to the `patches` branch

---

## Tree Transplant Conflicts

**Symptom**: `tree-transplant.sh` exits with code 2 (untracked files).

**Fix**: Run with `--confirm-clean` to remove the untracked files, OR inspect them manually.

---

## gh auth issues

**Symptom**: `gh api` returns 401/403.

**Fix**: Re-authenticate:
```bash
gh auth login
gh auth status
```

---

## Fork Divergence Warning

**Symptom**: Pre-flight reports "Fork is N commits behind midstream".

**Fix**:
```bash
git fetch midstream
git push origin midstream/main:main
```

---

## E2E Test Failures

**Symptom**: `run-e2e-tests.sh` fails.

**Common causes**:
1. Cluster not logged in (`oc login`)
2. AWS credentials not exported
3. S3 endpoint misconfigured
4. OVMS image not yet available in registry

**Debug**:
```bash
oc whoami --show-server           # Cluster check
skopeo inspect docker://<image>   # Image check
```

---

## State File Corruption

**Symptom**: CLI reports "cannot parse state file".

**Fix**: State files are in `~/.ovms-release/openvino_model_server/<version>/`. Backup exists as `.yaml.bak` if backup was enabled. Delete and re-init if needed:
```bash
rm ~/.ovms-release/openvino_model_server/<version>/release-state.yaml
ovms-release preflight <version>
```

---

## Jira Integration Issues

**Symptom**: "Jira: not configured" in pre-flight.

**Fix**: Tiered options:
1. Install and authenticate `acli`: `acli jira auth`
2. Set environment variables: `JIRA_API_TOKEN`, `JIRA_USER_EMAIL`
3. Configure Cursor MCP Jira plugin

The release proceeds without Jira (state-file only tracking).

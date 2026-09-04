## Summary

Describe the focused change and why it is needed.

## Safety and reproducibility

- [ ] No credentials, private configurations, proprietary images, captures, or malware artifacts are included.
- [ ] Host-specific inputs remain parameterized.
- [ ] Security-boundary implications are documented.
- [ ] Manifests, SBOMs, and user documentation are updated where applicable.

## Verification

List the exact commands run and their results.

- [ ] `make test`
- [ ] `make phase4-verify` when containers, packages, SBOMs, or runtime policy change
- [ ] `make templates` and `make smoke-test` when GNS3 behavior changes
- [ ] `git diff --check`

## Remaining limitations

State anything not tested, not reproduced, or intentionally outside scope.

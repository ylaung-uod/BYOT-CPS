# Security policy

## Supported versions

Security fixes are developed for the latest tagged BYOT-CPS release. Older
releases may be useful for reproducing historical labs but do not receive
security backports. Confirm the latest tag before reporting or testing a defect.

## Reporting a vulnerability

Use the repository host's private vulnerability-reporting feature when it is
available. Include:

- the affected release or commit;
- the component and prerequisite configuration;
- minimal reproduction steps;
- impact within the documented lab boundary; and
- a proposed remediation, if known.

Do not file sensitive details publicly. Do not attach credentials, private
pfSense backups, keys, proprietary installer media, VM disks, packet captures,
or malware samples. If private vulnerability reporting is unavailable, open a
minimal public issue that contains no sensitive details and asks maintainers to
establish a private contact channel.

Maintainers provide best-effort acknowledgment and triage. There is no guaranteed
response-time or remediation SLA. A report may be redirected when it concerns a
third-party dependency rather than BYOT-CPS code.

## Security scope

Supported reports include:

- committed secrets or unsafe handling of private inputs;
- path traversal, command injection, or unsafe file replacement;
- topology behavior that unexpectedly exposes host or production interfaces;
- template reconciliation that silently retains stale security-relevant state;
- cleanup failures that leave temporary GNS3 projects running; and
- documentation that causes a reasonable operator to cross the stated safety
  boundary.

The project does not support operational malware deployment, exploit delivery,
credential theft, persistence, evasion, unauthorized access, or attacks against
third-party systems. Requests for those activities will be declined.

## Public disclosure

Coordinate public disclosure with maintainers after a fix or mitigation is
available. Preserve third-party terms and avoid publishing secrets or controlled
artifacts in advisories, commits, tests, or reproductions.

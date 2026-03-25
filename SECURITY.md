# Security Policy

## Supported Versions

Only the most recent release of governance-os receives security fixes.

## Reporting a Vulnerability

Please do not report security vulnerabilities through the public issue tracker.

Instead, open a GitHub Security Advisory on the repository, or email the maintainer directly. Include:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested mitigations

You can expect an acknowledgement within 5 business days and a resolution timeline within 30 days for confirmed vulnerabilities.

## Scope

governance-os is a local CLI tool that reads markdown files from the filesystem. It does not make network requests, store credentials, or run arbitrary code from contracts. The primary attack surface is malformed input files; path traversal in contract `Outputs:` fields is explicitly detected and reported.

# Scanner Package (`packages/scanner`)

## Overview

The `scanner` package represents the isolated cryptographic discovery and network inspection module of Quantum Flow Technologies.

## Submodules
- `safety/`: Target verification, SSRF defense, RFC 1918 blocklists, DNS rebinding mitigation (to be implemented in Sprint 3).
- `tls/`: Low-level TLS socket handshake, X.509 certificate extraction, and ASN.1 metadata parsing (Sprint 3).
- `tests/`: Synthetic fixtures, ground-truth test lab cases, and safety abuse suites.

*Note: In Sprint 0, this package exists as an isolated architectural package boundary.*


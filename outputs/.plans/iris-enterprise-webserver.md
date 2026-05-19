# Research Plan: IRIS Enterprise Container Atelier REST / WebServer

## Questions
1. Is WebServer=0 in enterprise IRIS container images intentional by design?
2. Is there any supported way to enable the private web server in enterprise containers (CPF, env var, image variant)?
3. What is ISC's officially recommended developer tooling setup for enterprise containers?
4. Does iris-dev's recommendation (use webgateway OR community image) match ISC official guidance?
5. Is the `intersystems/webgateway` container the canonical solution ISC recommends?

## Strategy
- R1: ISC official docs (docs.intersystems.com, container docs, developer tools docs)
- R2: ISC Confluence + JIRA internal search
- R3: Web (Perplexity, GitHub, community forums, Docker Hub)
- R4: Direct container inspection evidence (already have from empirical testing)

## Acceptance Criteria
- [ ] ≥2 independent sources confirming intentional design decision
- [ ] Official ISC documentation on webgateway compose pattern found
- [ ] Any alternative CPF/env approaches identified or ruled out
- [ ] iris-dev recommendation validated or corrected

## Task Ledger
| ID | Owner | Task | Status | Output |
|---|---|---|---|---|
| T1 | R1 | ISC official docs search | todo | iris-enterprise-webserver-docs.md |
| T2 | R2 | Confluence + JIRA search | todo | iris-enterprise-webserver-internal.md |
| T3 | R3 | Web + community search via Perplexity | todo | iris-enterprise-webserver-web.md |

## Verification Log
| Item | Method | Status | Evidence |
|---|---|---|---|
| WebServer=0 in enterprise CPF | Direct container inspection | VERIFIED | iris:2026.1, irishealth:2026.1 |
| No httpd binary in enterprise | Direct container inspection | VERIFIED | /usr/irissys/httpd/ absent |
| CPF merge WebServer=1 crashes | Direct test | VERIFIED | NOTOPEN>WebServer+38^STU1 |

## Decision Log
- Empirical evidence is strong; need official confirmation this is by design

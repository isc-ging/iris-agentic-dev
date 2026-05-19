# IRIS Enterprise Docker Containers: Private Web Server / Atelier REST Endpoint

## Research Summary

The absence of a private web server (PWS) in enterprise IRIS Docker containers is a
**deliberate, documented, security-driven design decision** formalized in JIRA DPP-1192
and shipped starting with IRIS 2023.2. It is not a bug or oversight. The `/api/atelier/`
REST endpoint is inaccessible in enterprise containers because no httpd process runs and
`WebServer=0` is explicitly set in `iris.cpf`. The canonical workaround is to pair the
IRIS container with a separate `webgateway` container via docker-compose.

---

## Confluence Sources

### 1. Remove Apache Web Server - FAQ (Internal)
**URL:** https://usconfluence.iscinternal.com/pages/viewpage.action?pageId=561013409  
**Space:** DPP (Product Planning)

Key quotes from snippet:
- "Starting with IRIS 2023.2, **the enterprise edition versions of the IRIS product family will no longer install the private web server**. Cachè and Ensemble [are] not affected."
- Rationale: customers should install their own web server vs. using the private web server. Benefits: smaller installers, streamlined container images, more secure/up-to-date web server within their control.
- **Exceptions explicitly listed**: evaluation kits and community kits retain the PWS (traffic locked down). Enterprise kits/containers do not.
- Updated Feb 1, 2023: "Kits for Windows..." — implies the policy applied to containers as well as native kits.

---

### 2. IRIS 2023.2.0 - DPP-1192 (Discontinue installing a Private Web Server (PWS) for general distributions)
**URL:** https://usconfluence.iscinternal.com/pages/viewpage.action?pageId=597287097  
**Space:** QD (Quality & Development)

The primary QD test tracking page for DPP-1192 as shipped in IRIS 2023.2. References both the
JIRA ticket and the test plan below. Confirms this was a formal product release feature.

---

### 3. Test Plan for Removal of Private Apache Web Server (PWS): DPP-1192
**URL:** https://usconfluence.iscinternal.com/pages/viewpage.action?pageId=597726613  
**Space:** QD

Snippet: "There will be **exceptions, such as evaluation and community kits** (where traffic
will be locked down) [that] can continue to use the private web server. From the internal FAQ..."

Confirms the deliberate exception policy: community/eval = PWS present; enterprise = no PWS.

---

### 4. Removal of Private Web Server (TAE internal page)
**URL:** https://usconfluence.iscinternal.com/pages/viewpage.action?pageId=597669824  
**Space:** TAE (Test Automation Engineering)

Context: "IRIS ships with a private web server that talks to the web gateway. **This is
getting removed** because [it is a security concern / similar to when the SAMPLES database
got removed from IRIS]."

This page documents TAE's internal adaptation work and references DPP-1192 as the driving ticket.

---

### 5. Resources and Notes for Testing Removal of Private Apache Web Server
**URL:** https://usconfluence.iscinternal.com/pages/viewpage.action?pageId=638602286  
**Space:** QD

References the "NoPWS Project FAQ (customer facing)" and a Developer Community post titled
"Discontinue Apache web server installations (aka Private Web Server (PWS))". Apache web
server config with Web Gateway notes included.

---

### 6. Running IRIS & a Web Gateway with Docker
**URL:** https://usconfluence.iscinternal.com/pages/viewpage.action?pageId=767163902  
**Space:** ~aryanput (personal)

Documents how to run IRIS 2024.1 with a webgateway via docker-compose as the replacement
for the removed PWS. This is the recommended developer workaround pattern.

---

### 7. IRIS Dev Container
**URL:** https://usconfluence.iscinternal.com/pages/viewpage.action?pageId=890020031  
**Space:** ~jyin (personal)

"A container image specifically targeting the IRIS application dev workflow for a single
IRIS instance. This repository provides a Docker Compose setup for running an InterSystems
IRIS container for development purposes... pre-configuring the webgateway."

Explicitly uses webgateway + docker-compose as the dev setup pattern post-NoPWS.

---

### 8. HealthShare with Independent Web Server (Web Gateway)
**URL:** https://usconfluence.iscinternal.com/pages/viewpage.action?pageId=858354330  
**Space:** UCRO

"In this setup, there is a single Web Gateway in a container on your local machine and
any IRIS development instances on your machine are served by the single web gateway using
different web-server prefixes."

Practical internal guidance for the docker-compose + webgateway pattern.

---

### 9. IRIS 2024.1.0 - DPP-1593 (Adding Apache/IIS web server installation to Health Connect Phase 2)
**URL:** https://usconfluence.iscinternal.com/pages/viewpage.action?pageId=711961676  
**Space:** QD

"PHASE 1. IRIS 2023.2.0 - DPP-1192 (Discontinue installing a Private Web Server (PWS)
for general distributions)"

Confirms the phased rollout: PWS removed from IRIS enterprise in 2023.2, and subsequent
work (DPP-1593) re-added it selectively for Health Connect in some editions.

---

### 10. POC: Containerized HealthShare Development Environment
**URL:** https://usconfluence.iscinternal.com/pages/viewpage.action?pageId=1101714866  
**Space:** UCRO

"After appropriate setup, developer gets a container stack containing the web server, web
gateway, and the instance, properly configured."

Describes the docker-compose stack (IRIS + webgateway) as the dev environment solution
replacing the removed PWS.

---

### 11. DOCS-13488: Detail steps required to set up HTTPS in Web Gateway Container
**JIRA:** https://usjira.iscinternal.com/browse/DOCS-13488  
**Space:** (referenced as Confluence source via JIRA)

"In WRC 989204, AtScale is trying to set up a Web Gateway Container with InterSystems IRIS
2024.1, **since the Private Web Server is no longer available**."

Customer-facing confirmation that the PWS removal is the reason tooling must shift to the
Web Gateway Container.

---

## JIRA Tickets

### 1. DPP-1192 — Discontinue installing a Web Server for general distributions Phase 1
**URL:** https://usjira.iscinternal.com/browse/DPP-1192  
**Status:** Closed  
**Reporter:** Raj Singh  
**Assignee:** Alexander Enis  
**Created:** 2021-08-26 | **Updated:** 2024-05-23

**Description (key excerpt):**
> "While we might continue to ship one for special use case kits (e.g. Evaluation), we
> generally should not just install a web server on every machine we install InterSystems
> IRIS on. Typical organization will have a Web Server, and that is the one that should be
> used... Just installing a Web Server is a security concern, as it could be unknown to the
> user and organization, and therefore does not receive the required isolation protections."

**This is the root design decision ticket.** Shipped in IRIS 2023.2.

---

### 2. DPP-1627 — Discontinue installing the Private Web Server
**URL:** https://usjira.iscinternal.com/browse/DPP-1627  
**Status:** Inactive (Done)  
**Reporter:** Fabiano Sanches  
**Created:** 2023-08-17 | **Updated:** 2025-04-29

A follow-on ticket in the same DPP project continuing the PWS removal work.

---

### 3. DPQD-2390 — CART-322: Lockeddown IRIS Container Test
**URL:** https://usjira.iscinternal.com/browse/DPQD-2390  
**Status:** Closed  
**Reporter/Assignee:** Priya Simhadri  
**Created:** 2026-03-31 | **Updated:** 2026-04-06

**This is the most direct evidence that WebServer=0 is enforced in enterprise containers.**

Description (verbatim from test spec):
> "6. **Web Server Disabled:**  
> /CART-322/UnitTests/LockeddownTest.cls::TestProcess  
> Verifies no httpd processes are running  
> **Verifies WebServer is set to 0 in iris.cpf (via Config.Startup)**"

The CART-322 test suite is an automated IRIS QD test that runs against "lockeddown" (enterprise
distribution) containers. Web server being disabled (`WebServer=0` in `iris.cpf`) is
a **required, tested invariant** of the locked-down container configuration.

**This directly answers the root question**: the Atelier REST endpoint is unavailable in
enterprise containers because `WebServer=0` is explicitly required and tested as part of
the enterprise container security posture.

---

### 4. DP-423020 — IAM is unable to obtain license from an IRIS 2023.2 NOPWS instance (label: NoPWS)
**URL:** https://usjira.iscinternal.com/browse/DP-423020  
**Status:** Closed  
**Labels:** NoPWS  
**Created:** 2023-05-19

This ticket documents that IAM's test script routes through `/api/atelier/` to verify
connectivity, and that **with a NoPWS 2023.2 instance, IAM could successfully reach
`/api/atelier/`** once a separate Apache webserver was configured on port 80.

Key implication: `/api/atelier/` works fine in no-PWS setups when a web gateway is configured.
The endpoint itself is not gone — it just requires an external web server/gateway to front it.

Build string in ticket: `IRIS for UNIX (Red Hat Enterprise Linux 9 for x86-64) 2023.2.0NOPWS`
(note the `NOPWS` in the build identifier — ISC uses this suffix in kit builds).

---

### 5. DP-441101 — Distill review results into specific requirements for installer
**URL:** https://usjira.iscinternal.com/browse/DP-441101  
**Status:** Closed  
**Created:** 2025-05-05

Contains a requirements table with this item:
> "CSPpwd | Remove CSPpwd from all IRIS artifacts that **do not include a private web
> server** (everything except IRIS Community Edition container image)"

Confirms that community CE containers are explicitly the **exception** that retains PWS;
all other containers (enterprise) do not.

---

### 6. DOCS-13488 — Detail steps required to set up HTTPS in Web Gateway Container
**URL:** https://usjira.iscinternal.com/browse/DOCS-13488  
**Status:** Done (Highest priority)  
**Reporter:** Patrick Dunn  
**Created:** 2024-07-12 | **Updated:** 2025-01-13

Customer (AtScale) unable to set up Web Gateway Container with HTTPS after PWS removal.
"Since the Private Web Server is no longer available" — confirms the workaround pattern
is the webgateway container, and ISC docs were enhanced to cover the HTTPS setup steps.

---

## Key Answers to Research Questions

**Q: Is this a known/documented design decision?**  
Yes. DPP-1192 (filed 2021, shipped 2023.2) is the formal product decision. Extensively
documented in Confluence DPP, QD, and TAE spaces. Security rationale: unknown Apache
instances on production systems are a security risk.

**Q: Are there internal tickets about this issue?**  
Yes. DPP-1192 is the primary ticket. DPQD-2390 verifies it via automated CART tests.
DP-423020 (label: NoPWS) documents IAM integration testing against NoPWS instances.
DOCS-13488 documents downstream impact on tooling.

**Q: Is there official guidance for developer tools with enterprise containers?**  
Yes. The official pattern is a docker-compose stack with a separate `webgateway` container
(see Confluence pages 767163902, 890020031, 1101714866, 858354330). The webgateway container
fronts the IRIS superserver and serves `/api/atelier/`, `/csp/`, and Management Portal.

**Q: Any workarounds documented internally?**  
- Primary workaround: docker-compose with `containers.intersystems.com/intersystems/webgateway:<version>`
  as a sidecar. CSP.ini configured to point at IRIS superserver port 1972.
- For developer tools (VSCode ObjectScript extension, Studio): connect via the webgateway
  container's exposed port (typically 52773 or a remapped port).
- Community Edition containers retain the PWS and can be used for local development without
  a separate webgateway.

**Q: Does this affect the Atelier REST endpoint specifically?**  
Yes. `/api/atelier/` is served through the CSP/web gateway layer. With `WebServer=0` and
no httpd process running, there is nothing to serve HTTP requests. Configuring a webgateway
container restores `/api/atelier/` access (confirmed by DP-423020 testing).

# IRIS Enterprise Container: Private Web Server / Atelier REST — Research Brief

**Date:** 2026-05-03  
**Question:** Is it true that enterprise IRIS Docker containers do NOT include the Atelier REST API endpoint / private web server by default? Is this by design? What is the official workaround?

---

## Executive Summary

**Yes, it is true, it is by design, and it is documented.** Starting with IRIS 2023.2, InterSystems formally removed the private web server (PWS) — a bundled Apache httpd — from all enterprise IRIS product distributions, including containers. The decision (JIRA DPP-1192, filed 2021, shipped 2023.2) was security-motivated: an unknown Apache process running on enterprise/production systems cannot be properly patched and isolated. The `WebServer=0` setting in `iris.cpf` is an enforced, automatically-tested invariant for enterprise containers (JIRA DPQD-2390). Community Edition images (`intersystems/iris-community`, `intersystems/irishealth-community`) are an explicit exception — they retain the PWS on port 52773 for developer convenience.

The `/api/atelier/` Atelier REST endpoint is **not gone** — it is still served by IRIS. It simply requires an external web server to front it. The official ISC-provided solution is to pair the enterprise container with a separate `intersystems/webgateway` (or `webgateway-nginx`, or `webgateway-lockeddown`) sidecar container in docker-compose. **iris-dev's current recommendations are correct and match ISC official guidance exactly.**

---

## 1. The Design Decision: DPP-1192

The removal was a formal product decision, not an accident. JIRA **DPP-1192** ("Discontinue installing a Web Server for general distributions") was filed in August 2021 by Raj Singh and shipped in IRIS 2023.2:

> "While we might continue to ship one for special use case kits (e.g. Evaluation), we generally should not just install a web server on every machine we install InterSystems IRIS on. Typical organization will have a Web Server, and that is the one that should be used... Just installing a Web Server is a security concern, as it could be unknown to the user and organization, and therefore does not receive the required isolation protections."

The public documentation confirms this reasoning [Source: docs.intersystems.com GCGI_private_web]:

> "The PWS is not suitable for serving web applications in production, or for use outside of a secured environment. Beginning with version 2023.2, InterSystems stopped installing a PWS with new installations of InterSystems IRIS data platform products (except Community Editions and other evaluation distributions)."

Prior to 2023.2, the PWS was included in all distributions including containers [Source: docs.intersystems.com ADOCK]:

> "In versions of InterSystems IRIS prior to 2023.2, the Web Gateway and a preconfigured private web server were installed with InterSystems IRIS by default, **including in containers**. For this reason, if you are upgrading from a pre-2023.2 version to the current version, you must update all deployment scripts and tools to reflect the new deployment options described by this document."

---

## 2. Enterprise vs. Community: The Enforced Split

The split is architectural and enforced by automated tests, not just a default setting:

**Enterprise containers** (`intersystems/iris`, `intersystems/irishealth`, all versions ≥ 2023.2):
- `iris.cpf` `[Startup]` section: `WebServer=0`
- No `/usr/irissys/httpd/` directory
- No CSP.ini, no CSP.so
- Port 52773 not served — nothing listens there
- JIRA DPQD-2390 (CART-322 automated test) **verifies WebServer=0 as a required invariant**: "Verifies no httpd processes are running. Verifies WebServer is set to 0 in iris.cpf (via Config.Startup)."

**Community Edition containers** (`intersystems/iris-community`, `intersystems/irishealth-community`):
- `iris.cpf` `[Startup]` section: `WebServer=1`
- `/usr/irissys/httpd/bin/httpd` present (Apache binary)
- CSP.ini, CSP.so present
- Port 52773 actively served
- Explicitly documented as an exception "for the convenience of those testing and evaluating InterSystems IRIS" [Source: ADOCK]

| Property | Enterprise | Community Edition |
|----------|-----------|------------------|
| PWS included | ❌ No (since 2023.2) | ✅ Yes |
| Port 52773 served | ❌ No | ✅ Yes |
| WebServer CPF default | 0 (enforced) | 1 (enabled) |
| `/usr/irissys/httpd/` exists | ❌ No | ✅ Yes |
| Atelier REST without sidecar | ❌ Not accessible | ✅ Accessible |

---

## 3. Why `WebServer=1` via CPF Merge Crashes Enterprise Containers

Our empirical observation (the container crashes with `<NOTOPEN>WebServer+38^STU1`) is explained by the architecture: the CPF parameter `WebServer=1` instructs IRIS to start an httpd process at startup — but the httpd binary, CSP.ini, and the entire `/usr/irissys/httpd/` directory are **not installed** in enterprise images. IRIS fails trying to launch a binary that does not exist.

The CPF `WebServer=1` parameter is a recovery option for upgrading pre-2023.2 installations (where the httpd files exist but were disabled). It is not a mechanism to install the web server. The documentation notes [Source: GCGI_private_web]: "If you must re-enable an instance's PWS for any reason, you can do so by resetting the WebServer parameter to 1 in the CPF file and then restarting the instance." — but this only works when the httpd binary is actually present, which it never is in enterprise containers.

**There is no IRIS_ENABLE_WEBSERVER environment variable or other flag.** The separation is architectural, not configurable.

---

## 4. The Official Solution: Web Gateway Container

The ISC-official replacement is a docker-compose stack pairing the IRIS enterprise container with one of three `webgateway` images:

| Image | Web Server | Port | Use Case |
|-------|-----------|------|----------|
| `intersystems/webgateway` | Apache httpd | 80 | Standard dev/prod |
| `intersystems/webgateway-nginx` | Nginx | 80 | Nginx preference |
| `intersystems/webgateway-lockeddown` | Apache (hardened, non-root) | **52773** | Strict security, port compatibility |

The `webgateway-lockeddown` image is particularly notable: it uses port 52773 instead of 80, making it a drop-in replacement for the old PWS port that pre-2023.2 tooling expected.

ISC maintains [`intersystems-community/webgateway-examples`](https://github.com/intersystems-community/webgateway-examples) with five docker-compose and Kubernetes patterns, updated through January 2026.

Multiple internal Confluence pages document this pattern as the developer setup (pages 767163902 "Running IRIS & a Web Gateway with Docker", 890020031 "IRIS Dev Container", 1101714866 "POC: Containerized HealthShare Development Environment").

JIRA DOCS-13488 confirms a customer (AtScale) hit this issue when upgrading to IRIS 2024.1 — ISC's response was to enhance documentation covering the webgateway container setup, not to restore the PWS.

For VS Code / developer tools [Source: GCGI_private_web]:

> "To view, edit, and debug code on an InterSystems server, the InterSystems ObjectScript extensions for Microsoft Visual Studio Code (VS Code) communicate with an InterSystems server instance through the Web Gateway, using the API which the instance's `/api/atelier` web application provides."

The Atelier REST endpoint itself is unaffected — it is still served by IRIS. Only the HTTP frontend is missing. Once a webgateway container routes `/api/atelier/` to IRIS, developer tools work normally (confirmed by JIRA DP-423020: IAM successfully reached `/api/atelier/` on a NoPWS 2023.2 instance via Apache on port 80).

---

## 5. iris-dev Recommendation Assessment

**iris-dev's current guidance is correct and matches ISC official guidance exactly:**

| iris-dev recommendation | ISC official stance | Match? |
|------------------------|--------------------|----|
| Community images have PWS on 52773 | Explicitly documented | ✅ |
| Enterprise images lack PWS — not fixable via CPF | Enforced invariant (DPQD-2390) | ✅ |
| Use `intersystems/webgateway` sidecar for enterprise | Official documented pattern | ✅ |
| `WebServer=1` CPF crashes enterprise containers | Confirmed empirically; documented as "recovery for upgrades only" | ✅ |
| Auto-detect webgateway container in Docker scan | Not specifically addressed in ISC docs but consistent with the design intent | ✅ |

One nuance worth noting: the `webgateway-lockeddown` image is specifically designed for strict security environments and uses port 52773 — this makes it the most backward-compatible option for tools expecting that port. iris-dev's port scan already includes 52773 first, so this image would be auto-discovered correctly.

---

## 6. Timeline

| Date | Event |
|------|-------|
| Aug 2021 | DPP-1192 filed: "Discontinue installing a Web Server for general distributions" |
| 2023.2 | PWS removed from all enterprise distributions (kits + containers) |
| 2023.2 | Community Edition and evaluation kits explicitly exempted |
| 2023.2 | CART-322 automated test enforces WebServer=0 in enterprise containers |
| 2024.1 | DOCS-13488: ISC enhances webgateway container docs after customer hit this |
| 2025 | DP-441101: Requirements explicitly state "remove CSPpwd from everything except Community Edition container" |
| 2026-05-02 | iris-dev dogfood: confirmed empirically, research verified |

---

## 7. Open Questions

1. **Health Connect (DPP-1593):** JIRA DPP-1593 ("Adding Apache/IIS web server installation to Health Connect Phase 2") suggests PWS may have been selectively re-added to some HealthShare/HealthConnect distributions in IRIS 2024.1. This was not fully investigated. If true, `intersystems/irishealth` containers at 2024.1+ might behave differently from `intersystems/irishealth:2026.1`. *Confidence: low — needs verification.*

2. **The `NOPWS` build suffix:** JIRA DP-423020 references a build string `2023.2.0NOPWS` — it's unclear whether this is just an internal test label or whether it appears in container image metadata. Not material to the main finding.

3. **Upgrade path behavior:** The CPF reference notes "The default value is 0 for new installations, 1 for upgrades." This means containers upgraded from pre-2023.2 would retain WebServer=1 — but since the httpd binary is still absent post-upgrade, the behavior is unclear. Not relevant for fresh container pulls.

---

## Sources

1. **docs.intersystems.com CPF Reference [Startup] WebServer** — https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=RACS_webserver
2. **docs.intersystems.com Web Gateway Guide (GCGI_private_web)** — https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GCGI_private_web
3. **docs.intersystems.com Running in Containers (ADOCK)** — https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ADOCK
4. **intersystems-community/webgateway-examples (GitHub)** — https://github.com/intersystems-community/webgateway-examples
5. **JIRA DPP-1192** — Discontinue installing a Web Server (filed 2021, shipped 2023.2) — usjira.iscinternal.com/browse/DPP-1192
6. **JIRA DPQD-2390** — CART-322 automated test enforcing WebServer=0 — usjira.iscinternal.com/browse/DPQD-2390
7. **JIRA DP-423020** — IAM + NoPWS 2023.2 integration testing — usjira.iscinternal.com/browse/DP-423020
8. **JIRA DOCS-13488** — Webgateway HTTPS docs enhancement (AtScale customer) — usjira.iscinternal.com/browse/DOCS-13488
9. **JIRA DP-441101** — CSPpwd removal requirements — usjira.iscinternal.com/browse/DP-441101
10. **Confluence DPP FAQ: Remove Apache Web Server** — usconfluence.iscinternal.com/pages/viewpage.action?pageId=561013409
11. **Confluence QD: DPP-1192 test tracking** — usconfluence.iscinternal.com/pages/viewpage.action?pageId=597287097
12. **Confluence TAE: PWS removal** — usconfluence.iscinternal.com/pages/viewpage.action?pageId=597669824
13. **Confluence: Running IRIS & Web Gateway with Docker** — usconfluence.iscinternal.com/pages/viewpage.action?pageId=767163902
14. **Empirical evidence:** Direct container inspection of iris:2026.1 and irishealth:2026.1 (2026-05-02)

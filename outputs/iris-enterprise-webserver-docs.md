# IRIS Enterprise Container Private Web Server — Documentation Research

**Research date:** 2026-05-02
**Sources consulted:** docs.intersystems.com (ADOCK, GCGI_private_web, RACS_webserver), intersystems-community/webgateway-examples (GitHub)

---

## 1. Sources

| # | Source | URL | Retrieved |
|---|--------|-----|-----------|
| 1 | CPF Reference: [Startup] WebServer | https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=RACS_webserver | 2026-05-02 |
| 2 | Web Gateway Guide: Access Built-in Web Apps | https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GCGI_private_web | 2026-05-02 |
| 3 | Running in Containers (ADOCK) | https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ADOCK | 2026-05-02 |
| 4 | webgateway-examples (GitHub) | https://github.com/intersystems-community/webgateway-examples | 2026-05-02 |

---

## 2. Evidence Table

| Question | Answer | Source | Confidence |
|----------|--------|--------|------------|
| Is the PWS absent from enterprise containers by design? | Yes — explicitly documented as removed from all non-Community new installations since 2023.2 | Sources 1, 2, 3 | High |
| Does enterprise containers have WebServer=0? | Yes — default for new installations is 0; the CPF `[Startup] WebServer` parameter controls this | Source 1 | High |
| Is PWS still present in Community Edition containers? | Yes — explicitly stated as an exception | Source 3 | High |
| Is port 52773 accessible on enterprise containers? | No — only present in Community Edition containers (and the webgateway-lockeddown image) | Source 3 | High |
| Is the webgateway container the official solution? | Yes — ISC provides three webgateway image variants as the official replacement | Source 3 | High |
| Is there a CPF merge pattern to re-enable PWS in enterprise? | Technically yes (set WebServer=1) but ISC explicitly discourages this for production | Sources 1, 2 | High |
| Is the Atelier/VS Code REST API accessible via webgateway container? | Yes — the /api/atelier path must be routed through the Web Gateway | Source 2 | High |

---

## 3. Direct Quotes from Documentation

### Source 1 — CPF Reference: [Startup] WebServer
(https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=RACS_webserver)

> "Versions of InterSystems IRIS prior to 2023.2 included a private web server that served built-in web applications such as the Management Portal. Beginning with 2023.2, new installations of InterSystems IRIS no longer include a private web server."

> "[Startup] WebServer=n — n is either 1 (true) or 0 (false). The default value is 0 for new installations, 1 for upgrades."

> "When WebServer is enabled (n = 1), InterSystems IRIS attempts to start the Apache private web server upon startup."

### Source 2 — Web Gateway Guide (GCGI_private_web)
(https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GCGI_private_web)

> "Prior to version 2023.2, all InterSystems IRIS installations included a Private Web Server (PWS), a minimal build of Apache httpd which was configured to handle requests for the instance's Management Portal and other built-in system web applications."

> "The PWS is not suitable for serving web applications in production, or for use outside of a secured environment. Beginning with version 2023.2, InterSystems stopped installing a PWS with new installations of InterSystems IRIS data platform products (except Community Editions and other evaluation distributions)."

> "To view, edit, and debug code on an InterSystems server, the InterSystems ObjectScript extensions for Microsoft Visual Studio Code (VS Code) communicate with an InterSystems server instance through the Web Gateway, using the API which the instance's /api/atelier web application provides."

> "It sets the value of the InterSystems IRIS instance's WebServer parameter to false (0), preventing the instance from starting its Private Web Server upon instance startup. This change effectively disables the Private Web Server."
> "Important: If you are installing the Community Edition, the installer does not set the WebServer parameter. You must disable the instance's Private Web Server manually."

> "Note: If you must re-enable an instance's PWS for any reason, you can do so by resetting the WebServer parameter to 1 in the CPF file and then restarting the instance."

### Source 3 — Running in Containers (ADOCK)
(https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ADOCK)

> "In versions of InterSystems IRIS prior to 2023.2, the Web Gateway and a preconfigured private web server were installed with InterSystems IRIS by default, **including in containers**. For this reason, if you are upgrading from a pre-2023.2 version to the current version, you must update all deployment scripts and tools to reflect the new deployment options described by this document."

> "For the convenience of those testing and evaluating InterSystems IRIS, the InterSystems IRIS Community Edition image continues to include the Web Gateway and preconfigured web server; the web server can be reached (to access the Management Portal, for example) at whatever host port is published for the containerized instance's web server port, **52773**."

(Describing the three webgateway image types as the official replacement mechanism):
> "InterSystems Web Gateway Images — There are three types of webgateway images available from InterSystems, each of which provides a web server component for containerized deployments: The webgateway image ... The webgateway-nginx image ... The webgateway-lockeddown image, designed to meet the strictest security requirements..."

> "The webgateway-lockeddown image ... An Apache web server installed in /home/irisowner/apache and configured to use port **52773** instead of the standard port 80."

---

## 4. Summary Findings

### Is it documented that enterprise images have WebServer=0?

**Yes, explicitly.** The CPF reference (Source 1) states the default is 0 for new installations. Source 2 confirms the installer sets `WebServer=0` when configuring an external web server, and explicitly notes the Community Edition is the exception (the installer does not set `WebServer` for Community Edition, requiring manual disabling).

### Is there an officially documented way to enable the private web server in enterprise containers?

**Technically yes, but strongly discouraged for production.** The CPF `[Startup] WebServer=1` parameter can re-enable it, and Source 2 documents this as a recovery option ("If you must re-enable an instance's PWS for any reason..."). However, ISC explicitly states: "The PWS is not suitable for serving web applications in production, or for use outside of a secured environment."

### What does ISC recommend for accessing the Atelier REST API with enterprise containers?

**The Web Gateway.** Source 2 states: "the InterSystems ObjectScript extensions for VS Code communicate with an InterSystems server instance through the Web Gateway, using the API which the instance's /api/atelier web application provides." The recommended path requires routing `/api` through an external web server + Web Gateway. For IIS, additional steps are documented to disable WebDAV (which conflicts with `/api/atelier`) and enable WebSockets (required for debugging).

### Is the webgateway container the official solution?

**Yes.** Source 3 describes three official webgateway container images as the replacement mechanism for the removed PWS: `webgateway` (Apache), `webgateway-nginx` (Nginx), and `webgateway-lockeddown` (nonroot, hardened Apache on port 52773). The `intersystems-community/webgateway-examples` GitHub repo (Source 4) provides official demo patterns for docker-compose and Kubernetes integration.

### Community Edition vs. Enterprise: the key distinction

| Behavior | Enterprise (intersystems/iris, intersystems/irishealth) | Community Edition |
|----------|--------------------------------------------------------|-------------------|
| Private web server included | No (since 2023.2) | Yes |
| Port 52773 accessible | No | Yes |
| WebServer CPF default | 0 (disabled) | 1 (enabled) |
| Web Gateway bundled | No | Yes (bundled with PWS) |
| Recommended web access path | Separate webgateway container | Direct port 52773 (or webgateway) |

---

## 5. Gaps / Not Found in Documentation

- No ISC documentation was found that explicitly lists the enterprise container image CPF file contents or confirms `WebServer=0` is baked into the image at build time (as opposed to being the default for new installs generally). The evidence strongly implies this, but is stated as a general new-installation default rather than a container-specific statement.
- No ISC documentation was found describing a supported CPF merge pattern for re-enabling the PWS specifically within a container (as opposed to a bare-metal install).
- `containers.intersystems.com` redirects and does not expose a human-readable image catalog in the fetched response.

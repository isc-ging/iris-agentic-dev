# IRIS Enterprise Docker Container — Web Server / Atelier REST API: Web Research Findings

**Research date:** 2026-05-03
**Researcher note:** Perplexity quota was exhausted; all results are from direct web fetches and Playwright browser navigation against live sources.

---

## Key Findings Summary

The most authoritative finding is a direct quote from the official InterSystems documentation (source 1 below) that definitively explains the behavior:

> "In versions of InterSystems IRIS prior to 2023.2, the Web Gateway and a preconfigured private web server were installed with InterSystems IRIS by default, including in containers. For this reason, if you are upgrading from a pre-2023.2 version to the current version, you must update all deployment scripts and tools to reflect the new deployment options described by this document. Further, 2023.2 and later InterSystems IRIS containers should be used only with InterSystems Kubernetes Operator 3.6 and later."
>
> "For the convenience of those testing and evaluating InterSystems IRIS, the InterSystems IRIS Community Edition image continues to include the Web Gateway and preconfigured web server; the web server can be reached (to access the Management Portal, for example) at whatever host port is published for the containerized instance's web server port, 52773."

**Bottom line:** The private web server (and therefore the Atelier REST API at `/api/atelier/`) was intentionally removed from enterprise IRIS container images starting with version 2023.2. Community Edition images retain it. This is a documented, deliberate architectural decision by InterSystems.

---

## Numbered Source List

### Source 1 — Official InterSystems Documentation (PRIMARY, DEFINITIVE)

**URL:** `https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ADOCK`
**Title:** "Running InterSystems Products in Containers" — IRIS Data Platform 2026.1 (redirects from all 2023.x versions to latest)
**Section:** "Web Access Using the Web Gateway Container" (anchor: `#ADOCK_iris_webgateway`)
**Fetched:** 2026-05-03 via Playwright

**Direct quotes:**

1. The critical Note (found at what renders as the "Important" callout in the webgateway section):

   > "In versions of InterSystems IRIS prior to 2023.2, the Web Gateway and a preconfigured private web server were installed with InterSystems IRIS by default, including in containers. For this reason, if you are upgrading from a pre-2023.2 version to the current version, you must update all deployment scripts and tools to reflect the new deployment options described by this document. Further, 2023.2 and later InterSystems IRIS containers should be used only with InterSystems Kubernetes Operator 3.6 and later."

2. Community Edition exception:

   > "For the convenience of those testing and evaluating InterSystems IRIS, the InterSystems IRIS Community Edition image continues to include the Web Gateway and preconfigured web server; the web server can be reached (to access the Management Portal, for example) at whatever host port is published for the containerized instance's web server port, 52773."

3. On the webgateway image's purpose:

   > "webgateway — Deploys both the InterSystems Web Gateway and a web server, providing a web server component for containerized deployments of InterSystems IRIS-based applications"

4. On the Management Portal in containers:

   > "For information about accessing the Management Portal of a containerized InterSystems IRIS instance, see Web Access Using the Web Gateway Container."

5. Durable %SYS includes `/httpd/httpd.conf` in the persisted list:

   > "The file /httpd/httpd.conf, the configuration file for the instance web server."
   
   (This indicates the instance web server config is persisted when Durable %SYS is used, but this is in the context of containers generally — not a contradiction of the removal; it applies to Community Edition or pre-2023.2 images.)

**Confidence:** HIGH (this is the primary official documentation, fetched directly from docs.intersystems.com)

---

### Source 2 — intersystems-community/webgateway-examples GitHub Repo

**URL:** `https://github.com/intersystems-community/webgateway-examples`
**Fetched:** 2026-05-03 via Playwright
**Last commit:** Jan 13, 2026 (active maintenance)
**Contributors:** sgmatthews (Sarah Matthews, ISC), kuszewski (Bob Kuszewski, ISC)

**Evidence:** The existence and active maintenance of this repo, maintained by ISC engineers, directly confirms that enterprise IRIS containers need the separate webgateway container to serve web traffic. The repo provides five deployment patterns:

- `demo-compose` — simple docker-compose with webgateway container alongside IRIS container
- `demo-dockerfile` — builds a custom IRIS-based container **including** a web server and Web Gateway (showing this is not present by default)
- `demo-kubernetes` — IKO deployment with standalone web server and IRIS data node
- `demo-one-to-many` — one Web Gateway serving two IRIS instances' Management Portals
- `demo-many-to-many` — dedicated Web Gateway per IRIS instance for Management Portal

**Indirect quote from README:**
> "demo-dockerfile: a custom dockerfile that builds a new IRIS-based container including a web server and Web Gateway"

The phrase "including a web server and Web Gateway" implies these are not present by default and must be explicitly added.

**Confidence:** HIGH (official ISC community repo, actively maintained by ISC engineers)

---

### Source 3 — InterSystems Developer Community Search

**URL:** `https://community.intersystems.com/search?keys=atelier+REST+docker+container`
**Fetched:** 2026-05-03 via Playwright
**Result:** "Whoops! No results found."

**URL:** `https://community.intersystems.com/search?keys=docker+web+server+disabled`
**Result:** "Whoops! No results found."

**URL:** `https://community.intersystems.com/search?keys=webgateway+container+atelier`
**Result:** "Whoops! No results found."

**Interpretation:** The Developer Community search engine returned no posts specifically about this topic. This is consistent with the change being a documented ISC decision rather than a user-reported bug — the community discussion may have occurred at the time of the 2023.2 release (late 2023) and not been indexed by the search system, or the topic was simply addressed in official documentation without community debate.

**Confidence:** N/A (absence of evidence, not evidence of absence)

---

### Source 4 — GitHub Issues Search (vscode-objectscript)

**URL:** `https://github.com/intersystems-community/vscode-objectscript/issues?q=is%3Aissue+webserver`
**Fetched:** 2026-05-03 via Playwright

One issue found with Atelier API endpoint referenced: "request to http://serverIP:57772/api/atelier/ failed" — noting that port 57772 (the older CSP gateway port) is used in the issue title, suggesting this predates the web server change (pre-2023.2 behavior).

No issues specifically about enterprise container web server exclusion or Atelier REST API unavailability in Docker were found in this repo.

**Confidence:** LOW (inconclusive; absence does not confirm the issue doesn't exist)

---

### Source 5 — GitHub Global Issue Search

**URL:** `https://github.com/search?q=intersystems+iris+enterprise+container+"web+server"+atelier&type=issues`
**Result:** 0 issues matching

**URL:** `https://github.com/search?q=intersystems+iris+"2023.2"+"web+server"+container&type=issues`
**Result:** 1 issue ("WebSockets Terminal closes after approximately 60 seconds") — not relevant

**Confidence:** LOW (GitHub unauthenticated search is rate-limited and incomplete)

---

### Source 6 — InterSystems ADOCK docs, Durable %SYS section

**URL:** `https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ADOCK`
**Section:** Durable %SYS data list
**Fetched:** 2026-05-03 via Playwright

The documentation lists `/httpd/httpd.conf` as one of the files persisted under Durable %SYS:

> "The file /httpd/httpd.conf, the configuration file for the instance web server."

This confirms that when an instance web server IS present (Community Edition, or pre-2023.2), its config is tracked. It does not contradict the enterprise removal — it simply means Durable %SYS persists the httpd.conf when it exists.

**Confidence:** HIGH (direct documentation fetch)

---

### Source 7 — webgateway-examples repo: three webgateway image types documented

From ADOCK source (Source 1), the documentation lists three webgateway image variants:

> "The webgateway image contains: An InterSystems Web Gateway in /opt/webgateway. An Apache web server in /etc/apache2."

> "The webgateway-nginx image contains: An InterSystems Web Gateway in /opt/webgateway. An Nginx web server in /opt/nginx."

> "The webgateway-lockeddown image contains: An InterSystems Web Gateway installed in /home/irisowner/webgateway with locked-down security. An Apache web server installed in /home/irisowner/apache and configured to use port 52773 instead of the standard port 80."

**Confidence:** HIGH (direct documentation fetch)

---

### Source 8 — containers.intersystems.com Registry

**URL:** `https://containers.intersystems.com/contents`
**Result:** Page rendered only footer/navigation; no image list accessible without authentication.

**Confidence:** N/A (unauthenticated access insufficient)

---

### Source 9 — Docker Hub intersystems/iris

**URL:** `https://hub.docker.com/r/intersystems/iris/`
**Result:** 404 Not Found

**Interpretation:** The enterprise IRIS image is not published on Docker Hub (consistent with it being a licensed product requiring the ISC Container Registry). Community Edition is published separately.

**Confidence:** MEDIUM (404 confirms enterprise image is not on Docker Hub)

---

### Source 10 — iris-container-recipe (referenced in research task)

**URL:** `https://github.com/intersystems-community/iris-container-recipe`
**Result:** 404 Not Found — repository does not exist at this path.

---

## Answers to Key Questions

### 1. Is the exclusion of the private web server from enterprise containers intentional?

**YES — definitively confirmed.** The official InterSystems documentation explicitly states:

> "In versions of InterSystems IRIS prior to 2023.2, the Web Gateway and a preconfigured private web server were installed with InterSystems IRIS by default, including in containers."

The past tense and the "prior to 2023.2" phrasing make clear this was a deliberate architectural change made in 2023.2. The documentation tells users upgrading from pre-2023.2 to "update all deployment scripts and tools."

**Confidence: HIGH**

### 2. Community consensus on whether this is intentional?

The Developer Community search returned no results for the relevant queries, and GitHub issue searches returned nothing relevant. This strongly suggests the change is well-accepted as intentional ISC policy rather than a bug — there are no community complaints or workaround threads. The official ISC-maintained `webgateway-examples` repo (with active commits through Jan 2026) provides the canonical patterns for dealing with it.

**Confidence: MEDIUM** (absence of complaints interpreted as acceptance)

### 3. Known workarounds beyond the webgateway container?

From the documentation and webgateway-examples repo, the supported patterns are:

1. **webgateway container** (Apache-based) — standard approach, pairs alongside IRIS container
2. **webgateway-nginx container** — Nginx-based alternative
3. **webgateway-lockeddown container** — Apache on port 52773, non-root, for strict security
4. **demo-dockerfile pattern** — build a custom image that bakes in the web server and Web Gateway into a single container (useful for dev/test scenarios where you want one container)
5. **IKO sidecar** — for Kubernetes, IKO deploys a dedicated Web Gateway container as a sidecar in each IRIS pod

No `IRIS_ENABLE_WEBSERVER` environment variable or equivalent CPF setting was found documented. The web server is architecturally separated, not disabled by a flag.

**Confidence: HIGH**

### 4. Does this behavior differ across IRIS versions?

**Yes — the version boundary is 2023.2:**

- **Pre-2023.2 enterprise containers:** private web server included by default (port 52773 worked inside the container)
- **2023.2+ enterprise containers:** private web server removed; requires webgateway container
- **Community Edition (all versions):** private web server retained for developer convenience

No evidence was found that the behavior varies between enterprise editions (iris vs. irishealth) — both are enterprise images and presumably both changed at 2023.2. The documentation says "containers" generally, not just the `iris` image.

**Confidence: HIGH** (version boundary explicitly stated in docs)

### 5. Is there an IRIS_ENABLE_WEBSERVER env var or similar?

No evidence found. The official documentation makes no mention of such an environment variable. The architecture is a clean separation: enterprise containers ship without httpd; the webgateway image provides it. This is not a configuration toggle.

**Confidence: HIGH** (absence of any mention in primary documentation source)

### 6. Implications for the Atelier REST API

The Atelier REST API (`/api/atelier/`) is served by the web server component. Without a web server (httpd/nginx) fronting the IRIS instance, the REST endpoint is unreachable. This means:

- In enterprise containers (2023.2+), the Atelier REST API is **not directly accessible** without pairing with a webgateway container
- The VS Code ObjectScript extension, which uses the Atelier REST API, requires either:
  - A webgateway container (standard production approach)
  - The demo-dockerfile pattern (for dev use)
  - Using a Community Edition image (not available under enterprise license)
- The old approach of publishing port 52773 directly from the container and connecting VS Code to it **no longer works** with 2023.2+ enterprise images

This is the root cause of the behavior observed in the `iris-dev` project when connecting the objectscript-coder tools to an enterprise container.

**Confidence: HIGH**

---

## Raw Documentation Extract (Critical Passage)

From `https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ADOCK`, "Important" callout in the "Web Access Using the Web Gateway Container" section:

```
In versions of InterSystems IRIS prior to 2023.2, the Web Gateway and a
preconfigured private web server were installed with InterSystems IRIS by
default, including in containers. For this reason, if you are upgrading from
a pre-2023.2 version to the current version, you must update all deployment
scripts and tools to reflect the new deployment options described by this
document. Further, 2023.2 and later InterSystems IRIS containers should be
used only with InterSystems Kubernetes Operator 3.6 and later.

For the convenience of those testing and evaluating InterSystems IRIS, the
InterSystems IRIS Community Edition image continues to include the Web Gateway
and preconfigured web server; the web server can be reached (to access the
Management Portal, for example) at whatever host port is published for the
containerized instance's web server port, 52773.
```

---
name: pyprod-setup
description: Installation and environment setup for intersystems_pyprod — venv, pip install, IRIS target install, required environment variables, Docker setup.
---

# pyprod Setup & Installation

## 1. Install in Virtual Environment

**Linux / Mac:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install intersystems_pyprod
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install intersystems_pyprod
deactivate
```

---

## 2. Install into IRIS Target Directory

pyprod must also be installed where IRIS can find it — the `mgr/python` directory of the IRIS installation:

**Linux / Mac:**
```bash
pip install intersystems_pyprod --target /usr/irissys/mgr/python
```

**Windows:**
```powershell
pip install intersystems_pyprod --target C:\InterSystems\IRIS\mgr\python
```

Container default: `/usr/irissys/mgr/python`

---

## 3. Required Environment Variables

These connect pyprod to the IRIS instance.

**Linux / Mac:**
```bash
export IRISINSTALLDIR="/usr/irissys"          # container default; Windows: C:\InterSystems\IRIS
export IRISUSERNAME="SuperUser"
export IRISPASSWORD="SYS"
export IRISNAMESPACE="ENSEMBLE"               # must be a namespace with Interoperability enabled

export COMLIB="$IRISINSTALLDIR/bin"
export PYTHONPATH="$IRISINSTALLDIR/lib/python"
export DYLD_LIBRARY_PATH="$IRISINSTALLDIR/bin:$DYLD_LIBRARY_PATH"   # Mac only
export LD_LIBRARY_PATH="$IRISINSTALLDIR/bin:$LD_LIBRARY_PATH"       # Linux only
```

**Windows (PowerShell):**
```powershell
$Env:IRISINSTALLDIR="C:\InterSystems\IRIS"
$Env:IRISUSERNAME="SuperUser"
$Env:IRISPASSWORD="SYS"
$Env:IRISNAMESPACE="ENSEMBLE"

$Env:COMLIB="$Env:IRISINSTALLDIR\bin"
$Env:PYTHONPATH="$Env:IRISINSTALLDIR\lib\python"
```

---

## 4. Docker Setup

Set env vars in the Dockerfile and install to the IRIS mgr/python path:

```dockerfile
ARG IMAGE=intersystems/iris-community:latest-em
FROM $IMAGE

ENV IRISINSTALLDIR "/usr/irissys"
ENV LD_LIBRARY_PATH "$IRISINSTALLDIR/bin:$LD_LIBRARY_PATH"
ENV IRISUSERNAME "SuperUser"
ENV IRISPASSWORD "SYS"
ENV IRISNAMESPACE "ENSEMBLE"
ENV COMLIB "$IRISINSTALLDIR/bin"
ENV PYTHONPATH "$IRISINSTALLDIR/lib/python:$IRISINSTALLDIR/mgr/python"
ENV PATH "/usr/irissys/mgr/python/bin:/usr/irissys/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

WORKDIR /home/irisowner/dev
COPY . .

# Install dependencies to IRIS mgr/python so IRIS can import them
RUN python3 -m pip install -r requirements.txt --target /usr/irissys/mgr/python --upgrade

# Load production components into IRIS
RUN --mount=type=bind,src=.,dst=. \
    iris start IRIS && \
    intersystems_pyprod /home/irisowner/dev/src/myproject/components.py && \
    intersystems_pyprod /home/irisowner/dev/src/myproject/production.py && \
    iris stop IRIS quietly safely
```

---

## 5. IRIS Namespace Prerequisites

The target namespace must have:
- Interoperability enabled (use `ENSEMBLE` namespace or configure one)
- `ENSLIB` database set to read/write
- Service Callin feature enabled

---

## 6. Loading Components into IRIS

Use the CLI to load Python files into a running IRIS instance:

```bash
intersystems_pyprod /path/to/components.py
intersystems_pyprod /path/to/production.py
```

Load order matters: load component definitions before the production definition.

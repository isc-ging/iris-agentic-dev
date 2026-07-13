---
name: pyprod-production-definition
description: Reference for declaring IRIS production structure in Python using the Production class, ServiceItem, ProcessItem, and OperationItem — including loading components into IRIS via CLI.
---

# Production Definition

Declare the entire production structure in Python by subclassing `Production`. When the file is loaded into IRIS, the production definition is generated automatically.

```python
from intersystems_pyprod import Production, ServiceItem, ProcessItem, OperationItem

iris_package_name = "MyPackage"

class MyProduction(Production):
    description = "Production description"
    actor_pool_size = 2

    services = [
        ServiceItem(
            "MyPackage.MyService",
            "MyPackage.MyBusinessService",
            adapter_settings={"Port": 12345},
            host_settings={"target": "MyPackage.MyProcess"},
            pool_size=1
        )
    ]
    processes = [
        ProcessItem(
            "MyPackage.MyProcess",
            "MyPackage.MyBusinessProcess",
            host_settings={"target": "MyPackage.MyOperation"},
            pool_size=0
        )
    ]
    operations = [
        OperationItem(
            "MyPackage.MyOperation",
            "MyPackage.MyBusinessOperation",
            host_settings={"FailureTimeout": 30},
            adapter_settings={"IPAddress": "127.0.0.1", "Port": 9000}
        )
    ]
```

> Only attributes defined in the `Production` superclass are valid. Any other attribute emits a warning at load time.

---

## Production Class Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `services` | `list[ServiceItem]` | `None` | Business services |
| `processes` | `list[ProcessItem]` | `None` | Business processes |
| `operations` | `list[OperationItem]` | `None` | Business operations |
| `description` | `str` | `""` | Human-readable description |
| `actor_pool_size` | `int` | `2` | Shared actor pool size for business processes |
| `testing_enabled` | `bool` | `False` | Enable testing infrastructure |
| `log_general_trace_events` | `bool` | `False` | Log trace events not tied to a config item |
| `shutdown_timeout` | `int` | `120` | Seconds to wait during shutdown |
| `update_timeout` | `int` | `10` | Seconds to wait during update |
| `alert_notification_manager` | `str` | `""` | Full config item name of alert manager |
| `alert_notification_operation` | `str` | `""` | Full config item name of alert operation |
| `alert_notification_recipients` | `str` | `""` | Comma-separated alert recipients |
| `alert_action_window` | `int` | `60` | Alert action window in minutes |

> `actor_pool_size`, `testing_enabled`, `log_general_trace_events`, and item-level settings can be overridden by System Default Settings in the IRIS management portal — even when set explicitly here.

---

## Item Types

All three item types (`ServiceItem`, `ProcessItem`, `OperationItem`) share these arguments:

| Arg | Default | Notes |
|-----|---------|-------|
| `name` | required | Config item name as shown in UI, e.g. `"MyPackage.MyService"` |
| `class_name` | required | Full IRIS class name, e.g. `"MyPackage.MyBusinessService"` |
| `host_settings` | `None` | Dict of host property values. Keys are snake_case or PascalCase IRISProperty names |
| `category` | `""` | Comma-separated display categories (UI only, no runtime effect) |
| `pool_size` | `1` | Jobs to start. `0` = shared actor pool |
| `enabled` | `True` | Whether item starts enabled |
| `foreground` | `False` | Run in foreground (non-container only) |
| `comment` | `""` | Displayed in Production Configuration page |
| `log_trace_events` | `False` | Log trace events for this item |
| `schedule` | `""` | Start/stop schedule. e.g. `"START:*-*-*T08:00:00,STOP:*-*-*T17:00:00"` or `"@MyScheduleName"` |

**`adapter_settings`** — available on `ServiceItem` and `OperationItem` only. Dict of adapter property values.

### pool_size guidance

| Component | pool_size |
|-----------|-----------|
| Adapter-based BusinessService | `1` |
| Adapterless BusinessService | `0` (shared actor pool) |
| BusinessProcess (typical) | `0` (shared actor pool) |
| BusinessProcess (FIFO/dedicated) | `1` |
| BusinessOperation | `1` |

---

## Loading into IRIS

Use the `intersystems_pyprod` CLI. Load component definitions before the production definition.

```bash
intersystems_pyprod /path/to/components.py
intersystems_pyprod /path/to/production.py
```

In a Dockerfile:

```dockerfile
RUN iris start IRIS && \
    intersystems_pyprod /path/to/components.py && \
    intersystems_pyprod /path/to/production.py && \
    iris stop IRIS quietly safely
```

After loading, start the production from the Production Configuration page or programmatically:

```python
from intersystems_pyprod.director import start_production
status = start_production("MyPackage.MyProduction")
```

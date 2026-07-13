---
name: pyprod-director
description: Director module reference for controlling IRIS productions programmatically from Python — start, stop, status, messaging, and injecting into running productions.
---

# Director Module

`intersystems_pyprod.director` wraps `Ens.Director`, the IRIS interoperability runtime controller. All functions run inside an IRIS namespace.

Most functions return an IRIS status code as the first value. `1` = success; any other value = encoded error string.

```python
from intersystems_pyprod.director import (
    start_production, stop_production, restart_production,
    get_production_status, update_production, clean_production,
    enable_config_item, list_all_productions,
    get_host_messages, create_business_service,
)
```

---

## Production Lifecycle

### `start_production`

```python
start_production(prod_name: str = None) -> str
```

`prod_name`: full IRIS class name e.g. `"MyPackage.MyProduction"`. Omit to use last production in namespace.

```python
status = start_production("MyPackage.MyProduction")
```

---

### `stop_production`

```python
stop_production(timeout: int = 10, force: bool = False) -> str
```

`force=True` kills jobs that don't stop within timeout.

---

### `restart_production`

```python
restart_production(timeout: int = 10, force: bool = False) -> str
```

---

### `update_production`

Apply config changes to a running production without full stop/start:

```python
update_production(timeout: int = 10, force: bool = False, called_by_schedule_handler: bool = False) -> str
```

---

### `get_production_status`

```python
status, prod_name, state = get_production_status(lock_timeout=10, skip_lock_if_running=False)
```

`state` values:

| Value | Meaning |
|-------|---------|
| `"1"` | Running |
| `"2"` | Stopped |
| `"3"` | Suspended |
| `"4"` | Troubled |

```python
status, prod_name, state = get_production_status()
if state == "1":
    print(f"{prod_name} is running")
```

---

### `clean_production`

> **WARNING**: Removes all queued messages and production state. Development only, production must be stopped.

```python
clean_production(kill_app_data_too: bool = False) -> str
```

---

## Config Items

### `enable_config_item`

Enable or disable a config item. Works on running or stopped productions.

```python
enable_config_item(config_item_name: str, enable: bool = True, do_update: bool = True) -> str
```

`do_update=True` calls `update_production` automatically so changes take effect immediately.

```python
status = enable_config_item("MyPackage.MyService", enable=False)
```

---

### `list_all_productions`

```python
status, names, details = list_all_productions()
# details: {prod_name: {"status": str, "last_start_time": str|None, "last_stop_time": str|None}}

for name in names:
    print(name, details[name]["status"])
```

---

## Messaging

### `get_host_messages`

Returns messages sent from or received by a host, most recent first.

```python
messages = get_host_messages(host_name: str, max_results: int = 100) -> list[dict]
```

Each dict has: `id`, `time_created`, `source`, `target`, `status`, `session_id`, `body_class`, `body_id`.

```python
messages = get_host_messages("MyPackage.MyOperation", max_results=20)
for msg in messages:
    print(msg["time_created"], msg["source"], "->", msg["target"])
```

---

### `create_business_service`

Inject messages directly into a running production without an inbound adapter.

```python
status, service = create_business_service(service_class_name: str)
```

Returns an `_AdapterlessService` wrapper. Do not instantiate directly.

```python
status, service = create_business_service("MyPackage.MyAdapterlessService")
service.TargetConfigName = "MyPackage.MyProcess"   # set IRIS property
status, response = service.process_input(my_request)
```

Snake_case attribute names are auto-converted to PascalCase on the IRIS side.

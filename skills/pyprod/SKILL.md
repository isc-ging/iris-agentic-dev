---
name: pyprod
description: Use when creating or modifying InterSystems IRIS interoperability production components in Python — Business Services, Business Processes, Business Operations, Adapters, Messages, or Production definitions.
metadata:
  version: "1.1.0"
  compatibility: iris, python, pyprod
references:
  - setup: references/setup.md
  - director: references/director.md
  - production-definition: references/production-definition.md
---

# Building with pyprod

pyprod is the Python library for building InterSystems IRIS interoperability productions. See [[pyprod-setup]] for installation.

---

## Core Concepts

An IRIS production is a message-passing pipeline of **Business Hosts**:

```
External Input
  -> InboundAdapter       (optional, receives raw data)
  -> BusinessService      (packages into persistable message, routes)
  -> BusinessProcess      (orchestrates logic, transforms)
  -> BusinessOperation    (sends to external targets)
  -> OutboundAdapter      (optional, formats output)
```

All communication between BusinessService / BusinessProcess / BusinessOperation uses **persistable messages** (JsonSerialize or PickleSerialize subclasses).

---

## Import

```python
from intersystems_pyprod import (
    IRISParameter, IRISProperty,
    InboundAdapter, BusinessService,
    BusinessProcess, BusinessOperation, OutboundAdapter,
    Column, JsonSerialize, PickleSerialize,
    IRISLog, Status,
    Production, ServiceItem, ProcessItem, OperationItem
)
```

---

## Package Name

All classes in a script belong to a package. Set at module or class level:

```python
iris_package_name = "MyPackage"   # module-level (applies to all classes)
```

Classes appear in the UI as `iris_package_name.ClassName`. Class-level `iris_package_name` overrides module-level.

---

## Status Objects

Every callback returns `Status` as the first return value:

```python
return Status.OK()
return Status.ERROR("Descriptive error message")
```

Success = `1`. Failure = encoded error string.

---

## Persistable Messages

Messages passed between Business Hosts must be persistable. Choose serializer:

| Class | Serializer | Use when |
|-------|-----------|----------|
| `JsonSerialize` | json / orjson | JSON-compatible fields |
| `PickleSerialize` | pickle | Python objects not JSON-serializable |

**WARNING**: Never unpickle from untrusted sources.

```python
class MyMessage(JsonSerialize):
    field_1: str = Column(index=True)
    field_2 = Column(datatype=int)
    field_3 = "default_value"    # not a Column, not queryable via SQL

class MyPickleMessage(PickleSerialize):
    field_1 = ("tuple", "default")
    field_2: int
```

Instantiate:
```python
msg = MyMessage("value1", 42)
msg = MyMessage(field_2=42)
msg = MyMessage()
msg.field_1 = "value1"
```

### Column

`Column()` fields appear as separate SQL columns in the IRIS database:

```python
Column(default=None, datatype=None, description=None, index=False)
```

Supports string and numeric datatypes only.

---

## IRISProperty

Instance variables linked to the IRIS UI. State persists for adapters, services, and operations (not processes — new instance per message):

```python
prop = IRISProperty(default=None, datatype="", description="", settings="category:control")
```

| `settings` value | Effect |
|-----------------|--------|
| `""` | Shows in UI as empty text box |
| `"MyCategory"` | Shows under that category |
| `"MyCategory:control"` | Shows with named control |
| `":control"` | Shows with control, no category |
| `"-"` | Removes inherited property from UI |

Selector for host list:
```python
settings="Target:selector?context={Ens.ContextSearch/ProductionItems?targets=1&productionName=@productionId}"
```

**Custom `__init__`**: must preserve base class signature:
```python
def __init__(self, iris_host_object):
    super().__init__(iris_host_object)
    self.instance_variable = 0
```

---

## IRISParameter

Class constants on the IRIS side. Required for linking adapters:

```python
IRISParameter(value, datatype="", description="")
```

`value` format: `"iris_package_name.ClassName"`. No special characters allowed.

```python
ADAPTER = IRISParameter("MyPackage.MyAdapter")
```

---

## IRISLog

Sends log messages to the IRIS Production Log Viewer:

```python
IRISLog.Info("info message")
IRISLog.Warning("warning message")
IRISLog.Error("error message")
IRISLog.Status(Status.OK())
IRISLog.Status(Status.ERROR("error string"))
```

---

## Components

Both PascalCase and snake_case are accepted for callbacks and message-passing methods. **snake_case is preferred** — it follows Python conventions. The examples below use snake_case throughout.

### InboundAdapter

Polls external systems and passes data to Business Service.

```python
class MyInboundAdapter(InboundAdapter):

    def on_task(self):          # also accepted: OnTask
        data = ...              # fetch from external source
        status = self.business_host_process_input(data)   # also: BusinessHost_ProcessInput
        return status
```

- Required callback: `on_task`
- No message persistence at this stage — any Python type accepted
- Runs in same CPU process as its Business Service

---

### BusinessService

Receives data from adapter (or direct call), packages as persistable message, routes forward.

```python
class MyBusinessService(BusinessService):

    ADAPTER = IRISParameter("MyPackage.MyAdapter")   # omit for adapterless
    target = IRISProperty(settings="Target:selector?context={...}")

    def on_process_input(self, input):          # also accepted: OnProcessInput
        request = MyMessage(input)
        status, response = self.send_request_sync(self.target, request, timeout=-1)  # also: SendRequestSync
        # or non-blocking (no response_required param on BusinessService):
        status = self.send_request_async(self.target, request)                        # also: SendRequestAsync
        return status, response
```

- Required callback: `on_process_input`
- Adapterless service: omit `ADAPTER` parameter; set `pool_size=0` in `ServiceItem`
- `send_request_async` on BusinessService: `(target, request, description="")` — no `response_required`

---

### BusinessProcess

Core orchestration logic. New instance created per incoming message (no persistent state).

```python
class MyBusinessProcess(BusinessProcess):

    target = IRISProperty(settings="Target:selector?context={...}")

    def on_request(self, request):              # also accepted: OnRequest
        status, response = self.send_request_sync(self.target, request, timeout=-1)  # also: SendRequestSync
        return status, response

    def on_response(self, request, response, call_request, call_response, completion_key):  # also: OnResponse
        # required when send_request_async is called with response_required=1
        return status, response
```

- Required callback: `on_request`
- `on_response` is **required** whenever `send_request_async` is called with `response_required=1`

**`send_request_async` signature on BusinessProcess:**
```python
self.send_request_async(target, request, response_required=1, completion_key=0, description="")
```

`response_required` defaults to `1` — so `on_response` must be implemented unless you explicitly pass `response_required=0`. It is an **integer**, not a bool.

---

### BusinessOperation

Receives typed requests, dispatches to methods via `MessageMap`. Sends to external targets via adapter or directly.

```python
class MyBusinessOperation(BusinessOperation):

    ADAPTER = IRISParameter("MyPackage.MyAdapter")   # optional

    MessageMap = {
        "MyPackage.MessageType1": "method_1",
        "MyPackage.MessageType2": "method_2"
    }

    def method_1(self, request):
        status, result = self.ADAPTER.adapter_method("arg")
        response = MyMessage(result)
        return status, response

    def method_2(self, request):
        status = self.ADAPTER.adapter_method()
        return status

    def on_message(self, request):              # also accepted: OnMessage
        # optional: handles message types not in MessageMap
        return Status.OK()
```

MessageMap key format: `"iris_package_name.MessageClassName"`

To send within the production from a BO:
```python
status, response = self.send_request_sync(target, request)   # also: SendRequestSync
status = self.send_request_async(target, request)            # also: SendRequestAsync
```

`send_request_async` on BusinessOperation: `(target, request, description="")` — no `response_required`.

---

### OutboundAdapter

Interface to external systems. Called directly by Business Operation methods.

```python
class MyOutboundAdapter(OutboundAdapter):

    def adapter_method(self, arg1="default", arg2="default"):
        status = Status.OK()
        output = ...
        return status, output   # response can be any type
```

- No required callbacks
- No message persistence beyond this point
- Method names called from BO are converted from snake_case to PascalCase automatically

---

## Production Definition

See [[pyprod-production-definition]] for the full `Production` class reference, item type arguments, and loading instructions.

---

## Director Module

See [[pyprod-director]] for controlling productions programmatically — start, stop, status, injecting messages.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Not returning Status as first value | Every callback must return `Status.OK()` or `Status.ERROR(...)` first |
| Passing non-persistable message between hosts | Wrap data in `JsonSerialize` or `PickleSerialize` subclass before `SendRequest*` |
| MessageMap key wrong package | Key must be `iris_package_name.ClassName` where `iris_package_name` is the value in the message's module |
| `pool_size=1` for adapterless service | Use `pool_size=0` to run from shared actor pool |
| `Column()` with complex Python types | Columns support string and numeric only; use plain class attribute for other types |
| IRISProperty usedf or class-level constants | Use `IRISParameter` for constants; `IRISProperty` is for instance-configurable values |
| Business Process maintaining state | BP creates a new instance per message — use `IRISProperty` only on adapters, services, and operations |
| `BusinessProcess.send_request_async` with no `on_response` defined | Default is `response_required=1` — causes `NotImplementedError` unless `on_response` is implemented or `response_required=0` is passed explicitly |
| Passing `response_required=True` (bool) | `response_required` is an integer: use `0` or `1` |
| Calling BS/BO `send_request_async` expecting `response_required` | Only `BusinessProcess` has `response_required` — `BusinessService` and `BusinessOperation` `send_request_async` signatures do not include it |

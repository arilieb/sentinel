# Sentinel Framework - Developer Guide

## Overview

The **Sentinel Framework** provides an event-driven API for building standalone applications that respond to changes in exported KERI Key Event Logs (KEL), Transaction Event Logs (TEL), and Credentials.

Applications built with this framework run as **separate processes** from sentinel, watching the export directory for file changes and dispatching events to registered handlers.

## Key Features

- **Standalone Applications** - No integration with sentinel service required
- **Simple Handler-Based API** - Implement only the methods you need
- **Error Isolation** - Handler failures don't affect other handlers or the watcher
- **Optional KERI Integration** - Access `hby`/`essr`/`db` if provided
- **Polling-Based Watching** - No external dependencies, consistent with sentinel patterns
- **In-Memory State Tracking** - Simple mtime-based change detection

## Quick Start

### Basic Example

```python
#!/usr/bin/env python3
# myapp.py

from sentinel.framework import EventHandler, register_handler, run
from sentinel.framework import KELEvent

class MyApp(EventHandler):
    async def on_kel(self, event: KELEvent):
        print(f"New KEL for {event.aid}")
        print(f"Data size: {len(event.data)} bytes")

register_handler(MyApp())

if __name__ == "__main__":
    run(export_dir="/usr/local/sentinel")
```

Run your app:

```bash
# Terminal 1: Start sentinel with export directory
sentinel start -n mydb -a myalias --export-dir /usr/local/sentinel

# Terminal 2: Run your application
python myapp.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Sentinel Service                           │
│                  (separate process)                          │
│  Exports KEL/TEL/Cred to filesystem                         │
└─────────────────────────────────────────────────────────────┘
         │ writes to
         ↓
┌─────────────────────────────────────────────────────────────┐
│              /usr/local/sentinel/                            │
│              ├── kel/*.cesr                                  │
│              ├── tel/*.cesr                                  │
│              └── cred/*.cesr                                 │
└─────────────────────────────────────────────────────────────┘
         ↑ watches
         │
┌─────────────────────────────────────────────────────────────┐
│            Developer's Standalone App                        │
│            (separate process)                                │
│  Uses sentinel.framework to watch for changes               │
└─────────────────────────────────────────────────────────────┘
```

## API Reference

### EventHandler

Base class for implementing event handlers. All methods are optional.

```python
from sentinel.framework import EventHandler, KELEvent, TELEvent, CredentialEvent

class MyHandler(EventHandler):
    async def on_kel(self, event: KELEvent):
        """Called when a KEL file is new or modified"""
        pass

    async def on_tel(self, event: TELEvent):
        """Called when a TEL file is new or modified"""
        pass

    async def on_credential(self, event: CredentialEvent):
        """Called when a credential file is new or modified"""
        pass
```

**Methods can be sync or async** - async is preferred for I/O operations.

### Event Data Classes

All event types inherit from `BaseEvent` and provide:

```python
@dataclass
class BaseEvent:
    aid: str                        # Identifier prefix (from filename)
    filepath: str                   # Absolute path to .cesr file
    data: bytes                     # Raw CESR file contents
    timestamp: datetime             # File modification time

    # Optional: only populated if run() given KERI infrastructure
    hby: Optional[object] = None    # Habery instance
    essr: Optional[object] = None   # API client
    db: Optional[object] = None     # Database instance
```

**Event Types:**
- `KELEvent` - Key Event Log changes
- `TELEvent` - Transaction Event Log changes
- `CredentialEvent` - Credential changes

### register_handler()

Register a handler with the global registry.

```python
from sentinel.framework import register_handler

handler = MyHandler()
register_handler(handler)
```

### unregister_handler()

Unregister a handler from the global registry.

```python
from sentinel.framework import unregister_handler

unregister_handler(handler)
```

### run()

Main entry point to start the framework. Blocks until SIGINT/SIGTERM received.

```python
from sentinel.framework import run

run(
    export_dir="/usr/local/sentinel",  # Required: directory to watch
    poll_interval=2.0,                  # Optional: polling interval (seconds)
    name=None,                          # Optional: KERI database name
    base="",                            # Optional: KERI database directory
    bran=None,                          # Optional: KERI database passcode
    hby=None,                           # Optional: pre-configured Habery
    essr=None,                          # Optional: pre-configured API client
    db=None,                            # Optional: pre-configured database
)
```

## Usage Patterns

### Pattern 1: Simple Logger (No KERI Dependencies)

```python
#!/usr/bin/env python3
from sentinel.framework import EventHandler, register_handler, run
from sentinel.framework import KELEvent, TELEvent, CredentialEvent

class SimpleLogger(EventHandler):
    async def on_kel(self, event: KELEvent):
        print(f"KEL: {event.aid} ({len(event.data)} bytes)")

    async def on_tel(self, event: TELEvent):
        print(f"TEL: {event.aid}")

    async def on_credential(self, event: CredentialEvent):
        print(f"Credential: {event.aid}")

register_handler(SimpleLogger())

if __name__ == "__main__":
    run(export_dir="/usr/local/sentinel", poll_interval=2.0)
```

### Pattern 2: Multiple Handlers

Handlers execute independently with error isolation.

```python
#!/usr/bin/env python3
from sentinel.framework import EventHandler, register_handler, run
from sentinel.framework import KELEvent

class FileLogger(EventHandler):
    async def on_kel(self, event: KELEvent):
        with open("/var/log/kel.log", "a") as f:
            f.write(f"{event.timestamp} {event.aid}\n")

class MetricsCollector(EventHandler):
    def __init__(self):
        self.count = 0

    async def on_kel(self, event: KELEvent):
        self.count += 1
        print(f"Total KELs: {self.count}")

class AlertSystem(EventHandler):
    def __init__(self, watched_aids):
        self.watched_aids = set(watched_aids)

    async def on_kel(self, event: KELEvent):
        if event.aid in self.watched_aids:
            print(f"ALERT: {event.aid} changed!")

# Register all handlers
register_handler(FileLogger())
register_handler(MetricsCollector())
register_handler(AlertSystem(["EBdXt3g..."]))

if __name__ == "__main__":
    run(export_dir="/usr/local/sentinel")
```

### Pattern 3: KERI Integration

Access KERI infrastructure for deep inspection.

```python
#!/usr/bin/env python3
from sentinel.framework import EventHandler, register_handler, run, KELEvent

class KERIAnalyzer(EventHandler):
    async def on_kel(self, event: KELEvent):
        if event.hby:
            kever = event.hby.kevers.get(event.aid)
            if kever:
                print(f"KEL {event.aid}:")
                print(f"  Sequence: {kever.sner.num}")
                print(f"  Witnesses: {len(kever.wits)}")
            else:
                print(f"KEL {event.aid}: not in local database")
        else:
            print(f"KEL {event.aid}: {len(event.data)} bytes (no KERI)")

register_handler(KERIAnalyzer())

if __name__ == "__main__":
    # Framework will initialize Habery with these parameters
    run(
        export_dir="/usr/local/sentinel",
        name="analyzer_db",        # KERI database name
        base="/tmp/analyzer",       # KERI database location
    )
```

### Pattern 4: Data Processing Pipeline

```python
#!/usr/bin/env python3
import json
from pathlib import Path
from sentinel.framework import EventHandler, register_handler, run
from sentinel.framework import KELEvent

class DataExporter(EventHandler):
    def __init__(self, export_dir: str):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    async def on_kel(self, event: KELEvent):
        # Extract metadata
        metadata = {
            "aid": event.aid,
            "timestamp": event.timestamp.isoformat(),
            "size": len(event.data),
            "filepath": event.filepath,
        }

        # Export to JSON
        output = self.export_dir / f"{event.aid}_{event.timestamp.timestamp()}.json"
        with open(output, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"Exported: {output}")

register_handler(DataExporter(export_dir="/tmp/kel-exports"))

if __name__ == "__main__":
    run(export_dir="/usr/local/sentinel")
```

## Error Handling

The framework provides robust error handling with **handler isolation**:

1. **Handler Exceptions** - If one handler raises an exception, other handlers still execute
2. **File Errors** - If a file read fails, the watcher continues to next file
3. **Service Continuity** - The file watcher continues running despite errors
4. **Comprehensive Logging** - All errors are logged with handler class name and method

Example:

```python
class FailingHandler(EventHandler):
    async def on_kel(self, event: KELEvent):
        raise ValueError("Something went wrong!")

class WorkingHandler(EventHandler):
    async def on_kel(self, event: KELEvent):
        print("This still executes!")

# Both handlers registered - working handler still runs
register_handler(FailingHandler())
register_handler(WorkingHandler())
```

## Performance Considerations

1. **Polling Interval** - Default 2.0 seconds (configurable via `poll_interval`)
2. **File Scanning** - Only scans configured directories (kel/, tel/, cred/)
3. **Change Detection** - Simple mtime-based comparison (O(1) per file)
4. **Handler Dispatch** - Sequential execution (can be made parallel if needed)
5. **Memory Usage** - In-memory state tracking ({filepath: mtime} dictionary)

## Testing Your Handlers

### Unit Testing

```python
import pytest
from datetime import datetime
from sentinel.framework import EventHandler, KELEvent

class TestMyHandler:
    @pytest.mark.asyncio
    async def test_on_kel(self):
        handler = MyHandler()
        event = KELEvent(
            aid="test_aid",
            filepath="/tmp/test.cesr",
            data=b"test data",
            timestamp=datetime.now(),
        )

        await handler.on_kel(event)

        # Assert expected behavior
        assert handler.processed_count == 1
```

### Integration Testing

```python
import tempfile
from pathlib import Path
from sentinel.framework import FileWatchingService, register_handler

@pytest.mark.asyncio
async def test_end_to_end():
    with tempfile.TemporaryDirectory() as tmpdir:
        export_dir = Path(tmpdir)
        (export_dir / "kel").mkdir()

        handler = MyHandler()
        register_handler(handler)

        service = FileWatchingService(
            export_dir=str(export_dir),
            poll_interval=0.1,
        )

        task = service.start()
        await asyncio.sleep(0.2)

        # Create KEL file
        (export_dir / "kel" / "test.cesr").write_bytes(b"data")
        await asyncio.sleep(0.3)

        service.stop()
        await task

        assert len(handler.events) == 1
```

## Examples

Full working examples are available in the `examples/` directory:

- **simple_logger.py** - Basic logging of all events
- **multi_handler.py** - Multiple handlers with different responsibilities
- **keri_analyzer.py** - KERI integration for deep inspection

Run examples:

```bash
python examples/simple_logger.py
python examples/multi_handler.py
python examples/keri_analyzer.py
```

## Troubleshooting

### No events detected

1. Check that export directory exists and has correct subdirectories:
   ```bash
   ls /usr/local/sentinel/kel/
   ls /usr/local/sentinel/tel/
   ls /usr/local/sentinel/cred/
   ```

2. Verify sentinel is running with `--export-dir` flag:
   ```bash
   sentinel start -n mydb -a myalias --export-dir /usr/local/sentinel
   ```

3. Check that handlers are registered before calling `run()`:
   ```python
   register_handler(MyHandler())  # Must be before run()
   run(export_dir="/usr/local/sentinel")
   ```

4. Verify files have `.cesr` extension

### Handler not being called

1. Check that handler method name matches event type:
   - KEL events → `on_kel()`
   - TEL events → `on_tel()`
   - Credentials → `on_credential()`

2. Verify handler is registered:
   ```python
   from sentinel.framework import get_registry
   print(f"Registered handlers: {len(get_registry().get_handlers())}")
   ```

3. Check logs for handler exceptions

### KERI infrastructure not available

If `event.hby` is `None`:

1. Pass `name` parameter to `run()`:
   ```python
   run(export_dir="/usr/local/sentinel", name="mydb")
   ```

2. Check KERI installation:
   ```bash
   python -c "from keri.app import habbing; print('OK')"
   ```

## Best Practices

1. **Keep handlers focused** - Each handler should have a single responsibility
2. **Use async for I/O** - Make handlers async if they perform I/O operations
3. **Handle errors gracefully** - Don't let exceptions propagate
4. **Log important events** - Use Python's logging module
5. **Test handlers independently** - Unit test handlers before integration
6. **Use appropriate poll interval** - Balance responsiveness vs system load
7. **Clean up resources** - Use context managers for file handles, connections
8. **Document handler behavior** - Add docstrings explaining what each handler does

## Future Enhancements

Potential future features:

- Watchdog library support for event-driven file watching
- Event filtering by AID or other criteria
- Parallel handler execution with asyncio.gather
- Batch event processing
- Event persistence for replay/debugging
- Handler priorities
- Handler lifecycle management (setup/teardown)
- Execution metrics (timing, error rates)
- Remote event dispatch (webhooks, message queues)

## Support

For issues, questions, or contributions:

- GitHub Issues: https://github.com/pfeairheller/sentinel/issues
- Documentation: https://github.com/pfeairheller/sentinel/tree/main/docs

## License

This framework is part of the Sentinel project and follows the same license.

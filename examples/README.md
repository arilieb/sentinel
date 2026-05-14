# Sentinel Framework Examples

This directory contains example applications demonstrating the Sentinel Framework.

## Prerequisites

1. **Sentinel installed and running:**
   ```bash
   sentinel start -n mydb -a myalias --export-dir /tmp/sentinel-export
   ```

2. **Python environment with sentinel installed:**
   ```bash
   pip install -e .
   ```

## Examples

### 1. Simple Logger (`simple_logger.py`)

Basic example that logs all KEL/TEL/Credential events to stdout.

**Features:**
- No KERI dependencies required
- Logs all three event types
- Simple output format

**Usage:**
```bash
python examples/simple_logger.py
```

**Output:**
```
=== KEL Event ===
AID: EBdXt3gIXOf2BBWNHdSXCJnFJL5OuQPyM5K0neuniccM
File: /tmp/sentinel-export/kel/EBdXt3gIXOf2BBWNHdSXCJnFJL5OuQPyM5K0neuniccM.cesr
Size: 1234 bytes
Time: 2024-01-15 10:30:45.123456
=================
```

### 2. Multi-Handler (`multi_handler.py`)

Demonstrates using multiple handlers simultaneously with different responsibilities.

**Features:**
- Multiple independent handlers
- Error isolation between handlers
- Different handler types (logger, metrics, alerts, exporter)

**Handlers:**
- `FileLogger` - Logs events to `/tmp/sentinel-events.log`
- `MetricsCollector` - Counts events and prints totals
- `AlertSystem` - Alerts on specific AIDs
- `DataExporter` - Exports metadata to JSON files in `/tmp/sentinel-exports`

**Usage:**
```bash
python examples/multi_handler.py
```

**Customize watched AIDs:**
```python
# Edit multi_handler.py
register_handler(
    AlertSystem(
        watched_aids=[
            "EBdXt3gIXOf2BBWNHdSXCJnFJL5OuQPyM5K0neuniccM",  # Your AID here
        ]
    )
)
```

### 3. KERI Analyzer (`keri_analyzer.py`)

Advanced example with KERI infrastructure integration for deep inspection.

**Features:**
- Accesses KERI Habery instance
- Queries key event state
- Displays witness information
- Creates separate KERI database

**Usage:**
```bash
python examples/keri_analyzer.py
```

**Output:**
```
=== Analyzing KEL: EBdXt3g... ===
File: /tmp/sentinel-export/kel/EBdXt3g....cesr
Size: 1234 bytes
Time: 2024-01-15 10:30:45

KERI Analysis:
  Sequence: 5
  Witnesses: 3
  Witness list: ['BBilc4...', 'BLskR...', 'BIKKu...']
  Keys: [Verfer(qb64=...)]
==================================================
```

**Notes:**
- Creates database at `/tmp/keri-analyzer`
- Requires KERI library installed
- Independent from sentinel's database

## Testing Examples

### Terminal Setup

**Terminal 1 - Sentinel Service:**
```bash
# Start sentinel with export directory
sentinel start -n testdb -a testalias --export-dir /tmp/sentinel-export
```

**Terminal 2 - Your Application:**
```bash
# Run one of the examples
python examples/simple_logger.py

# Or
python examples/multi_handler.py

# Or
python examples/keri_analyzer.py
```

**Terminal 3 - Trigger Events:**
```bash
# Manually create test files
echo "test data" > /tmp/sentinel-export/kel/test_aid.cesr

# Or trigger via sentinel operations
sentinel watch add -n testdb --aid EBdXt3g... --alias watched_entity
# This will sync KEL and trigger events
```

## Customizing Examples

### Change Export Directory

All examples default to `/tmp/sentinel-export`. To change:

```python
# Edit the run() call in any example
run(
    export_dir="/your/custom/path",  # Change this
    poll_interval=2.0,
)
```

### Adjust Poll Interval

For faster detection (uses more CPU):
```python
run(export_dir="/tmp/sentinel-export", poll_interval=0.5)  # 500ms
```

For slower detection (uses less CPU):
```python
run(export_dir="/tmp/sentinel-export", poll_interval=5.0)  # 5 seconds
```

### Add Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now framework will log all operations
run(export_dir="/tmp/sentinel-export")
```

## Creating Your Own Application

1. **Start with simple_logger.py as a template:**
   ```bash
   cp examples/simple_logger.py myapp.py
   ```

2. **Customize the handler:**
   ```python
   class MyHandler(EventHandler):
       async def on_kel(self, event: KELEvent):
           # Your custom logic here
           pass
   ```

3. **Run your app:**
   ```bash
   python myapp.py
   ```

## Common Issues

### No events detected

- Check sentinel is running with `--export-dir` flag
- Verify export directory exists: `ls /tmp/sentinel-export/kel/`
- Check permissions on export directory
- Trigger an event manually to test

### Handler errors

- Check logs for exceptions
- Verify handler methods are properly named (`on_kel`, `on_tel`, `on_credential`)
- Test handler independently before integration

### KERI errors (keri_analyzer.py)

- Verify KERI library installed: `python -c "from keri.app import habbing"`
- Check database directory permissions
- Use different database name to avoid conflicts

## Next Steps

1. Read the full framework documentation: `docs/framework.md`
2. Review the test suite: `tests/framework/`
3. Build your own application using these examples as templates
4. Share your application with the community!

## Support

- Framework Documentation: `docs/framework.md`
- GitHub Issues: https://github.com/pfeairheller/sentinel/issues

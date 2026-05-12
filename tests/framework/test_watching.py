"""
Tests for framework file watching service
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
from sentinel.framework.watching import FileWatchingService
from sentinel.framework.handlers import EventHandler
from sentinel.framework.events import KELEvent, TELEvent, CredentialEvent
from sentinel.framework.registry import register_handler, get_registry


class CollectingHandler(EventHandler):
    """Test handler that collects events"""

    def __init__(self):
        self.kel_events = []
        self.tel_events = []
        self.cred_events = []

    async def on_kel(self, event: KELEvent):
        self.kel_events.append(event)

    async def on_tel(self, event: TELEvent):
        self.tel_events.append(event)

    async def on_credential(self, event: CredentialEvent):
        self.cred_events.append(event)


@pytest.fixture
def temp_export_dir():
    """Create temporary export directory structure"""
    with tempfile.TemporaryDirectory() as tmpdir:
        export_dir = Path(tmpdir)
        (export_dir / "kel").mkdir()
        (export_dir / "tel").mkdir()
        (export_dir / "cred").mkdir()
        yield export_dir


@pytest.fixture
def handler():
    """Create and register a collecting handler"""
    # Clear registry
    registry = get_registry()
    registry._handlers = set()

    # Create and register handler
    h = CollectingHandler()
    register_handler(h)
    yield h

    # Cleanup
    registry._handlers = set()


class TestFileWatchingService:
    """Test FileWatchingService"""

    def test_service_initialization(self, temp_export_dir):
        """Test service can be initialized"""
        service = FileWatchingService(
            export_dir=str(temp_export_dir),
            poll_interval=0.1,
        )
        assert service.export_dir == temp_export_dir
        assert service.poll_interval == 0.1
        assert service._running is False
        assert len(service._file_state) == 0

    def test_watch_dirs_created(self, temp_export_dir):
        """Test that watch directories are configured"""
        service = FileWatchingService(export_dir=str(temp_export_dir))
        assert "kel" in service.watch_dirs
        assert "tel" in service.watch_dirs
        assert "credential" in service.watch_dirs
        assert service.watch_dirs["kel"] == temp_export_dir / "kel"
        assert service.watch_dirs["credential"] == temp_export_dir / "cred"

    @pytest.mark.asyncio
    async def test_detect_new_kel_file(self, temp_export_dir, handler):
        """Test detecting a new KEL file"""
        service = FileWatchingService(
            export_dir=str(temp_export_dir),
            poll_interval=0.1,
        )

        # Start service
        task = service.start()

        # Give service time to start
        await asyncio.sleep(0.2)

        # Create a KEL file
        kel_file = temp_export_dir / "kel" / "test_aid.cesr"
        kel_file.write_bytes(b"test kel data")

        # Wait for polling
        await asyncio.sleep(0.3)

        # Stop service
        service.stop()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        # Check that event was dispatched
        assert len(handler.kel_events) == 1
        event = handler.kel_events[0]
        assert event.aid == "test_aid"
        assert event.data == b"test kel data"
        assert event.filepath == str(kel_file)

    @pytest.mark.asyncio
    async def test_detect_modified_kel_file(self, temp_export_dir, handler):
        """Test detecting a modified KEL file"""
        service = FileWatchingService(
            export_dir=str(temp_export_dir),
            poll_interval=0.1,
        )

        # Create a KEL file before starting service
        kel_file = temp_export_dir / "kel" / "test_aid.cesr"
        kel_file.write_bytes(b"initial data")

        # Start service
        task = service.start()
        await asyncio.sleep(0.2)

        # Should detect initial file
        assert len(handler.kel_events) == 1

        # Modify file
        await asyncio.sleep(0.2)
        kel_file.write_bytes(b"modified data")

        # Wait for polling
        await asyncio.sleep(0.3)

        # Stop service
        service.stop()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        # Check that both events were dispatched
        assert len(handler.kel_events) == 2
        assert handler.kel_events[0].data == b"initial data"
        assert handler.kel_events[1].data == b"modified data"

    @pytest.mark.asyncio
    async def test_detect_tel_file(self, temp_export_dir, handler):
        """Test detecting TEL file"""
        service = FileWatchingService(
            export_dir=str(temp_export_dir),
            poll_interval=0.1,
        )

        task = service.start()
        await asyncio.sleep(0.2)

        # Create TEL file
        tel_file = temp_export_dir / "tel" / "test_tel.cesr"
        tel_file.write_bytes(b"tel data")

        await asyncio.sleep(0.3)

        service.stop()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert len(handler.tel_events) == 1
        assert handler.tel_events[0].aid == "test_tel"

    @pytest.mark.asyncio
    async def test_detect_credential_file(self, temp_export_dir, handler):
        """Test detecting credential file"""
        service = FileWatchingService(
            export_dir=str(temp_export_dir),
            poll_interval=0.1,
        )

        task = service.start()
        await asyncio.sleep(0.2)

        # Create credential file
        cred_file = temp_export_dir / "cred" / "test_cred.cesr"
        cred_file.write_bytes(b"cred data")

        await asyncio.sleep(0.3)

        service.stop()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert len(handler.cred_events) == 1
        assert handler.cred_events[0].aid == "test_cred"

    @pytest.mark.asyncio
    async def test_no_duplicate_events_for_unchanged_files(
        self, temp_export_dir, handler
    ):
        """Test that unchanged files don't trigger events"""
        service = FileWatchingService(
            export_dir=str(temp_export_dir),
            poll_interval=0.1,
        )

        # Create file
        kel_file = temp_export_dir / "kel" / "test_aid.cesr"
        kel_file.write_bytes(b"data")

        task = service.start()

        # Wait for multiple poll cycles
        await asyncio.sleep(0.5)

        service.stop()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        # Should only have one event (initial detection)
        assert len(handler.kel_events) == 1

    @pytest.mark.asyncio
    async def test_service_with_keri_infrastructure(self, temp_export_dir, handler):
        """Test that KERI infrastructure is passed to events"""
        mock_hby = object()
        mock_essr = object()
        mock_db = object()

        service = FileWatchingService(
            export_dir=str(temp_export_dir),
            poll_interval=0.1,
            hby=mock_hby,
            essr=mock_essr,
            db=mock_db,
        )

        task = service.start()
        await asyncio.sleep(0.2)

        kel_file = temp_export_dir / "kel" / "test.cesr"
        kel_file.write_bytes(b"data")

        await asyncio.sleep(0.3)

        service.stop()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()

        assert len(handler.kel_events) == 1
        event = handler.kel_events[0]
        assert event.hby is mock_hby
        assert event.essr is mock_essr
        assert event.db is mock_db

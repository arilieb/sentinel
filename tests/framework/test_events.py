"""
Tests for framework event data classes
"""

import pytest
from datetime import datetime
from sentinel.framework.events import BaseEvent, KELEvent, TELEvent, CredentialEvent


def test_base_event_creation():
    """Test BaseEvent can be created with required fields"""
    event = BaseEvent(
        aid="EBdXt3gIXOf2BBWNHdSXCJnFJL5OuQPyM5K0neuniccM",
        filepath="/tmp/test.cesr",
        data=b"test data",
        timestamp=datetime.now(),
    )
    assert event.aid == "EBdXt3gIXOf2BBWNHdSXCJnFJL5OuQPyM5K0neuniccM"
    assert event.filepath == "/tmp/test.cesr"
    assert event.data == b"test data"
    assert isinstance(event.timestamp, datetime)
    assert event.hby is None
    assert event.essr is None
    assert event.db is None


def test_base_event_with_optional_fields():
    """Test BaseEvent with optional KERI infrastructure fields"""
    mock_hby = object()
    mock_essr = object()
    mock_db = object()

    event = BaseEvent(
        aid="test_aid",
        filepath="/tmp/test.cesr",
        data=b"test",
        timestamp=datetime.now(),
        hby=mock_hby,
        essr=mock_essr,
        db=mock_db,
    )
    assert event.hby is mock_hby
    assert event.essr is mock_essr
    assert event.db is mock_db


def test_kel_event_creation():
    """Test KELEvent creation"""
    event = KELEvent(
        aid="test_kel",
        filepath="/tmp/kel/test.cesr",
        data=b"kel data",
        timestamp=datetime.now(),
    )
    assert isinstance(event, BaseEvent)
    assert event.aid == "test_kel"
    assert event.filepath == "/tmp/kel/test.cesr"


def test_tel_event_creation():
    """Test TELEvent creation"""
    event = TELEvent(
        aid="test_tel",
        filepath="/tmp/tel/test.cesr",
        data=b"tel data",
        timestamp=datetime.now(),
    )
    assert isinstance(event, BaseEvent)
    assert event.aid == "test_tel"
    assert event.filepath == "/tmp/tel/test.cesr"


def test_credential_event_creation():
    """Test CredentialEvent creation"""
    event = CredentialEvent(
        aid="test_cred",
        filepath="/tmp/cred/test.cesr",
        data=b"cred data",
        timestamp=datetime.now(),
    )
    assert isinstance(event, BaseEvent)
    assert event.aid == "test_cred"
    assert event.filepath == "/tmp/cred/test.cesr"

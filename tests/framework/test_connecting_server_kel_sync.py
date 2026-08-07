# -*- encoding: utf-8 -*-
"""
Tests for connect_to_healthkeri's post-rotation server_kel sync -- the fix for
guardian/server AIDs never being resolvable via hkweb's
RegistrarService.get_oobi_cesr, because the only upload of the guardian's KEL
happened *before* witness rotation (see connecting.py's inline comment).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sentinel.framework import connecting


class FakeResponse:
    def __init__(self, status_code=201, content=b"{}"):
        self.status_code = status_code
        self.content = content
        self.text = ""

    def json(self):
        return {}


def _make_config():
    config = MagicMock()
    config.root_oobi = "http://witness/oobi/root"
    config.api_oobi = "http://witness/oobi/api"
    config.root_aid = "ERootAID"
    config.api_aid = "EApiAID"
    config.unprotected_url = "http://unprotected"
    config.protected_url = "http://protected"
    return config


def _make_sentinel_hab(config):
    hab = MagicMock()
    hab.pre = "ESentinelAID"
    hab.kevers = {config.root_aid: object(), config.api_aid: object()}
    hab.psr.parse = MagicMock()
    hab.kvy.processEscrows = MagicMock()
    hab.replyToOobi = MagicMock(return_value=b"sentinel-controller-reply")
    return hab


def _make_server_hab():
    hab = MagicMock()
    hab.pre = "EServerAID"
    hab.replyToOobi = MagicMock(return_value=b"server-sn0-controller-reply")
    hab.db.clonePreIter = MagicMock(return_value=[b"icp-msg", b"rot-msg"])
    return hab


@pytest.mark.asyncio
async def test_connect_to_healthkeri_syncs_server_kel_after_rotation():
    """After rotate_witness succeeds, the guardian's full (post-rotation) KEL
    is PUT to /servers/{sentinel_hab.pre} via essr -- not the sn=0 KEL used
    for the earlier /account/teams/servers registration."""
    config = _make_config()
    sentinel_hab = _make_sentinel_hab(config)
    server_hab = _make_server_hab()

    essr_instance = MagicMock()
    essr_instance.request = AsyncMock(return_value=FakeResponse(status_code=204))

    mock_rotate_witness = AsyncMock()

    with (
        patch.object(connecting, "HealthKERIConfig") as mock_config_cls,
        patch("sentinel.framework.connecting.requests") as mock_requests,
        patch.object(connecting, "APIClient", return_value=essr_instance),
        patch.object(
            connecting,
            "reserve_witness_for_server",
            new=AsyncMock(
                return_value={
                    "eid": "EWitnessAID",
                    "name": "wit0",
                    "oobi": "http://witness-host/oobi/EWitnessAID/witness",
                }
            ),
        ),
        patch.object(connecting, "load_oobi"),
        patch.object(connecting, "authenticate_witness", return_value="123456"),
        patch.object(connecting, "rotate_witness", new=mock_rotate_witness),
    ):

        mock_config_cls.get_instance.return_value = config
        mock_requests.get.return_value = FakeResponse(
            status_code=200, content=b"oobi-bytes"
        )
        mock_requests.post.return_value = FakeResponse(status_code=201)

        result = await connecting.connect_to_healthkeri(
            server_name="peer1-server",
            sentinel_hby=MagicMock(),
            sentinel_hab=sentinel_hab,
            auth_key="test-auth-code",
            server_hby=MagicMock(),
            server_hab=server_hab,
            witness=True,
        )

        # Rotation must have already happened before the sync call fires.
        mock_rotate_witness.assert_awaited_once()

    # The sync call went to /servers/{sentinel_hab.pre} (matches
    # SecureTeamServerResourceEnd's `get_server_by_aid` lookup, which is keyed
    # by TeamServer.aid == sentinel_hab.pre, not server_hab.pre).
    essr_instance.request.assert_awaited_once()
    call = essr_instance.request.await_args
    assert call.kwargs["path"] == f"/servers/{sentinel_hab.pre}"
    assert call.kwargs["method"] == "PUT"

    # Uploaded bytes are the *full* post-rotation KEL (clonePreIter's icp+rot),
    # not the sn=0-only replyToOobi snapshot used for the pre-rotation upload.
    uploaded = call.kwargs["files"]["server_kel"][1]
    assert uploaded == b"icp-msgrot-msg"

    assert result["guardian_oobi"].startswith(
        "http://witness-host/oobi/EServerAID/witness/"
    )


@pytest.mark.asyncio
async def test_connect_to_healthkeri_kel_sync_failure_is_non_fatal():
    """A failed sync PUT (network error, non-2xx) must not fail provisioning --
    the guardian AID is already correctly witnessed; only cross-peer
    resolution of connection credentials depends on the sync succeeding."""
    config = _make_config()
    sentinel_hab = _make_sentinel_hab(config)
    server_hab = _make_server_hab()

    essr_instance = MagicMock()
    essr_instance.request = AsyncMock(side_effect=RuntimeError("network error"))

    with (
        patch.object(connecting, "HealthKERIConfig") as mock_config_cls,
        patch("sentinel.framework.connecting.requests") as mock_requests,
        patch.object(connecting, "APIClient", return_value=essr_instance),
        patch.object(
            connecting,
            "reserve_witness_for_server",
            new=AsyncMock(
                return_value={
                    "eid": "EWitnessAID",
                    "name": "wit0",
                    "oobi": "http://witness-host/oobi/EWitnessAID/witness",
                }
            ),
        ),
        patch.object(connecting, "load_oobi"),
        patch.object(connecting, "authenticate_witness", return_value="123456"),
        patch.object(connecting, "rotate_witness", new=AsyncMock()),
    ):

        mock_config_cls.get_instance.return_value = config
        mock_requests.get.return_value = FakeResponse(
            status_code=200, content=b"oobi-bytes"
        )
        mock_requests.post.return_value = FakeResponse(status_code=201)

        # Must not raise despite the essr.request failure above.
        result = await connecting.connect_to_healthkeri(
            server_name="peer1-server",
            sentinel_hby=MagicMock(),
            sentinel_hab=sentinel_hab,
            auth_key="test-auth-code",
            server_hby=MagicMock(),
            server_hab=server_hab,
            witness=True,
        )

    assert result["witness_aid"] == "EWitnessAID"

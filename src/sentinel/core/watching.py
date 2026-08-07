# -*- encoding: utf-8 -*-
"""
sentinel.core.watching module

Functions and services for managing healthKERI account watchers
"""

import asyncio
import httpx
import os
import random
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Set

from kept.hk.essring import APIClient
from keri import help, kering
from keri.app.connecting import Organizer
from keri.app.habbing import Habery
from keri.core import coring, parsing
from keri.vdr.credentialing import Regery

from sentinel.core import filing, remoting
from sentinel.core.credentialing import CredentialLoader, SaaSCredentialLoader

logger = help.ogler.getLogger()


async def fetch_account_watched(
    essr,
    page: int = 0,
    page_size: int = 10,
    filter_term: Optional[str] = None,
    order: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Fetch account watchers from the healthKERI API.

    Args:
        hby: Habery instance for managing healthKERI accounts
        essr: APIClient instance for interacting with healthKERI API
        page: Page number (0-indexed)
        page_size: Number of items per page
        filter_term: Optional filter/search term
        order: Optional list of sort orders (e.g., ['+name', '-eid'])

    Returns:
        API response with watchers data
    """
    try:
        # Build query parameters
        params = [f"page={page}", f"page_size={page_size}"]

        if filter_term:
            params.append(f"filter={urllib.parse.quote(filter_term)}")

        if order:
            for o in order:
                params.append(f"order={urllib.parse.quote(o)}")

        path = f"/watched?{'&'.join(params)}"

        # Make async request - APIClient.request is the async method
        response = await essr.request(path=path, method="GET")
        if response and response.status_code == 200:
            data = response.json()
            data["success"] = True
            return data
        else:
            return {
                "success": False,
                "error": f"API error: {response.status_code if response else 'No response'}",
            }

    except Exception as e:
        logger.error(f"Error fetching watched identifiers: {e}")
        return {"success": False, "error": str(e)}


async def delete_account_watcher(essr, eid: str) -> Dict[str, Any]:
    """
    Delete a watcher from the healthKERI account.

    Args:
        essr: ESSR connection instance
        eid: ID of the watcher to delete

    Returns:
        Dict with 'success' and optional 'error'
    """

    try:
        # APIClient.request is the async method
        response = await essr.request(path=f"/watched/{eid}", method="DELETE")

        if response and response.status_code == 204:
            return {"success": True}
        else:
            error_msg = "Unknown error"
            if response:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("description", str(response.status_code))
                except Exception:
                    error_msg = f"Status {response.status_code}"
            return {"success": False, "error": error_msg}

    except Exception as e:
        logger.error(f"Error deleting account watcher: {e}")
        return {"success": False, "error": str(e)}


async def resolve_identifier_kel(
    hby,
    aid: str,
    registrar_url: Optional[str] = None,
    export_dir: Optional[str] = None,
) -> dict:
    """
    Resolve and load KEL for an identifier from registrar if not already in kevers.

    Args:
        hby: Habery instance
        aid: Identifier to resolve
        registrar_url: URL of registrar to fetch OOBI from
        export_dir: Directory to export KEL to after loading

    Returns:
        Dict with 'success' and optional 'error'
    """
    try:
        # Check if identifier already in kevers
        if aid in hby.kevers:
            logger.debug(f"Identifier {aid} already in kevers, no resolution needed")
            return {"success": True}

        # If no registrar_url, cannot resolve
        if not registrar_url:
            logger.error(
                f"Identifier {aid} not in kevers and no registrar_url provided"
            )
            return {
                "success": False,
                "error": "Identifier not found and no registrar URL available",
            }

        logger.info(
            f"Identifier {aid} not in kevers, attempting OOBI resolution from registrar"
        )

        # Fetch OOBI from registrar
        oobi_url = f"{registrar_url.rstrip('/')}/oobi/{aid}"
        logger.info(f"Fetching OOBI from {oobi_url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(oobi_url)

                if response.status_code == 404:
                    logger.error(f"OOBI not found for {aid} at registrar")
                    return {
                        "success": False,
                        "error": f"Identifier {aid} not found at registrar",
                    }

                if response.status_code != 200:
                    logger.error(
                        f"Failed to fetch OOBI for {aid}: status {response.status_code}"
                    )
                    return {
                        "success": False,
                        "error": f"Failed to fetch OOBI (status {response.status_code})",
                    }

                oobi_data = response.content
                logger.debug(
                    f"Successfully fetched OOBI for {aid} ({len(oobi_data)} bytes)"
                )

            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching OOBI for {aid}: {e}")
                return {
                    "success": False,
                    "error": "Network error fetching OOBI from registrar",
                }

        # Parse OOBI to load KEL
        logger.debug(f"Parsing OOBI data for {aid}")
        hby.psr.parse(oobi_data)
        hby.kvy.processEscrows()
        if hasattr(hby, "rvy") and hby.rvy:
            hby.rvy.processEscrowReply()

        # Verify KEL loaded successfully
        if aid not in hby.kevers:
            logger.error(f"Failed to load KEL for {aid} after OOBI resolution")
            return {
                "success": False,
                "error": f"Identifier {aid} could not be resolved",
            }

        logger.info(f"Successfully resolved OOBI for {aid}")

        # Export KEL to filesystem if export_dir provided
        if export_dir:
            try:
                success = await filing.export_kel(
                    hby=hby, aid=aid, export_dir=export_dir
                )
                if success:
                    logger.info(f"Successfully exported KEL for {aid}")
                else:
                    logger.warning(f"Failed to export KEL for {aid}")
            except Exception as e:
                logger.error(f"Error exporting KEL for {aid}: {e}")
                # Continue - export failure shouldn't block resolution

        return {"success": True}

    except Exception as e:
        logger.error(f"Error resolving identifier KEL for {aid}: {e}")
        return {"success": False, "error": str(e)}


async def resolve_identifier_via_essr(
    hby,
    essr,
    aid: str,
    export_dir: Optional[str] = None,
) -> dict:
    """
    Resolve and load KEL for an identifier via the ESSR-authenticated
    healthKERI registrar API, for use when no plain-HTTP registrar_url is
    available (SaaS/healthKERI mode) -- hkweb's /registrar/oobi/{aid} route
    sits behind signature-validation middleware, so a plain httpx GET (as
    resolve_identifier_kel does against registrar_url) cannot reach it; the
    caller's own essr client must be used instead.

    Args:
        hby: Habery instance
        essr: APIClient instance for interacting with healthKERI API
        aid: Identifier to resolve
        export_dir: Directory to export KEL to after loading

    Returns:
        Dict with 'success' and optional 'error'
    """
    try:
        # Check if identifier already in kevers
        if aid in hby.kevers:
            logger.debug(f"Identifier {aid} already in kevers, no resolution needed")
            return {"success": True}

        # If no essr, cannot resolve
        if not essr:
            logger.error(f"Identifier {aid} not in kevers and no essr client provided")
            return {
                "success": False,
                "error": "Identifier not found and no ESSR client available",
            }

        logger.info(
            f"Identifier {aid} not in kevers, attempting OOBI resolution via ESSR"
        )

        try:
            response = await essr.request(path=f"/registrar/oobi/{aid}", method="GET")
        except Exception as e:
            logger.error(f"ESSR error fetching OOBI for {aid}: {e}")
            return {
                "success": False,
                "error": "Network error fetching OOBI via ESSR",
            }

        if response is None:
            logger.error(f"No response fetching OOBI for {aid} via ESSR")
            return {
                "success": False,
                "error": "No response fetching OOBI via ESSR",
            }

        if response.status_code == 404:
            logger.error(f"OOBI not found for {aid} via ESSR registrar")
            return {
                "success": False,
                "error": f"Identifier {aid} not found at registrar",
            }

        if response.status_code != 200:
            logger.error(
                f"Failed to fetch OOBI for {aid} via ESSR: status {response.status_code}"
            )
            return {
                "success": False,
                "error": f"Failed to fetch OOBI (status {response.status_code})",
            }

        oobi_data = response.content
        logger.debug(
            f"Successfully fetched OOBI for {aid} via ESSR ({len(oobi_data)} bytes)"
        )

        # Parse OOBI to load KEL
        logger.debug(f"Parsing OOBI data for {aid}")
        hby.psr.parse(oobi_data)
        hby.kvy.processEscrows()
        if hasattr(hby, "rvy") and hby.rvy:
            hby.rvy.processEscrowReply()

        # Verify KEL loaded successfully
        if aid not in hby.kevers:
            logger.error(f"Failed to load KEL for {aid} after ESSR OOBI resolution")
            return {
                "success": False,
                "error": f"Identifier {aid} could not be resolved",
            }

        logger.info(f"Successfully resolved OOBI for {aid} via ESSR")

        # Export KEL to filesystem if export_dir provided
        if export_dir:
            try:
                success = await filing.export_kel(
                    hby=hby, aid=aid, export_dir=export_dir
                )
                if success:
                    logger.info(f"Successfully exported KEL for {aid}")
                else:
                    logger.warning(f"Failed to export KEL for {aid}")
            except Exception as e:
                logger.error(f"Error exporting KEL for {aid}: {e}")
                # Continue - export failure shouldn't block resolution

        return {"success": True}

    except Exception as e:
        logger.error(f"Error resolving identifier KEL via ESSR for {aid}: {e}")
        return {"success": False, "error": str(e)}


async def resolve_registrar_identity(
    hby,
    essr,
    export_dir: Optional[str] = None,
) -> dict:
    """
    Pre-trust hkweb's SaaS registrar identity (its own hab, distinct from
    `root_aid`/`api_aid`) before resolving any other OOBIs through it.

    `RegistrarService.get_oobi_cesr()` (hkweb's `/registrar/oobi/{aid}`)
    calls `hab.replyToOobi(aid=aid, role=witness)` on the *registrar's own*
    hab -- for any watched AID the registrar itself doesn't witness, this
    embeds a fresh `/end/role/add` reply signed by that hab (see
    `keri.app.habbing.Habitat.replyEndRole`'s `makeEndRole` branch). If this
    sentinel has never resolved the registrar's own key state, `Revery`
    verifies that signed reply against an unknown signer and escrows it
    forever (`Revery: escrowing without key state for signer`, retried by
    the `Escrower` every poll with no way to ever resolve).

    Calls `GET /registrar` to learn the registrar hab's AID (this is exactly
    what `RegistrarService.get_identity()` exists for -- see its docstring),
    then resolves that AID's own KEL the same way any other watched
    identifier is resolved via ESSR. Safe/idempotent to call repeatedly.

    Returns:
        Dict with 'success' and optional 'error'. Never raises.
    """
    try:
        response = await essr.request(path="/registrar", method="GET")
    except Exception as e:
        logger.error(f"Error fetching registrar identity: {e}")
        return {"success": False, "error": "Network error fetching registrar identity"}

    if response is None or response.status_code != 200:
        status = response.status_code if response else "No response"
        logger.error(f"Failed to fetch registrar identity: {status}")
        return {
            "success": False,
            "error": f"Failed to fetch registrar identity ({status})",
        }

    registrar_aid = response.json().get("aid")
    if not registrar_aid:
        logger.error("Registrar identity response missing 'aid'")
        return {"success": False, "error": "Registrar identity response missing 'aid'"}

    result = await resolve_identifier_via_essr(
        hby=hby, essr=essr, aid=registrar_aid, export_dir=export_dir
    )
    if not result.get("success"):
        logger.error(
            f"Failed to resolve registrar identity {registrar_aid}: {result.get('error')}"
        )
        return result

    logger.info(f"Resolved and trusted registrar identity {registrar_aid}")
    return {"success": True}


async def add_watched_identifier(
    hby,
    essr,
    watched_aid: str,
    alias: str,
    registrar_url: Optional[str] = None,
    export_dir: Optional[str] = None,
    _retry_count: int = 0,
) -> dict:
    try:
        # Guard against infinite recursion
        MAX_RETRY_COUNT = 1
        if _retry_count > MAX_RETRY_COUNT:
            logger.error(f"Maximum retry count exceeded for {watched_aid}")
            raise ValueError(
                f"Failed to add watched identifier {watched_aid} after retry"
            )

        # Verify watched identifier is in kevers
        if watched_aid not in hby.kevers:
            # Attempt OOBI resolution if this is first try and a resolver is
            # available: registrar_url (self-hosted "registrar" mode, plain
            # HTTP) takes precedence when present; otherwise fall back to
            # essr (healthKERI SaaS mode, ESSR-authenticated) if given.
            if _retry_count == 0 and (registrar_url or essr):
                if registrar_url:
                    result = await resolve_identifier_kel(
                        hby=hby,
                        aid=watched_aid,
                        registrar_url=registrar_url,
                        export_dir=export_dir,
                    )
                else:
                    result = await resolve_identifier_via_essr(
                        hby=hby,
                        essr=essr,
                        aid=watched_aid,
                        export_dir=export_dir,
                    )

                if not result.get("success"):
                    raise ValueError(
                        result.get("error", "Failed to resolve identifier")
                    )

                # Retry with incremented counter
                return await add_watched_identifier(
                    hby=hby,
                    essr=essr,
                    watched_aid=watched_aid,
                    alias=alias,
                    registrar_url=registrar_url,
                    export_dir=export_dir,
                    _retry_count=_retry_count + 1,
                )
            else:
                # No registrar_url/essr or already retried
                raise ValueError(
                    f"Watched identifier {watched_aid} not found in KERI database"
                )

        kever = hby.kevers[watched_aid]

        # Verify watched identifier has witnesses
        if not kever.wits:
            raise ValueError(
                f"Watched identifier {watched_aid} does not have witnesses"
            )

        wit = random.choice(kever.wits)
        urls = {
            keys[1]: loc.url
            for keys, loc in hby.db.locs.getItemIter(keys=(wit,))
            if loc.url
        }
        if not urls:
            raise ValueError(f"unable to query witness {wit}, no http endpoint")

        url = (
            urls[kering.Schemes.https]
            if kering.Schemes.https in urls
            else urls[kering.Schemes.http]
        )
        oobi = f"{url.rstrip("/")}/oobi/{kever.serder.pre}/witness"

        doc = {"name": alias, "aid": watched_aid, "oobi": oobi}

        # APIClient.request is the async method
        response = await essr.request(path="/watched", method="POST", json=doc)

        if response and response.status_code in (204, 200, 201):
            return {"success": True}
        else:
            error_msg = "Unknown error"
            if response:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("description", str(response.status_code))
                except Exception:
                    error_msg = f"Status {response.status_code}"
            return {"success": False, "error": error_msg}

    except Exception as e:
        logger.error(f"Error adding watched identifier: {e}")
        return {"success": False, "error": str(e)}


class WatchedAdjudicationPoller:
    """
    Background asyncio task that polls for adjudications of watched identifiers.

    Checks the ESSR service for new adjudications after the last poll time,
    compares remote sequence numbers with local state, and creates notifications
    when watched identifiers are out of sync (local state is behind remote).

    The poll datetime is stored in the healthKERI database's watched_poll table.
    """

    def __init__(
        self,
        hby: Habery,
        rgy: Regery,
        essr: APIClient,
        db,
        poll_interval: float = 30.0,
        export_dir: str = "/usr/local/sentinel",
        registrar_url: Optional[str] = None,
        saas_loader: Optional[SaaSCredentialLoader] = None,
    ):
        """
        Initialize the WatchedAdjudicationPoller.

        Args:
            hby: Habery instance for managing healthKERI accounts
            essr: APIClient instance for interacting with healthKERI API
            db: Database instance with watched_poll table
            poll_interval: Polling interval in seconds (default: 30 seconds)
            export_dir: Directory for exporting CESR files (default: /usr/local/sentinel)
            registrar_url: URL for credential registrar API (local mode, default: None)
            saas_loader: SaaSCredentialLoader for SaaS mode (takes priority over registrar_url)

        """
        self.hby = hby
        self.essr = essr
        if saas_loader is not None:
            self.credential_loader = saas_loader
        elif registrar_url:
            self.credential_loader = CredentialLoader(
                hby, self.essr.hab, rgy, export_dir, registrar_url
            )
        else:
            self.credential_loader = None

        self.db = db
        self.poll_interval = poll_interval
        self.export_dir = export_dir

        self.query_done = True
        self._task = None
        self._running = False
        # watched_aid -> highest remote_sn seen for it that we have not yet
        # locally caught up to. A resync attempt can leave the newest event
        # sitting in escrow (e.g. insufficient witness receipts at fetch
        # time) without raising, so "we synced" and "we caught up" are not
        # the same thing. The `/adjudications?date=...` checkpoint (see
        # `_async_poll_adjudications`) only re-surfaces an adjudication
        # while it's newer than the last-seen date, so once that checkpoint
        # advances past it, an AID stuck in escrow would otherwise never be
        # retried again. This dict keeps retrying such AIDs every poll cycle
        # independent of whether the adjudications feed mentions them again.
        self._pending_resync: Dict[str, int] = {}

    async def run(self):
        """
        Main asyncio loop that polls for adjudications on a timer.

        This method:
        1. Runs in an infinite loop with poll_interval sleep
        2. Reads the last poll datetime from watched_poll database
        3. Queries ESSR for adjudications after that datetime
        4. For each adjudication, checks if local state is out of sync
        5. Syncs out-of-sync watched identifiers
        6. Updates the poll datetime in the database

        This method should be run as an asyncio task.
        """
        self._running = True
        logger.info(
            f"WatchedAdjudicationPoller: Starting with poll_interval={self.poll_interval}s"
        )

        while self._running:
            try:
                # Sleep for poll_interval before polling
                await asyncio.sleep(self.poll_interval)

                # Check if we have necessary resources
                if not self.db:
                    logger.debug(
                        "WatchedAdjudicationPoller: No ESSR or DB available, skipping poll"
                    )
                    continue

                if not self.db.watched_poll:
                    logger.debug(
                        "WatchedAdjudicationPoller: watched_poll database not available"
                    )
                    continue

                # Skip if previous query still running
                if not self.query_done:
                    logger.debug(
                        "WatchedAdjudicationPoller: Previous query still running, skipping"
                    )
                    continue

                # Get last poll datetime from database
                last_poll_dater = self.db.watched_poll.get(keys=("last",))

                if last_poll_dater:
                    # Convert Dater to datetime
                    last_poll_dt = datetime.fromisoformat(last_poll_dater.dts)
                    logger.debug(
                        f"WatchedAdjudicationPoller: Last poll time: {last_poll_dt}"
                    )
                else:
                    # First poll - use a datetime from 1 day ago
                    last_poll_dt = datetime.now(timezone.utc).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    logger.debug(
                        f"WatchedAdjudicationPoller: First poll, using {last_poll_dt}"
                    )

                # Query ESSR for adjudications after last poll time
                # Format datetime for API query (ISO 8601)
                after_param = last_poll_dt.isoformat()
                path = f"/adjudications?date={urllib.parse.quote(after_param)}"

                logger.debug(f"WatchedAdjudicationPoller: Querying {path}")

                # Poll adjudications
                await self._async_poll_adjudications(path)

            except asyncio.CancelledError:
                logger.info("WatchedAdjudicationPoller: Task cancelled")
                break
            except Exception as e:
                logger.exception(f"WatchedAdjudicationPoller: Error in run loop: {e}")
                # Continue running despite errors

        logger.info("WatchedAdjudicationPoller: Stopped")

    async def _resync_watched_identifier(
        self, watched_aid: str, remote_sn: int, watched_name: str
    ) -> bool:
        """
        Attempt to bring a single watched identifier's local KEL up to
        `remote_sn`, export it, and trigger a credential search off the
        actual post-sync state.

        Returns True if the local KEL is caught up to (or past) `remote_sn`
        after this attempt, False if it's still behind (e.g. the newest
        event is sitting in escrow pending witness receipts) and should be
        retried on a later poll cycle.
        """
        kever = self.hby.kevers[watched_aid]

        await remoting.sync_watched_identifier(self.hby, self.essr, kever.serder.pre)

        # Export KEL to filesystem
        try:
            await filing.export_kel(
                hby=self.hby,
                aid=kever.serder.pre,
                export_dir=self.export_dir,
            )
        except Exception as e:
            logger.exception(
                f"WatchedAdjudicationPoller: Failed to export KEL for {watched_name}: {e}"
            )

        # Re-read post-sync: `sync_watched_identifier` may not have fully
        # caught the identifier up (the newest event can land in escrow
        # rather than commit), so the pre-sync `local_sn` is not a safe
        # signal of what actually happened.
        post_sync_sn = kever.sner.num

        if post_sync_sn < remote_sn:
            logger.info(
                f"WatchedAdjudicationPoller: {watched_name} still out of sync after resync - "
                f"local SN {post_sync_sn} < remote SN {remote_sn}, will retry next poll"
            )
            return False

        logger.info(
            f"WatchedAdjudicationPoller: Triggering credential search for {self.credential_loader} as {post_sync_sn}"
        )
        if self.credential_loader:
            asyncio.create_task(
                self.credential_loader.search_for_credentials(watched_aid, post_sync_sn)
            )

        return True

    async def _retry_pending_resyncs(self, org: "Organizer"):
        """
        Retry any watched identifiers that were left out of sync by a
        previous poll cycle, independent of whether the adjudications feed
        surfaces them again.
        """
        for watched_aid, remote_sn in list(self._pending_resync.items()):
            try:
                if watched_aid not in self.hby.kevers:
                    continue

                contact = org.get(pre=watched_aid)
                watched_name = contact.get("alias") if contact else watched_aid

                caught_up = await self._resync_watched_identifier(
                    watched_aid, remote_sn, watched_name
                )
                if caught_up:
                    del self._pending_resync[watched_aid]
            except Exception as e:
                logger.exception(
                    f"WatchedAdjudicationPoller: Error retrying pending resync for {watched_aid}: {e}"
                )

    async def _async_poll_adjudications(self, path: str):
        """
        Async helper to poll adjudications and sync watched identifiers.

        Args:
            path: API path to query
        """
        self.query_done = False
        try:
            response = await self.essr.request(path=path, method="GET")
            logger.debug(
                f"WatchedAdjudicationPoller: Query response status: {response.status_code} - {response.text}"
            )
            if not response or response.status_code != 200:
                logger.error(
                    f"WatchedAdjudicationPoller: API error: "
                    f"{response.status_code if response else 'No response'}"
                )
                return

            data = response.json()
            adjudications = data.get("adjudications", [])

            if not adjudications:
                logger.info("WatchedAdjudicationPoller: No new adjudications")
            else:
                logger.info(
                    f"WatchedAdjudicationPoller: Found {len(adjudications)} adjudications"
                )

            org = Organizer(hby=self.hby)

            # Retry any identifiers a previous cycle couldn't fully catch up
            # (see `_pending_resync` docstring) before looking at new
            # adjudications, so these aren't only retried when the feed
            # happens to mention the same AID again.
            if self._pending_resync:
                await self._retry_pending_resyncs(org)

            # Process each adjudication
            for adj in adjudications:
                try:
                    watched_aid = adj.get("watched_aid")
                    remote_sn = int(adj.get("sn", 0))

                    if not watched_aid:
                        logger.info(
                            "WatchedAdjudicationPoller: Adjudication missing aid, skipping"
                        )
                        continue

                    # Check local state
                    if watched_aid not in self.hby.kevers:
                        logger.info(
                            f"WatchedAdjudicationPoller: Watched identifier {watched_aid} {self.hby.kevers}"
                            f"not found locally, skipping"
                        )
                        continue

                    kever = self.hby.kevers[watched_aid]

                    contact = org.get(pre=watched_aid)
                    watched_name = contact.get("alias") if contact else watched_aid

                    local_sn = kever.sner.num

                    # Check if out of sync (local behind remote)
                    if local_sn < remote_sn:
                        logger.info(
                            f"WatchedAdjudicationPoller: {watched_name} is out of sync - "
                            f"local SN {local_sn} < remote SN {remote_sn}"
                        )

                        caught_up = await self._resync_watched_identifier(
                            watched_aid, remote_sn, watched_name
                        )

                        if caught_up:
                            self._pending_resync.pop(watched_aid, None)
                        else:
                            # Keep retrying on later poll cycles even if this
                            # AID never appears in the adjudications feed
                            # again (the feed is checkpointed by date below,
                            # so a one-time miss here would otherwise be
                            # dropped for good).
                            self._pending_resync[watched_aid] = max(
                                remote_sn, self._pending_resync.get(watched_aid, 0)
                            )

                    else:
                        logger.debug(
                            f"WatchedAdjudicationPoller: {watched_name} is in sync - "
                            f"local SN {local_sn} >= remote SN {remote_sn}"
                        )

                except Exception as e:
                    logger.exception(
                        f"WatchedAdjudicationPoller: Error processing adjudication: {e}"
                    )
                    continue

            # Update last poll datetime to now
            now = datetime.now(timezone.utc)
            now_dater = coring.Dater(dts=now.isoformat())
            self.db.watched_poll.pin(keys=("last",), val=now_dater)
            logger.debug(f"WatchedAdjudicationPoller: Updated last poll time to {now}")

        except Exception as e:
            logger.exception(f"WatchedAdjudicationPoller: Error in async poll: {e}")
        finally:
            self.query_done = True

    def start(self):
        """
        Start the poller as an asyncio task.

        Returns:
            The asyncio Task object
        """
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run())
        return self._task

    def stop(self):
        """
        Stop the poller task.
        """
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()


class ObvsSocketListener:
    """
    Asyncio-based Unix Domain Socket listener that monitors new obvs entries.

    Listens on a Unix Domain Socket for connections. When a connection is received,
    reads all data from the connection, then checks hby.db.obvs for new entries
    (datetime > last_check) and calls add_watched_identifier for each new entry.
    """

    def __init__(
        self,
        hby: Habery,
        essr: APIClient,
        db,
        socket_path: str,
        poll_interval: float = 0.5,
        registrar_url: Optional[str] = None,
        export_dir: Optional[str] = None,
    ):
        """
        Initialize the ObvsSocketListener.

        Args:
            hby: Habery instance for managing healthKERI accounts
            essr: APIClient instance for interacting with healthKERI API
            db: Database instance with watched_poll table
            socket_path: Path to Unix Domain Socket (e.g., /tmp/sentinel_name.sock)
            poll_interval: Timer interval for checking connections (default: 0.5 seconds)
            registrar_url: URL for credential registrar API (default: None)
            export_dir: Directory for exporting CESR files (default: None)
        """
        self.hby = hby
        self.psr = parsing.Parser(kvy=self.hby.kvy, rvy=self.hby.rvy, local=True)
        self.essr = essr
        self.db = db
        self.socket_path = socket_path
        self.poll_interval = poll_interval
        self.registrar_url = registrar_url
        self.export_dir = export_dir
        self._server = None
        self._task = None
        self._running = False
        self._connection_tasks: Set[asyncio.Task] = set()

    async def run(self):
        """
        Main asyncio loop that runs the Unix Domain Socket server.

        This method:
        1. Removes existing socket file if present
        2. Creates Unix Domain Socket server
        3. Accepts connections and processes them
        4. Handles cleanup on shutdown
        """
        self._running = True
        logger.info(f"ObvsSocketListener: Starting server on {self.socket_path}")

        try:
            # Remove existing socket file if present
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
                logger.debug(
                    f"ObvsSocketListener: Removed existing socket file {self.socket_path}"
                )

            # Create Unix Domain Socket server
            self._server = await asyncio.start_unix_server(
                self._handle_connection, path=self.socket_path
            )

            logger.info(f"ObvsSocketListener: Server listening on {self.socket_path}")

            # Run server loop
            while self._running:
                await asyncio.sleep(self.poll_interval)

                # Clean up finished connection tasks
                self._connection_tasks = {
                    task for task in self._connection_tasks if not task.done()
                }

        except asyncio.CancelledError:
            logger.info("ObvsSocketListener: Task cancelled")
        except Exception as e:
            logger.exception(f"ObvsSocketListener: Error in run loop: {e}")
        finally:
            await self._cleanup()

        logger.info("ObvsSocketListener: Stopped")

    async def _cleanup(self):
        """
        Clean up server resources and socket file.
        """
        try:
            logger.info("ObvsSocketListener: Cleaning up...")

            # Close server
            if self._server:
                self._server.close()
                await self._server.wait_closed()
                logger.debug("ObvsSocketListener: Server closed")

            # Remove socket file
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
                logger.debug(
                    f"ObvsSocketListener: Removed socket file {self.socket_path}"
                )

            # Cancel all connection tasks
            if self._connection_tasks:
                logger.debug(
                    f"ObvsSocketListener: Cancelling {len(self._connection_tasks)} connection tasks"
                )
                for task in self._connection_tasks:
                    task.cancel()

                # Wait for all tasks to complete
                await asyncio.gather(*self._connection_tasks, return_exceptions=True)

        except Exception as e:
            logger.exception(f"ObvsSocketListener: Error during cleanup: {e}")

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """
        Handle a new connection by creating a task for it.

        Args:
            reader: StreamReader for reading from the connection
            writer: StreamWriter for writing to the connection
        """
        task = asyncio.create_task(self._process_connection(reader, writer))
        self._connection_tasks.add(task)

    async def _process_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """
        Process a single connection: read data and check obvs.

        Args:
            reader: StreamReader for reading from the connection
            writer: StreamWriter for writing to the connection
        """
        peer = writer.get_extra_info("peername")
        logger.info(f"ObvsSocketListener: New connection from {peer}")

        try:
            # Read all data from connection
            data = bytearray()
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                data.extend(chunk)

            logger.debug(f"ObvsSocketListener: Received {len(data)} bytes from {peer}")

            # Check and add new obvs entries
            self.psr.parseOne(data)
            await self._check_and_add_obvs()

        except Exception as e:
            logger.exception(
                f"ObvsSocketListener: Error processing connection from {peer}: {e}"
            )
        finally:
            try:
                writer.close()
                await writer.wait_closed()
                logger.info(f"ObvsSocketListener: Connection from {peer} closed")
            except Exception as e:
                logger.exception(f"ObvsSocketListener: Error closing connection: {e}")

    async def _check_and_add_obvs(self):
        """
        Check hby.db.obvs for new entries and add them as watched identifiers.

        Filters obvs entries based on timestamp (datetime > last_check) and calls
        add_watched_identifier for each new entry.
        """
        try:
            # Check if we have necessary resources
            if not self.db:
                logger.warning(
                    "ObvsSocketListener: No DB available, skipping obvs check"
                )
                return

            if not self.db.watched_poll:
                logger.warning(
                    "ObvsSocketListener: watched_poll database not available"
                )
                return

            if not hasattr(self.hby.db, "obvs"):
                logger.warning("ObvsSocketListener: obvs database not available")
                return

            # Get last check timestamp from database
            last_check_dater = self.db.watched_poll.get(keys=("obvs_last",))

            if last_check_dater:
                last_check_dt = datetime.fromisoformat(last_check_dater.dts)
                logger.debug(f"ObvsSocketListener: Last check time: {last_check_dt}")
            else:
                # First check - use epoch
                last_check_dt = datetime(1970, 1, 1, tzinfo=timezone.utc)
                logger.debug(
                    f"ObvsSocketListener: First check, using epoch {last_check_dt}"
                )

            # Iterate through obvs entries
            new_count = 0
            success_count = 0
            error_count = 0

            for (cid, aid, oid), observed in self.hby.db.obvs.getItemIter():
                try:
                    # Check if entry has datetime and is newer than last check
                    if not hasattr(observed, "datetime") or not observed.datetime:
                        logger.debug(
                            f"ObvsSocketListener: Skipping obvs entry without datetime - oid={oid}"
                        )
                        continue

                    observed_dt = datetime.fromisoformat(observed.datetime)

                    if observed_dt > last_check_dt:
                        new_count += 1
                        logger.info(
                            f"ObvsSocketListener: New obvs entry - cid={cid}, aid={aid}, oid={oid}, "
                            f"name={getattr(observed, 'name', 'N/A')}, datetime={observed.datetime}"
                        )

                        # Add watched identifier
                        alias = getattr(observed, "name", oid)
                        result = await add_watched_identifier(
                            hby=self.hby,
                            essr=self.essr,
                            watched_aid=oid,
                            alias=alias,  # type: ignore
                            registrar_url=self.registrar_url,
                            export_dir=self.export_dir,
                        )

                        if result.get("success"):
                            success_count += 1
                            logger.info(
                                f"ObvsSocketListener: Successfully added watched identifier - "
                                f"oid={oid}, alias={alias}"
                            )
                        else:
                            error_count += 1
                            error_msg = result.get("error", "Unknown error")
                            logger.error(
                                f"ObvsSocketListener: Failed to add watched identifier - "
                                f"oid={oid}, alias={alias}, error={error_msg}"
                            )

                except Exception as e:
                    error_count += 1
                    logger.exception(
                        f"ObvsSocketListener: Error processing obvs entry (oid={oid}): {e}"
                    )
                    continue

            # Update last check timestamp to now
            now = datetime.now(timezone.utc)
            now_dater = coring.Dater(dts=now.isoformat())
            self.db.watched_poll.pin(keys=("obvs_last",), val=now_dater)
            logger.debug(f"ObvsSocketListener: Updated last check time to {now}")

            logger.info(
                f"ObvsSocketListener: Processed {new_count} new obvs entries - "
                f"success={success_count}, errors={error_count}"
            )

        except Exception as e:
            logger.exception(f"ObvsSocketListener: Error in _check_and_add_obvs: {e}")

    def start(self):
        """
        Start the socket listener as an asyncio task.

        Returns:
            The asyncio Task object
        """
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run())
        return self._task

    def stop(self):
        """
        Stop the socket listener task.
        """
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

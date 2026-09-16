from __future__ import annotations

"""Unified YADO core access layer with broad public HTTPS read/discovery V2."""

import socket
from urllib.parse import urlsplit

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_personal_public_web_access_v2 import (
    channel_snapshot,
    discover_links,
    fetch_public,
)


class UnifiedYADOCorePersonalWebV2(UnifiedYADOCoreV1):
    """Compatibility-preserving access layer over the canonical G2 core.

    It does not change generation identity or authorize canonical mutation. It adds
    a kernel-owned public HTTPS read/discovery channel with fail-closed network
    validation and bounded exploration.
    """

    ACCESS_LAYER_ID = "UNIFIED_YADO_CORE_PERSONAL_PUBLIC_WEB_V2"

    def public_web_channel_snapshot(self) -> dict:
        snap = channel_snapshot()
        return {
            **snap,
            "access_layer_id": self.ACCESS_LAYER_ID,
            "base_core_id": self.CORE_ID,
            "generation": self.head.get("generation_id"),
        }

    def public_web_fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        timeout: float = 15.0,
        max_bytes: int = 2_000_000,
        max_redirects: int = 5,
        resolver=None,
        transport=None,
    ) -> dict:
        kwargs = {
            "method": method,
            "timeout": timeout,
            "max_bytes": max_bytes,
            "max_redirects": max_redirects,
        }
        if resolver is not None:
            kwargs["resolver"] = resolver
        if transport is not None:
            kwargs["transport"] = transport
        result = fetch_public(url, **kwargs)
        return {
            **result,
            "core_route": self.ACCESS_LAYER_ID,
            "generation": self.head.get("generation_id"),
        }

    def public_web_discover(self, content: str, base_url: str, *, limit: int = 24, resolver=None) -> list[dict]:
        kwargs = {"limit": limit}
        if resolver is not None:
            kwargs["resolver"] = resolver
        return discover_links(content, base_url, **kwargs)

    def public_web_explore(
        self,
        seed_url: str,
        *,
        max_pages: int = 3,
        links_per_page: int = 12,
        timeout: float = 15.0,
        resolver=None,
        transport=None,
    ) -> dict:
        """Bounded breadth-first public-web exploration from one seed.

        Failures on secondary links are recorded and skipped. The seed itself must
        succeed. No page can authorize writes, private access, credentials, or code
        execution; those constraints remain inside the underlying transport.
        """
        if not 1 <= int(max_pages) <= 5:
            raise ValueError("PUBLIC_WEB_PAGE_BUDGET")
        if not 1 <= int(links_per_page) <= 24:
            raise ValueError("PUBLIC_WEB_LINK_BUDGET")

        first = self.public_web_fetch(
            seed_url,
            timeout=timeout,
            resolver=resolver,
            transport=transport,
        )
        pages = [first]
        failures = []
        seen = {first["receipt"]["final_url"]}
        queue = self.public_web_discover(
            first["content"],
            first["receipt"]["final_url"],
            limit=links_per_page,
            resolver=resolver,
        )

        while queue and len(pages) < max_pages:
            link = queue.pop(0)
            if link["url"] in seen:
                continue
            seen.add(link["url"])
            try:
                page = self.public_web_fetch(
                    link["url"],
                    timeout=timeout,
                    resolver=resolver,
                    transport=transport,
                )
            except Exception as exc:
                failures.append({
                    "url": link["url"],
                    "error_type": type(exc).__name__,
                    "reason": str(exc),
                })
                continue
            pages.append(page)
            if len(pages) < max_pages:
                more = self.public_web_discover(
                    page["content"],
                    page["receipt"]["final_url"],
                    limit=links_per_page,
                    resolver=resolver,
                )
                queue.extend(x for x in more if x["url"] not in seen)

        return {
            "schema": "yado.personal_public_web_explore.v2",
            "status": "PASS_BOUNDED_PUBLIC_WEB_EXPLORATION_V2",
            "seed_url": seed_url,
            "page_count": len(pages),
            "hosts": sorted({urlsplit(x["receipt"]["final_url"]).hostname for x in pages}),
            "pages": [x["receipt"] for x in pages],
            "secondary_failures": failures,
            "read_only": True,
            "credentials_used": False,
            "private_network_access": False,
            "external_write": False,
            "downloaded_code_executed": False,
            "automatic_canonical_mutation": False,
            "core_route": self.ACCESS_LAYER_ID,
        }

    def audit(self) -> dict:
        report = super().audit()
        access = self.public_web_channel_snapshot()
        checks = dict(report["checks"])
        checks.update({
            "personal_public_web_access_v2_bound": access.get("status") == "AVAILABLE_BROAD_PUBLIC_HTTPS_READ_ONLY_V2",
            "personal_public_web_public_only": access.get("dns_public_only") is True and access.get("private_networks") is False,
            "personal_public_web_read_only": access.get("external_writes") is False and access.get("credentials") is False,
            "personal_public_web_dns_pinned": access.get("dns_pinned_transport") is True and access.get("redirect_revalidation") is True,
        })
        report["checks"] = checks
        report["pass"] = all(checks.values())
        report["personal_public_web"] = access
        return report

    def snapshot(self) -> dict:
        snap = super().snapshot()
        snap["personal_public_web"] = self.public_web_channel_snapshot()
        snap["access_layer_id"] = self.ACCESS_LAYER_ID
        snap["semantic_boundary"] = (
            "CANONICAL G2 CORE PLUS BROAD PUBLIC HTTPS READ/DISCOVERY; NO PRIVATE NETWORKS, "
            "CREDENTIALS, WRITES, DOWNLOADED-CODE EXECUTION, AUTOMATIC CANONICAL MUTATION, G3, "
            "AGI, OR SUBJECTIVE-CONSCIOUSNESS CLAIM."
        )
        return snap


__all__ = ["UnifiedYADOCorePersonalWebV2"]

import hashlib

from django.core.cache import cache

VIEW_COUNT_DEDUP_WINDOW_SECONDS = 60 * 60


def get_client_ip(request) -> str:
    """Extract the client IP address from a request.

    Checks X-Forwarded-For first (left-most entry, the original client per
    common proxy conventions), falling back to REMOTE_ADDR.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or "unknown"


def should_count_view(cache_prefix: str, object_id, ip_address: str) -> bool:
    """Return True if this (prefix, object_id, ip) view has not been counted yet
    within the dedup window.

    Uses cache.add(), an atomic set-if-not-exists, so concurrent requests from
    the same IP can't race past this check.
    """
    ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:16]
    cache_key = f"view_count_dedup:{cache_prefix}:{object_id}:{ip_hash}"
    return cache.add(cache_key, value=True, timeout=VIEW_COUNT_DEDUP_WINDOW_SECONDS)

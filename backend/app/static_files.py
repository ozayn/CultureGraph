"""Static file serving helpers."""

from __future__ import annotations

from starlette.responses import Response
from starlette.staticfiles import StaticFiles


class CachedStaticFiles(StaticFiles):
    """Serve uploads with cache headers for CDN/browser caching."""

    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers.setdefault("Cache-Control", "public, max-age=86400")
        return response

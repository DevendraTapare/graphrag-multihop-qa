from contextlib import asynccontextmanager

import httpx


@asynccontextmanager
async def api_client(app):
    """Exercise the ASGI app and its real lifespan with the required httpx client."""
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            yield client

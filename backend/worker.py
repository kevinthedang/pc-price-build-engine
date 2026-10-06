from fastapi.middleware.cors import CORSMiddleware
from workers import asgi

import main as build_engine
from api import CATALOG_FILES, app


class CatalogAssetsMiddleware:
    def __init__(self, app):
        self.app = app
        self.catalogs_loaded = False

    async def __call__(self, scope, receive, send):
        environment = scope.get("env")
        if scope["type"] == "http" and environment is not None:
            if not self.catalogs_loaded:
                filenames = (*CATALOG_FILES.values(), "offers.json")
                catalogs = {}
                for filename in filenames:
                    response = await environment.CATALOGS.fetch(
                        f"https://assets.local/{filename}"
                    )
                    if response.status != 200:
                        raise RuntimeError(
                            f"Could not load catalog asset {filename}: "
                            f"HTTP {response.status}"
                        )
                    catalogs[filename] = await response.text()
                build_engine.set_worker_catalogs(catalogs)
                self.catalogs_loaded = True
        await self.app(scope, receive, send)


worker_app = CatalogAssetsMiddleware(app)
worker_app = CORSMiddleware(
    worker_app,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

Default = asgi.entrypoint(worker_app)

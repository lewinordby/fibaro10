"""Register domain routes in the established order without recreating handlers."""
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import APIRouter, FastAPI


@dataclass
class RouterBundle:
    router: APIRouter
    endpoints: dict[str, Callable[..., Any]]
    dependencies: Any

    def register_endpoint(self, app: FastAPI, name: str) -> None:
        endpoint = self.endpoints[name]
        routes = [route for route in self.router.routes if route.endpoint is endpoint]
        if not routes:
            raise ValueError(f'No route registered for {name}')
        app.router.routes.extend(routes)

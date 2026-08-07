from .pwa import PwaConfig, inject_pwa_head, pwa_head_tags, register_pwa

__all__ = [
    "DomainAppConfig",
    "PwaConfig",
    "create_domain_app",
    "inject_pwa_head",
    "pwa_head_tags",
    "register_pwa",
]


def __getattr__(name: str):
    if name in {"DomainAppConfig", "create_domain_app"}:
        from .runtime import DomainAppConfig, create_domain_app

        return {
            "DomainAppConfig": DomainAppConfig,
            "create_domain_app": create_domain_app,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

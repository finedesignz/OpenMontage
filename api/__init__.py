"""OpenMontage HTTP API — async job queue around the agent-driven pipeline.

Deployed as a single Coolify container. See docs/API.md.
"""

__all__ = ["create_app"]


def create_app():
    # Imported lazily so `import api` stays cheap (and importable without FastAPI
    # installed, e.g. during contract tests that only touch the core package).
    from .main import create_app as _create_app

    return _create_app()

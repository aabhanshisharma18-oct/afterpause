"""Keep the original Flask entry point connected to the integrated museum app."""

from app import create_app

__all__ = ["create_app"]

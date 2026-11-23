"""Shared test configuration.

Unit tests (tests/unit) need no services. Database, storage and integration tests load
``.env.test`` in tests/integration/conftest.py and never touch the ``ps5`` database or
the development bucket (docs/05 §12).
"""

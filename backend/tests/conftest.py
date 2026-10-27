"""Shared test configuration.

PBKDF2 at the production work factor costs ~1s per hash. The test suite
creates and verifies many credentials, so the work factor is lowered for tests
only; `tests/test_auth.py::test_password_hash_uses_configured_work_factor`
still exercises the configured default explicitly.
"""

import pytest

from app.config import settings

TEST_KDF_ITERATIONS = 10_000


@pytest.fixture(autouse=True)
def fast_kdf(request, monkeypatch):
    if "real_kdf" in request.keywords:
        # The test opts in to exercising the shipped work factor.
        yield
        return
    monkeypatch.setattr(settings, "password_hash_iterations", TEST_KDF_ITERATIONS)
    yield

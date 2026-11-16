"""Descargas HTTPS restringidas (hosts, redirecciones, rangos, tamaño, reintentos)."""

from __future__ import annotations

import ast
import email.message
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from acoustic_pilot import remote, remote_zip
from acoustic_pilot.remote import check_url, make_opener, read_https

HOSTS = {"zenodo.org"}


class _Response:
    def __init__(self, data: bytes, url: str, status: int) -> None:
        self.data, self.url, self.status = data, url, status

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def geturl(self) -> str:
        return self.url

    def read(self, n: int) -> bytes:
        return self.data[:n]


class _Opener:
    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.requests: list[urllib.request.Request] = []

    def open(self, request: urllib.request.Request, timeout: float) -> object:
        self.requests.append(request)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _http_error(code: int, retry_after: str | None = None) -> urllib.error.HTTPError:
    headers = email.message.Message()
    if retry_after:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError("https://zenodo.org/x", code, "err", headers, None)


def test_only_https_on_allowed_hosts() -> None:
    check_url("https://zenodo.org/api/records/1", HOSTS)
    for bad in ("http://zenodo.org/x", "https://evil.example/x", "https://zenodo.org.evil.io/x"):
        with pytest.raises(ValueError, match="no permitido"):
            check_url(bad, HOSTS)


def test_redirect_to_foreign_host_is_refused_before_following() -> None:
    opener = make_opener(HOSTS)
    handler = next(h for h in opener.handlers if isinstance(h, urllib.request.HTTPRedirectHandler))
    request = urllib.request.Request("https://zenodo.org/a")
    with pytest.raises(ValueError, match="no permitido"):
        handler.redirect_request(request, None, 302, "Found", {}, "https://evil.example/b")
    ok = handler.redirect_request(request, None, 302, "Found", {}, "https://zenodo.org/b")
    assert ok is not None and ok.full_url == "https://zenodo.org/b"


def test_final_url_outside_allowed_hosts_fails() -> None:
    opener = _Opener(_Response(b"x", "https://evil.example/x", 200))
    with pytest.raises(ValueError, match="no permitido"):
        read_https("https://zenodo.org/x", HOSTS, opener=opener)


def test_range_request_requires_206_and_exact_length() -> None:
    opener = _Opener(_Response(b"abcd", "https://zenodo.org/x", 206))
    assert read_https("https://zenodo.org/x", HOSTS, byte_range=(10, 14), opener=opener) == b"abcd"
    assert opener.requests[0].get_header("Range") == "bytes=10-13"
    with pytest.raises(ValueError, match="rango"):
        read_https(
            "https://zenodo.org/x",
            HOSTS,
            byte_range=(0, 4),
            opener=_Opener(_Response(b"abcd", "https://zenodo.org/x", 200)),
        )
    with pytest.raises(ConnectionError, match="incompleto"):
        read_https(
            "https://zenodo.org/x",
            HOSTS,
            byte_range=(0, 4),
            retries=1,
            opener=_Opener(
                _Response(b"ab", "https://zenodo.org/x", 206),
                _Response(b"a", "https://zenodo.org/x", 206),
            ),
            sleep=lambda _s: None,
        )
    # Una transferencia cortada o un fallo de red se reintenta y luego se verifica.
    retried = _Opener(
        _Response(b"ab", "https://zenodo.org/x", 206),
        urllib.error.URLError("reset"),
        _Response(b"abcd", "https://zenodo.org/x", 206),
    )
    got = read_https(
        "https://zenodo.org/x", HOSTS, byte_range=(0, 4), opener=retried, sleep=lambda _s: None
    )
    assert got == b"abcd" and len(retried.requests) == 3
    with pytest.raises(ValueError, match="rango no válido"):
        read_https("https://zenodo.org/x", HOSTS, byte_range=(5, 5), opener=_Opener())


def test_size_limit_is_enforced() -> None:
    opener = _Opener(_Response(b"x" * 11, "https://zenodo.org/x", 200))
    with pytest.raises(ValueError, match="demasiado grande"):
        read_https("https://zenodo.org/x", HOSTS, limit=10, opener=opener)


def test_rate_limit_is_retried_with_retry_after_then_gives_up() -> None:
    waits: list[float] = []
    opener = _Opener(_http_error(429, "7"), _Response(b"ok", "https://zenodo.org/x", 200))
    assert read_https("https://zenodo.org/x", HOSTS, opener=opener, sleep=waits.append) == b"ok"
    assert waits == [7.0]
    with pytest.raises(urllib.error.HTTPError):
        read_https(
            "https://zenodo.org/x",
            HOSTS,
            retries=1,
            opener=_Opener(_http_error(503), _http_error(503)),
            sleep=waits.append,
        )
    with pytest.raises(urllib.error.HTTPError):  # 404 no se reintenta
        read_https("https://zenodo.org/x", HOSTS, opener=_Opener(_http_error(404)), sleep=print)


@pytest.mark.parametrize("module", [remote, remote_zip])
def test_modules_are_self_contained_for_colab_embedding(module: object) -> None:
    source = Path(module.__file__).read_text(encoding="utf-8")  # type: ignore[attr-defined]
    assert "__future__" not in source
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported <= {"collections", "struct", "time", "urllib", "zlib"}

# Descargas HTTPS restringidas: solo hosts permitidos (también tras redirecciones), rangos
# opcionales, tope de tamaño y reintentos ante 429/503 respetando Retry-After (Zenodo limita
# a ~133 peticiones/minuto). Autocontenido (solo stdlib): build_colab.py lo incrusta tal cual.
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

USER_AGENT = "Atalaya-Colab-Pilot/1"


def check_url(url: str, allowed_hosts: set[str] | frozenset[str]) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        raise ValueError(f"origen no permitido: {url}")


def make_opener(allowed_hosts: set[str] | frozenset[str]) -> urllib.request.OpenerDirector:
    """Opener que comprueba cada redirección ANTES de seguirla."""
    hosts = frozenset(allowed_hosts)

    class CheckedRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
            check_url(newurl, hosts)
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    return urllib.request.build_opener(CheckedRedirect)


def read_https(
    url: str,
    allowed_hosts: set[str] | frozenset[str],
    *,
    byte_range: tuple[int, int] | None = None,
    limit: int = 1 << 31,
    timeout: float = 120,
    retries: int = 6,
    opener: object | None = None,
    sleep=time.sleep,  # type: ignore[no-untyped-def]
) -> bytes:
    """GET con host permitido. byte_range = (inicio, fin_exclusivo) exige respuesta 206 con
    exactamente esos bytes. Falla si la respuesta supera ``limit``."""
    check_url(url, allowed_hosts)
    headers = {"User-Agent": USER_AGENT}
    if byte_range is not None:
        start, end = byte_range
        if not 0 <= start < end:
            raise ValueError("rango no válido")
        headers["Range"] = f"bytes={start}-{end - 1}"
        limit = min(limit, end - start)
    client = opener or make_opener(allowed_hosts)
    for attempt in range(retries + 1):
        try:
            with client.open(urllib.request.Request(url, headers=headers), timeout=timeout) as r:  # type: ignore[attr-defined]
                check_url(r.geturl(), allowed_hosts)
                status = getattr(r, "status", 200)
                if byte_range is not None and status != 206:
                    raise ValueError(f"el servidor no respetó el rango (HTTP {status})")
                data = r.read(limit + 1)
            if len(data) > limit:
                raise ValueError(f"respuesta demasiado grande: {url}")
            if byte_range is not None and len(data) != byte_range[1] - byte_range[0]:
                raise ConnectionError("rango incompleto")
            return data
        except urllib.error.HTTPError as error:
            if error.code not in (429, 502, 503, 504) or attempt == retries:
                raise
            wait = error.headers.get("Retry-After") if error.headers else None
            sleep(min(120.0, float(wait)) if wait and wait.isdigit() else 2.0 * (attempt + 1))
        except (ConnectionError, TimeoutError, urllib.error.URLError):
            # Transferencia cortada o red caída: se reintenta; los datos se verifican después.
            if attempt == retries:
                raise
            sleep(2.0 * (attempt + 1))
    raise ConnectionError("sin respuesta")  # inalcanzable: el último intento devuelve o lanza

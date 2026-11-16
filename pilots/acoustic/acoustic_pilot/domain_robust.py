# Técnicas contra el atajo de dominio (hito 2, iteración 6), ligeras y sobre embeddings:
# - modelo lineal con estandarización PLEGADA en (coef, intercept) del espacio original: el Mac
#   solo necesita un producto escalar (artefacto pequeño, JSON);
# - INLP (Ravfogel et al., 2020, «Iterative Null-space Projection»): se entrenan clasificadores
#   lineales de FUENTE dentro de cada clase y se proyecta fuera de sus direcciones, de modo que lo
#   que distingue una fuente de otra (canal, micrófono) deja de estar disponible para el
#   clasificador de dron; alternativa lineal y estable al entrenamiento adversarial de dominio;
# - group-DRO (Sagawa et al., 2020) por pesos exponenciados sobre grupos fuente x clase: minimiza
#   la pérdida del peor grupo en vez de la media;
# - umbral robusto por peor fuente: el más bajo que deja la FPR de CADA fuente de validación por
#   debajo del máximo (y su umbral de fin de alerta, con histéresis);
# - centrado por fuente con negativos de calibración (variante de sitio, D-7, siempre aparte).
# Autocontenido (numpy, scikit-learn): build_colab.py lo incrusta tal cual.
import math
from collections.abc import Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -60, 60)))


def _orthonormal(columns: np.ndarray) -> np.ndarray:
    if columns.size == 0:
        return columns
    q, r = np.linalg.qr(columns)
    keep = np.abs(np.diag(r)) > 1e-8
    return q[:, keep]


def inlp_directions(
    z: np.ndarray,
    labels: Sequence[int],
    domains: Sequence[str],
    *,
    rounds: int,
    seed: int,
    c: float = 0.1,
) -> np.ndarray:
    """Base ortonormal (d x k) de las direcciones que predicen la fuente DENTRO de cada clase
    (así no se borra la información de clase). z debe estar estandarizada."""
    y = np.asarray(labels, dtype=int)
    dom = np.asarray(domains)
    basis = np.zeros((z.shape[1], 0))
    for _ in range(rounds):
        found = []
        proj = z - (z @ basis) @ basis.T if basis.size else z
        for cls in sorted(set(y.tolist())):
            mask = y == cls
            if len(set(dom[mask].tolist())) < 2:
                continue
            clf = LogisticRegression(C=c, max_iter=1000, random_state=seed)
            clf.fit(proj[mask], dom[mask])
            found.append(clf.coef_.T)
        if not found:
            break
        new = np.hstack(found)
        new = new - basis @ (basis.T @ new) if basis.size else new
        basis = _orthonormal(np.hstack([basis, new]))
    return basis


def fit_linear(
    x: np.ndarray,
    labels: Sequence[int],
    weights: Sequence[float],
    *,
    seed: int,
    c: float = 1.0,
    domains: Sequence[str] | None = None,
    inlp_rounds: int = 0,
    max_iter: int = 3000,
) -> dict:
    """Regresión logística sobre rasgos estandarizados (y, si inlp_rounds > 0, proyectados fuera
    de las direcciones de fuente); devuelve coef/intercept en el espacio ORIGINAL."""
    prep = _prepare(x, labels, domains, inlp_rounds=inlp_rounds, seed=seed)
    return _fit_prepared(prep, labels, weights, seed=seed, c=c, max_iter=max_iter)


def _prepare(
    x: np.ndarray,
    labels: Sequence[int],
    domains: Sequence[str] | None,
    *,
    inlp_rounds: int,
    seed: int,
) -> dict:
    """Estandarización y base INLP, calculadas una sola vez por ajuste (también para DRO)."""
    x = np.asarray(x, dtype=np.float64)
    mu = x.mean(axis=0)
    sd = np.maximum(x.std(axis=0), 1e-6)
    z = (x - mu) / sd
    basis = np.zeros((x.shape[1], 0))
    if inlp_rounds > 0:
        if domains is None:
            raise ValueError("INLP necesita la fuente de cada muestra")
        basis = inlp_directions(z, labels, domains, rounds=inlp_rounds, seed=seed)
        z = z - (z @ basis) @ basis.T
    return {"mu": mu, "sd": sd, "basis": basis, "z": z}


def _fit_prepared(
    prep: dict,
    labels: Sequence[int],
    weights: Sequence[float],
    *,
    seed: int,
    c: float,
    max_iter: int = 3000,
) -> dict:
    lr = LogisticRegression(C=c, max_iter=max_iter, random_state=seed)
    lr.fit(prep["z"], np.asarray(labels, dtype=int), sample_weight=np.asarray(weights, float))
    w = lr.coef_[0]
    basis, mu, sd = prep["basis"], prep["mu"], prep["sd"]
    if basis.size:
        w = w - basis @ (basis.T @ w)
    return {
        "coef": w / sd,
        "intercept": float(lr.intercept_[0] - np.sum(w * mu / sd)),
        "inlp_direcciones": int(basis.shape[1]),
    }


def linear_logit(model: dict, x: np.ndarray) -> np.ndarray:
    return np.asarray(x, dtype=np.float64) @ np.asarray(model["coef"]) + model["intercept"]


def linear_proba(model: dict, x: np.ndarray) -> np.ndarray:
    return _sigmoid(linear_logit(model, x))


def group_dro_fit(
    x: np.ndarray,
    labels: Sequence[int],
    groups: Sequence[str],
    *,
    seed: int,
    rounds: int = 4,
    eta: float = 1.0,
    c: float = 1.0,
    domains: Sequence[str] | None = None,
    inlp_rounds: int = 0,
) -> tuple[dict, list[dict]]:
    """Group-DRO por pesos exponenciados: cada grupo (p. ej. «fuente|clase») pesa q_g en total;
    tras cada ajuste, q_g <- q_g · exp(eta · pérdida_g) y se renormaliza."""
    y = np.asarray(labels, dtype=int)
    g = np.asarray(groups)
    names = sorted(set(g.tolist()))
    q = np.full(len(names), 1.0 / len(names))
    index = {name: i for i, name in enumerate(names)}
    gi = np.array([index[v] for v in g.tolist()])
    counts = np.bincount(gi, minlength=len(names)).astype(float)
    history = []
    model = None
    prep = _prepare(x, y, domains, inlp_rounds=inlp_rounds, seed=seed)
    for _ in range(rounds + 1):
        w = q[gi] / counts[gi] * len(y)
        model = _fit_prepared(prep, y, w, seed=seed, c=c)
        p = np.clip(linear_proba(model, x), 1e-7, 1 - 1e-7)
        loss_i = -(y * np.log(p) + (1 - y) * np.log(1 - p))
        losses = np.bincount(gi, weights=loss_i, minlength=len(names)) / counts
        history.append(
            {
                "q": dict(zip(names, q.round(6).tolist(), strict=True)),
                "perdida": dict(zip(names, losses.round(6).tolist(), strict=True)),
            }
        )
        q = q * np.exp(eta * losses)
        q = q / q.sum()
    return model, history


def worst_source_threshold(
    labels: Sequence[int], scores: Sequence[float], sources: Sequence[str], *, max_fpr: float
) -> dict:
    """Umbral más bajo con FPR <= max_fpr en CADA fuente con negativos (la peor fuente manda).
    Devuelve también recall de validación por fuente con dron y la FPR por fuente."""
    y = np.asarray(labels, dtype=int)
    p = np.asarray(scores, dtype=np.float64)
    s = np.asarray(sources)
    if not 0 <= max_fpr < 1:
        raise ValueError("max_fpr debe estar en [0, 1)")
    neg_sources = sorted(set(s[y == 0].tolist()))
    if not neg_sources:
        raise ValueError("no hay negativos en validación")
    per = {}
    for src in neg_sources:
        neg = np.sort(p[(y == 0) & (s == src)])[::-1]
        allowed = int(math.floor(max_fpr * len(neg)))
        per[src] = float(np.nextafter(neg[allowed], np.inf)) if allowed < len(neg) else 0.0
    threshold = max(per.values())
    return {
        "threshold": threshold,
        "fuente_limitante": max(per, key=per.get),
        "umbral_por_fuente": per,
        "fpr_validacion": {
            src: float(np.mean(p[(y == 0) & (s == src)] >= threshold)) for src in neg_sources
        },
        "recall_validacion": {
            src: float(np.mean(p[(y == 1) & (s == src)] >= threshold))
            for src in sorted(set(s[y == 1].tolist()))
        },
    }


def hysteresis_thresholds(
    labels: Sequence[int],
    scores: Sequence[float],
    sources: Sequence[str],
    *,
    max_fpr_on: float,
    max_fpr_off: float,
) -> dict:
    """theta_on con max_fpr_on por peor fuente; theta_off (fin de alerta) con max_fpr_off >
    max_fpr_on, siempre estrictamente por debajo de theta_on y dentro de (0, 1)."""
    if max_fpr_off <= max_fpr_on:
        raise ValueError("max_fpr_off debe ser mayor que max_fpr_on")
    on = worst_source_threshold(labels, scores, sources, max_fpr=max_fpr_on)
    off = worst_source_threshold(labels, scores, sources, max_fpr=max_fpr_off)
    theta_on = float(min(max(on["threshold"], 1e-4), 1 - 1e-6))
    theta_off = float(min(max(off["threshold"], 5e-5), theta_on * 0.999))
    return {"theta_on": theta_on, "theta_off": theta_off, "detalle_on": on}


def calibration_centers(
    x: np.ndarray, sources: Sequence[str], mask: Sequence[bool]
) -> dict[str, np.ndarray]:
    """Media por fuente de las filas de calibración (negativos del sitio, D-7)."""
    x = np.asarray(x, dtype=np.float64)
    s = np.asarray(sources)
    m = np.asarray(mask, dtype=bool)
    out = {}
    for src in sorted(set(s.tolist())):
        sel = m & (s == src)
        if not sel.any():
            raise ValueError(f"la fuente {src} no tiene filas de calibración")
        out[src] = x[sel].mean(axis=0)
    return out


def apply_centers(
    x: np.ndarray, sources: Sequence[str], centers: dict[str, np.ndarray]
) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    return x - np.vstack([centers[v] for v in sources])


def safe_roc_auc(labels: Sequence[int], scores: Sequence[float]) -> float | None:
    y = np.asarray(labels, dtype=int)
    if len(set(y.tolist())) < 2:
        return None
    return float(roc_auc_score(y, np.asarray(scores, dtype=np.float64)))

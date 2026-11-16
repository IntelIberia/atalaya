"""Interfaces (``Protocol``) para enchufar las piezas que llegan en otras tareas del hito 2.

- ``EmbeddingModel``: YAMNet en ONNX (H2.6 da la implementación ``OnnxEmbeddingModel``).
- ``ChannelNormalizer``: normalización de canal compartida con Colab (H2.1, ``acoustic_pilot``).
- ``HarmonicFeatures``: rasgo armónico de hélices (H2.4, ``acoustic_pilot``).
- ``SpeechGate``: puerta de voz en directo (H2.9).
- ``DroneScorer``: regresión + Platt sobre embedding y rasgos (H2.10).
- ``Source``: origen de bloques de sonido; ``capture.SoundDeviceSource`` en el Mac y fuentes
  sintéticas en los tests (H2.7).

Ningún método devuelve ni recibe rutas de fichero: todo vive en memoria.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

Float32Array = NDArray[np.float32]
FloatArray = NDArray[np.floating]


@runtime_checkable
class EmbeddingModel(Protocol):
    """Una ventana mono de ``window_samples`` a 16 kHz → (embedding, puntuaciones por clase)."""

    window_samples: int

    def infer(self, window: Float32Array) -> tuple[FloatArray, FloatArray]: ...


@runtime_checkable
class ChannelNormalizer(Protocol):
    """Ventana cruda → ventana normalizada de la misma longitud (sin E/S)."""

    def __call__(self, window: Float32Array, sample_rate: int) -> Float32Array: ...


@runtime_checkable
class HarmonicFeatures(Protocol):
    """Ventana normalizada → vector corto de rasgos armónicos, en el orden del artefacto."""

    names: tuple[str, ...]

    def __call__(self, window: Float32Array, sample_rate: int) -> FloatArray: ...


@runtime_checkable
class SpeechGate(Protocol):
    """``True`` si la ventana contiene voz y debe descartarse antes del clasificador."""

    def is_speech(self, class_scores: FloatArray) -> bool: ...


@runtime_checkable
class DroneScorer(Protocol):
    """Embedding + rasgos armónicos → probabilidad calibrada de dron en [0, 1]."""

    def probability(self, embedding: FloatArray, harmonic: FloatArray) -> float: ...


@runtime_checkable
class Source(Protocol):
    """Origen de bloques mono ``float32`` en [-1, 1] a ``sample_rate`` Hz.

    ``start`` recibe la función a la que entregar cada bloque (se copia; el origen puede
    reutilizar su memoria). ``stop`` cierra el dispositivo y es idempotente.
    """

    sample_rate: int

    def start(self, on_block: BlockCallback) -> None: ...

    def stop(self) -> None: ...


class BlockCallback(Protocol):
    def __call__(self, block: Float32Array, /) -> None: ...

"""Trayectorias por puntos de paso con límites cinemáticos por clase (T1.11, REQ-FUN-004).

Modelo (sintético y declarado como tal):

- En horizontal, tramos rectos unidos por **giros coordinados** (arcos de circunferencia tangentes
  a ambos tramos). El radio es `max(v/ω_max, v²/(a_max/2))`: la tasa de giro no supera la de la
  clase y la aceleración centrípeta no pasa de la mitad de la máxima.
- C1-C2 (`can_hover`) arrancan y paran en reposo, con perfil trapezoidal de aceleración
  tangencial `a_max/2`, y pueden hacer **vuelo estacionario** (`hover_s`) en un punto de paso.
  El resto de clases vuela a velocidad constante y no admite estacionario.
- La altitud sigue un `smoothstep` entre puntos de paso (velocidad vertical nula en cada uno).
- Antes de construir se comprueban cotas superiores de velocidad, aceleración y espacio para cada
  giro; si la ruta es imposible para la clase → `ValueError` con la clase y el límite.

Coordenadas ENU locales en metros respecto al centro del emplazamiento; tiempos en segundos
desde el inicio de la trayectoria.
"""

from __future__ import annotations

import bisect
import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass

from sim.classes import ClassKinematics, kinematics

Vec2 = tuple[float, float]
Vec3 = tuple[float, float, float]
_MAX_TURN_DEG = 179.0


@dataclass(frozen=True)
class Waypoint:
    east_m: float
    north_m: float
    up_m: float
    hover_s: float = 0.0


@dataclass(frozen=True)
class State:
    position: Vec3
    velocity: Vec3
    acceleration: Vec3


@dataclass(frozen=True)
class _Piece:
    s0: float
    length: float
    start: Vec2
    direction: Vec2  # tramo recto
    center: Vec2  # arco
    radius: float
    angle0: float
    sign: float  # 0 recto, +1 antihorario, -1 horario

    def at(self, sigma: float) -> tuple[Vec2, Vec2, float]:
        """Posición, tangente unitaria y curvatura con signo a `sigma` metros del inicio."""
        if self.sign == 0:
            x = self.start[0] + self.direction[0] * sigma
            y = self.start[1] + self.direction[1] * sigma
            return (x, y), self.direction, 0.0
        phi = self.angle0 + self.sign * sigma / self.radius
        pos = (
            self.center[0] + self.radius * math.cos(phi),
            self.center[1] + self.radius * math.sin(phi),
        )
        tangent = (-self.sign * math.sin(phi), self.sign * math.cos(phi))
        return pos, tangent, self.sign / self.radius


def _line(s0: float, a: Vec2, b: Vec2) -> _Piece:
    length = math.dist(a, b)
    direction = ((b[0] - a[0]) / length, (b[1] - a[1]) / length) if length > 0 else (1.0, 0.0)
    return _Piece(s0, length, a, direction, (0.0, 0.0), 0.0, 0.0, 0.0)


class _Run:
    """Tramo entre paradas: geometría horizontal, nudos de altitud y perfil de velocidad."""

    def __init__(
        self, pieces: list[_Piece], knots: list[tuple[float, float]], speed: float, accel: float
    ) -> None:
        self.pieces = pieces
        self.starts = [p.s0 for p in pieces]
        self.knots_s = [k[0] for k in knots]
        self.knots_z = [k[1] for k in knots]
        self.length = knots[-1][0]
        self.accel = accel
        if accel == 0:
            self.peak = speed
            self.d_acc = self.t_acc = 0.0
        else:
            self.peak = min(speed, math.sqrt(accel * self.length))
            self.t_acc = self.peak / accel
            self.d_acc = self.peak * self.peak / (2 * accel)
        self.t_cruise = max(0.0, self.length - 2 * self.d_acc) / self.peak
        self.duration = 2 * self.t_acc + self.t_cruise

    def profile(self, tau: float) -> tuple[float, float, float]:
        """(s, ṡ, s̈) a `tau` segundos del inicio del tramo."""
        a, vp = self.accel, self.peak
        if a == 0:
            return min(vp * tau, self.length), vp, 0.0
        if tau < self.t_acc:
            return 0.5 * a * tau * tau, a * tau, a
        if tau <= self.t_acc + self.t_cruise:
            return self.d_acc + vp * (tau - self.t_acc), vp, 0.0
        rest = max(0.0, self.duration - tau)
        return self.length - 0.5 * a * rest * rest, a * rest, -a

    def time_at(self, s: float) -> float:
        a, vp = self.accel, self.peak
        if a == 0:
            return s / vp
        if s < self.d_acc:
            return math.sqrt(2 * s / a)
        if s <= self.length - self.d_acc:
            return self.t_acc + (s - self.d_acc) / vp
        return self.duration - math.sqrt(max(0.0, 2 * (self.length - s) / a))

    def state(self, tau: float) -> State:
        s, sd, sdd = self.profile(tau)
        s = min(max(s, 0.0), self.length)
        index = max(0, bisect.bisect_right(self.starts, s) - 1)
        piece = self.pieces[index]
        (x, y), (tx, ty), kappa = piece.at(min(s - piece.s0, piece.length))
        k = min(max(bisect.bisect_right(self.knots_s, s) - 1, 0), len(self.knots_s) - 2)
        s0, s1 = self.knots_s[k], self.knots_s[k + 1]
        dz, span = self.knots_z[k + 1] - self.knots_z[k], s1 - s0
        u = (s - s0) / span
        z = self.knots_z[k] + dz * (3 * u * u - 2 * u * u * u)
        z_s = dz * 6 * u * (1 - u) / span
        z_ss = dz * (6 - 12 * u) / (span * span)
        normal = sd * sd * kappa
        return State(
            (x, y, z),
            (sd * tx, sd * ty, z_s * sd),
            (sdd * tx - normal * ty, sdd * ty + normal * tx, z_ss * sd * sd + z_s * sdd),
        )


class Trajectory:
    """Trayectoria de una clase por `route` a velocidad horizontal `speed_mps`."""

    @staticmethod
    def turn_radius_m(class_id: str, speed_mps: float) -> float:
        k = kinematics(class_id)
        omega = math.radians(k.max_turn_rate_dps.value)
        return max(speed_mps / omega, 2 * speed_mps * speed_mps / k.max_accel_mps2.value)

    def __init__(self, class_id: str, route: Sequence[Waypoint], speed_mps: float) -> None:
        self.class_id = class_id
        self.kin = kinematics(class_id)
        self._check_inputs(route, speed_mps)
        self.route = list(route)
        self.speed = speed_mps
        self.radius = self.turn_radius_m(class_id, speed_mps)
        self.waypoint_tolerance_m = [0.0] * len(route)
        self.waypoint_times_s = [0.0] * len(route)
        self._segments: list[tuple[float, float, _Run | Vec3]] = []
        hover = self.kin.can_hover
        stops = [0, *[i for i in range(1, len(route) - 1) if route[i].hover_s > 0]]
        stops.append(len(route) - 1)
        if not hover:
            stops = [0, len(route) - 1]
        t = 0.0
        if hover:
            t = self._hover(0, t)
        for a, b in itertools.pairwise(stops):
            run, knot_indices = self._build_run(
                a, b, accel=self.kin.max_accel_mps2.value / 2 if hover else 0.0
            )
            for index, s in knot_indices:
                self.waypoint_times_s[index] = t + run.time_at(s)
            self._segments.append((t, t + run.duration, run))
            t += run.duration
            self.waypoint_times_s[b] = t
            if hover:
                t = self._hover(b, t)
        self.duration_s = t

    def _hover(self, index: int, t: float) -> float:
        p = self.route[index]
        end = t + p.hover_s
        self._segments.append((t, end, (p.east_m, p.north_m, p.up_m)))
        return end

    def _fail(self, message: str) -> ValueError:
        return ValueError(f"{self.class_id}: {message}")

    def _check_inputs(self, route: Sequence[Waypoint], speed: float) -> None:
        k: ClassKinematics = self.kin
        if len(route) < 2:
            raise self._fail("la ruta necesita al menos dos puntos de paso")
        if not math.isfinite(speed) or speed <= 0:
            raise self._fail(f"velocidad inválida: {speed!r}")
        if speed > k.max_speed_mps.value:
            raise self._fail(
                f"velocidad {speed:g} m/s supera el máximo de la clase "
                f"({k.max_speed_mps.value:g} m/s)"
            )
        for index, p in enumerate(route):
            if not all(math.isfinite(v) for v in (p.east_m, p.north_m, p.up_m)):
                raise self._fail(f"punto {index} con coordenadas no finitas")
            if not math.isfinite(p.hover_s) or p.hover_s < 0:
                raise self._fail(f"punto {index}: vuelo estacionario inválido ({p.hover_s!r} s)")
            if p.hover_s > 0 and not k.can_hover:
                raise self._fail("la clase no admite vuelo estacionario")
        for index in range(len(route) - 1):
            a, b = route[index], route[index + 1]
            if math.hypot(b.east_m - a.east_m, b.north_m - a.north_m) <= 1e-9:
                raise self._fail(f"tramo {index} sin desplazamiento horizontal")

    def _build_run(
        self, first: int, last: int, accel: float
    ) -> tuple[_Run, list[tuple[int, float]]]:
        pts = self.route[first : last + 1]
        xy = [(p.east_m, p.north_m) for p in pts]
        legs = [math.dist(xy[i], xy[i + 1]) for i in range(len(xy) - 1)]
        dirs = [
            ((xy[i + 1][0] - xy[i][0]) / legs[i], (xy[i + 1][1] - xy[i][1]) / legs[i])
            for i in range(len(legs))
        ]
        r = self.radius
        turns = [0.0] * len(xy)
        signs = [0.0] * len(xy)
        for i in range(1, len(xy) - 1):
            d_in, d_out = dirs[i - 1], dirs[i]
            cross = d_in[0] * d_out[1] - d_in[1] * d_out[0]
            dot = d_in[0] * d_out[0] + d_in[1] * d_out[1]
            turns[i] = math.atan2(abs(cross), dot)
            signs[i] = 1.0 if cross >= 0 else -1.0
            if math.degrees(turns[i]) > _MAX_TURN_DEG:
                raise self._fail(
                    f"giro de {math.degrees(turns[i]):.0f}° en el punto {first + i} imposible "
                    "sin vuelo estacionario"
                )
        tangent = [r * math.tan(theta / 2) for theta in turns]
        for j, leg in enumerate(legs):
            need = tangent[j] + tangent[j + 1]
            if need > leg + 1e-9:
                i = j if tangent[j] >= tangent[j + 1] else j + 1
                raise self._fail(
                    f"giro de {math.degrees(turns[i]):.0f}° en el punto {first + i} necesita "
                    f"{need:.0f} m de tramo a {self.speed:g} m/s y hay {leg:.0f} m (radio mínimo "
                    f"{r:.0f} m: tasa de giro máx. {self.kin.max_turn_rate_dps.value:g} °/s, "
                    f"aceleración máx. {self.kin.max_accel_mps2.value:g} m/s²)"
                )
        pieces: list[_Piece] = []
        knots: list[tuple[float, float]] = [(0.0, pts[0].up_m)]
        knot_indices: list[tuple[int, float]] = []
        s = 0.0
        current = xy[0]
        for i in range(1, len(xy) - 1):
            d_in, d_out, t_len = dirs[i - 1], dirs[i], tangent[i]
            a_pt = (xy[i][0] - d_in[0] * t_len, xy[i][1] - d_in[1] * t_len)
            line = _line(s, current, a_pt)
            pieces.append(line)
            s += line.length
            sign = signs[i]
            center = (a_pt[0] - sign * d_in[1] * r, a_pt[1] + sign * d_in[0] * r)
            angle0 = math.atan2(a_pt[1] - center[1], a_pt[0] - center[0])
            arc_len = r * turns[i]
            pieces.append(_Piece(s, arc_len, a_pt, d_in, center, r, angle0, sign))
            knots.append((s + arc_len / 2, pts[i].up_m))
            knot_indices.append((first + i, s + arc_len / 2))
            self.waypoint_tolerance_m[first + i] = r * (1 / math.cos(turns[i] / 2) - 1)
            s += arc_len
            current = (xy[i][0] + d_out[0] * t_len, xy[i][1] + d_out[1] * t_len)
        line = _line(s, current, xy[-1])
        pieces.append(line)
        s += line.length
        knots.append((s, pts[-1].up_m))
        run = _Run([p for p in pieces if p.length > 0] or [line], knots, self.speed, accel)
        self._check_bounds(run, first, any(t > 0 for t in turns))
        return run, knot_indices

    def _check_bounds(self, run: _Run, first: int, has_arcs: bool) -> None:
        k = self.kin
        vp, a_t = run.peak, run.accel
        a_c = vp * vp / self.radius if has_arcs else 0.0
        for j in range(len(run.knots_s) - 1):
            span = run.knots_s[j + 1] - run.knots_s[j]
            dz = abs(run.knots_z[j + 1] - run.knots_z[j])
            if span <= 0:
                raise self._fail(f"tramo {first + j} sin desplazamiento horizontal")
            vz = 1.5 * dz / span * vp
            az = 6 * dz * vp * vp / (span * span) + 1.5 * dz / span * a_t
            if math.hypot(vp, vz) > k.max_speed_mps.value:
                raise self._fail(
                    f"pendiente vertical del tramo {first + j} exige {math.hypot(vp, vz):.1f} m/s "
                    f"(máximo {k.max_speed_mps.value:g} m/s)"
                )
            total = math.sqrt(a_t * a_t + a_c * a_c + az * az)
            if total > k.max_accel_mps2.value:
                raise self._fail(
                    f"cambio vertical del tramo {first + j} exige {total:.2f} m/s² "
                    f"(aceleración máx. {k.max_accel_mps2.value:g} m/s²)"
                )

    def state(self, t: float) -> State:
        if not 0.0 <= t <= self.duration_s:
            raise ValueError(f"instante fuera de la trayectoria: {t!r} (0…{self.duration_s:g} s)")
        for start, end, item in self._segments:
            if isinstance(item, tuple) and start <= t <= end:
                return State(item, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        for start, end, item in self._segments:
            if isinstance(item, _Run) and start <= t <= end:
                return item.state(t - start)
        raise AssertionError("instante sin tramo: la línea temporal no es contigua")

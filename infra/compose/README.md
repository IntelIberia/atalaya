# infra/compose

Stack local de la FASE 0 (T0.10): `make up` / `make smoke` / `make down`. Credenciales en `.env`
(`make bootstrap`), nunca en el repositorio.

- **Contraseñas fuera de argv** (revisión P5): NATS las lee de `nats/nats.conf` (variables de entorno
  `$NATS_USER`/`$NATS_PASSWORD`); Redis genera `/tmp/redis.conf` al arrancar con el `printf` interno
  de `sh`. El healthcheck y el smoke de Mosquitto pasan la contraseña por argv a `mosquitto_sub`/`pub`,
  procesos efímeros dentro del contenedor: riesgo aceptado.
- **Imágenes fijadas por `etiqueta@sha256:digest`**. Para actualizar: `docker pull imagen:etiqueta`
  y `docker inspect --format '{{index .RepoDigests 0}}' imagen:etiqueta`.

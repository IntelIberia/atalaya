# Investigación: fuentes abiertas de sonidos de fondo españoles (negativos para Ceuta)

- **Fecha de consulta:** 2026-11-11 (todas las URL y licencias se consultaron ese día).
- **Propósito:** buscar audio de fondo **sin drones** grabado en España o en un entorno mediterráneo o norteafricano comparable, para entrenar y evaluar el clasificador de SOLO DETECCIÓN de Atalaya (piloto en Ceuta: prisión, puerto y frontera).
- **Estado:** solo es investigación. Ninguna fuente queda dada de alta. Antes de usar cualquiera hay que pasar la skill `dataset-intake` (licencia verificada, hash, procedencia, data card y análisis de fugas).
- **Convención:** **NO VERIFICADO** quiere decir que no lo pude confirmar en una fuente primaria. Si una licencia no aparece literalmente, no se da por hecha.
- **Cómo se consultó:** las fuentes se leyeron por web el 2026-11-11. Xeno-canto (`/about/terms` y `/explore/api`) y el repositorio DAU de la URL bloquearon el acceso automático («Access Denied»), y la página de MDPI devolvió 403. Lo que dependa de esas páginas queda marcado como NO VERIFICADO.

---

## 1. Resumen ejecutivo

1. **No existe ningún corpus abierto de audio grabado en Ceuta.** En Freesound, la búsqueda «ceuta» da 4 resultados, y todos son de protestas o del paso fronterizo, con voz y contenido político. No sirven como negativos. La grabación propia en Ceuta es **imprescindible** y es la única fuente realmente del dominio.
2. **Los ayuntamientos (Barcelona/Sentilo, Valencia, Madrid) y AENA publican solo niveles (LAeq en dB), no audio.** Sirven para calibrar los niveles y la relación señal/ruido de la aumentación, no como negativos de audio.
3. **El audio abierto con uso comercial es escaso y se concede por grabación.** Freesound (CC0/CC-BY por sonido), FSD50K (con subconjunto CC0/CC-BY), BCNDataset (CC BY 4.0, Barcelona), radio aporee, Xeno-canto e iNaturalist (licencia por grabación) son las únicas vías viables.
4. **Trampa importante en Freesound:** aunque el sonido sea CC0 o CC-BY, **la API de Freesound solo es gratuita para fines no comerciales**. Para un uso comercial de la API hay que negociar una licencia con el MTG-UPF (ver §3.1).
5. **Quedan excluidos por ser no comerciales o tener derechos reservados:** DCASE/TAU Urban Acoustic Scenes 2019 y 2020 («Other (Non-Commercial)»), BBC Sound Effects (RemArc), UrbanSound8K (CC BY-NC), Historical Soundscapes (CC BY-NC) y RTVE (derechos reservados). ShipsEar (Vigo) no tiene licencia publicada y es audio **subacuático**.
6. **Ninguna licencia revisada tiene una cláusula que excluya expresamente la seguridad o la vigilancia.** El riesgo legal principal no está en las licencias. Está en el **RGPD (voz en espacios públicos)** y en los **permisos para grabar** en recintos penitenciarios, portuarios, fronterizos y de Defensa.

---

## 2. Tabla de fuentes

Leyenda de la columna «Comercial»: **Sí** (lo permite la licencia), **Por grabación** (hay que filtrar), **No** o **?** (NO VERIFICADO).

| # | Fuente | URL original | Licencia (literal / tal como figura) | Comercial | Cláusula anti-seguridad/vigilancia | Voz / datos personales | Volumen | Grabaciones largas continuas | Ubicación España/Med. |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Freesound** (sonidos individuales) | https://freesound.org/ · API: https://freesound.org/docs/api/resources_apiv2.html | Por sonido. Valores del campo `license`: «Creative Commons 0», «Attribution», «Attribution NonCommercial» (más el antiguo Sampling+). **Términos de la API:** «You can use the Freesound API for free only for non-commercial purposes.» / «To use the Freesound API for commercial purposes, please contact us using the Freesound contact form» (https://freesound.org/docs/api/terms_of_use.html) | Por grabación (CC0/CC-BY sí). **La API comercial requiere un acuerdo** | No encontrada. Hay un panel de «Generative AI preferences» del autor (afecta a la IA generativa; conviene respetarlo y registrarlo) | Alto en grabaciones urbanas o de mercados. Filtrar por etiquetas y aplicar VAD | Cientos de miles de sonidos en total. La parte geoetiquetada en España: NO VERIFICADO (requiere consulta con token) | Algunas (campo `duration`, filtro `duration:[600 TO *]`) | Sí, con el filtro `geotag` |
| 2 | **FSD50K** (MTG-UPF, Barcelona) | https://zenodo.org/records/4060432 | Zenodo: «Other (Attribution)». El conjunto en bloque es CC-BY (`LICENSE-DATASET`). **Cada clip conserva su licencia:** dev 14.959 CC0 / 20.017 CC-BY / 4.616 CC-BY-NC / 1.374 Sampling+; eval 4.914 / 3.489 / 1.425 / 403 | Por grabación (excluir NC y Sampling+) | No encontrada | Hay clases de voz y de multitud. Excluirlas por etiqueta | 51.197 clips, 108,3 h | No (clips ≤30 s) | No geolocalizado. Útil por clases (helicóptero, moto, gaviota, viento, oleaje, barco) |
| 3 | **BCNDataset** (La Salle - URL, con el Ayuntamiento de Barcelona) | https://zenodo.org/records/3956503 · artículo: https://doi.org/10.3390/su12198140 | «Creative Commons Attribution 4.0 International» (CC BY 4.0) | Sí | No encontrada | **Alto**: ocio nocturno (bares y peatones). Hay que aplicar VAD y revisar antes de usarlo | 363 min 53 s (≈6 h), 3 WAV de unos 2 GB | Sí, probablemente (3 ficheros largos; NO VERIFICADO si son continuos) | Barcelona, centro |
| 4 | **radio aporee ::: maps** (y copia en archive.org) | https://aporee.org/maps/info | Por grabación: «one of 6 Creative Commons licences, and public domain», elegida por el autor y no revocable | Por grabación (filtrar CC0/PD/CC-BY/CC-BY-SA) | No encontrada | Medio-alto (paisajes urbanos). VAD | Total y parte española: NO VERIFICADO | Sí, muchas son tomas largas (NO VERIFICADO por pieza) | Hay grabaciones españolas (p. ej. Córdoba, Guadalquivir) |
| 5 | **Xeno-canto** (aves; también ortópteros) | https://xeno-canto.org/ · API v3: https://xeno-canto.org/api/3/recordings | Por grabación, elegida por el grabador. Hay muchas BY-NC-SA y BY-NC-ND. La lista exacta de licencias posibles y si existe CC0: **NO VERIFICADO** (la página de términos bloqueó el acceso automático) | Por grabación (solo CC0/CC-BY/CC-BY-SA; excluir NC y ND) | No encontrada | Bajo (alguna voz del grabador al anunciar la especie: recortar) | España: NO VERIFICADO | No (cortes cortos) | Sí, por país (`cnt:`; sintaxis NO VERIFICADA) |
| 6 | **iNaturalist** (sonidos de observaciones: chicharras, gaviotas) | https://api.inaturalist.org/v1/docs/ | Licencia por sonido (CC0/CC-BY/CC-BY-NC…). Parámetros de filtro: **NO VERIFICADO** (la documentación no se pudo leer) | Por grabación | NO VERIFICADO | Bajo | NO VERIFICADO | No | Sí (filtro por lugar) |
| 7 | **Barcelona: red de monitorización de ruido** (Sentilo) | https://opendata-ajuntament.barcelona.cat/data/dataset/xarxasoroll-equipsmonitor-dades | «Creative Commons Attribution 4.0» | Sí | No | No hay audio | LAeq_1min (2024-07/2026) y LAeq_1h (2015-2023) | No aplica (solo niveles) | Barcelona |
| 8 | **Valencia: sensores de ruido de Russafa y estaciones ZAS** | p. ej. https://opendata.vlci.valencia.es/en/dataset/t248678-daily | Se vio CC BY 4.0 en algunas fichas y «Licencia no especificada» en otra. **Verificar ficha por ficha** | ? | No | No hay audio | LAeq diario y por minuto | No aplica | Valencia |
| 9 | **Madrid: red de vigilancia acústica** | https://datos.gob.es/catalogo/l01280796-contaminacion-acustica-estaciones-de-medida1 | **NO VERIFICADO** (el campo de licencia no se pudo leer) | ? | No | No hay audio | 31 estaciones fijas, índices diarios | No aplica | Madrid |
| 10 | **AENA SIRMA / WebTrak** | https://www.aena.es/es/corporativa/sostenibilidad-ambiental/ruido/sistemas-de-monitorado-de-ruido/as-madrid-barajas.html | NO VERIFICADO | ? | No | No hay audio | Niveles por evento y informes mensuales | No aplica | Madrid, Barcelona, Valencia, Málaga… (no se encontró nada de Ceuta ni Algeciras) |
| 11 | **DCASE: TAU Urban Acoustic Scenes 2019 / 2020 Mobile** | https://zenodo.org/records/2589280 · https://zenodo.org/records/3670167 | «Other (Non-Commercial)» («No further description») | **No** | No aplica | Medio | 2019: ≈40 h; 2020: 64 h; segmentos de 10 s | No | Incluye Barcelona, Madrid y Lisboa según fuentes secundarias |
| 12 | **ShipsEar** (Universidad de Vigo, Uvigo-Sonitum) | https://underwaternoise.atlanttic.uvigo.es/ | **No publica licencia.** Solo «©Uvigo-Sonitum 2016». Acceso completo: «send a request to the email contact» | ? (hay que solicitarlo) | No encontrada | Bajo | 90 grabaciones de 11 tipos de buque (artículo de 2016). Duraciones de unos 10 s a 11 min (las fuentes no coinciden) | No | Puerto de Vigo. **Es un hidrófono (submarino), no audio aéreo** |
| 13 | **DYNAMAP** (La Salle GTM; Milán urbano 154 h, Roma A90) | https://sciforum.net/paper/6637 · https://dau.url.edu/handle/20.500.14342/3417 | La licencia de los **datos** es NO VERIFICADA (CC BY 4.0 y CC BY-NC-ND 4.0 solo se refieren a los **artículos**) | ? | No encontrada | Medio-alto | 154 h (Milán) + Roma | Sí | Italia (mediterráneo comparable) |
| 14 | **SATP** (Universidad de Granada) | https://zenodo.org/records/18715282 | CC BY 4.0 | Sí | No | Medio | 27 × 30 s, binaural | No | **Londres** (no es España). Poco útil |
| 15 | **UrbanSound8K** | https://zenodo.org/records/1203745 | CC BY-NC | **No** | No aplica | Medio | 8.732 clips | No | Nueva York |
| 16 | **Historical Soundscapes** | https://www.historicalsoundscapes.com/en/informacion/aviso-legal | «Creative Commons Attribution-NonCommercial 4.0» (salvo indicación contraria) | **No** | No aplica | Medio | NO VERIFICADO | NO VERIFICADO | España. Ceuta solo como reconstrucción histórica, sin grabación |
| 17 | **IPCE: Mapa de Patrimonio Sonoro No Musical de España** | (web del IPCE) | NO VERIFICADO | ? | No aplica | Variable | Es un **directorio de fondos**, no audio descargable | No aplica | España |
| 18 | **Fonoteca / mapas sonoros autonómicos** (Escoitar.org, Carlos de la Hita, etc.) | varias | No se encontró ninguna licencia abierta verificada | ? | No aplica | Variable | NO VERIFICADO | NO VERIFICADO | España |
| 19 | **RTVE / RNE (Archivo de la Palabra)** | https://www.rtve.es/ · licencia de retos con la Cátedra RTVE-Unizar: https://catedrartve.unizar.es/docs/RTVE_database_license_v2025_v3.pdf | Derechos reservados. La licencia de los retos dice «All materials shall remain the property of RTVE» (pensada para retos de investigación) | **No** (sin contrato) | No aplica | Alto (radio y TV) | No aplica | No aplica | España |
| 20 | **BBC Sound Effects** | https://sound-effects.bbcrewind.co.uk/ | RemArc: uso personal, educativo y de investigación. El uso comercial requiere licencia (Pro Sound Effects) | **No** (excluido) | No aplica | No aplica | ≈33.000 | No aplica | Reino Unido |

Notas a la tabla:
- «Voz»: todo el audio urbano o portuario puede contener voz identificable. Bajo el RGPD/LOPDGDD, la voz de una persona identificable es un dato personal. Aunque la fuente sea CC0, la licencia **no** resuelve el tratamiento de datos de terceros. Mitigación común en el §5.
- No se ha medido la duración en España de Freesound, Xeno-canto, aporee ni iNaturalist porque hace falta una clave o token. Es la primera tarea de `dataset-intake`.

---

## 3. Cómo filtrar por licencia y ubicación

### 3.1 Freesound (API v2)

**Antes de nada, el aspecto legal.** Atalaya es comercial, así que **hay que pedir al MTG-UPF una licencia comercial de la API** a través de https://freesound.org/contact/. Mientras no exista ese acuerdo, la única vía limpia es la **descarga manual** desde la web de sonidos CC0/CC-BY concretos, con su atribución. Los términos de la API no mencionan almacenamiento ni seguridad.

- Autenticación: la búsqueda funciona con un token (`token=…`). Para **descargar el original** hace falta **OAuth2** (`Authorization: Bearer …`). Con solo el token se obtienen *previews* con pérdida (mp3/ogg), que **no** sirven para entrenar.
- Límites de peticiones por usuario («burst» por minuto y «sustained» por 24 h), consultables en `GET /apiv2/usage/`. Las cifras exactas no están documentadas en la página.
- Filtros documentados:
  - Radio: `filter={!geofilt sfield=geotag pt=<LAT>,<LON> d=<KM>}`
  - Rectángulo: `geotag:"Intersects(<minLon> <minLat> <maxLon> <maxLat>)"` (la documentación también muestra otra forma `geotag:[... TO ...]`, que no es coherente con esta: **probar ambas**).
  - Licencia: `license:"Creative Commons 0"` o `license:"Attribution"`.
  - Duración: `duration:[600 TO *]` (`TO` en mayúsculas).
  - Campos: `fields=id,name,username,license,geotag,duration,tags,description,samplerate,channels`.

Ejemplos (sin probar contra la API real; validarlos durante el alta):

```text
# Estrecho de Gibraltar (Ceuta, Algeciras, Tánger) en un radio de 60 km, CC0, de 60 s o más
GET https://freesound.org/apiv2/search/?query=
    &filter={!geofilt sfield=geotag pt=35.889,-5.316 d=60} license:"Creative Commons 0" duration:[60 TO *]
    &fields=id,name,username,license,geotag,duration,tags,description
    &page_size=150&token=<TOKEN>

# España peninsular y Baleares, CC-BY, por etiquetas relevantes
GET https://freesound.org/apiv2/search/?query=seagull OR waves OR moped OR scooter OR harbour OR ferry OR wind OR cicada OR helicopter
    &filter=geotag:"Intersects(-9.5 35.8 4.5 43.9)" license:"Attribution"
    &fields=...&token=<TOKEN>
# Repetir para Canarias y para Melilla (35.29,-2.94) por separado.
```

Después de buscar:
- Excluir las etiquetas `voice`, `speech`, `talk*`, `conversation`, `crowd`, `people`, `protest`, `market`.
- Aplicar VAD y escucha muestral.
- Guardar `username`, `license` y la URL de cada sonido para generar la atribución CC-BY.
- Registrar la preferencia de IA generativa del autor si la API la expone (NO VERIFICADO).
- La geoetiqueta la pone el autor y **puede ser imprecisa**.

### 3.2 FSD50K
Filtrar con el fichero de licencias por clip que trae el conjunto. Quedarse solo con CC0 y CC-BY, y excluir CC-BY-NC y Sampling+. Excluir las clases de voz y de multitud de la ontología de AudioSet. Mantener la partición dev/eval original para evitar fugas.

### 3.3 Xeno-canto (API v3)
- Desde el 10-10-2025 hace falta una **clave**, asociada a una cuenta con el correo verificado (`https://xeno-canto.org/api/3/recordings?query=…&key=…`).
- Las etiquetas de consulta `cnt:spain`, `lic:` y `grp:` **no se pudieron verificar**: el sitio bloqueó el acceso automático.
- Filtrar en el cliente por el campo de licencia de la respuesta. Quedarse solo con CC0, BY o BY-SA (y valorar BY-SA por la cláusula «compartir igual» sobre los derivados). Excluir NC y ND.
- El FAQ de Xeno-canto pide contactar con el grabador en proyectos con componente económico, incluso dudosos.

### 3.4 iNaturalist / radio aporee
Licencia por elemento. Descargar los metadatos, filtrar por licencia (CC0/CC-BY o dominio público) y por lugar (España, Ceuta, Melilla, norte de Marruecos), y guardar el autor y la URL. Los parámetros exactos de la API de iNaturalist son NO VERIFICADO.

---

## 4. Recomendación ordenada para Ceuta

| Prioridad | Fuente | Para qué | Condición previa |
|---|---|---|---|
| 1 | **Grabación propia en Ceuta** (§5) | La única fuente del dominio. Base de la medición de **falsas alarmas por hora** | Autorizaciones, DPIA, VAD |
| 2 | **Freesound CC0/CC-BY geoetiquetado** en el Estrecho, Andalucía, el Levante y el norte de Marruecos | Gaviotas, oleaje, levante/poniente, motos y ciclomotores, ferris, megafonía, helicópteros | **Licencia comercial de la API (MTG)** o descarga manual. Filtro de voz |
| 3 | **FSD50K, subconjunto CC0/CC-BY** | Variedad por clase (helicóptero, avioneta, moto, barco, viento, agua, insectos) y negativos difíciles | Filtro por licencia de clip. Excluir voz |
| 4 | **BCNDataset** (CC BY 4.0) | Prueba larga de falsas alarmas por hora en una ciudad mediterránea española (tráfico y motos nocturnas) | VAD y revisión de voz. Atribución |
| 5 | **radio aporee / archive.org**, solo CC0/PD/CC-BY | Tomas largas de costa, puertos y ciudades españolas | Verificar la licencia de cada pieza. VAD |
| 6 | **Xeno-canto / iNaturalist** CC0/BY(/BY-SA) | Gaviotas (*Larus michahellis*), pardelas, vencejos, chicharras y ortópteros | Filtrar por licencia y recortar la locución |
| 7 | **Niveles municipales** (Barcelona CC BY 4.0; Valencia por ficha; mapa de ruidos de Ceuta) | Calibrar la SNR y los niveles día/noche en la aumentación y en el simulador | Solo números, sin audio |
| 8 | **ShipsEar / DYNAMAP** | Solo si se obtiene una licencia escrita (correo a los autores) | ShipsEar es subacuático: solo valdría con hidrófono |
| No usar | DCASE TAU (NC), UrbanSound8K (NC), BBC (RemArc), RTVE, Historical Soundscapes (NC), las 4 grabaciones «Ceuta» de Freesound (protestas con voz) | | |

---

## 5. Plan de grabación propia de fondo en Ceuta

Lo exige el MEGAPROMPT: «50-100 h de fondo sin drones por emplazamiento, en sesiones autorizadas y con voz suprimida» (§253). La grabación solo se permite en una «sesión autorizada explícita, con supresión de voz (VAD), registro de consentimiento y metadatos» (§104). Antes de tratar datos de personas hace falta asesoría jurídica (regla 9).

### 5.1 Emplazamientos y horas
| Emplazamiento | Horas objetivo | Fuentes de ruido esperadas |
|---|---|---|
| Perímetro del centro penitenciario | 50-100 h | Tráfico de acceso, megafonía interior, perros, viento, aves, obras |
| Puerto (Autoridad Portuaria de Ceuta) | 50-100 h | Ferris de Algeciras (motores, bocinas), grúas, megafonía, gaviotas, oleaje, motos de agua, helicóptero (Helipuerto de Ceuta: NO VERIFICADO que haya línea regular activa) |
| Frontera (Tarajal / Benzú) | 50-100 h | Colas de vehículos, ciclomotores y motos, megafonía, viento de levante, multitudes (**voz: riesgo alto**) |

### 5.2 Estratificación (para no sesgar la medición de falsas alarmas por hora)
- **Viento:** levante, poniente y calma. Cada sesión debe incluir un anemómetro con registro de velocidad y dirección cada 1 s.
- **Hora:** día, tarde y noche. **Día de la semana:** laborable y festivo.
- **Estación:** verano (chicharras; Operación Paso del Estrecho con picos de tráfico portuario y de motos) e invierno (temporales).
- **Eventos etiquetables mediante registros externos:** ADS-B (aeronaves y helicópteros), AIS (buques) y horarios de ferris. Sirven como negativos difíciles etiquetados automáticamente.

### 5.3 Captura
- **El mismo micrófono y el mismo nodo** que se desplegarán, para que el dominio coincida. 48 kHz, sin AGC, ganancia fija documentada y calibrador acústico al principio y al final.
- **Sesiones continuas de 2 a 12 h**, con hora GPS/PTP. Se necesitan continuas para medir falsas alarmas por hora de forma realista.
- Metadatos por sesión: autorización, responsable, emplazamiento (coordenadas a nivel de emplazamiento), meteorología, versión del firmware, hash SHA-256 de cada fichero y log de VAD.
- **«Sin drones»:** no se puede garantizar. Etiquetar el material como «negativo presunto». Coordinar con el operador del emplazamiento por si hay vuelos autorizados. Revisar a mano los segmentos con mayor puntuación y excluir o reetiquetar los dudosos.

### 5.4 Supresión de voz (VAD) y privacidad
1. VAD en el borde antes de guardar nada (p. ej. WebRTC VAD o Silero VAD; elegirlo y evaluarlo en un ADR). Usar un umbral conservador y **descartar el segmento completo con un margen de ±1 s**. No basta con atenuarlo.
2. Medir la tasa de voz residual con una auditoría humana sobre una muestra aleatoria (p. ej. el 1 % de los segmentos, con un objetivo de 0 segmentos con habla inteligible). Si la auditoría falla, se descarta la sesión.
3. Nada de audio en la nube. Almacenamiento cifrado y retención configurable. Registro de actividades de tratamiento y DPIA en `docs/dpia/`.
4. Prohibido grabar a menos de X m de puntos de conversación (garitas, colas peatonales). La distancia la fija la asesoría jurídica.
5. Particionar train/val/test **por sesión y día**, nunca por segmentos de la misma sesión, para evitar fugas.

### 5.5 Autorizaciones (a confirmar con asesoría jurídica; nada de esto está verificado)
- Prisión: Secretaría General de Instituciones Penitenciarias / dirección del centro.
- Puerto: Autoridad Portuaria de Ceuta.
- Frontera: Delegación del Gobierno, Policía Nacional y Guardia Civil.
- Posibles zonas de interés para la Defensa Nacional: Ministerio de Defensa.
- Hay que comprobar si la captación de sonido en lugares públicos cae en algún régimen especial (normativa de videovigilancia y captación de sonido por las FCSE, y LO 7/2021). Esto lo determina la asesoría, no este informe.

---

## 6. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| **Usar la API de Freesound con fines comerciales sin acuerdo** | Incumplir los términos de la API | Licencia del MTG-UPF o descarga manual; registrarlo en `dataset-intake` |
| La licencia comercial de la API de Freesound puede tener coste, y el presupuesto obligatorio es **0 €** (CLAUDE.md) | Bloqueo de la vía API | Si hay coste, hace falta un ADR. Si no, descarga manual de sonidos concretos, que es más lenta |
| **Voz en audio urbano** (fuentes abiertas y propias) | RGPD/LOPDGDD; reputación | Filtro por etiquetas, VAD, auditoría muestral, descartar segmentos y DPIA |
| Licencia por grabación mal registrada (CC-BY sin atribución, NC o ND colados) | Infracción de licencia | Manifiesto por fichero con licencia, autor, URL y hash; test que falle si aparece NC o ND |
| CC-BY-SA en Xeno-canto o aporee | Posible obligación de «compartir igual» sobre derivados | Excluir SA del conjunto de entrenamiento comercial salvo que la asesoría diga otra cosa |
| Desajuste de dominio (otro micrófono o compresión mp3) | Falsas alarmas infraestimadas | Usar las fuentes abiertas solo para entrenar o aumentar. **Medir las falsas alarmas por hora solo con grabación propia de Ceuta** |
| Geoetiquetas de Freesound imprecisas | Sesgo geográfico | Usarlas como indicio, no como garantía |
| Drones no declarados dentro del «fondo» | Negativos contaminados | Revisar los segmentos con mayor puntuación y etiquetarlos como «negativo presunto» |
| Fuga entre particiones (segmentos de la misma sesión) | Métricas infladas | Particionar por sesión, día y emplazamiento |
| Permisos de grabación en recintos sensibles | Bloqueo del piloto o sanción | Asesoría jurídica antes de cualquier sesión (regla 9 del MEGAPROMPT) |
| Fuentes sin licencia (ShipsEar, DYNAMAP, mapas sonoros) | Uso no autorizado | No usarlas hasta tener una licencia escrita |

---

## 7. Pendientes que se resuelven con `dataset-intake`
- [ ] Pedir la licencia comercial de la API de Freesound (MTG-UPF) y medir las horas de CC0/CC-BY geoetiquetadas en España y en el Estrecho.
- [ ] Verificar los términos de Xeno-canto (licencias posibles y sintaxis `cnt:`/`lic:`) desde un navegador.
- [ ] Verificar los parámetros de la API de iNaturalist (`sounds`, licencia de sonido, `place_id`).
- [ ] Confirmar si los 3 WAV de BCNDataset son continuos y revisar sus clases (artículo DOI 10.3390/su12198140).
- [ ] Escribir a Uvigo (ShipsEar) y a La Salle GTM (DYNAMAP) para pedir la licencia de los datos.
- [ ] Verificar las licencias de Madrid (datos.madrid.es), de cada ficha de Valencia y del mapa de ruidos de Ceuta.

# carrusel-elquebradero

API REST para generar imágenes de carruseles de Instagram para **El Quebradero**. Recibe el contenido de un artículo vía JSON y devuelve slides JPEG listos para publicar (formato 1080 × 1350 px).

---

## Qué hace

1. El cliente llama a `POST /generar` con el título, categoría, imagen de portada y los puntos de contenido.
2. La API lanza el trabajo en un hilo de fondo y responde inmediatamente con un `job_id`.
3. El script `generar_carrusel.py` construye tres tipos de slides con Pillow:
   - **Portada** — imagen de fondo con degradado, etiqueta de categoría y título.
   - **Contenido** (uno por cada elemento en `slides`) — subtítulo + cuerpo en texto.
   - **CTA** — slide final con la URL del artículo.
4. El cliente consulta `GET /resultado/<job_id>` hasta que el estado sea `ok`, y obtiene las URLs de descarga de cada slide.

---

## Arquitectura

```
         Cliente (n8n / Make / curl)
                    │
          POST /generar (JSON)
                    │
             ┌──────▼──────┐
             │   api.py    │  Flask · puerto 8000
             │  (jobs={})  │
             └──────┬──────┘
      hilo daemon   │  subprocess
                    ▼
          generar_carrusel.py
          (Pillow · LiberationSans)
                    │
            /app/output/<job_id>/
            slide_01.jpg … slide_NN.jpg
                    │
          GET /output/<job_id>/slide_NN.jpg
```

Los trabajos se almacenan **en memoria** (dict `jobs`). Al reiniciar el contenedor los jobs pendientes o completados se pierden, pero las imágenes ya guardadas en disco permanecen mientras exista el volumen.

---

## Endpoints

### `GET /health`

Comprobación de vida del servicio.

**Respuesta 200**
```json
{ "status": "ok" }
```

---

### `POST /generar`

Lanza la generación del carrusel de forma asíncrona.

**Body JSON**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `titulo` | string | Sí | Título principal del artículo (slide de portada) |
| `slides` | array | Sí | Lista de slides de contenido (mínimo 1) |
| `slides[].subtitulo` | string | Sí | Titular del slide de contenido |
| `slides[].cuerpo` | string | Sí | Texto del slide de contenido |
| `categoria` | string | No | Etiqueta de categoría en portada. Default: `"SEVILLA"` |
| `imagen_url` | string | No | URL de la imagen de fondo de la portada |
| `url` | string | No | URL del artículo para el slide CTA. Default: `"elquebradero.com"` |

**Ejemplo de body**
```json
{
  "titulo": "El Betis vence al Sevilla en el derbi",
  "categoria": "FÚTBOL",
  "imagen_url": "https://ejemplo.com/foto.jpg",
  "url": "elquebradero.com/betis-sevilla",
  "slides": [
    { "subtitulo": "Primer gol", "cuerpo": "Isco abrió el marcador en el minuto 23." },
    { "subtitulo": "La remontada", "cuerpo": "El Betis marcó dos goles en el segundo tiempo." }
  ]
}
```

**Respuesta 200**
```json
{ "job_id": "a3f7b2c1", "status": "procesando" }
```

---

### `GET /resultado/<job_id>`

Consulta el estado de un trabajo.

**Respuesta — en proceso**
```json
{ "status": "procesando" }
```

**Respuesta — completado**
```json
{
  "status": "ok",
  "total": 4,
  "slides": [
    "https://carrusel-elquebradero.sliplane.app/output/a3f7b2c1/slide_01.jpg",
    "https://carrusel-elquebradero.sliplane.app/output/a3f7b2c1/slide_02.jpg",
    "https://carrusel-elquebradero.sliplane.app/output/a3f7b2c1/slide_03.jpg",
    "https://carrusel-elquebradero.sliplane.app/output/a3f7b2c1/slide_04.jpg"
  ]
}
```

**Respuesta — error**
```json
{ "status": "error", "error": "mensaje de error" }
```

**Respuesta 404** — si el `job_id` no existe.

---

### `GET /output/<job_id>/<filename>`

Descarga directa de un slide JPEG generado.

---

## Variables de entorno

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `BASE_URL` | No | `https://carrusel-elquebradero.sliplane.app` | URL base pública del servicio. Se usa para construir las URLs de los slides en la respuesta de `/resultado`. Debe apuntar al dominio donde está desplegado el contenedor. |

---

## Dependencias

| Paquete | Uso |
|---------|-----|
| Flask | Servidor HTTP |
| Pillow | Generación de imágenes |
| requests | Descarga de la imagen de portada desde URL |
| fonts-liberation | Fuente LiberationSans (portada y contenido) |

---

## Despliegue

### Con Docker (local)

```bash
docker build -t carrusel-elquebradero .
docker run -p 8000:8000 -e BASE_URL=http://localhost:8000 carrusel-elquebradero
```

La API quedará disponible en `http://localhost:8000`.

### En Sliplane

El proyecto está configurado para desplegarse en [Sliplane](https://sliplane.io). Sliplane construye la imagen a partir del `Dockerfile` y expone el puerto 8000.

Variables a configurar en el panel de Sliplane:

| Variable | Valor |
|----------|-------|
| `BASE_URL` | `https://carrusel-elquebradero.sliplane.app` (o el dominio asignado) |

El directorio `/app/output` vive dentro del contenedor. Si se necesita persistencia de imágenes entre reinicios, configurar un volumen que monte ese directorio.

---

## Notas de diseño

- El carrusel generado siempre tiene **portada + N slides de contenido + 1 CTA**, con un total de `N + 2` slides.
- Las imágenes se guardan en JPEG con calidad 95.
- El timeout máximo de generación es de **120 segundos** por trabajo.
- Los trabajos se procesan en hilos daemon; si el proceso principal muere, los hilos en vuelo se cancelan.

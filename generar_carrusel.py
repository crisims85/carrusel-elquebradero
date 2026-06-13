import json, sys, os, time, requests

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

W, H = 1080, 1350

BG = "#111111"
ROJO = "#e02020"
BLANCO = "#ffffff"
GRIS = "#aaaaaa"
GRIS_OSCURO = "#333333"

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

# Márgenes
M = 120        # margen lateral izquierdo y derecho
MAX_W = W - (M * 2)  # ancho máximo del texto: 1080 - 240 = 840px

def error_fatal(motivo):
    """Aborta el servicio reportando el motivo en stderr y en stdout (JSON) con exit 2."""
    print(motivo, file=sys.stderr)
    print(json.dumps({"error": "PORTADA_SIN_IMAGEN", "motivo": motivo}))
    sys.exit(2)

def fuente(size):
    try: return ImageFont.truetype(FONT_BOLD, size)
    except: return ImageFont.load_default()

def fuente_normal(size):
    try: return ImageFont.truetype(FONT_REG, size)
    except: return ImageFont.load_default()

def wrap(texto, f, draw, max_w):
    palabras = texto.split()
    lineas, linea = [], ""
    for p in palabras:
        prueba = linea + " " + p if linea else p
        if draw.textlength(prueba, font=f) <= max_w: linea = prueba
        else:
            if linea: lineas.append(linea)
            linea = p
    if linea: lineas.append(linea)
    return lineas

def pie(draw, num_slide, total):
    y = H - 90
    draw.rectangle([M, y, W-M, y+1], fill=GRIS_OSCURO)
    f = fuente(32)
    draw.text((M, y+14), "EL ", font=f, fill=BLANCO)
    ancho_el = draw.textlength("EL ", font=f)
    draw.text((M+ancho_el, y+14), "QUEBRADERO", font=f, fill=ROJO)

def url_valida(u):
    """True solo si img_url es una URL http(s) real. Rechaza '', 'false', 'null', etc."""
    if not u or not isinstance(u, str):
        return False
    u = u.strip()
    if u.lower() in ("false", "null", "none", "undefined", ""):
        return False
    return u.startswith("http://") or u.startswith("https://")

def descargar_foto(img_url, intentos=3):
    """Descarga la imagen con reintentos. Devuelve (Image, None) o (None, motivo_error)."""
    ultimo_error = None
    for n in range(intentos):
        try:
            r = requests.get(img_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()  # lanza error si el status no es 2xx (404, 500, etc.)
            foto = Image.open(BytesIO(r.content)).convert("RGB")
            return foto, None
        except Exception as e:
            ultimo_error = e
            print(f"Intento {n+1}/{intentos} fallido al descargar imagen: {e}", file=sys.stderr)
            if n < intentos - 1:
                time.sleep(2)  # espera 2s antes de reintentar
    return None, f"No se pudo descargar la imagen tras {intentos} intentos: {ultimo_error}"

def slide_portada(titulo, categoria, img_url, num, total):
    # 1. Validar que hay URL de imagen antes de nada
    if not url_valida(img_url):
        error_fatal(f"Falta la imagen de portada o la URL no es valida (recibido: '{img_url}')")

    # 2. Descargar la imagen (con reintentos). Si falla, abortar reportando el motivo.
    foto, err = descargar_foto(img_url)
    if foto is None:
        error_fatal(f"Falta la imagen de portada: {err}")

    # 3. Procesar la imagen: recorte a 1080x1350 + degradado oscuro inferior
    try:
        ratio = max(W/foto.width, H/foto.height)
        nw, nh = int(foto.width*ratio), int(foto.height*ratio)
        foto = foto.resize((nw, nh), Image.LANCZOS)
        x, y = (nw-W)//2, (nh-H)//2
        foto = foto.crop((x, y, x+W, y+H))

        inicio_gradiente = int(H * 0.40)
        gradiente = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_grad = ImageDraw.Draw(gradiente)
        for fila in range(inicio_gradiente, H):
            progreso = (fila - inicio_gradiente) / (H - inicio_gradiente)
            alpha = int(progreso * 200)
            draw_grad.line([(0, fila), (W, fila)], fill=(0, 0, 0, alpha))

        foto_rgba = foto.convert("RGBA")
        foto_rgba.paste(gradiente, (0, 0), gradiente)
        img = foto_rgba.convert("RGB")
    except Exception as e:
        error_fatal(f"Falta la imagen de portada: la imagen se descargo pero no se pudo procesar: {e}")

    # 4. Dibujar textos sobre la imagen
    draw = ImageDraw.Draw(img)

    fc = fuente(38)
    cat_w = int(draw.textlength(categoria.upper(), font=fc)) + 30
    draw.rectangle([M, 900, M+cat_w, 950], fill=ROJO)
    draw.text((M+15, 906), categoria.upper(), font=fc, fill=BLANCO)

    draw.rectangle([M, 973, M+70, 978], fill=ROJO)
    ft = fuente(56)
    lineas = wrap(titulo, ft, draw, MAX_W)
    y = 990
    for l in lineas[:4]:
        draw.text((M, y), l, font=ft, fill=BLANCO)
        y += 68

    pie(draw, num, total)
    return img

def slide_contenido(subtitulo, cuerpo, num, total):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([M, 380, M+70, 386], fill=ROJO)
    fs = fuente(62)
    lineas_sub = wrap(subtitulo, fs, draw, MAX_W)
    y = 406
    for l in lineas_sub[:2]:
        draw.text((M, y), l, font=fs, fill=BLANCO)
        y += 76

    fb = fuente_normal(46)
    lineas_b = wrap(cuerpo, fb, draw, MAX_W)
    y += 20
    for l in lineas_b:
        draw.text((M, y), l, font=fb, fill=GRIS)
        y += 62

    pie(draw, num, total)
    return img

def slide_cta(url, num, total):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    f = fuente(58)
    t1, t2 = "Lee la informacion completa", "en El Quebradero"
    w1, w2 = draw.textlength(t1, font=f), draw.textlength(t2, font=f)
    draw.text(((W-w1)//2, 530), t1, font=f, fill=BLANCO)
    draw.text(((W-w2)//2, 606), t2, font=f, fill=BLANCO)

    fu = fuente(50)
    wu = draw.textlength(url, font=fu)
    draw.text(((W-wu)//2, 730), url, font=fu, fill=ROJO)

    pie(draw, num, total)
    return img


data        = json.loads(sys.argv[1])
titulo      = data["titulo"]
categoria   = data.get("categoria", "SEVILLA")
img_url     = data.get("imagen_url", "")
url         = data.get("url", "elquebradero.com")
slides_data = data["slides"]
total       = len(slides_data) + 2
output_dir  = data.get("output_dir", "/app/output")
os.makedirs(output_dir, exist_ok=True)

rutas = []

# La portada se genera PRIMERO. Si no hay imagen valida, slide_portada aborta
# con exit(2) y el resto del script (slides de contenido y CTA) no se ejecuta:
# no se crea ninguna imagen y no se gasta nada de procesamiento.
s = slide_portada(titulo, categoria, img_url, 1, total)
ruta = f"{output_dir}/slide_01.jpg"
s.save(ruta, "JPEG", quality=95)
rutas.append(ruta)

for i, slide in enumerate(slides_data):
    s = slide_contenido(slide["subtitulo"], slide["cuerpo"], i+2, total)
    ruta = f"{output_dir}/slide_{str(i+2).zfill(2)}.jpg"
    s.save(ruta, "JPEG", quality=95)
    rutas.append(ruta)

s = slide_cta(url, total, total)
ruta = f"{output_dir}/slide_{str(total).zfill(2)}.jpg"
s.save(ruta, "JPEG", quality=95)
rutas.append(ruta)

print(json.dumps({"slides": rutas, "total": total}))

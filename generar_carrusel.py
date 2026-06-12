import json, sys, os, requests
import numpy as np

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350

BG = "#111111"
ROJO = "#e02020"
BLANCO = "#ffffff"
GRIS = "#aaaaaa"
GRIS_OSCURO = "#333333"

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

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
    draw.rectangle([60, y, W-60, y+1], fill=GRIS_OSCURO)
    f = fuente(32)
    draw.text((60, y+14), "EL ", font=f, fill=BLANCO)
    ancho_el = draw.textlength("EL ", font=f)
    draw.text((60+ancho_el, y+14), "QUEBRADERO", font=f, fill=ROJO)

def slide_portada(titulo, categoria, img_url, num, total):
    img = Image.new("RGB", (W, H), BG)
    if img_url:
        try:
            r = requests.get(img_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            from io import BytesIO
            foto = Image.open(BytesIO(r.content)).convert("RGB")
            ratio = max(W/foto.width, H/foto.height)
            nw, nh = int(foto.width*ratio), int(foto.height*ratio)
            foto = foto.resize((nw, nh), Image.LANCZOS)
            x, y = (nw-W)//2, (nh-H)//2
            foto = foto.crop((x, y, x+W, y+H))

            # Gradiente vectorizado con numpy (sustituye el bucle putpixel píxel a píxel)
            inicio_gradiente = int(H * 0.40)
            alphas = np.zeros(H, dtype=np.uint8)
            alphas[inicio_gradiente:] = np.linspace(0, 200, H - inicio_gradiente).astype(np.uint8)
            grad_array = np.zeros((H, W, 4), dtype=np.uint8)
            grad_array[:, :, 3] = alphas[:, np.newaxis]
            gradiente = Image.fromarray(grad_array, "RGBA")

            foto_rgba = foto.convert("RGBA")
            foto_rgba.paste(gradiente, (0, 0), gradiente)
            img = foto_rgba.convert("RGB")
        except Exception as e:
            print(f"Error imagen: {e}", file=sys.stderr)

    draw = ImageDraw.Draw(img)

    fc = fuente(38)
    cat_w = int(draw.textlength(categoria.upper(), font=fc)) + 30
    draw.rectangle([60, 900, 60+cat_w, 950], fill=ROJO)
    draw.text((75, 906), categoria.upper(), font=fc, fill=BLANCO)

    draw.rectangle([60, 973, 130, 978], fill=ROJO)
    ft = fuente(56)
    lineas = wrap(titulo, ft, draw, W-130)
    y = 990
    for l in lineas[:4]:
        draw.text((60, y), l, font=ft, fill=BLANCO)
        y += 68

    pie(draw, num, total)
    return img

def slide_contenido(subtitulo, cuerpo, num, total):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([60, 380, 130, 386], fill=ROJO)
    fs = fuente(62)
    lineas_sub = wrap(subtitulo, fs, draw, W-120)
    y = 406
    for l in lineas_sub[:2]:
        draw.text((60, y), l, font=fs, fill=BLANCO)
        y += 76

    fb = fuente_normal(46)
    lineas_b = wrap(cuerpo, fb, draw, W-120)
    y += 20
    for l in lineas_b:
        draw.text((60, y), l, font=fb, fill=GRIS)
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


data       = json.loads(sys.argv[1])
titulo     = data["titulo"]
categoria  = data.get("categoria", "SEVILLA")
img_url    = data.get("imagen_url", "")
url        = data.get("url", "elquebradero.com")
slides_data = data["slides"]
total      = len(slides_data) + 2
output_dir = data.get("output_dir", "/app/output")
os.makedirs(output_dir, exist_ok=True)

rutas = []

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

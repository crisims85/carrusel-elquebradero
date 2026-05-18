FROM python:3.12-slim
RUN apt-get update && apt-get install -y fonts-liberation && rm -rf /var/lib/apt/lists/*
RUN pip install pillow requests flask
WORKDIR /app
RUN mkdir -p /app/output

RUN cat > /app/generar_carrusel.py << 'EOF'
import json, sys, os, requests
from PIL import Image, ImageDraw, ImageFont

# CAMBIO 1: Dimensiones actualizadas a formato 4:5 (recomendado para feed de Instagram)
W, H = 1080, 1350

BG = "#111111"
ROJO = "#e02020"
BLANCO = "#ffffff"
GRIS = "#aaaaaa"
GRIS_OSCURO = "#333333"
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

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

            # CAMBIO 2: Sustituimos el blend uniforme por un gradiente
            # Antes: img = Image.blend(foto, oscuro, 0.55)
            # Eso ponía un 55% de negro sobre TODA la imagen, tapando mucho la foto.
            #
            # Ahora: creamos una capa RGBA con un gradiente que va de
            # alpha=0 (transparente) en la parte superior
            # a alpha=200 (bastante opaco) en la parte inferior.
            # Así la foto se ve con claridad arriba, y el texto tiene
            # contraste suficiente en la zona inferior donde aparece.

            gradiente = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            for fila in range(H):
                # La opacidad empieza a subir desde el 40% de altura
                # y llega al máximo (200 de 255) al final de la imagen
                inicio_gradiente = int(H * 0.40)
                if fila < inicio_gradiente:
                    alpha = 0
                else:
                    progreso = (fila - inicio_gradiente) / (H - inicio_gradiente)
                    alpha = int(progreso * 200)
                for col in range(W):
                    gradiente.putpixel((col, fila), (0, 0, 0, alpha))

            # Convertimos la foto a RGBA para poder pegar el gradiente encima
            foto_rgba = foto.convert("RGBA")
            foto_rgba.paste(gradiente, (0, 0), gradiente)
            # Volvemos a RGB para guardar como JPEG
            img = foto_rgba.convert("RGB")

        except Exception as e:
            print(f"Error imagen: {e}", file=sys.stderr)

    draw = ImageDraw.Draw(img)

    # La categoría y el título bajan un poco porque ahora tenemos más altura (1350 vs 1080)
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

    # El contenido se centra verticalmente en la nueva altura
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
    # El CTA también se centra en la nueva altura
    draw.text(((W-w1)//2, 530), t1, font=f, fill=BLANCO)
    draw.text(((W-w2)//2, 606), t2, font=f, fill=BLANCO)
    fu = fuente(50)
    wu = draw.textlength(url, font=fu)
    draw.text(((W-wu)//2, 730), url, font=fu, fill=ROJO)
    pie(draw, num, total)
    return img

data = json.loads(sys.argv[1])
titulo = data["titulo"]
categoria = data.get("categoria", "SEVILLA")
img_url = data.get("imagen_url", "")
url = data.get("url", "elquebradero.com")
slides_data = data["slides"]
total = len(slides_data) + 2
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
EOF

RUN cat > /app/api.py << 'EOF'
import json, os, subprocess, uuid, threading
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)
jobs = {}

def procesar(job_id, data, base_url):
    try:
        run_id = job_id
        output_dir = f"/app/output/{run_id}"
        data["output_dir"] = output_dir
        resultado = subprocess.run(
            ["python3", "/app/generar_carrusel.py", json.dumps(data)],
            capture_output=True, text=True, timeout=120
        )
        if resultado.returncode != 0:
            jobs[job_id] = {"status": "error", "error": resultado.stderr}
            return
        output = json.loads(resultado.stdout.strip())
        urls = [f"{base_url}/output/{run_id}/{os.path.basename(r)}" for r in output["slides"]]
        jobs[job_id] = {"status": "ok", "total": output["total"], "slides": urls}
    except Exception as e:
        jobs[job_id] = {"status": "error", "error": str(e)}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/output/<path:filename>')
def servir_imagen(filename):
    return send_from_directory('/app/output', filename)

@app.route('/generar', methods=['POST'])
def generar():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se recibio JSON"}), 400
    job_id = str(uuid.uuid4())[:8]
    base_url = os.environ.get("BASE_URL", "https://carrusel-test.lwytb3.easypanel.host")
    jobs[job_id] = {"status": "procesando"}
    t = threading.Thread(target=procesar, args=(job_id, data, base_url))
    t.daemon = True
    t.start()
    return jsonify({"job_id": job_id, "status": "procesando"})

@app.route('/resultado/<job_id>', methods=['GET'])
def resultado(job_id):
    if job_id not in jobs:
        return jsonify({"error": "job no encontrado"}), 404
    return jsonify(jobs[job_id])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
EOF

CMD ["python3", "/app/api.py"]

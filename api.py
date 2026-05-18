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
    base_url = os.environ.get("BASE_URL", "https://carrusel-elquebradero.sliplane.app")
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

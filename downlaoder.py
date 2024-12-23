from flask import Flask, render_template, request, jsonify
from pathlib import Path
import yt_dlp as youtube_dl
import json
import threading

app = Flask(__name__)

# Configuración inicial
CONFIG_PATH = Path.home() / ".cancion_downloader_config.json"

# Estado global para el progreso
estado_progreso = {"busqueda": "", "descarga": ""}

# Cargar configuración
def cargar_configuracion():
    default_config = {
        'download_path': str(Path.home() / "Music" / "Downloads"),
        'search_limit': 10,
        'format': 'mp3'
    }
    if CONFIG_PATH.is_file():
        with open(CONFIG_PATH, 'r') as config_file:
            user_config = json.load(config_file)
            return {**default_config, **user_config}
    return default_config

# Guardar configuración
def guardar_configuracion(config):
    with open(CONFIG_PATH, 'w') as config_file:
        json.dump(config, config_file)

# Obtener ruta de descarga
def obtener_ruta_descarga(config):
    ruta = Path(config["download_path"])
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta

@app.route('/')
def index():
    config = cargar_configuracion()
    return render_template('index.html', config=config)

@app.route('/buscar', methods=['POST'])
def buscar():
    busqueda = request.form.get('busqueda')
    if not busqueda:
        return jsonify({'error': 'La búsqueda no puede estar vacía'}), 400

    config = cargar_configuracion()
    ydl_opts = {
        'format': 'bestaudio/best' if config["format"] == "mp3" else 'bestvideo+bestaudio',
        'noplaylist': True,
    }

    estado_progreso["busqueda"] = "Buscando canciones..."
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            resultados = ydl.extract_info(f"ytsearch{config['search_limit']}:{busqueda}", download=False)
            estado_progreso["busqueda"] = "Búsqueda completada."
            if 'entries' in resultados and len(resultados['entries']) > 0:
                # Añadir detalles como duración y tamaño
                for entry in resultados['entries']:
                    entry['duration_formatted'] = (
                        f"{entry['duration'] // 60}m {entry['duration'] % 60}s"
                        if 'duration' in entry else "Duración desconocida"
                    )
                    entry['size'] = (
                        f"{round(entry.get('filesize', 0) / (1024 * 1024), 2)} MB"
                        if 'filesize' in entry else "Tamaño desconocido"
                    )
                return jsonify({'resultados': resultados['entries']})
            else:
                estado_progreso["busqueda"] = "No se encontraron resultados."
                return jsonify({'error': 'No se encontraron resultados'}), 404
    except Exception as e:
        estado_progreso["busqueda"] = f'Error al buscar: {str(e)}'
        return jsonify({'error': f'Error al buscar: {str(e)}'}), 500

@app.route('/progreso', methods=['GET'])
def progreso():
    return jsonify(estado_progreso)

@app.route('/descargar', methods=['POST'])
def descargar():
    enlace = request.form.get('enlace')
    if not enlace:
        return jsonify({'error': 'El enlace no puede estar vacío'}), 400

    config = cargar_configuracion()
    salida = obtener_ruta_descarga(config)
    ydl_opts = {
        'format': 'bestaudio/best' if config["format"] == "mp3" else 'bestvideo+bestaudio',
        'outtmpl': str(salida / f'%(title)s.{"mp3" if config["format"] == "mp3" else "mp4"}'),
    }

    def descargar_enlace():
        estado_progreso["descarga"] = "Descargando..."
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([enlace])
                estado_progreso["descarga"] = "Descarga completada."
        except Exception as e:
            estado_progreso["descarga"] = f'Error al descargar: {str(e)}'

    thread = threading.Thread(target=descargar_enlace)
    thread.start()
    return jsonify({'message': 'Descarga iniciada'})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000)

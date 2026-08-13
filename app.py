import os
import re
import yt_dlp
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)

DOWNLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/fetch-info", methods=["POST"])
def fetch_info():
    data = request.get_json() or {}
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"status": "error", "message": "A valid media URL is required."}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            formats = []
            seen_heights = set()
            raw_formats = info.get('formats', [])
            
            preview_stream_url = info.get('url')
            
            for f in reversed(raw_formats):
                height = f.get('height')
                ext = f.get('ext')
                format_url = f.get('url')
                
                if not preview_stream_url and format_url:
                    preview_stream_url = format_url
                    
                if height and height not in seen_heights and ext in ['mp4', 'm3u8']:
                    seen_heights.add(height)
                    formats.append({
                        'format_id': f.get('format_id'),
                        'resolution': f"{height}p",
                        'ext': 'mp4',
                        'filesize': f.get('filesize') or f.get('filesize_approx') or 0,
                        'stream_url': format_url
                    })
            
            formats.sort(key=lambda x: int(x['resolution'].replace('p', '')), reverse=True)

            if not formats:
                formats.append({
                    'format_id': 'best',
                    'resolution': 'Best Available',
                    'ext': 'mp4',
                    'filesize': 0,
                    'stream_url': preview_stream_url
                })

            return jsonify({
                "status": "success",
                "data": {
                    "title": info.get('title', 'Video Media'),
                    "duration": info.get('duration', 0),
                    "thumbnail": info.get('thumbnail', ''),
                    "uploader": info.get('uploader', 'Unknown Creator'),
                    "preview_url": preview_stream_url,
                    "formats": formats
                }
            })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/convert", methods=["POST"])
def convert():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    format_id = data.get("format_id", "best")

    if not url:
        return jsonify({"status": "error", "message": "URL missing."}), 400

    output_template = os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s')

    ydl_opts = {
        'format': f'{format_id}/best[ext=mp4]/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if not filename.endswith('.mp4'):
                base_name = os.path.splitext(filename)[0]
                filename = f"{base_name}.mp4"

            return jsonify({
                "status": "success",
                "download_url": f"/api/download-file?file={os.path.basename(filename)}"
            })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/download-file", methods=["GET"])
def download_file():
    file_name = request.args.get("file", "")
    safe_path = os.path.abspath(os.path.join(DOWNLOAD_FOLDER, file_name))

    if not safe_path.startswith(os.path.abspath(DOWNLOAD_FOLDER)) or not os.path.exists(safe_path):
        return jsonify({"status": "error", "message": "File not found."}), 404

    return send_file(safe_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

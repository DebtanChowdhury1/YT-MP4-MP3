from flask import Flask, request, send_file, render_template, jsonify, after_this_request
from yt_dlp import YoutubeDL
import os, uuid

app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'
COOKIES_FILE = 'cookies.txt'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/formats', methods=['POST'])
def list_formats():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        seen = set()

        for f in info.get('formats', []):
            if (f.get('vcodec') != 'none' and f.get('acodec') == 'none' and f.get('ext') == 'mp4'):
                height = f.get('height')
                fid = f.get('format_id')
                if height and fid not in seen:
                    formats.append({
                        'format_id': fid,
                        'label': f"{height}p - mp4"
                    })
                    seen.add(fid)

        formats.sort(key=lambda x: int(x['label'].split('p')[0]))

        return jsonify({'title': info.get('title', 'Video'), 'formats': formats})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id')

    if not url or not format_id:
        return jsonify({'error': 'Missing URL or format ID'}), 400

    try:
        filename = f"{uuid.uuid4()}.mp4"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        ydl_opts = {
            'format': f"{format_id}+bestaudio",
            'outtmpl': filepath,
            'merge_output_format': 'mp4',
            'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }],
            'postprocessor_args': [
                '-c:v', 'copy',
                '-c:a', 'aac',  # Important: AAC supported by all players
                '-b:a', '192k',
                '-ac', '2'
            ]
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        @after_this_request
        def cleanup(response):
            try:
                os.remove(filepath)
            except Exception:
                pass
            return response

        return send_file(filepath, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download_audio', methods=['POST'])
def download_audio():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'Missing URL'}), 400

    try:
        uid = str(uuid.uuid4())
        final_mp3 = os.path.join(DOWNLOAD_FOLDER, uid + '.mp3')

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': final_mp3.replace('.mp3', '.%(ext)s'),
            'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }]
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        @after_this_request
        def cleanup(response):
            try:
                os.remove(final_mp3)
            except Exception:
                pass
            return response

        return send_file(final_mp3, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

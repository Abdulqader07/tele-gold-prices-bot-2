import threading
from datetime import datetime

from flask import Flask, jsonify, request
from config import config

app = Flask(__name__)

last_check_at = None
bot_running = False
_alert = None
_secret = None


def configure(alert, secret):
    global _alert, _secret
    _alert = alert
    _secret = secret


def mark_check():
    global last_check_at
    last_check_at = datetime.now().isoformat()


@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy' if bot_running else 'starting',
        'timestamp': datetime.now().isoformat(),
        'last_check_at': last_check_at,
    })


@app.route('/check', methods=['POST'])
def check():
    if _secret and request.headers.get('X-Check-Secret') != _secret:
        return jsonify({'error': 'unauthorized'}), 401
    if _alert is None:
        return jsonify({'error': 'not ready'}), 503

    import asyncio
    try:
        result = asyncio.run(_alert.checkPriceChange())
        mark_check()
        return jsonify({'ok': True, 'alerted': bool(result)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


def _run():
    app.run(host='0.0.0.0', port=config.PORT, debug=False, use_reloader=False)


def start_health_server():
    global bot_running
    bot_running = True
    threading.Thread(target=_run, daemon=True).start()
    print(f'Health server on port {config.PORT}')
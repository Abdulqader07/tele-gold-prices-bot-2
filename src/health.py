import threading
from datetime import datetime

from flask import Flask, jsonify
from config import config

app = Flask(__name__)

# Set by the main process so the health endpoint reports real state.
last_check_at = None
bot_running = False


def mark_check():
    global last_check_at
    last_check_at = datetime.now().isoformat()


@app.route('/')
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy' if bot_running else 'starting',
        'timestamp': datetime.now().isoformat(),
        'bot_running': bot_running,
        'last_check_at': last_check_at,
    })


def _run():
    app.run(host='0.0.0.0', port=config.PORT, debug=False, use_reloader=False)


def start_health_server():
    global bot_running
    bot_running = True
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    print(f'Health server started on port {config.PORT}')
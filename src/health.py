from flask import Flask, jsonify
from datetime import datetime
import threading

app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bot_running": True
    })

def run_health_server():
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
    
health_check_thread = threading.Thread(target=run_health_server, daemon=True)
health_check_thread.start()

print("Health check server started on port 8080")

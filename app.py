import os
import json
import urllib.parse
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)
SECRET = "APiX2026"

def is_running(ch_id):
    res = subprocess.run(["tmux", "has-session", "-t", str(ch_id)], capture_output=True)
    return res.returncode == 0

def parse_vless_to_xray(vless_url):
    parsed = urllib.parse.urlparse(vless_url)
    if parsed.scheme != 'vless': return None
    user_info = parsed.netloc.split('@')
    uuid = user_info[0]
    host_port = user_info[1].split(':')
    qs = urllib.parse.parse_qs(parsed.query)
    def get_qs(key, default=""): return qs.get(key, [default])[0]
    
    outbound = {
        "protocol": "vless",
        "settings": {"vnext": [{"address": host_port[0], "port": int(host_port[1]), "users": [{"id": uuid, "encryption": "none", "flow": get_qs("flow", "")}]}]},
        "streamSettings": {"network": get_qs("type", "tcp"), "security": get_qs("security", "none")}
    }
    if get_qs("security") == "reality":
        outbound["streamSettings"]["realitySettings"] = {"serverName": get_qs("sni"), "publicKey": get_qs("pbk"), "shortId": get_qs("sid"), "fingerprint": get_qs("fp", "chrome")}
    elif get_qs("security") == "tls":
        outbound["streamSettings"]["tlsSettings"] = {"serverName": get_qs("sni"), "fingerprint": get_qs("fp", "chrome")}

    return {"inbounds": [{"port": 1080, "listen": "127.0.0.1", "protocol": "socks", "settings": {"auth": "noauth", "udp": True}}], "outbounds": [outbound]}

def auto_start_vpn():
    vpn_url = os.environ.get("VPN_URL")
    if vpn_url:
        config = parse_vless_to_xray(vpn_url)
        if config:
            with open("config.json", "w") as f:
                json.dump(config, f)
            subprocess.run(["tmux", "new-session", "-d", "-s", "xray_vpn", "xray run -c config.json"])
            print("✅ VPN Started Automatically on port 1080")

@app.route('/')
def hello():
    return "APiX Cloud Terminal is Running 🚀"

@app.route('/api/tmux', methods=['POST'])
def tmux_api():
    data = request.json
    if not data or data.get("secret") != SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    
    action = data.get("action")
    ch_id = str(data.get("id"))
    
    if action == "status":
        return jsonify({"running": is_running(ch_id)})
    elif action == "start":
        cmd = data.get("cmd")
        if not is_running(ch_id):
            subprocess.run(["tmux", "new-session", "-d", "-s", ch_id])
            subprocess.run(["tmux", "send-keys", "-t", ch_id, cmd, "C-m"])
            return jsonify({"status": "started"})
        return jsonify({"status": "already_running"})
    elif action == "log":
        if is_running(ch_id):
            result = subprocess.run(["tmux", "capture-pane", "-t", ch_id, "-p", "-S", "-40"], capture_output=True, text=True)
            return jsonify({"status": "ok", "log": result.stdout})
        return jsonify({"status": "error", "log": "النافذة مغلقة."})
    elif action == "stop":
        if is_running(ch_id):
            subprocess.run(["tmux", "kill-session", "-t", ch_id])
            return jsonify({"status": "stopped"})
        return jsonify({"status": "not_running"})

if __name__ == '__main__':
    auto_start_vpn()
    app.run(host='0.0.0.0', port=7860)

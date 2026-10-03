import os
import json
import urllib.parse
import subprocess
from flask import Flask, request, jsonify, make_response

app = Flask(__name__)
SECRET = "APiX2026"

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
    return response

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
    # 1. تهيئة VLESS إذا كان موجوداً (على البورت 1080)
    vpn_url = os.environ.get("VPN_URL")
    if vpn_url:
        config = parse_vless_to_xray(vpn_url)
        if config:
            with open("config.json", "w") as f:
                json.dump(config, f)
            subprocess.run(["tmux", "new-session", "-d", "-s", "xray_vpn", "xray run -c config.json"])
            print("✅ VLESS VPN Ready on Socks5 port 1080")

    # 2. تهيئة Cloudflare WARP إذا كان موجوداً (على البورت 1081)
    vpn_cloud = os.environ.get("VPN_CLOUD")
    if vpn_cloud:
        with open("wg0.conf", "w") as f:
            f.write(vpn_cloud)
        
        wireproxy_conf = """WGConfig = wg0.conf
[Socks5]
BindAddress = 127.0.0.1:1081
"""
        with open("wireproxy.conf", "w") as f:
            f.write(wireproxy_conf)
            
        subprocess.run(["tmux", "new-session", "-d", "-s", "cloud_vpn", "wireproxy -c wireproxy.conf"])
        print("✅ Cloudflare VPN Ready on Socks5 port 1081")

@app.route('/')
def hello():
    return "APiX Cloud Terminal is Running 🚀"

@app.route('/api/tmux', methods=['POST', 'OPTIONS'])
def tmux_api():
    if request.method == 'OPTIONS':
        return make_response('', 204)

    data = request.json or {}
    if data.get("secret") != SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    
    action = data.get("action")
    ch_id = str(data.get("id"))
    
    if action == "status":
        return jsonify({"running": is_running(ch_id)})

    elif action == "start":
        cmd = data.get("cmd", "")
        if not is_running(ch_id):
            subprocess.run(["tmux", "new-session", "-d", "-s", ch_id])
            subprocess.run(["tmux", "send-keys", "-t", ch_id, "-l", cmd])
            subprocess.run(["tmux", "send-keys", "-t", ch_id, "Enter"])
            return jsonify({"status": "started", "running": True})
        return jsonify({"status": "already_running", "running": True})

    elif action == "log":
        if is_running(ch_id):
            result = subprocess.run(["tmux", "capture-pane", "-t", ch_id, "-p", "-S", "-50"], capture_output=True, text=True)
            return jsonify({"status": "ok", "log": result.stdout})
        return jsonify({"status": "error", "log": "النافذة مغلقة أو لم تبدأ بعد."})

    elif action == "stop":
        if is_running(ch_id):
            subprocess.run(["tmux", "kill-session", "-t", ch_id])
            return jsonify({"status": "stopped", "running": False})
        return jsonify({"status": "not_running", "running": False})

if __name__ == '__main__':
    auto_start_vpn()
    app.run(host='0.0.0.0', port=7860)

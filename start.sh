#!/bin/bash

# إذا كان لديك رمز نفق دائم، استخدمه، وإلا أنشئ نفقاً مؤقتاً
if [ -n "$CF_TOKEN" ]; then
    echo "🌐 Starting Cloudflare Tunnel with Token..."
    cloudflared tunnel run --token "$CF_TOKEN" &
else
    echo "🌐 Generating Cloudflare Quick Tunnel..."
    cloudflared tunnel --url http://localhost:7860 &
fi

# تشغيل تطبيق بايثون
python app.py

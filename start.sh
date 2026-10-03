#!/bin/bash

# تشغيل نفق سحابي مجاني يعطيك رابطاً مباشراً للتحكم
echo "🌐 Generating Cloudflare Tunnel for Control Panel..."
cloudflared tunnel --url http://localhost:7860 &

# تشغيل تطبيق بايثون الأساسي
python app.py

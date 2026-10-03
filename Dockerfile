FROM python:3.10-slim

# تثبيت الأدوات الأساسية
RUN apt-get update && apt-get install -y ffmpeg curl jq tmux wget unzip && rm -rf /var/lib/apt/lists/*

# تثبيت Cloudflared
RUN wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && dpkg -i cloudflared-linux-amd64.deb

# تثبيت Xray-core
RUN wget -q https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip && unzip Xray-linux-64.zip -d /usr/local/bin/ && chmod +x /usr/local/bin/xray

# تثبيت Wireproxy لتحويل إعدادات WireGuard إلى بروكسي SOCKS5
RUN wget -q https://github.com/octeep/wireproxy/releases/latest/download/wireproxy_linux_amd64.tar.gz && \
    tar -xzf wireproxy_linux_amd64.tar.gz && \
    mv wireproxy /usr/local/bin/ && \
    chmod +x /usr/local/bin/wireproxy

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app
COPY --chown=user:user . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 7860

CMD ["bash", "start.sh"]

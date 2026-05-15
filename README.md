# 餐评生成器

一个用 FastAPI 和阿里云百炼 / DashScope 模型生成 150 字中文餐厅点评的小工具。

## 本地运行

1. 复制环境变量示例：

```bash
cp .env.example .env
```

2. 编辑 `.env`：

```bash
DASHSCOPE_API_KEY=你的阿里云百炼APIKey
DASHSCOPE_MODEL=qwen3.6-flash
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
HOST=127.0.0.1
PORT=3000
```

3. 安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. 启动：

```bash
uvicorn main:app --host 127.0.0.1 --port 3000
```

5. 打开：

```text
http://localhost:3000
```

## 阿里云服务器部署

服务器需要 Python 3.10 或更新版本。

```bash
scp -r /path/to/this-folder root@你的服务器IP:/opt/restaurant-review-generator
ssh root@你的服务器IP
cd /opt/restaurant-review-generator
cp .env.example .env
vim .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 3000
```

生产环境推荐用 `systemd` 守护进程：

```ini
[Unit]
Description=Restaurant Review Generator
After=network.target

[Service]
WorkingDirectory=/opt/restaurant-review-generator
EnvironmentFile=/opt/restaurant-review-generator/.env
ExecStart=/opt/restaurant-review-generator/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 3000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

如果使用 Nginx，可反向代理到本服务：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 配置说明

- `DASHSCOPE_API_KEY`：阿里云百炼 API Key，必须放在后端环境变量里。
- `DASHSCOPE_MODEL`：模型名，默认 `qwen3.6-flash`。
- `DASHSCOPE_BASE_URL`：北京地域默认 `https://dashscope.aliyuncs.com/compatible-mode/v1`。
- `HOST`：默认 `127.0.0.1`，适合 Nginx 反代；直接开放端口时可设为 `0.0.0.0`。
- `PORT`：本地服务端口，默认 `3000`。

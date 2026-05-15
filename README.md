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

推荐用 Docker 运行应用容器，再用服务器上的 Nginx 转发 80 端口到容器。

```bash
ssh root@你的服务器IP
git clone git@github.com:LLLBO123/vibecoding.git /opt/restaurant-review-generator
cd /opt/restaurant-review-generator
cp .env.example .env
vim .env
docker compose up -d --build
```

Docker 会把应用绑定到服务器本机的 `127.0.0.1:8000`，不会直接暴露给公网。

也可以使用仓库里的脚本一次性启动 Docker 并安装 Nginx 配置：

```bash
cd /opt/restaurant-review-generator
sudo bash deploy/server-deploy.sh
```

### Nginx 反向代理

把仓库里的配置复制到 Nginx：

```bash
cp /opt/restaurant-review-generator/deploy/nginx/vibecoding.conf /etc/nginx/conf.d/vibecoding.conf
nginx -t
systemctl reload nginx
```

如果已经有域名，把 `server_name 47.115.133.42;` 改成你的域名：

```nginx
server_name your-domain.com;
```

### 常用 Docker 命令

```bash
docker compose ps
docker compose logs -f
docker compose restart
docker compose down
```

## 配置说明

- `DASHSCOPE_API_KEY`：阿里云百炼 API Key，必须放在后端环境变量里。
- `DASHSCOPE_MODEL`：模型名，默认 `qwen3.6-flash`。
- `DASHSCOPE_BASE_URL`：北京地域默认 `https://dashscope.aliyuncs.com/compatible-mode/v1`。
- `HOST`：默认 `127.0.0.1`，适合 Nginx 反代；直接开放端口时可设为 `0.0.0.0`。
- `PORT`：本地服务端口，默认 `3000`。

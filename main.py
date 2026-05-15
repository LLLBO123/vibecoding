import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Request as FastAPIRequest
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel


ROOT_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT_DIR / "public"


def load_local_env() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")

        if key and key not in os.environ:
            os.environ[key] = value


load_local_env()

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen3.6-flash")
DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
).rstrip("/")

app = FastAPI(title="Restaurant Review Generator")


@app.exception_handler(HTTPException)
async def http_exception_handler(
    _request: FastAPIRequest, exc: HTTPException
) -> JSONResponse:
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


class ReviewRequest(BaseModel):
    restaurantName: str | None = ""
    location: str | None = ""
    cuisine: str | None = ""
    price: str | None = ""
    highlights: str | None = ""
    scene: str | None = "朋友聚餐"
    tone: str | None = "真诚自然"
    sentiment: str | None = "正向好评"


class ReviewInput(BaseModel):
    restaurant_name: str
    location: str
    cuisine: str
    price: str
    highlights: str
    scene: str
    tone: str
    sentiment: str


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "model": DASHSCOPE_MODEL,
        "hasApiKey": bool(DASHSCOPE_API_KEY),
        "backend": "fastapi",
    }


@app.post("/api/review")
async def create_review(payload: ReviewRequest) -> dict[str, Any]:
    if not DASHSCOPE_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="缺少 DASHSCOPE_API_KEY，请先在 .env 或服务器环境变量中配置。",
        )

    review_input = normalize_input(payload)

    if not review_input.restaurant_name and not review_input.highlights:
        raise HTTPException(status_code=400, detail="至少填写餐厅名或亮点。")

    review = await generate_review(review_input)

    return {
        "review": review,
        "length": len(review),
        "model": DASHSCOPE_MODEL,
    }


@app.api_route("/{path:path}", methods=["GET", "HEAD"])
async def serve_static(path: str, _request: FastAPIRequest) -> Response:
    if path.startswith("api/"):
        return JSONResponse({"error": "Not found"}, status_code=404)

    requested = "index.html" if path in {"", "/"} else path
    target = (PUBLIC_DIR / requested).resolve()

    try:
        target.relative_to(PUBLIC_DIR.resolve())
    except ValueError:
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    if target.is_file():
        return FileResponse(target, headers=cache_headers(target))

    return FileResponse(PUBLIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})


async def generate_review(review_input: ReviewInput) -> str:
    prompt = "\n".join(
        [
            f"餐厅名：{review_input.restaurant_name or '未提供'}",
            f"城市/商圈：{review_input.location or '未提供'}",
            f"菜系/类型：{review_input.cuisine or '未提供'}",
            f"人均：{review_input.price or '未提供'}",
            f"推荐菜/亮点：{review_input.highlights or '未提供'}",
            f"消费场景：{review_input.scene}",
            f"口吻：{review_input.tone}",
            f"态度：{review_input.sentiment}",
            "",
            "请生成一段适合发布在大众点评、美团、小红书等平台的中文餐厅点评。",
        ]
    )

    messages = [
        {
            "role": "system",
            "content": (
                "你是中文餐厅点评文案助手。只输出评价正文，不要标题、序号、解释、引号或 Markdown。"
                "评价要自然、具体、像真实用户写的，不要夸张虚假，不要承诺不存在的服务。"
                "严格控制在 145 到 155 个中文字符左右。"
            ),
        },
        {"role": "user", "content": prompt},
    ]

    review = tidy_review(await call_dashscope(messages))

    for _ in range(4):
        length = len(review)
        if 145 <= length <= 155:
            return review

        if length < 135:
            guidance = f"还差约 {150 - length} 个字符，请补充菜品口感、服务细节或环境感受。"
        else:
            guidance = f"多了约 {length - 150} 个字符，请删掉重复修饰，保留核心体验。"

        review = tidy_review(
            await call_dashscope(
                [
                    *messages,
                    {"role": "assistant", "content": review},
                    {
                        "role": "user",
                        "content": (
                            f"程序实际统计这段是 {length} 个字符，目标是 145 到 155 个字符，"
                            f"字符数包含中文、数字和标点。{guidance}请改写到 150 字附近，只输出评价正文。"
                        ),
                    },
                ]
            )
        )

    return review


async def call_dashscope(messages: list[dict[str, str]]) -> str:
    payload = {
        "model": DASHSCOPE_MODEL,
        "messages": messages,
        "temperature": 0.85,
        "top_p": 0.9,
        "max_tokens": 220,
    }

    return await asyncio.to_thread(send_dashscope_request, payload)


def send_dashscope_request(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"{DASHSCOPE_BASE_URL}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        message = parse_error_message(error.read().decode("utf-8", errors="ignore"))
        raise HTTPException(status_code=502, detail=message) from error
    except URLError as error:
        raise HTTPException(status_code=502, detail=f"阿里云模型接口连接失败：{error.reason}") from error
    except TimeoutError as error:
        raise HTTPException(status_code=504, detail="阿里云模型接口响应超时。") from error

    content = data.get("choices", [{}])[0].get("message", {}).get("content")

    if not content:
        raise HTTPException(status_code=502, detail="模型没有返回有效内容。")

    return str(content)


def parse_error_message(raw_body: str) -> str:
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        return "阿里云模型接口调用失败。"

    error = data.get("error")
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])

    if data.get("message"):
        return str(data["message"])

    return "阿里云模型接口调用失败。"


def normalize_input(payload: ReviewRequest) -> ReviewInput:
    return ReviewInput(
        restaurant_name=clean(payload.restaurantName),
        location=clean(payload.location),
        cuisine=clean(payload.cuisine),
        price=clean(payload.price),
        highlights=clean(payload.highlights),
        scene=clean(payload.scene) or "朋友聚餐",
        tone=clean(payload.tone) or "真诚自然",
        sentiment=clean(payload.sentiment) or "正向好评",
    )


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:160]


def tidy_review(value: str) -> str:
    review = re.sub(r"^[\s\"'“”‘’`]+|[\s\"'“”‘’`]+$", "", str(value))
    review = re.sub(r"\n+", " ", review)
    return re.sub(r"\s+", " ", review).strip()


def cache_headers(path: Path) -> dict[str, str]:
    if path.suffix == ".html":
        return {"Cache-Control": "no-cache"}
    return {"Cache-Control": "public, max-age=3600"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "3000")),
    )

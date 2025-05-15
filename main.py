# coding=utf-8
import logging
import multiprocessing
import time
import traceback
import colorlog
import platform

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.models import CommonResponse, StatusCode
from api.routes import router

# 配置日志
logger = logging.getLogger("api")
# 清除现有的处理器，防止重复
if logger.handlers:
    logger.handlers.clear()
logger.setLevel(logging.INFO)
# 防止日志传播到根日志器
logger.propagate = False

# 配置彩色日志处理器
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(name)s - %(levelname)s%(reset)s%(message_log_color)s - %(message)s%(reset)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    },
    secondary_log_colors={
        'message': {
            'DEBUG': 'bold_white',
            'INFO': 'bold_white',
            'WARNING': 'bold_white',
            'ERROR': 'bold_white',
            'CRITICAL': 'bold_white',
        }
    },
    reset=True
))
logger.addHandler(handler)

# 添加文件处理器
file_handler = logging.FileHandler('api.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# 关闭uvicorn的访问日志
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# 创建FastAPI应用
app = FastAPI(title="行动优化算法API", description="行动优化算法API")

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有域名访问
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有请求头
)

# 条件挂载静态文件（离线资源接口文档）
if platform.system() != "Darwin":  # 非macOS系统
    from starlette.staticfiles import StaticFiles

    app.mount('/static', StaticFiles(directory='static'), name="static")


# 添加请求验证异常处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # 打印验证错误详情
    traceback.print_exc()

    # 格式化错误信息
    error_details = []
    for error in exc.errors():
        loc = " -> ".join([str(loc) for loc in error["loc"] if loc != "body"])
        error_details.append(f"{loc}: {error['msg']}")

    error_msg = "请求参数验证失败: " + "; ".join(error_details)

    # 返回与CommonResponse相同格式的错误响应
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=CommonResponse(
            code=StatusCode.INVALID_PARAMS,
            msg=error_msg
        ).dict()
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    # 记录请求开始时间
    start_time = time.time()

    # 获取请求路径和方法
    path = request.url.path
    method = request.method

    # 记录请求信息
    logger.info(f"请求开始: {method} {path}")

    # 处理请求
    response = await call_next(request)

    # 计算处理时间
    process_time = time.time() - start_time

    # 记录请求完成信息
    logger.info(f"请求完成: {method} {path} - 状态码: {response.status_code} - 耗时: {process_time:.4f}秒")

    return response


# 注册路由
app.include_router(router)

if __name__ == "__main__":
    workers_count = multiprocessing.cpu_count()  # 获取CPU核心数
    logger.info(f"Starting server with {workers_count // 4}/{workers_count} workers")
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        workers=workers_count // 4,
        log_level="info",
        access_log=False  # 完全关闭访问日志
    )

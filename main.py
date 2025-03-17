# coding=utf-8
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import traceback

from api.routes import router
from api.models import CommonResponse, StatusCode

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


# 注册路由
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

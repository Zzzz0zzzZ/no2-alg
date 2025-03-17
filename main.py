# coding=utf-8
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from basemodel import *

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


# 根路径重定向到API文档
@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


# 准备接口
@app.post("/alg/prepare", response_model=CommonResponse)
async def prepare(data: PrepareDTO):
    try:
        print(data)
        return CommonResponse(
            code=StatusCode.SUCCESS,
            msg="准备成功",
            data={"status": "ready"}
        )
    except Exception as e:
        return CommonResponse(
            code=StatusCode.SERVER_ERROR,
            msg=f"准备失败: {str(e)}"
        )


# 优化接口
@app.post("/alg/optimize", response_model=CommonResponse)
async def optimize(data: OptimizeDTO):
    try:
        # 这里添加实际的优化逻辑
        print(data)
        return CommonResponse(
            code=StatusCode.SUCCESS,
            msg="优化成功",
            data={
                "result": "optimized",
                "optimization_details": {
                    "status": "completed",
                    "score": 100
                }
            }
        )
    except Exception as e:
        return CommonResponse(
            code=StatusCode.SERVER_ERROR,
            msg=f"优化失败: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

# coding=utf-8
import traceback

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from api.models import *
from core import apicall as alg

# 创建路由器
router = APIRouter()


# 根路径重定向到API文档
@router.get("/")
async def root():
    return RedirectResponse(url="/docs")


# 准备接口
@router.post("/alg/prepare", response_model=CommonResponse)
async def prepare(data: PrepareDTO):
    try:
        print(data)
        return CommonResponse(
            code=StatusCode.SUCCESS,
            msg="准备成功",
            data={"status": "ready"}
        )
    except Exception as e:
        # 打印完整的堆栈跟踪信息
        traceback.print_exc()

        return CommonResponse(
            code=StatusCode.SERVER_ERROR,
            msg=f"准备失败: {str(e)}"
        )


# 优化接口
@router.post("/alg/optimize", response_model=CommonResponse)
async def optimize(data: OptimizeDTO):
    try:
        # 调用优化算法
        res = alg.apicall(data)

        if len(res["solutions"]) == 0:
            return CommonResponse(
                code=StatusCode.SUCCESS_NO_RESULT,
                msg="无法找到满足所有资源约束的方案，已经是较优解了",
                data=res
            )

        return CommonResponse(
            code=StatusCode.SUCCESS,
            msg="优化成功",
            data=res
        )
    except Exception as e:
        # 打印完整的堆栈跟踪信息
        traceback.print_exc()
        if isinstance(e, ValueError):
            return CommonResponse(
                code=StatusCode.INVALID_PARAMS,
                msg=f"[数据问题]{str(e)}"
            )
        return CommonResponse(
            code=StatusCode.SERVER_ERROR,
            msg=f"优化失败: {str(e)}"
        )

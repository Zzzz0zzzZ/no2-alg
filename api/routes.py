# coding=utf-8
import logging
import traceback

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from api.models import *
from core import apicall as alg

# 创建路由器
router = APIRouter()
logger = logging.getLogger("api")

# 根路径重定向到API文档
@router.get("/")
async def root():
    return RedirectResponse(url="/docs")


# 优化接口 - test_case_new_1.json格式数据
@router.post("/alg/optimize", response_model=CommonResponse)
async def optimize(data: TestCaseNewDTO):
    try:
        logger.info(f"请求入参: {data}")
        # 调用优化算法
        res = alg.apicall(data)

        if len(res["solutions"]) == 0:
            return CommonResponse(
                code=StatusCode.SUCCESS_NO_RESULT,
                msg="无法找到满足所有资源/时间约束的方案，原方案已经是较优解",
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

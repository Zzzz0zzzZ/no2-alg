# coding=utf-8
import traceback

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from api.models import *
from api.strategy_processor import generate_army_specific_strategies
from core import apicall as alg

# 创建路由器
router = APIRouter()


# 根路径重定向到API文档
@router.get("/")
async def root():
    return RedirectResponse(url="/docs")


# 优化接口 - test_case_new_1.json格式数据
@router.post("/alg/optimize", response_model=CommonResponse)
async def optimize(data: TestCaseDTO):
    try:
        # 直接调用策略处理函数处理数据对象，无需创建临时文件
        filtered_data = generate_army_specific_strategies(data)

        # 构建优化所需的OptimizeDTO
        optimize_data = OptimizeDTO(
            strategies=filtered_data['strategies'],
            actions=filtered_data['actions'],
            replacement_options=filtered_data['replacement_options'],
            constraints=Constraints(**filtered_data['constraints']),
            time_limit=filtered_data.get('time_limit'),
            solution_count=filtered_data.get('solution_count')
        )

        # 调用优化算法
        res = alg.apicall(optimize_data)

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

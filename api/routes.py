# coding=utf-8
import traceback
import tempfile
import os
import json

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from api.models import *
from core import apicall as alg
from api.strategy_processor import process_strategy_file, generate_army_specific_strategies

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


# 策略处理接口
@router.post("/strategy/process", response_model=CommonResponse)
async def strategy_process(data: StrategyProcessDTO):
    try:
        # 调用策略处理函数
        result = process_strategy_file(data.input_file_path, data.output_dir)
        
        return CommonResponse(
            code=StatusCode.SUCCESS,
            msg="策略处理成功",
            data={
                "output_file": result["output_file"],
                "stats": result["summary"]
            }
        )
    except Exception as e:
        # 打印完整的堆栈跟踪信息
        traceback.print_exc()
        
        if isinstance(e, FileNotFoundError):
            return CommonResponse(
                code=StatusCode.INVALID_PARAMS,
                msg=f"文件不存在: {str(e)}"
            )
        
        return CommonResponse(
            code=StatusCode.SERVER_ERROR,
            msg=f"策略处理失败: {str(e)}"
        )


# # 新增: 集成策略处理和优化的接口 - 直接接收test_case_3.json格式数据
# @router.post("/alg/process_and_optimize", response_model=CommonResponse)
# async def process_and_optimize(data: TestCaseDTO):
#     try:
#         # 将输入数据保存到临时文件
#         with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w', encoding='utf-8') as tmp_input:
#             json.dump(data.dict(), tmp_input, ensure_ascii=False, indent=2)
#             input_path = tmp_input.name
        
#         # 创建临时输出目录
#         output_dir = tempfile.mkdtemp()
#         output_path = os.path.join(output_dir, 'processed_test_case.json')
        
#         try:
#             # 调用策略处理函数处理数据
#             filtered_data = generate_army_specific_strategies(input_path, output_path)
            
#             # 构建优化所需的OptimizeDTO
#             optimize_data = OptimizeDTO(
#                 strategies=filtered_data['strategies'],
#                 actions=filtered_data['actions'],
#                 replacement_options=filtered_data['replacement_options'],
#                 constraints=Constraints(**filtered_data['constraints']),
#                 time_limit=filtered_data.get('time_limit'),
#                 solution_count=filtered_data.get('solution_count')
#             )
            
#             # 调用优化算法
#             res = alg.apicall(optimize_data)
            
#             if len(res["solutions"]) == 0:
#                 return CommonResponse(
#                     code=StatusCode.SUCCESS_NO_RESULT,
#                     msg="无法找到满足所有资源约束的方案，已经是较优解了",
#                     data=res
#                 )
            
#             return CommonResponse(
#                 code=StatusCode.SUCCESS,
#                 msg="处理和优化成功",
#                 data=res
#             )
#         finally:
#             # 清理临时文件
#             if os.path.exists(input_path):
#                 os.remove(input_path)
                
#             # 注意：此处不删除输出文件，可能有其他地方需要用到
    
#     except Exception as e:
#         # 打印完整的堆栈跟踪信息
#         traceback.print_exc()
#         if isinstance(e, ValueError):
#             return CommonResponse(
#                 code=StatusCode.INVALID_PARAMS,
#                 msg=f"[数据问题]{str(e)}"
#             )
#         return CommonResponse(
#             code=StatusCode.SERVER_ERROR,
#             msg=f"处理和优化失败: {str(e)}"
#         )


# 优化接口 - 使用test_case_3.json格式数据
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

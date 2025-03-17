# coding=utf-8

from enum import Enum
from typing import Optional, Any, List, Dict

from pydantic import BaseModel


class StatusCode(int, Enum):
    SUCCESS = 200  # 成功
    SUCCESS_NO_RESULT = 201  # 优化成功，找不到更优解
    INVALID_PARAMS = 400  # 参数错误
    SERVER_ERROR = 500  # 服务器错误


# 统一返回格式
class CommonResponse(BaseModel):
    code: int
    msg: str
    data: Optional[Dict[str, Any]] = None


# /alg/prepare 入参
class PrepareDTO(BaseModel):
    test_case_path: str  # 测试用例文件路径


class Strategy(BaseModel):
    replaceable: bool
    aircraft: Dict[str, List[int]]  # 键为载机类型，值为[数量, 单价]列表
    ammunition: Dict[str, List[int]]  # 键为弹药类型，值为[数量, 单价]列表


class Constraints(BaseModel):
    aircraft: Dict[str, int]  # 载机约束，键为载机类型，值为最大数量
    ammunition: Dict[str, int]  # 弹药约束，键为弹药类型，值为最大数量


# /alg/optimize 入参
class OptimizeDTO(BaseModel):
    strategies: Dict[str, Strategy]  # 键为策略ID，值为策略详情
    actions: Dict[str, List[str]]  # 键为行动ID，值为策略ID列表
    replacement_options: Dict[str, List[str]]  # 键为可替换策略ID，值为替换策略ID列表
    constraints: Constraints  # 资源约束条件
    solution_count: Optional[int]  # 返回几种优化方案
    time_limit: Optional[int]  # 算法执行时间限制

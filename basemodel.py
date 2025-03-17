# coding=utf-8

from enum import Enum
from plistlib import Dict
from typing import Optional, Any, List

from pydantic import BaseModel


class StatusCode(int, Enum):
    SUCCESS = 200  # 成功
    PARAM_ERROR = 400  # 参数错误
    SERVER_ERROR = 500  # 服务器错误


# 统一返回格式
class CommonResponse(BaseModel):
    code: int
    msg: str
    data: Optional[Dict[str, Any]] = None


# 请求体模型
class PrepareDTO(BaseModel):
    test_case_path: str  # 测试用例文件路径


class Strategy(BaseModel):
    replaceable: bool
    aircraft: Dict[str, List[int]]  # 键为载机类型，值为[数量, 单价]列表
    ammunition: Dict[str, List[int]]  # 键为弹药类型，值为[数量, 单价]列表


class Constraints(BaseModel):
    aircraft: Dict[str, int]  # 载机约束，键为载机类型，值为最大数量
    ammunition: Dict[str, int]  # 弹药约束，键为弹药类型，值为最大数量


class OptimizeDTO(BaseModel):
    strategies: Dict[str, Strategy]  # 键为策略ID，值为策略详情
    actions: Dict[str, List[str]]  # 键为行动ID，值为策略ID列表
    replacement_options: Dict[str, List[str]]  # 键为可替换策略ID，值为替换策略ID列表
    constraints: Constraints  # 资源约束条件

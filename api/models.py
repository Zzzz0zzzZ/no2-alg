# coding=utf-8

from enum import Enum, IntEnum
from typing import Optional, Any, List, Dict
from pydantic import BaseModel, validator

from pydantic import BaseModel


class StatusCode(int, Enum):
    SUCCESS = 200  # 成功
    SUCCESS_NO_RESULT = 201  # 优化成功，找不到更优解
    INVALID_PARAMS = 400  # 参数错误
    SERVER_ERROR = 500  # 服务器错误


# 优化类型枚举
class OptimizationType(IntEnum):
    PRICE = 0  # 效费比优化，价格最低
    AIRCRAFT_LOSS = 1  # 效损比优化，飞机损失最少
    AIRCRAFT_USAGE = 2  # 出动兵力最少（总出动飞机数量最少）


# 统一返回格式
class CommonResponse(BaseModel):
    code: int
    msg: str
    data: Optional[Dict[str, Any]] = None


# 策略定义
class Strategy(BaseModel):
    replaceable: bool
    aircraft: Dict[str, List[int]]  # 键为载机类型，值为[数量, 单价]列表
    ammunition: Dict[str, List[int]]  # 键为弹药类型，值为[数量, 单价]列表
    army_init: Optional[str] = None  # 策略初始军队 - 「只有原始草案中的策略携带该参数」
    time_range: Optional[List[int]] = None  # 策略的时间范围 [开始时间, 结束时间] - 「只有原始草案中的策略携带该参数」
    penetration_rate: Optional[float] = 0.8  # 突防率，0.0~1.0之间，默认0.8
    
    @validator('penetration_rate')
    def validate_penetration_rate(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('突防率必须在0到1之间')
        return v


# 军队资源定义
class ArmyResource(BaseModel):
    aircraft: Dict[str, Dict[str, Any]]  # 键为飞机类型，值为详情
    ammunition: Dict[str, Dict[str, Any]]  # 键为弹药类型，值为详情


# 约束定义
class Constraints(BaseModel):
    aircraft: Dict[str, int]  # 载机约束，键为载机类型，值为最大数量
    ammunition: Dict[str, int]  # 弹药约束，键为弹药类型，值为最大数量


# /alg/optimize 入参
class TestCaseDTO(BaseModel):
    strategies: Dict[str, Strategy]  # 键为策略ID，值为策略详情
    actions: Dict[str, List[str]]  # 键为行动ID，值为策略ID列表
    replacement_options: Dict[str, List[str]]  # 键为可替换策略ID，值为替换策略ID列表
    armies: Dict[str, ArmyResource]  # 键为军队ID，值为军队资源
    stage: Optional[List[str]] = []  # 需要优化的阶段(传空列表，代表优化全部，否则只优化列表中的阶段)
    time_limit: Optional[int] = None  # 算法执行时间限制
    solution_count: Optional[int] = None  # 返回几种优化方案
    opt_type: Optional[OptimizationType] = OptimizationType.PRICE  # 优化类型，默认为价格优化


# 算法入参
class OptimizeDTO(BaseModel):
    strategies: Dict[str, Strategy]  # 键为策略ID，值为策略详情
    actions: Dict[str, List[str]]  # 键为行动ID，值为策略ID列表
    replacement_options: Dict[str, List[str]]  # 键为可替换策略ID，值为替换策略ID列表
    constraints: Constraints  # 资源约束条件
    solution_count: Optional[int]  # 返回几种优化方案
    time_limit: Optional[int]  # 算法执行时间限制
    opt_type: Optional[OptimizationType] = OptimizationType.PRICE  # 优化类型，默认为价格优化

# coding=utf-8
from typing import Dict, List, Tuple
from api.models import OptimizeDTO
from core.genetic_strategy_optimization import Strategy, Action, ActionList, run_optimize


def apicall(data: OptimizeDTO) -> Tuple[Dict, float]:
    """
    API调用入口，处理OptimizeDTO输入并调用优化算法
    
    Args:
        data: OptimizeDTO对象，包含策略、行动和约束条件信息
        
    Returns:
        Tuple[Dict, float]: 最优替换方案和对应的总价格
        
    Raises:
        ValueError: 当输入数据无效或不完整时抛出
    """
    # 检查输入数据的有效性
    if not data.strategies:
        raise ValueError("策略列表不能为空")
    if not data.actions:
        raise ValueError("行动列表不能为空")
    if not data.constraints.aircraft and not data.constraints.ammunition:
        raise ValueError("至少需要一个资源约束条件")

    # 检查策略引用的有效性
    all_strategy_ids = set(data.strategies.keys())
    for action_id, strategy_ids in data.actions.items():
        if not strategy_ids:
            raise ValueError(f"行动 {action_id} 没有关联任何策略")
        invalid_strategies = set(strategy_ids) - all_strategy_ids
        if invalid_strategies:
            raise ValueError(f"行动 {action_id} 引用了不存在的策略: {invalid_strategies}")
    
    # 检查替换选项的有效性
    for strategy_id, replacement_ids in data.replacement_options.items():
        if strategy_id not in all_strategy_ids:
            raise ValueError(f"替换选项引用了不存在的策略: {strategy_id}")
        invalid_replacements = set(replacement_ids) - all_strategy_ids
        if invalid_replacements:
            raise ValueError(f"策略 {strategy_id} 的替换选项包含不存在的策略: {invalid_replacements}")
    
    # 创建策略字典，将DTO中的策略数据转换为Strategy对象
    strategy_objects = {}
    for strategy_id, strategy_data in data.strategies.items():
        strategy_objects[strategy_id] = Strategy(
            id=strategy_id,
            replaceable=strategy_data.replaceable,
            aircraft={
                aircraft_type: (count_price[0], count_price[1])
                for aircraft_type, count_price in strategy_data.aircraft.items()
            },
            ammunition={
                ammo_type: (count_price[0], count_price[1])
                for ammo_type, count_price in strategy_data.ammunition.items()
            }
        )
    
    # 创建ActionList对象
    action_list = ActionList()
    
    # 添加Action和对应的Strategy
    for action_id, strategy_ids in data.actions.items():
        action = Action(id=action_id)
        for strategy_id in strategy_ids:
            action.add_strategy(strategy_objects[strategy_id])
        action_list.add_action(action)
    
    # 添加替换选项
    for strategy_id, replacement_ids in data.replacement_options.items():
        replacement_strategies = [strategy_objects[rid] for rid in replacement_ids]
        action_list.add_replacement_option(strategy_id, replacement_strategies)
    
    # 调用优化算法
    best_combinations, total_prices = run_optimize(
        action_list,
        data.constraints.aircraft,
        data.constraints.ammunition,
        plot_convergence=False,     # API调用不需要绘图
        solution_count=data.solution_count if data.solution_count is not None else 1,  # 默认最优的1种
        time_limit=data.time_limit if data.time_limit is not None else None    # 默认无执行时间限制
    )
    
    return best_combinations, total_prices


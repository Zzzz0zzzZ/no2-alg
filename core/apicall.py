# coding=utf-8
from typing import Dict, List, Tuple
import time
from api.models import OptimizeDTO
from core.genetic_strategy_optimization import Strategy, Action, ActionList, run_optimize


def apicall(data: OptimizeDTO) -> Dict:
    """
    API调用入口，处理OptimizeDTO输入并调用优化算法
    
    Args:
        data: OptimizeDTO对象，包含任务、阶段和约束条件信息
        
    Returns:
        Dict: 包含算法耗时、方案数量、最优价格和具体方案详情的字典
        
    Raises:
        ValueError: 当输入数据无效或不完整时抛出
    """
    # 检查输入数据的有效性
    if not data.strategies:
        raise ValueError("任务列表不能为空")
    if not data.actions:
        raise ValueError("阶段列表不能为空")
    if not data.constraints.aircraft and not data.constraints.ammunition:
        raise ValueError("至少需要一个资源约束条件")
    if data.time_limit is not None and data.time_limit == 0:
        data.time_limit = None
    if data.solution_count is not None and data.solution_count <= 0:
        data.solution_count = 1
    # 检查任务引用的有效性
    all_strategy_ids = set(data.strategies.keys())
    for action_id, strategy_ids in data.actions.items():
        if not strategy_ids:
            raise ValueError(f"阶段 {action_id} 没有关联任何任务")
        invalid_strategies = set(strategy_ids) - all_strategy_ids
        if invalid_strategies:
            raise ValueError(f"阶段 {action_id} 引用了不存在的任务: {invalid_strategies}")
    
    # 检查替换选项的有效性
    for strategy_id, replacement_ids in data.replacement_options.items():
        if strategy_id not in all_strategy_ids:
            raise ValueError(f"替换选项引用了不存在的任务: {strategy_id}")
        invalid_replacements = set(replacement_ids) - all_strategy_ids
        if invalid_replacements:
            raise ValueError(f"任务 {strategy_id} 的替换选项包含不存在的任务: {invalid_replacements}")
    
    # 创建任务字典，将DTO中的任务数据转换为Strategy对象
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
    
    # 记录开始时间
    start_time = time.time()
    
    # 调用优化算法
    best_combinations, total_prices = run_optimize(
        action_list,
        data.constraints.aircraft,
        data.constraints.ammunition,
        plot_convergence=False,     # API调用不需要绘图
        solution_count=data.solution_count if data.solution_count is not None else 1,  # 默认最优的1种
        time_limit=data.time_limit if data.time_limit is not None else None    # 默认无执行时间限制
    )
    
    # 计算算法耗时
    elapsed_time = round(time.time() - start_time, 2)

    # 计算原始方案的总价格
    original_price = 0
    for action in action_list.actions:
        for strategy in action.strategies:
            original_price += strategy.price

    # 如果没有找到可行解
    if not best_combinations or not total_prices:
        return {
            "elapsed_time": elapsed_time,
            "solution_count": 0,
            "original_price": original_price,
            "saved_amount": 0,
            "best_price": original_price,  # 第一个方案的价格就是最优价格
            "solutions": []
        }

    # 组装返回结果
    solutions = []
    for idx, (combination, price) in enumerate(zip(best_combinations, total_prices)):
        solution = {
            "sort": idx + 1,  # 排序号，从1开始
            "total_price": price,
            "saved_amount": original_price - price if price < original_price else 0,
            "increased_amount": price - original_price if price > original_price else 0,
            "strategy_details": [],
            "resource_usage": {
                "aircraft": [],
                "ammunition": []
            }
        }
        
        # 计算资源使用情况
        # 初始化资源使用情况结构
        for aircraft_type, total in data.constraints.aircraft.items():
            solution["resource_usage"]["aircraft"].append({
                "id": aircraft_type,
                "total": total,
                "used": 0,
                "remaining": total
            })
        
        for ammo_type, total in data.constraints.ammunition.items():
            solution["resource_usage"]["ammunition"].append({
                "id": ammo_type,
                "total": total,
                "used": 0,
                "remaining": total
            })
        
        # 累计各类资源的使用情况
        for action in action_list.actions:
            for strategy in action.strategies:
                # 如果任务可替换且在替换方案中，使用替换后的任务
                if strategy.replaceable and strategy.id in combination:
                    strategy = combination[strategy.id]
                
                # 获取任务的资源使用情况
                aircraft_usage, ammunition_usage = strategy.get_resource_usage()
                
                # 累计载机使用情况
                for aircraft_type, count in aircraft_usage.items():
                    for aircraft in solution["resource_usage"]["aircraft"]:
                        if aircraft["id"] == aircraft_type:
                            aircraft["used"] += count
                            aircraft["remaining"] = aircraft["total"] - aircraft["used"]
                            break
                
                # 累计弹药使用情况
                for ammo_type, count in ammunition_usage.items():
                    for ammo in solution["resource_usage"]["ammunition"]:
                        if ammo["id"] == ammo_type:
                            ammo["used"] += count
                            ammo["remaining"] = ammo["total"] - ammo["used"]
                            break
        
        # 添加任务替换详情
        for action in action_list.actions:
            for strategy in action.strategies:
                if strategy.replaceable and strategy.id in combination:
                    replacement = combination[strategy.id]
                    detail = {
                        "from_strategy": strategy.id,
                        "to_strategy": replacement.id,
                        "desc": f"在阶段{action.id}中，将任务{strategy.id}替换为任务{replacement.id}，"
                               f"{'节省' if replacement.price < strategy.price else '增加'}"
                               f"{abs(strategy.price - replacement.price)}元"
                    }
                    solution["strategy_details"].append(detail)
        
        solutions.append(solution)
    
    return {
        "elapsed_time": elapsed_time,
        "solution_count": len(solutions),
        "original_price": original_price,
        "saved_amount": original_price - total_prices[0],
        "best_price": total_prices[0],  # 第一个方案的价格就是最优价格
        "solutions": solutions
    }


# coding=utf-8
import time
from enum import IntEnum
from typing import Dict

from api.models import OptimizeDTO, Constraints, OptimizationType, TestCaseNewDTO
from core.converter import convert_to_old_format
from core.preprocessor import generate_army_specific_strategies
from core.genetic_strategy_optimization import Strategy, Action, ActionList, run_optimize
from core.simulate import initialize_cache

ALG_SEPARATOR = '~~~###~~~'


# 定义替换类型枚举
class ReplacementType(IntEnum):
    ORIGINAL = 0  # 原方案
    OPTIMIZED = 1  # 已优化


def apicall(data: TestCaseNewDTO) -> Dict:
    """
    API调用入口，处理TestCaseNewDTO输入，转换为原来的TestCaseDTO，根据策略库扩充分队级策略，并调用优化算法
    
    Args:
        data: OptimizeDTO对象，包含任务、阶段和约束条件信息
        
    Returns:
        Dict: 包含算法耗时、方案数量、最优价格和具体方案详情的字典
        
    Raises:
        ValueError: 当输入数据无效或不完整时抛出
    """
    # 每次API请求时强制重新初始化战斗参数缓存
    initialize_cache(force_reload=True)

    # 转为旧TestCaseDTO格式以适配算法入参
    data = convert_to_old_format(data)

    # 校验原始草案中的行动，必须有time_range字段
    for action_id, strategy_ids in data.actions.items():
        for strategy_id in strategy_ids:
            if strategy_id in data.strategies and data.strategies[strategy_id].time_range is None:
                raise ValueError(f"策略 {strategy_id} 缺少 time_range 字段")
            time_range = data.strategies[strategy_id].time_range
            if len(time_range) != 2 or time_range[0] >= time_range[1]:
                raise ValueError(f"策略 {strategy_id} 的 time_range 字段格式不正确：{time_range}")

    # 处理需要优化的阶段信息
    stages_to_optimize = data.stage if hasattr(data, 'stage') and data.stage else []

    # 如果指定了需要优化的阶段，则将不在列表中的阶段的策略设置为不可替换
    if stages_to_optimize and hasattr(data, 'actions') and data.actions:
        for action_id, strategy_ids in data.actions.items():
            # 如果当前阶段不在需要优化的阶段列表中
            if action_id not in stages_to_optimize:
                # 将该阶段中的所有策略设置为不可替换
                for strategy_id in strategy_ids:
                    if strategy_id in data.strategies:
                        data.strategies[strategy_id].replaceable = False

    # 获取优化类型
    opt_type = data.opt_type if hasattr(data, 'opt_type') else OptimizationType.PRICE

    # 根据策略库信息，扩充分队级策略
    filtered_data = generate_army_specific_strategies(data)

    # 构建优化所需的OptimizeDTO
    data = OptimizeDTO(
        strategies=filtered_data['strategies'],
        actions=filtered_data['actions'],
        replacement_options=filtered_data['replacement_options'],
        constraints=Constraints(**filtered_data['constraints']),
        time_limit=filtered_data.get('time_limit'),
        solution_count=filtered_data.get('solution_count'),
        opt_type=filtered_data.get('opt_type', OptimizationType.PRICE)  # 添加优化类型参数
    )

    # 检查输入数据的有效性
    if not data.strategies:
        raise ValueError("任务列表strategies不能为空")
    if not data.actions:
        raise ValueError("阶段列表actions不能为空")
    if not data.constraints.aircraft and not data.constraints.ammunition:
        raise ValueError("至少需要一个资源约束条件(constraints.aircraft/constraints.ammunition)")
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
        # 在创建 Strategy 对象时添加 penetration_rate 和 enemies 字段
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
            },
            time_range=strategy_data.time_range if hasattr(strategy_data, 'time_range') else None,
            penetration_rate=strategy_data.penetration_rate if hasattr(strategy_data, 'penetration_rate') else 1.0,
            enemies=strategy_data.enemies if hasattr(strategy_data, 'enemies') else None
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
    best_combinations, total_prices, total_losses, total_bingli = run_optimize(
        action_list,
        data.constraints.aircraft,
        data.constraints.ammunition,
        plot_convergence=False,  # API调用不需要绘图
        solution_count=data.solution_count if data.solution_count is not None else 1,  # 默认最优的1种
        time_limit=data.time_limit if data.time_limit is not None else None,  # 默认无执行时间限制
        opt_type=data.opt_type if hasattr(data, 'opt_type') else OptimizationType.PRICE  # 添加优化类型参数
    )

    # 计算算法耗时
    elapsed_time = round(time.time() - start_time, 2)

    # 计算原始方案的总价格和飞机损失
    original_price = 0
    original_loss = 0
    original_bingli = 0  # 原始兵力统计
    for action in action_list.actions:
        for strategy in action.strategies:
            original_price += strategy.price
            _, loss_count = strategy.get_aircraft_loss()
            original_loss += loss_count
            # 计算原始兵力
            aircraft_usage, _ = strategy.get_resource_usage()
            for _, count in aircraft_usage.items():
                original_bingli += count

    # 如果没有找到可行解
    if not best_combinations or not total_prices:
        return {
            "elapsed_time": elapsed_time,
            "solution_count": 0,
            "original_price": original_price,
            "saved_amount": 0,
            "best_price": original_price,  # 第一个方案的价格就是最优价格
            "original_loss": original_loss,  # 原始飞机损失
            "saved_loss": 0,  # 节省的飞机损失
            "best_loss": original_loss,  # 最优方案的飞机损失
            "is_saving_loss": False,  # 是否节省飞机损失
            "original_bingli": original_bingli,  # 原始兵力
            "saved_bingli": 0,  # 节省的兵力
            "best_bingli": original_bingli,  # 最优方案的兵力
            "is_saving_bingli": False,  # 是否节省兵力
            "opt_type": opt_type,  # 优化类型
            "solutions": []
        }

    # 组装返回结果
    solutions = []
    for idx, (combination, price, loss, bingli) in enumerate(
            zip(best_combinations, total_prices, total_losses, total_bingli)):
        solution = {
            "sort": idx + 1,  # 排序号，从1开始
            "total_price": price,
            "price_difference": abs(original_price - price),
            "is_saving": price < original_price,
            "total_loss": loss,  # 总飞机损失
            "loss_difference": abs(original_loss - loss),  # 飞机损失差异
            "is_saving_loss": loss < original_loss,  # 是否节省飞机损失
            "total_bingli": bingli,  # 总兵力
            "bingli_difference": abs(original_bingli - bingli),  # 兵力差异
            "is_saving_bingli": bingli < original_bingli,  # 是否节省兵力
            "strategy_details": [],
            "resource_usage": []  # 直接按军队分类的资源使用情况
        }

        # 计算资源使用情况
        # 按军队分类初始化资源使用情况结构
        solution["resource_usage"] = []

        # 提取所有军队ID
        army_ids = set()
        for resource_id in data.constraints.aircraft.keys():
            if ALG_SEPARATOR in resource_id:
                army_ids.add(resource_id.split(ALG_SEPARATOR)[1])
        for resource_id in data.constraints.ammunition.keys():
            if ALG_SEPARATOR in resource_id:
                army_ids.add(resource_id.split(ALG_SEPARATOR)[1])

        # 初始化每个军队的资源使用情况
        for army_id in army_ids:
            army_resource = {
                "army_id": int(army_id),
                "aircraft": [],
                "ammunition": []
            }

            # 初始化该军队的飞机资源
            for aircraft_type, total in data.constraints.aircraft.items():
                if ALG_SEPARATOR in aircraft_type and aircraft_type.split(ALG_SEPARATOR)[1] == army_id:
                    resource_id = aircraft_type.split(ALG_SEPARATOR)[0]  # 提取资源基本ID
                    army_resource["aircraft"].append({
                        "aircraft_type": int(resource_id),
                        "total": total,
                        "used": 0,  # 出动的数量
                        "loss": 0,  # 损毁的数量
                        "remaining": total  # 剩余的数量（总的-损毁的）
                    })

            # 初始化该军队的弹药资源
            for ammo_type, total in data.constraints.ammunition.items():
                if ALG_SEPARATOR in ammo_type and ammo_type.split(ALG_SEPARATOR)[1] == army_id:
                    resource_id = ammo_type.split(ALG_SEPARATOR)[0]  # 提取资源基本ID
                    army_resource["ammunition"].append({
                        "ammunition_type": int(resource_id),
                        "total": total,
                        "used": 0,
                        "remaining": total
                    })

            solution["resource_usage"].append(army_resource)

        # 累计各类资源的使用情况
        for action in action_list.actions:
            for strategy in action.strategies:
                # 如果任务可替换且在替换方案中，使用替换后的任务
                if strategy.replaceable and strategy.id in combination:
                    strategy = combination[strategy.id]

                # 获取任务的资源使用情况
                aircraft_usage, ammunition_usage = strategy.get_resource_usage()

                # 获取任务的飞机损耗情况
                aircraft_loss, _ = strategy.get_aircraft_loss()

                # 累计飞机使用情况
                for aircraft_type, count in aircraft_usage.items():
                    if ALG_SEPARATOR in aircraft_type:
                        resource_parts = aircraft_type.split(ALG_SEPARATOR)
                        resource_id = resource_parts[0]
                        resource_army_id = resource_parts[1]

                        # 查找对应的军队资源
                        for army_resource in solution["resource_usage"]:
                            if army_resource["army_id"] == int(resource_army_id):
                                # 查找对应的飞机类型
                                for aircraft in army_resource["aircraft"]:
                                    if aircraft["aircraft_type"] == int(resource_id):
                                        # 更新出动数量
                                        aircraft["used"] += count

                                        # 计算并更新损毁数量
                                        loss_count = aircraft_loss.get(aircraft_type, 0)
                                        aircraft["loss"] += loss_count

                                        # 更新剩余数量（总的-损毁的）
                                        aircraft["remaining"] = aircraft["total"] - aircraft["loss"]
                                        break

                # 累计弹药使用情况
                for ammo_type, count in ammunition_usage.items():
                    if ALG_SEPARATOR in ammo_type:
                        resource_parts = ammo_type.split(ALG_SEPARATOR)
                        resource_id = resource_parts[0]
                        resource_army_id = resource_parts[1]

                        # 查找对应的军队资源
                        for army_resource in solution["resource_usage"]:
                            if army_resource["army_id"] == int(resource_army_id):
                                # 查找对应的弹药类型
                                for ammo in army_resource["ammunition"]:
                                    if ammo["ammunition_type"] == int(resource_id):
                                        ammo["used"] += count
                                        ammo["remaining"] = ammo["total"] - ammo["used"]
                                        break

        # 添加任务替换详情
        for action in action_list.actions:
            for strategy in action.strategies:
                if strategy.replaceable and strategy.id in combination:
                    replacement = combination[strategy.id]

                    # 计算原策略的飞机损耗
                    raw_from_aircraft_loss, from_total_loss = strategy.get_aircraft_loss()
                    # 处理原策略的飞机损耗信息，移除分隔符和军队信息
                    from_aircraft_loss = []
                    for aircraft_type, loss_count in raw_from_aircraft_loss.items():
                        resource_id = aircraft_type.split(ALG_SEPARATOR)[
                            0] if ALG_SEPARATOR in aircraft_type else aircraft_type
                        from_aircraft_loss.append({
                            "aircraft_type": int(resource_id),
                            "count": loss_count
                        })

                    # 计算替换策略的飞机损耗
                    raw_to_aircraft_loss, to_total_loss = replacement.get_aircraft_loss()
                    # 处理替换策略的飞机损耗信息，移除分隔符和军队信息
                    to_aircraft_loss = []
                    for aircraft_type, loss_count in raw_to_aircraft_loss.items():
                        resource_id = aircraft_type.split(ALG_SEPARATOR)[
                            0] if ALG_SEPARATOR in aircraft_type else aircraft_type
                        to_aircraft_loss.append({
                            "aircraft_type": int(resource_id),
                            "count": loss_count
                        })

                    # 分割策略ID和军队ID
                    from_parts = strategy.id.split(ALG_SEPARATOR) if ALG_SEPARATOR in strategy.id else [strategy.id,
                                                                                                        "未知军队"]
                    to_parts = replacement.id.split(ALG_SEPARATOR) if ALG_SEPARATOR in replacement.id else [
                        replacement.id, "未知军队"]

                    # 提取策略ID和军队ID
                    from_strategy_id = from_parts[0]
                    from_army_id = from_parts[1] if len(from_parts) > 1 else "未知军队"
                    to_strategy_id = to_parts[0]
                    to_army_id = to_parts[1] if len(to_parts) > 1 else "未知军队"

                    # 处理原策略的资源信息，移除分隔符和军队信息
                    from_aircraft = []
                    from_ammunition = []
                    for aircraft_type, value in strategy.aircraft.items():
                        resource_id = aircraft_type.split(ALG_SEPARATOR)[
                            0] if ALG_SEPARATOR in aircraft_type else aircraft_type
                        from_aircraft.append({
                            "aircraft_type": int(resource_id),
                            "count": value[0],
                            "price": value[1]
                        })

                    for ammo_type, value in strategy.ammunition.items():
                        resource_id = ammo_type.split(ALG_SEPARATOR)[0] if ALG_SEPARATOR in ammo_type else ammo_type
                        from_ammunition.append({
                            "ammunition_type": int(resource_id),
                            "count": value[0],
                            "price": value[1]
                        })

                    # 处理替换策略的资源信息，移除分隔符和军队信息
                    to_aircraft = []
                    to_ammunition = []
                    for aircraft_type, value in replacement.aircraft.items():
                        resource_id = aircraft_type.split(ALG_SEPARATOR)[
                            0] if ALG_SEPARATOR in aircraft_type else aircraft_type
                        to_aircraft.append({
                            "aircraft_type": int(resource_id),
                            "count": value[0],
                            "price": value[1]
                        })

                    for ammo_type, value in replacement.ammunition.items():
                        resource_id = ammo_type.split(ALG_SEPARATOR)[0] if ALG_SEPARATOR in ammo_type else ammo_type
                        to_ammunition.append({
                            "aircraft_type": int(resource_id),
                            "count": value[0],
                            "price": value[1]
                        })

                    # 计算原策略和替换策略的兵力（出动飞机数量）
                    from_bingli = 0
                    to_bingli = 0

                    # 计算原策略的兵力
                    from_aircraft_usage, _ = strategy.get_resource_usage()
                    for _, count in from_aircraft_usage.items():
                        from_bingli += count

                    # 计算替换策略的兵力
                    to_aircraft_usage, _ = replacement.get_resource_usage()
                    for _, count in to_aircraft_usage.items():
                        to_bingli += count

                    # 计算兵力差异
                    bingli_diff = abs(from_bingli - to_bingli)

                    # 计算价格差异和飞机损失差异
                    price_diff = abs(strategy.price - replacement.price)
                    loss_diff = abs(from_total_loss - to_total_loss)

                    # 根据优化类型和差异生成描述文本
                    if opt_type == OptimizationType.AIRCRAFT_LOSS:
                        if loss_diff == 0:
                            desc_text = f"在阶段[{action.id}]中，用分队[{from_army_id}]执行任务[{from_strategy_id}]替换为用分队[{to_army_id}]执行任务[{to_strategy_id}]也可以完成任务，飞机损失不变"
                        else:
                            desc_text = f"在阶段[{action.id}]中，用分队[{from_army_id}]执行任务[{from_strategy_id}]替换为用分队[{to_army_id}]执行任务[{to_strategy_id}]，" \
                                        f"{'减少' if to_total_loss < from_total_loss else '增加'}" \
                                        f"{loss_diff}架飞机损失"
                    elif opt_type == OptimizationType.AIRCRAFT_USAGE:
                        if bingli_diff == 0:
                            desc_text = f"在阶段[{action.id}]中，用分队[{from_army_id}]执行任务[{from_strategy_id}]替换为用分队[{to_army_id}]执行任务[{to_strategy_id}]也可以完成任务，兵力派遣不变"
                        else:
                            desc_text = f"在阶段[{action.id}]中，用分队[{from_army_id}]执行任务[{from_strategy_id}]替换为用分队[{to_army_id}]执行任务[{to_strategy_id}]，" \
                                        f"{'减少' if to_bingli < from_bingli else '增加'}" \
                                        f"{bingli_diff}兵力派遣"
                    else:
                        if price_diff == 0:
                            desc_text = f"在阶段[{action.id}]中，用分队[{from_army_id}]执行任务[{from_strategy_id}]替换为用分队[{to_army_id}]执行任务[{to_strategy_id}]也可以完成任务，价格不变"
                        else:
                            desc_text = f"在阶段[{action.id}]中，用分队[{from_army_id}]执行任务[{from_strategy_id}]替换为用分队[{to_army_id}]执行任务[{to_strategy_id}]，" \
                                        f"{'节省' if replacement.price < strategy.price else '增加'}" \
                                        f"{price_diff}元"

                    detail = {
                        "from_strategy_id": int(from_strategy_id),  # 分割后的策略ID
                        "from_army_id": int(from_army_id),  # 分割后的军队ID
                        "to_strategy_id": int(to_strategy_id),  # 分割后的策略ID
                        "to_army_id": int(to_army_id),  # 分割后的军队ID
                        "from_strategy_details": {  # 添加原策略的详细信息（移除分隔符和军队信息）
                            "aircraft": from_aircraft,
                            "ammunition": from_ammunition,
                            "price": strategy.price,
                            "time_range": {
                                "start": strategy.time_range[0],
                                "end": strategy.time_range[1]
                            },
                            "aircraft_loss": from_aircraft_loss,  # 添加飞机损耗信息
                            "total_aircraft_loss": from_total_loss,  # 添加总飞机损耗
                            "penetration_rate": strategy.penetration_rate,  # 突防率(回传)
                            "total_bingli": from_bingli  # 原策略的总兵力
                        },
                        "to_strategy_details": {  # 添加替换策略的详细信息（移除分隔符和军队信息）
                            "aircraft": to_aircraft,
                            "ammunition": to_ammunition,
                            "price": replacement.price,
                            "time_range": {
                                "start": strategy.time_range[0],
                                "end": strategy.time_range[1]
                            },
                            "aircraft_loss": to_aircraft_loss,  # 添加飞机损耗信息
                            "total_aircraft_loss": to_total_loss,  # 添加总飞机损耗
                            "penetration_rate": strategy.penetration_rate,  # 突防率(回传)
                            "total_bingli": to_bingli  # 替换策略的总兵力
                        },
                        "price_difference": price_diff,
                        "is_saving": replacement.price < strategy.price,
                        "loss_difference": loss_diff,  # 飞机损失差异
                        "is_saving_loss": to_total_loss < from_total_loss,  # 是否节省飞机损失
                        "bingli_difference": bingli_diff,  # 兵力差异
                        "is_saving_bingli": to_bingli < from_bingli,  # 是否节省兵力
                        "desc": desc_text
                    }
                    solution["strategy_details"].append(detail)

        # 添加替换类型和替换说明
        if not solution["strategy_details"]:
            # 原方案
            solution["replacement_type"] = ReplacementType.ORIGINAL
            solution["replacement_desc"] = "原方案"
        else:
            # 优化后方案
            solution["replacement_type"] = ReplacementType.OPTIMIZED
            solution["replacement_desc"] = "已优化方案"

        solutions.append(solution)

    return {
        "elapsed_time": elapsed_time,
        "solution_count": len(solutions),
        "original_price": original_price,
        "price_difference": abs(original_price - total_prices[0]),
        "is_saving": total_prices[0] < original_price,
        "best_price": total_prices[0],  # 第一个方案的价格就是最优价格
        "original_loss": original_loss,  # 原始飞机损失
        "loss_difference": abs(original_loss - total_losses[0]),  # 节省的飞机损失
        "best_loss": total_losses[0],  # 最优方案的飞机损失
        "is_saving_loss": total_losses[0] < original_loss,  # 是否节省飞机损失
        "original_bingli": original_bingli,  # 原始兵力
        "bingli_difference": abs(original_bingli - total_bingli[0]),  # 节省的兵力
        "best_bingli": total_bingli[0],  # 最优方案的兵力
        "is_saving_bingli": total_bingli[0] < original_bingli,  # 是否节省兵力
        "opt_type": opt_type,  # 优化类型
        "solutions": solutions
    }

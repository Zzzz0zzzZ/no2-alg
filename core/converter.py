# coding=utf-8
import logging

from api.models import TestCaseDTO, Strategy, ArmyResource, TestCaseNewDTO

logger = logging.getLogger("api")

def convert_to_old_format(new_dto: TestCaseNewDTO) -> TestCaseDTO:
    """
    将新的 API 入参形式转换为原来的形式
    
    Args:
        new_dto: 新的 API 入参对象
        
    Returns:
        TestCaseDTO: 转换后的原格式对象
    """

    # 转换 strategies
    strategies = {}
    for strategy in new_dto.strategies:
        # 转换 aircraft
        aircraft = {}
        for ac in strategy.aircraft:
            aircraft[str(ac.aircraft_type)] = [ac.count, ac.price]  # 将int转为str
        
        # 转换 ammunition
        ammunition = {}
        for ammo in strategy.ammunition:
            ammunition[str(ammo.ammunition_type)] = [ammo.count, ammo.price]  # 将int转为str
        
        # 转换 time_range
        time_range = None
        if strategy.time_range:
            if strategy.time_range.start is not None and strategy.time_range.end is not None:
                time_range = [strategy.time_range.start, strategy.time_range.end]
        
        # 将int类型的strategy_id转为str作为key
        strategies[str(strategy.strategy_id)] = Strategy(
            replaceable=strategy.replaceable,
            aircraft=aircraft,
            ammunition=ammunition,
            army_init=str(strategy.army_init) if strategy.army_init is not None else None,  # 将int转为str
            time_range=time_range,
            penetration_rate=strategy.penetration_rate
        )
    
    # 转换 actions
    actions = {}
    for action in new_dto.actions:
        # 将int类型的action_id转为str作为key，并将strategies列表中的int转为str
        actions[str(action.action_id)] = [str(s) for s in action.strategies]
    
    # 转换 replacement_options
    replacement_options = {}
    for option in new_dto.replacement_options:
        # 将int类型的original_strategy转为str作为key，并将replacement_strategies列表中的int转为str
        replacement_options[str(option.original_strategy)] = [str(s) for s in option.replacement_strategies]
    
    # 转换 armies
    armies = {}
    for army in new_dto.armies:
        # 转换 aircraft
        aircraft = {}
        for ac in army.aircraft:
            aircraft[str(ac.aircraft_type)] = {"数量": ac.count}  # 将int转为str
        
        # 转换 ammunition
        ammunition = {}
        for ammo in army.ammunition:
            ammunition[str(ammo.ammunition_type)] = {"数量": ammo.count}  # 将int转为str
        
        # 将int类型的army_id转为str作为key
        armies[str(army.army_id)] = ArmyResource(
            aircraft=aircraft,
            ammunition=ammunition
        )

    # 将stage列表中的int转为str
    stage = [str(s) for s in new_dto.stage] if new_dto.stage else []

    res = TestCaseDTO(
        strategies=strategies,
        actions=actions,
        replacement_options=replacement_options,
        armies=armies,
        stage=stage,
        time_limit=new_dto.time_limit,
        solution_count=new_dto.solution_count,
        opt_type=new_dto.opt_type
    )

    logger.info(f"转换入参: {res}")

    # 创建并返回 TestCaseDTO 对象
    return res
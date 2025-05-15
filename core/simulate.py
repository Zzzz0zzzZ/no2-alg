# coding=utf-8
"""
模拟空中和地面作战的函数库
用于计算飞机的战损情况
"""

import math
import logging
import pymysql
from typing import Dict, List, Any, Tuple
from config import MYSQL_CONFIG
from core.preprocessor import ALG_SEPARATOR

# 配置日志
logger = logging.getLogger("api")

# -------------------- 防止遗传算法频繁查db ---------------------
# 缓存数据库中的交换比和突防率数据
# 格式: {(our_aircraft_type, enemy_aircraft_type): (our_ratio, enemy_ratio)}
AIR_EXCHANGE_RATIO_CACHE = {}
# 格式: {ground_type: detection_hit_rate}
GROUND_DEFENSE_RATE_CACHE = {}

# 是否已初始化缓存
_CACHE_INITIALIZED = False


# ------------------------------------------------------------

def initialize_cache(force_reload=False):
    """
    初始化缓存，一次性加载所有交换比和突防率数据
    
    Args:
        force_reload: 如果为True，强制重新加载数据，无论缓存是否已初始化
    """
    global _CACHE_INITIALIZED, AIR_EXCHANGE_RATIO_CACHE, GROUND_DEFENSE_RATE_CACHE

    if _CACHE_INITIALIZED and not force_reload:
        return

    # 如果强制重载，先清空现有缓存
    if force_reload:
        AIR_EXCHANGE_RATIO_CACHE.clear()
        GROUND_DEFENSE_RATE_CACHE.clear()
        logger.debug("强制重新加载战斗参数缓存...")
    else:
        logger.debug("初始化战斗参数缓存...")

    # 尝试连接数据库
    conn = None
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        # 加载所有空中交换比数据
        try:
            cursor.execute(
                "SELECT our_aircraft_type, enemy_aircraft_type, our_aircraft_ratio, enemy_aircraft_ratio FROM air_exchange_ratios")
            for row in cursor.fetchall():
                our_type, enemy_type, our_ratio, enemy_ratio = row
                AIR_EXCHANGE_RATIO_CACHE[(our_type, enemy_type)] = (our_ratio, enemy_ratio)
            logger.info(f"已加载 {len(AIR_EXCHANGE_RATIO_CACHE)} 条空中交换比数据")
            logger.info(AIR_EXCHANGE_RATIO_CACHE)
        except pymysql.Error as e:
            logger.error(f"加载空中交换比数据出错: {e}")

        # 加载所有地面防御率数据
        try:
            cursor.execute("SELECT ground_type, detection_hit_rate FROM ground_defense_rates")
            for row in cursor.fetchall():
                ground_type, detection_rate = row
                GROUND_DEFENSE_RATE_CACHE[ground_type] = detection_rate
            logger.info(f"已加载 {len(GROUND_DEFENSE_RATE_CACHE)} 条地面防御率数据")
            logger.info(GROUND_DEFENSE_RATE_CACHE)
        except pymysql.Error as e:
            logger.error(f"加载地面防御率数据出错: {e}")

    except pymysql.Error as e:
        logger.error(f"连接数据库出错: {e}")
    finally:
        if conn:
            conn.close()

    _CACHE_INITIALIZED = True
    logger.debug("战斗参数缓存初始化完成")


def get_air_exchange_ratio(our_aircraft_type: str, enemy_aircraft_type: str) -> Tuple[float, float]:
    """
    获取空中飞机交换比
    
    Args:
        our_aircraft_type: 我方飞机类型
        enemy_aircraft_type: 敌方飞机类型
    
    Returns:
        Tuple[float, float]: (我方损失比例, 敌方损失比例)
    """
    # 检查并处理我方飞机类型中的分隔符
    original_type = our_aircraft_type  # 保存原始类型
    if ALG_SEPARATOR in our_aircraft_type:
        # 分割字符串并取分隔符前面的部分作为真正的飞机类型
        our_aircraft_type = our_aircraft_type.split(ALG_SEPARATOR)[0]

    # 从缓存中获取数据
    key = (our_aircraft_type, enemy_aircraft_type)
    if key in AIR_EXCHANGE_RATIO_CACHE:
        return AIR_EXCHANGE_RATIO_CACHE[key]

    # 如果缓存中没有，使用默认值
    # 这里采用一个简单的默认值，假设我方和敌方的交换比为1:1.2（即我方损失少）
    default_ratio = (1.0, 1.2)
    AIR_EXCHANGE_RATIO_CACHE[key] = default_ratio  # 缓存此默认值
    return default_ratio


def get_ground_defense_rate(ground_type: str) -> float:
    """
    获取地面防空设施的命中率/发现率
    
    Args:
        ground_type: 地面防空设施类型
    
    Returns:
        float: 命中率/发现率（0-1之间的浮点数）
    """
    # 处理地面设施类型中可能存在的分隔符
    if ALG_SEPARATOR in ground_type:
        ground_type = ground_type.split(ALG_SEPARATOR)[0]

    # 从缓存中获取数据
    if ground_type in GROUND_DEFENSE_RATE_CACHE:
        return GROUND_DEFENSE_RATE_CACHE[ground_type]

    # 如果缓存中没有，使用默认值
    default_rate = 0.2  # 默认为20%
    GROUND_DEFENSE_RATE_CACHE[ground_type] = default_rate  # 缓存此默认值
    return default_rate


def get_simulate_ground_break_through_loss(ground_enemies: List[Dict[str, Any]], our_aircraft: Dict[str, int]) -> Dict[
    str, int]:
    """
    模拟地面防空对飞机的影响，计算突防后剩余的飞机数量
    
    Args:
        ground_enemies: 地面防空力量列表，每个元素包含ground_type和count
        our_aircraft: 我方飞机，键为飞机类型，值为数量
    
    Returns:
        Dict[str, int]: 突防后剩余的飞机数量，键为飞机类型，值为数量
    """
    if not ground_enemies:
        return our_aircraft.copy()  # 如果没有地面防空，直接返回原始飞机数量

    # 计算综合突防率
    # 基础突防率，假设基础突防率为95%，提高基础突防率
    base_penetration_rate = 0.95

    # 计算地面防空力量的综合影响因子
    ground_factor = 0
    total_defense_effect = 0

    for enemy in ground_enemies:
        ground_type = enemy.get("ground_type")
        count = enemy.get("count", 0)

        # 获取该类型地面防空的命中率/发现率
        defense_rate = get_ground_defense_rate(ground_type)

        # 使用改进的计算方法
        # 1. 使用对数函数减缓累积效应：ln(count+1)代替线性累加
        # 2. 降低基础乘数从0.5降低到0.2
        if count > 0:
            defense_effect = (1 - (1 - defense_rate) ** count)
            log_effect = math.log(count + 1) / math.log(10)  # 以10为底的对数
            total_defense_effect += defense_effect * log_effect * 0.2

    # 限制总防御效果最大值
    total_defense_effect = min(total_defense_effect, 0.7)  # 最多降低70%的突防率

    # 计算最终的突防率，地面因子越大，突防率越低
    # 保证即使在最大防御效果下，突防率至少为30%
    final_penetration_rate = max(0.3, base_penetration_rate - total_defense_effect)
    logger.debug(f"地面防空综合影响因子: {total_defense_effect}, 最终突防率: {final_penetration_rate}")

    # 计算突防后剩余的飞机数量
    remaining_aircraft = {}
    total_loss = 0
    for aircraft_type, count in our_aircraft.items():
        # 计算剩余数量，向下取整
        remaining = math.floor(count * final_penetration_rate)
        loss = count - remaining
        total_loss += loss
        remaining_aircraft[aircraft_type] = remaining

    # 打印最终突防率和损失数量
    logger.debug(f"突防计算结果: 最终突防率={final_penetration_rate:.4f}, 我方损失飞机数量={total_loss}")

    return remaining_aircraft


def get_simulate_air_exchange_loss(air_enemies: List[Dict[str, Any]], our_aircraft: Dict[str, int]) -> Dict[str, int]:
    """
    模拟空中交战，计算交战后剩余的飞机数量
    
    Args:
        air_enemies: 敌方空中力量列表，每个元素包含aircraft_type和count
        our_aircraft: 我方飞机，键为飞机类型，值为数量
    
    Returns:
        Dict[str, int]: 交战后剩余的飞机数量，键为飞机类型，值为数量
    """
    if not air_enemies:
        return our_aircraft.copy()  # 如果没有空中敌人，直接返回原始飞机数量

    # 复制一份我方和敌方飞机数据，用于模拟交战
    our_remaining = our_aircraft.copy()
    enemy_remaining = {enemy["aircraft_type"]: enemy["count"] for enemy in air_enemies}

    # 记录交换比信息和原始类型到处理后类型的映射
    exchange_ratio_info = []
    type_mapping = {}  # 存储原始类型到处理后类型的映射
    total_our_losses = 0

    # 按照一定的优先级进行交战模拟
    # 1. 先计算交换比
    # 2. 按照我方飞机类型顺序进行交战

    # 模拟多轮交战
    max_rounds = 10  # 最大交战轮数
    for round_idx in range(max_rounds):
        # 检查是否还有敌方飞机
        if not any(enemy_remaining.values()):
            break

        # 检查是否还有我方飞机
        if not any(our_remaining.values()):
            break

        # 按照类型进行交战模拟
        for our_type, our_count in list(our_remaining.items()):
            if our_count <= 0:
                continue

            for enemy_type, enemy_count in list(enemy_remaining.items()):
                if enemy_count <= 0:
                    continue

                # 保存原始类型
                original_our_type = our_type

                # 处理我方飞机类型的分隔符
                processed_our_type = our_type
                if ALG_SEPARATOR in our_type:
                    processed_our_type = our_type.split(ALG_SEPARATOR)[0]
                    type_mapping[our_type] = processed_our_type

                # 获取交换比
                our_ratio, enemy_ratio = get_air_exchange_ratio(our_type, enemy_type)

                # 计算本轮交战我方能击落的敌机和我方损失的飞机
                # 我方每损失1架，敌方损失enemy_ratio/our_ratio架
                exchange_ratio = enemy_ratio / our_ratio

                # 记录交换比信息 - 只保存一次每对飞机类型的交换比
                # 使用原始类型记录，但同时保存处理后的类型用于日志输出
                if (original_our_type, enemy_type) not in [(item[0], item[1]) for item in exchange_ratio_info]:
                    exchange_ratio_info.append((original_our_type, enemy_type, processed_our_type, exchange_ratio))

                # 假设本轮参与交战的我方飞机数量
                engaged_our = min(our_count, 5)  # 每轮最多5架我方飞机参战

                # 可以击落的敌机数量
                enemy_losses = min(enemy_count, math.floor(engaged_our * exchange_ratio))

                # 计算我方损失
                our_losses = min(our_count, math.ceil(enemy_losses / exchange_ratio))
                total_our_losses += our_losses

                # 更新剩余数量
                our_remaining[our_type] = our_count - our_losses
                enemy_remaining[enemy_type] = enemy_count - enemy_losses

                logger.debug(
                    f"轮次 {round_idx + 1}: 我方{original_our_type}损失{our_losses}架, 敌方{enemy_type}损失{enemy_losses}架")

                # 如果敌方该类型飞机全部被击落，继续处理下一种敌机
                if enemy_remaining[enemy_type] <= 0:
                    continue

                # 如果我方该类型飞机全部损失，继续处理下一种我方飞机
                if our_remaining[our_type] <= 0:
                    break

    # 打印交换比和损失飞机数量
    # 使用处理后的飞机类型（去除分隔符）来显示交换比
    exchange_ratio_str = ", ".join(
        [f"{processed_type}:{enemy}={ratio:.2f}" for _, enemy, processed_type, ratio in exchange_ratio_info])
    logger.debug(f"空战计算结果: 交换比=[{exchange_ratio_str}], 我方损失飞机数量={total_our_losses}")

    return our_remaining


def calculate_aircraft_losses(strategy: Dict) -> Tuple[Dict[str, int], int]:
    """
    计算策略执行时的飞机损失情况
    
    Args:
        strategy: 策略数据，包含aircraft和enemies信息
    
    Returns:
        Tuple[Dict[str, int], int]: (各类型飞机损失数量, 总损失数量)
    """
    # 提取我方飞机信息
    our_aircraft = {aircraft_type: count_price[0] for aircraft_type, count_price in strategy['aircraft'].items()}

    # 初始飞机数量
    initial_aircraft = our_aircraft.copy()

    # 剩余飞机数量，初始等于初始数量
    remaining_aircraft = our_aircraft.copy()

    # 获取敌人信息
    enemies = strategy.get('enemies', {})
    if not enemies:
        # 如果没有敌人信息，则使用penetration_rate计算
        penetration_rate = strategy.get('penetration_rate', 1.0)
        for aircraft_type, count in our_aircraft.items():
            # 计算剩余数量，向上取整损失数量
            remaining_aircraft[aircraft_type] = count - math.ceil(count * (1 - penetration_rate))

        # 打印使用默认突防率计算的结果
        total_loss = sum(initial_aircraft.values()) - sum(remaining_aircraft.values())
        logger.debug(f"默认突防计算结果: 默认突防率={penetration_rate:.4f}, 我方损失飞机数量={total_loss}")
    else:
        # 如果有地面防空，先计算突防损失
        ground_enemies = enemies.get('ground', [])
        if ground_enemies:
            remaining_aircraft = get_simulate_ground_break_through_loss(ground_enemies, remaining_aircraft)

        # 如果有空中敌人，再计算空战损失
        air_enemies = enemies.get('air', [])
        if air_enemies:
            remaining_aircraft = get_simulate_air_exchange_loss(air_enemies, remaining_aircraft)

    # 计算各类型飞机的损失数量
    aircraft_losses = {}
    total_loss = 0

    for aircraft_type, initial_count in initial_aircraft.items():
        remaining_count = remaining_aircraft.get(aircraft_type, 0)
        loss = initial_count - remaining_count
        if loss > 0:
            aircraft_losses[aircraft_type] = loss
            total_loss += loss

    # 打印最终损失结果
    logger.debug(f"最终计算结果: 总损失飞机数量={total_loss}, 损失明细={aircraft_losses}")

    return aircraft_losses, total_loss

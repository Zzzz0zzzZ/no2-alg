# 基于遗传算法的策略优化实现
import glob
import json
import os
import math
import random
import time
import logging

import matplotlib.pyplot as plt  # 添加matplotlib库用于绘图
from pylab import mpl
from api.models import OptimizationType  # 导入优化类型枚举
from core.simulate import calculate_aircraft_losses  # 导入模拟对战函数

# 配置日志
logger = logging.getLogger("api")

# 设置显示中文字体
mpl.rcParams["font.sans-serif"] = ["SimHei"]


class Strategy:
    def __init__(self, id, replaceable=False, aircraft=None, ammunition=None, price=0, time_range=None, penetration_rate=1.0, enemies=None):
        """
        初始化策略对象
        
        参数:
        id: 策略ID
        replaceable: 是否可替换
        aircraft: 字典，键为载机种类，值为(数量, 单价)元组
        ammunition: 字典，键为弹药种类，值为(数量, 单价)元组
        price: 策略总价格
        time_range: 策略的时间范围 [开始时间, 结束时间]
        penetration_rate: 突防率，0.0~1.0之间，默认1.0（已废弃，仅为兼容保留）
        enemies: 执行策略过程中遇到的敌人信息
        """
        self.id = id
        self.replaceable = replaceable
        self.aircraft = aircraft if aircraft else {}
        self.ammunition = ammunition if ammunition else {}
        self.time_range = time_range
        self.penetration_rate = penetration_rate  # 已废弃，仅为兼容保留
        self.enemies = enemies  # 新增：敌人信息

        # 如果没有提供价格，则根据载机损耗和弹药计算总价格
        if price == 0:
            self.price = self.calculate_price()
        else:
            self.price = price

    def calculate_price(self):
        """
        计算策略的总价格：飞机损耗价格 + 弹药价格
        飞机损耗价格 = 飞机单价 * 损失数量
        弹药价格 = 弹药数量 * 单价
        """
        # 计算飞机损耗价格
        aircraft_loss_price = 0
        aircraft_losses, _ = self.get_aircraft_loss()
        
        for aircraft_type, loss_count in aircraft_losses.items():
            _, price = self.aircraft[aircraft_type]
            aircraft_loss_price += loss_count * price
        
        # 计算弹药价格
        ammunition_price = sum(count * price for count, price in self.ammunition.values())
        
        return aircraft_loss_price + ammunition_price

    def get_resource_usage(self):
        """
        获取策略使用的资源情况
        
        返回:
        aircraft_usage: 字典，键为载机种类，值为数量
        ammunition_usage: 字典，键为弹药种类，值为数量
        """
        aircraft_usage = {k: v[0] for k, v in self.aircraft.items()}
        ammunition_usage = {k: v[0] for k, v in self.ammunition.items()}
        return aircraft_usage, ammunition_usage
    
    def get_aircraft_loss(self):
        """
        获取策略执行时的飞机损耗情况
        
        返回:
        aircraft_loss: 字典，键为载机种类，值为损耗数量
        total_loss: 总损耗数量
        """
        # 创建一个包含完整策略信息的字典，用于传递给calculate_aircraft_losses函数
        strategy_data = {
            'aircraft': self.aircraft,
            'enemies': self.enemies,
            'penetration_rate': self.penetration_rate  # 当enemies为空时使用
        }
        
        # 调用模拟对战函数计算损失
        aircraft_losses, total_loss = calculate_aircraft_losses(strategy_data)
        
        return aircraft_losses, total_loss

    def __str__(self):
        return f"Strategy {self.id} (价格: {self.price}, 可替换: {self.replaceable})"


class Action:
    def __init__(self, id, strategies=None):
        """
        初始化行动对象
        
        参数:
        id: 行动ID
        strategies: 行动包含的策略列表
        """
        self.id = id
        self.strategies = strategies if strategies else []

    def add_strategy(self, strategy):
        """
        添加策略到行动中
        """
        self.strategies.append(strategy)

    def __str__(self):
        return f"Action {self.id} (策略数: {len(self.strategies)})"


class ActionList:
    def __init__(self):
        """
        初始化作战行动清单
        """
        self.actions = []
        self.replacement_options = {}  # 存储可替换策略的替换选项

    def add_action(self, action):
        """
        添加行动到作战行动清单
        """
        self.actions.append(action)

    def add_replacement_option(self, strategy_id, replacement_strategies):
        """
        添加策略的替换选项
        
        参数:
        strategy_id: 可替换策略的ID
        replacement_strategies: 可用于替换的策略列表
        """
        self.replacement_options[strategy_id] = replacement_strategies

    def optimize(self, aircraft_constraints, ammunition_constraints, plot_convergence=False, solution_count=1,
                 time_limit=None, opt_type=OptimizationType.PRICE):
        """
        使用遗传算法优化作战行动清单，根据优化类型找出最优的替换方案
        
        参数:
        aircraft_constraints: 字典，键为载机种类，值为最大可用数量
        ammunition_constraints: 字典，键为弹药种类，值为最大可用数量
        plot_convergence: 是否绘制收敛曲线
        solution_count: 返回的最优解数量，默认为1
        time_limit: 算法运行时间限制（秒），默认为None表示无限制
        opt_type: 优化类型，默认为价格优化
        
        返回:
        best_combinations: 最优替换方案列表，每个元素是一个字典，键为策略ID，值为替换后的策略
        total_prices: 对应的总价格列表
        total_losses: 对应的总飞机损失列表
        total_usages: 对应的总出动飞机数量列表
        """
        # 检查初始方案是否满足资源约束
        initial_ammunition_usage = {}  # 弹药总使用量
        time_based_aircraft_usage = {}  # 基于时间段的飞机使用量
        initial_price = 0
        initial_loss = 0  # 初始方案的总飞机损失
        initial_usage = 0  # 初始方案的总出动飞机数量

        for action in self.actions:
            for strategy in action.strategies:
                aircraft_usage, ammunition_usage = strategy.get_resource_usage()
                initial_price += strategy.price
                
                # 计算初始方案的飞机损失
                _, loss_count = strategy.get_aircraft_loss()
                initial_loss += loss_count

                # 计算初始方案的总出动飞机数量
                for _, count in aircraft_usage.items():
                    initial_usage += count

                # 累加弹药总使用量
                for ammo_type, count in ammunition_usage.items():
                    initial_ammunition_usage[ammo_type] = initial_ammunition_usage.get(ammo_type, 0) + count

                # 记录时间段的飞机使用情况
                time_range = strategy.time_range
                if time_range:
                    start_time, end_time = time_range
                    for t in range(start_time, end_time):
                        if t not in time_based_aircraft_usage:
                            time_based_aircraft_usage[t] = {}
                        
                        for aircraft_type, count in aircraft_usage.items():
                            time_based_aircraft_usage[t][aircraft_type] = time_based_aircraft_usage[t].get(
                                aircraft_type, 0) + count

        # 检查初始方案是否超出资源约束
        resource_exceeded = False
        exceeded_resources = []

        # 检查时间段的飞机约束
        for t, t_aircraft_usage in time_based_aircraft_usage.items():
            for aircraft_type, count in t_aircraft_usage.items():
                if aircraft_type in aircraft_constraints and count > aircraft_constraints[aircraft_type]:
                    resource_exceeded = True
                    exceeded_resources.append(
                        f"时间点 {t} 的载机 {aircraft_type}: {count}/{aircraft_constraints[aircraft_type]}")

        # 检查弹药总量约束
        for ammo_type, count in initial_ammunition_usage.items():
            if ammo_type in ammunition_constraints and count > ammunition_constraints[ammo_type]:
                resource_exceeded = True
                exceeded_resources.append(f"弹药 {ammo_type}: {count}/{ammunition_constraints[ammo_type]}")

        if resource_exceeded:
            logger.debug("警告: 初始方案已超出资源约束限制:")
            for resource in exceeded_resources:
                logger.debug(f"  - {resource}")
            logger.debug("尝试寻找满足约束的替换方案...")

        # 获取所有可替换策略
        replaceable_strategies = []
        for action in self.actions:
            for strategy in action.strategies:
                if strategy.replaceable and strategy.id in self.replacement_options:
                    replaceable_strategies.append(strategy.id)

        # 如果没有可替换策略，直接返回初始方案
        if not replaceable_strategies:
            logger.debug("没有可替换的策略，保持原方案不变")
            return {}, [initial_price], [initial_loss], [initial_usage]

        # 使用遗传算法找出最优替换方案
        best_combinations, total_prices, total_losses, total_usages, convergence_data = self._genetic_algorithm_optimize(
            replaceable_strategies,
            aircraft_constraints,
            ammunition_constraints,
            initial_price,
            initial_loss,
            plot_convergence,
            solution_count,
            time_limit,
            opt_type
        )

        # 如果需要绘制收敛曲线
        if plot_convergence and convergence_data:
            self._plot_convergence_curve(convergence_data, opt_type)

        # 检查是否找到了满足约束的方案
        if not best_combinations or total_prices[0] == float('inf'):
            logger.debug("无法找到满足所有资源约束的方案。")
            return [], [], [], []
        else:
            if resource_exceeded:
                # 检查是否真的找到了新的替换方案
                if not best_combinations[0]:
                    logger.debug("无法找到满足资源约束的替换方案。")
                    return [], [], [], []
                else:
                    logger.debug(f"找到{len(best_combinations)}个满足资源约束的替换方案:")
                    for i, (combination, price, loss, usage) in enumerate(
                            zip(best_combinations, total_prices, total_losses, total_usages), 1):
                        logger.debug(f"\n方案 {i}:")
                        
                        if opt_type == OptimizationType.AIRCRAFT_LOSS:
                            logger.debug(f"总飞机损失: {loss} 架")
                            if loss < initial_loss:
                                logger.debug(f"比原方案减少: {initial_loss - loss} 架")
                            else:
                                logger.debug(f"比原方案增加: {loss - initial_loss} 架")
                            logger.debug(f"总价格: {price}")
                            logger.debug(f"总出动飞机数量: {usage} 架")
                        elif opt_type == OptimizationType.AIRCRAFT_USAGE:
                            logger.debug(f"总出动飞机数量: {usage} 架")
                            if usage < initial_usage:
                                logger.debug(f"比原方案减少: {initial_usage - usage} 架")
                            else:
                                logger.debug(f"比原方案增加: {usage - initial_usage} 架")
                            logger.debug(f"总价格: {price}")
                            logger.debug(f"总飞机损失: {loss} 架")
                        else:
                            logger.debug(f"总价格: {price}")
                            if price < initial_price:
                                logger.debug(f"比原方案节省: {initial_price - price}")
                            else:
                                logger.debug(f"比原方案增加: {price - initial_price}")
                            logger.debug(f"总飞机损失: {loss} 架")
                            logger.debug(f"总出动飞机数量: {usage} 架")

                        # 打印替换方案详情
                        logger.debug("\n替换方案详情:")
                        for action in self.actions:
                            logger.debug(f"行动 {action.id}:")
                            for strategy in action.strategies:
                                if strategy.replaceable and strategy.id in combination:
                                    replacement = combination[strategy.id]
                                    logger.debug(
                                        f"  - 策略 {strategy.id} 替换为 {replacement.id} (价格: {replacement.price}, 飞机损失: {replacement.get_aircraft_loss()[1]})")
                                else:
                                    _, loss_count = strategy.get_aircraft_loss()
                                    logger.debug(
                                        f"  - {strategy} {'(不可替换)' if not strategy.replaceable else '(未替换)'}, 飞机损失: {loss_count}")

                        # 打印资源使用情况
                        logger.debug("\n资源使用情况:")
                        total_aircraft_usage = {}
                        total_ammunition_usage = {}
                        total_aircraft_loss = {}

                        for action in self.actions:
                            for strategy in action.strategies:
                                if strategy.replaceable and strategy.id in combination:
                                    strategy = combination[strategy.id]

                                aircraft_usage, ammunition_usage = strategy.get_resource_usage()
                                aircraft_loss_dict, _ = strategy.get_aircraft_loss()

                                for aircraft_type, count in aircraft_usage.items():
                                    total_aircraft_usage[aircraft_type] = total_aircraft_usage.get(aircraft_type,
                                                                                                   0) + count

                                for aircraft_type, loss_count in aircraft_loss_dict.items():
                                    total_aircraft_loss[aircraft_type] = total_aircraft_loss.get(aircraft_type,
                                                                                                 0) + loss_count

                                for ammo_type, count in ammunition_usage.items():
                                    total_ammunition_usage[ammo_type] = total_ammunition_usage.get(ammo_type, 0) + count

                        logger.debug("载机使用:")
                        for aircraft_type, count in total_aircraft_usage.items():
                            loss = total_aircraft_loss.get(aircraft_type, 0)
                            logger.debug(
                                f"  - {aircraft_type}: 使用 {count}/{aircraft_constraints.get(aircraft_type, '无限制')}, 损失 {loss} 架")

                        logger.debug("弹药使用:")
                        for ammo_type, count in total_ammunition_usage.items():
                            logger.debug(f"  - {ammo_type}: {count}/{ammunition_constraints.get(ammo_type, '无限制')}")
            else:
                if (opt_type == OptimizationType.PRICE and total_prices[0] < initial_price) or \
                        (opt_type == OptimizationType.AIRCRAFT_LOSS and total_losses[0] < initial_loss) or \
                        (opt_type == OptimizationType.AIRCRAFT_USAGE and total_usages[0] < initial_usage):
                    logger.debug(f"找到{len(best_combinations)}个更优方案:")
                    for i, (combination, price, loss, usage) in enumerate(
                            zip(best_combinations, total_prices, total_losses, total_usages), 1):
                        logger.debug(f"\n方案 {i}:")

                        if opt_type == OptimizationType.AIRCRAFT_LOSS:
                            logger.debug(f"总飞机损失: {loss} 架，减少: {initial_loss - loss} 架")
                            logger.debug(f"总价格: {price}")
                            logger.debug(f"总出动飞机数量: {usage} 架")
                        elif opt_type == OptimizationType.AIRCRAFT_USAGE:
                            logger.debug(f"总出动飞机数量: {usage} 架，减少: {initial_usage - usage} 架")
                            logger.debug(f"总价格: {price}")
                            logger.debug(f"总飞机损失: {loss} 架")
                        else:
                            logger.debug(f"总价格: {price}，节省: {initial_price - price}")
                            logger.debug(f"总飞机损失: {loss} 架")
                            logger.debug(f"总出动飞机数量: {usage} 架")

                        # 打印替换方案详情
                        logger.debug("\n替换方案详情:")
                        for action in self.actions:
                            logger.debug(f"行动 {action.id}:")
                            for strategy in action.strategies:
                                if strategy.replaceable and strategy.id in combination:
                                    replacement = combination[strategy.id]
                                    logger.debug(
                                        f"  - 策略 {strategy.id} 替换为 {replacement.id} (价格: {replacement.price}, 飞机损失: {replacement.get_aircraft_loss()[1]})")
                                else:
                                    _, loss_count = strategy.get_aircraft_loss()
                                    logger.debug(
                                        f"  - {strategy} {'(不可替换)' if not strategy.replaceable else '(未替换)'}, 飞机损失: {loss_count}")

                        # 打印资源使用情况
                        logger.debug("\n资源使用情况:")
                        total_aircraft_usage = {}
                        total_ammunition_usage = {}
                        total_aircraft_loss = {}

                        for action in self.actions:
                            for strategy in action.strategies:
                                if strategy.replaceable and strategy.id in combination:
                                    strategy = combination[strategy.id]

                                aircraft_usage, ammunition_usage = strategy.get_resource_usage()
                                aircraft_loss_dict, _ = strategy.get_aircraft_loss()

                                for aircraft_type, count in aircraft_usage.items():
                                    total_aircraft_usage[aircraft_type] = total_aircraft_usage.get(aircraft_type,
                                                                                                   0) + count

                                for aircraft_type, loss_count in aircraft_loss_dict.items():
                                    total_aircraft_loss[aircraft_type] = total_aircraft_loss.get(aircraft_type,
                                                                                                 0) + loss_count

                                for ammo_type, count in ammunition_usage.items():
                                    total_ammunition_usage[ammo_type] = total_ammunition_usage.get(ammo_type, 0) + count

                        logger.debug("载机使用:")
                        for aircraft_type, count in total_aircraft_usage.items():
                            loss = total_aircraft_loss.get(aircraft_type, 0)
                            logger.debug(
                                f"  - {aircraft_type}: 使用 {count}/{aircraft_constraints.get(aircraft_type, '无限制')}, 损失 {loss} 架")

                        logger.debug("弹药使用:")
                        for ammo_type, count in total_ammunition_usage.items():
                            logger.debug(f"  - {ammo_type}: {count}/{ammunition_constraints.get(ammo_type, '无限制')}")
                else:
                    logger.debug("未找到更优方案，保持原方案不变")

        return best_combinations, total_prices, total_losses, total_usages

    def _genetic_algorithm_optimize(self, replaceable_strategies, aircraft_constraints, ammunition_constraints,
                                    initial_price, initial_loss, plot_convergence=False, solution_count=1,
                                    time_limit=None, opt_type=OptimizationType.PRICE):
        """
        使用遗传算法寻找最优替换方案

        参数:
        replaceable_strategies: 可替换策略ID列表
        aircraft_constraints: 载机约束
        ammunition_constraints: 弹药约束
        initial_price: 初始方案总价格
        initial_loss: 初始方案总飞机损失
        plot_convergence: 是否记录收敛数据
        solution_count: 返回的最优解数量
        time_limit: 算法运行时间限制（秒）
        opt_type: 优化类型，默认为价格优化

        返回:
        best_combinations: 最优替换方案列表
        total_prices: 最优方案总价格列表
        total_losses: 最优方案总飞机损失列表
        total_usages: 最优方案总出动飞机数量列表
        convergence_data: 收敛数据，如果plot_convergence为True
        """
        # 遗传算法参数
        population_size = 100  # 种群大小
        generations = 200  # 迭代代数
        mutation_rate = 0.1  # 变异率
        elite_size = 10  # 精英数量

        # 初始化种群
        population = self._initialize_population(replaceable_strategies, population_size)

        # 记录最优解集合
        best_solutions = []
        best_prices = []
        best_losses = []
        best_usages = []  # 记录最优解的总出动飞机数量

        # 用于记录收敛曲线数据
        convergence_data = [] if plot_convergence else None

        # 计算初始方案的总出动飞机数量
        initial_usage = 0
        for action in self.actions:
            for strategy in action.strategies:
                aircraft_usage, _ = strategy.get_resource_usage()
                for _, count in aircraft_usage.items():
                    initial_usage += count

        # 记录开始时间
        start_time = time.time()

        # 迭代进化
        for generation in range(generations):
            # 评估种群适应度
            fitness_scores = []
            for individual in population:
                fitness, price, loss, usage, valid = self._evaluate_fitness(
                    individual,
                    replaceable_strategies,
                    aircraft_constraints,
                    ammunition_constraints,
                    opt_type
                )
                fitness_scores.append((individual, fitness, price, loss, usage, valid))

            # 排序，适应度高的在前面
            fitness_scores.sort(key=lambda x: x[1], reverse=True)

            # 更新最优解集合
            current_best_valid_fitness = float('-inf')
            current_best_valid_price = float('inf')
            current_best_valid_loss = float('inf')
            current_best_valid_usage = float('inf')

            # 获取所有有效解
            valid_solutions = [(individual, fitness, price, loss, usage) for
                               individual, fitness, price, loss, usage, valid in
                               fitness_scores if valid]

            # 根据优化类型排序
            if opt_type == OptimizationType.AIRCRAFT_LOSS:
                valid_solutions.sort(key=lambda x: x[3])  # 按飞机损失排序
            elif opt_type == OptimizationType.AIRCRAFT_USAGE:
                valid_solutions.sort(key=lambda x: x[4])  # 按出动飞机数量排序
            else:
                valid_solutions.sort(key=lambda x: x[2])  # 按价格排序

            # 更新最优解集合
            new_best_solutions = []
            new_best_prices = []
            new_best_losses = []
            new_best_usages = []
            seen_combinations = set()  # 用于记录已经见过的方案

            for individual, fitness, price, loss, usage in valid_solutions:
                # 解码当前个体
                combination = self._decode_individual(individual, replaceable_strategies)

                # 将combination转换为可哈希的形式以便去重
                combination_tuple = tuple(sorted((k, v.id) for k, v in combination.items()))

                # 判断是否需要添加到最优解集合
                should_add = False
                if combination_tuple not in seen_combinations:
                    if len(new_best_solutions) < solution_count:
                        should_add = True
                    elif opt_type == OptimizationType.AIRCRAFT_LOSS and loss < max(new_best_losses):
                        should_add = True
                    elif opt_type == OptimizationType.AIRCRAFT_USAGE and usage < max(new_best_usages):
                        should_add = True
                    elif opt_type == OptimizationType.PRICE and price < max(new_best_prices):
                        should_add = True

                if should_add:
                    # 如果最优解集合已满，移除最差的解
                    if len(new_best_solutions) >= solution_count:
                        if opt_type == OptimizationType.AIRCRAFT_LOSS:
                            max_loss_index = new_best_losses.index(max(new_best_losses))
                            old_combination = new_best_solutions[max_loss_index]
                            old_combination_tuple = tuple(sorted((k, v.id) for k, v in old_combination.items()))
                            seen_combinations.remove(old_combination_tuple)
                            new_best_solutions.pop(max_loss_index)
                            new_best_prices.pop(max_loss_index)
                            new_best_losses.pop(max_loss_index)
                            new_best_usages.pop(max_loss_index)
                        elif opt_type == OptimizationType.AIRCRAFT_USAGE:
                            max_usage_index = new_best_usages.index(max(new_best_usages))
                            old_combination = new_best_solutions[max_usage_index]
                            old_combination_tuple = tuple(sorted((k, v.id) for k, v in old_combination.items()))
                            seen_combinations.remove(old_combination_tuple)
                            new_best_solutions.pop(max_usage_index)
                            new_best_prices.pop(max_usage_index)
                            new_best_losses.pop(max_usage_index)
                            new_best_usages.pop(max_usage_index)
                        else:
                            max_price_index = new_best_prices.index(max(new_best_prices))
                            old_combination = new_best_solutions[max_price_index]
                            old_combination_tuple = tuple(sorted((k, v.id) for k, v in old_combination.items()))
                            seen_combinations.remove(old_combination_tuple)
                            new_best_solutions.pop(max_price_index)
                            new_best_prices.pop(max_price_index)
                            new_best_losses.pop(max_price_index)
                            new_best_usages.pop(max_price_index)

                    new_best_solutions.append(combination)
                    new_best_prices.append(price)
                    new_best_losses.append(loss)
                    new_best_usages.append(usage)
                    seen_combinations.add(combination_tuple)

                    if fitness > current_best_valid_fitness:
                        current_best_valid_fitness = fitness
                        current_best_valid_price = price
                        current_best_valid_loss = loss
                        current_best_valid_usage = usage

            # 更新全局最优解集合
            if new_best_solutions:
                best_solutions = new_best_solutions
                best_prices = new_best_prices
                best_losses = new_best_losses
                best_usages = new_best_usages

            # 记录当前代的最佳适应度和价格/损失/出动数量
            if plot_convergence:
                # 根据优化类型记录不同的收敛数据
                if opt_type == OptimizationType.AIRCRAFT_LOSS:
                    convergence_data.append(
                        (generation, current_best_valid_loss if current_best_valid_loss != float('inf') else None))
                elif opt_type == OptimizationType.AIRCRAFT_USAGE:
                    convergence_data.append(
                        (generation, current_best_valid_usage if current_best_valid_usage != float('inf') else None))
                else:
                    convergence_data.append(
                        (generation, current_best_valid_price if current_best_valid_price != float('inf') else None))

            # 检查是否达到时间限制
            if time_limit is not None and time.time() - start_time >= time_limit:
                logger.debug(f"达到时间限制 {time_limit} 秒，提前结束迭代")
                break

            # 判断是否可以提前终止迭代
            if generation > 150:  # 至少运行150代
                # 检查最近30代是否有显著改进
                if generation > 50 and convergence_data:
                    if opt_type == OptimizationType.AIRCRAFT_LOSS:
                        if all(
                                abs(data[1] - best_losses[0]) < 0.001 * best_losses[0] if data[1] is not None else False
                                for data in convergence_data[-30:]
                        ):
                            logger.debug("最近30代无显著改进，提前结束迭代")
                            break
                    elif opt_type == OptimizationType.AIRCRAFT_USAGE:
                        if all(
                                abs(data[1] - best_usages[0]) < 0.001 * best_usages[0] if data[1] is not None else False
                                for data in convergence_data[-30:]
                        ):
                            logger.debug("最近30代无显著改进，提前结束迭代")
                            break
                    else:
                        if all(
                                abs(data[1] - best_prices[0]) < 0.001 * best_prices[0] if data[1] is not None else False
                                for data in convergence_data[-30:]
                        ):
                            logger.debug("最近30代无显著改进，提前结束迭代")
                            break

            # 选择精英个体
            elites = [fs[0] for fs in fitness_scores[:elite_size]]

            # 选择父代进行交叉和变异
            new_population = elites.copy()

            # 使用轮盘赌选择和交叉生成新个体
            while len(new_population) < population_size:
                parent1 = self._selection(fitness_scores)
                parent2 = self._selection(fitness_scores)
                child = self._crossover(parent1, parent2)
                child = self._mutation(child, mutation_rate)
                new_population.append(child)

            population = new_population

        # 如果没有找到满足约束的解，返回空方案列表
        if not best_solutions:
            return [], [float('inf')], [float('inf')], [float('inf')], convergence_data

        # 在返回前对最终结果进行去重
        unique_solutions = []
        unique_prices = []
        unique_losses = []
        unique_usages = []
        seen_combinations = set()

        for solution, price, loss, usage in zip(best_solutions, best_prices, best_losses, best_usages):
            # 将solution转换为可哈希的形式以便去重
            solution_tuple = tuple(sorted((k, v.id) for k, v in solution.items()))

            # 如果这个方案还没见过，添加到最终结果中
            if solution_tuple not in seen_combinations:
                unique_solutions.append(solution)
                unique_prices.append(price)
                unique_losses.append(loss)
                unique_usages.append(usage)
                seen_combinations.add(solution_tuple)

        return unique_solutions, unique_prices, unique_losses, unique_usages, convergence_data

    def _plot_convergence_curve(self, convergence_data, opt_type=OptimizationType.PRICE):
        """
        绘制遗传算法的收敛曲线

        参数:
        convergence_data: 收敛数据，包含(代数, 价格或损失或出动数量)元组的列表
        opt_type: 优化类型，默认为价格优化
        """
        generations = [data[0] for data in convergence_data]
        values = [data[1] for data in convergence_data]
        logger.debug("迭代轮次: ", len(generations))

        # 处理无效解（值为None的情况）
        valid_gens = []
        valid_values = []
        for gen, value in zip(generations, values):
            if value is not None:
                valid_gens.append(gen)
                valid_values.append(value)

        plt.figure(figsize=(10, 6))

        # 如果有有效解，绘制有效解的收敛曲线
        if valid_values:
            plt.plot(valid_gens, valid_values, 'b-', label='有效解')
            plt.scatter(valid_gens, valid_values, color='blue', s=20)

        # 标记无效解的代数
        invalid_gens = [gen for gen, value in zip(generations, values) if value is None]
        if invalid_gens:
            plt.scatter(invalid_gens, [max(valid_values) * 1.1 if valid_values else 1000] * len(invalid_gens),
                        color='red', marker='x', label='无有效解的代数')

        plt.title('遗传算法收敛曲线')
        plt.xlabel('代数')

        # 根据优化类型设置y轴标签
        if opt_type == OptimizationType.AIRCRAFT_LOSS:
            plt.ylabel('最佳有效解飞机损失数')
        elif opt_type == OptimizationType.AIRCRAFT_USAGE:
            plt.ylabel('最佳有效解出动飞机数量')
        else:
            plt.ylabel('最佳有效解价格')

        plt.grid(True)
        plt.legend()

        # 保存图像
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 根据优化类型设置文件名
        if opt_type == OptimizationType.AIRCRAFT_LOSS:
            filename = 'convergence_curve_loss.png'
        elif opt_type == OptimizationType.AIRCRAFT_USAGE:
            filename = 'convergence_curve_usage.png'
        else:
            filename = 'convergence_curve_price.png'

        plt.savefig(os.path.join(output_dir, filename))
        logger.debug(f"收敛曲线已保存至: {os.path.join(output_dir, filename)}")
        plt.close()

    def _initialize_population(self, replaceable_strategies, population_size):
        """
        初始化种群
        
        参数:
        replaceable_strategies: 可替换策略ID列表
        population_size: 种群大小
        
        返回:
        population: 初始种群，每个个体是一个染色体（替换方案的编码）
        """
        population = []

        # 创建一个不替换任何策略的个体
        no_replacement = [0] * len(replaceable_strategies)
        population.append(no_replacement)

        # 随机生成其他个体
        for _ in range(population_size - 1):
            individual = []
            for strategy_id in replaceable_strategies:
                # 对于每个可替换策略，随机选择是否替换以及替换为哪个选项
                # 0表示不替换，1~n表示替换为第n个替换选项
                max_option = len(self.replacement_options.get(strategy_id, []))
                individual.append(random.randint(0, max_option))
            population.append(individual)

        return population

    def _evaluate_fitness(self, individual, replaceable_strategies, aircraft_constraints, ammunition_constraints,
                          opt_type=OptimizationType.PRICE):
        """
        评估个体的适应度，计算在给定约束条件下的总价格、总飞机损失、总出动飞机数量和可行性

        参数:
        individual: list, 个体（染色体），表示每个可替换策略的替换选项索引
        replaceable_strategies: list, 可替换策略ID列表
        aircraft_constraints: dict, 载机约束，键为载机类型，值为最大可用数量（基于时间段约束）
        ammunition_constraints: dict, 弹药约束，键为弹药类型，值为最大可用数量（基于总量约束）
        opt_type: 优化类型，默认为价格优化

        返回:
        tuple: (fitness, total_price, total_loss, total_usage, valid)
            - fitness: float, 适应度分数，有效解为优化目标的负值，无效解为惩罚值
            - total_price: float, 方案总价格
            - total_loss: int, 方案总飞机损失
            - total_usage: int, 方案总出动飞机数量
            - valid: bool, 是否满足所有约束条件
        """
        # 解码个体，获取替换方案
        combination = self._decode_individual(individual, replaceable_strategies)

        # 计算总价格、总飞机损失、总出动飞机数量和资源使用情况
        total_price = 0
        total_loss = 0
        total_usage = 0  # 总出动飞机数量
        total_ammunition_usage = {}  # 弹药总使用量
        time_based_aircraft_usage = {}  # 基于时间段的飞机使用量
        time_based_aircraft_loss = {}  # 基于时间段的飞机损耗量
        available_aircraft = {k: v for k, v in aircraft_constraints.items()}  # 可用飞机数量，初始为约束值

        # 按时间顺序排序行动
        sorted_actions = sorted(self.actions, key=lambda a: min(
            [s.time_range[0] if s.time_range else 0 for s in a.strategies]) if a.strategies else 0)

        for action in sorted_actions:
            for strategy in action.strategies:
                # 如果策略可替换且在替换方案中，使用替换后的策略
                if strategy.replaceable and strategy.id in combination:
                    strategy = combination[strategy.id]

                # 累加总价格
                total_price += strategy.price

                # 获取策略的资源使用情况
                aircraft_usage, ammunition_usage = strategy.get_resource_usage()

                # 获取策略的飞机损耗情况
                aircraft_loss, loss_count = strategy.get_aircraft_loss()
                total_loss += loss_count

                # 累加总出动飞机数量
                for aircraft_type, count in aircraft_usage.items():
                    total_usage += count

                # 累加弹药使用量
                for ammo_type, count in ammunition_usage.items():
                    total_ammunition_usage[ammo_type] = total_ammunition_usage.get(ammo_type, 0) + count

                # 记录时间段的飞机使用和损耗情况
                time_range = strategy.time_range
                if time_range:
                    start_time, end_time = time_range
                    for t in range(start_time, end_time):
                        if t not in time_based_aircraft_usage:
                            time_based_aircraft_usage[t] = {}
                            time_based_aircraft_loss[t] = {}

                        # 检查该时间点是否有足够的飞机可用
                        for aircraft_type, count in aircraft_usage.items():
                            # 检查可用数量
                            if aircraft_type in available_aircraft and available_aircraft[aircraft_type] < count:
                                return float('-inf'), float('inf'), float('inf'), float('inf'), False  # 资源不足，无效解

                            # 记录使用量
                            time_based_aircraft_usage[t][aircraft_type] = time_based_aircraft_usage[t].get(
                                aircraft_type, 0) + count

                        # 记录损耗量并更新可用飞机数量
                        for aircraft_type, loss_count in aircraft_loss.items():
                            time_based_aircraft_loss[t][aircraft_type] = time_based_aircraft_loss[t].get(aircraft_type,
                                                                                                         0) + loss_count

                            # 更新可用飞机数量（在时间段结束后）
                            if t == end_time - 1:  # 最后一个时间点
                                available_aircraft[aircraft_type] -= loss_count
                                if available_aircraft[aircraft_type] < 0:
                                    return float('-inf'), float('inf'), float('inf'), float('inf'), False  # 资源不足，无效解

        # 检查资源约束
        valid = True

        # 检查弹药总量约束
        for ammo_type, count in total_ammunition_usage.items():
            if ammo_type in ammunition_constraints and count > ammunition_constraints[ammo_type]:
                valid = False
                break

        # 如果有效，根据优化类型返回适应度
        if valid:
            if opt_type == OptimizationType.AIRCRAFT_LOSS:
                return -total_loss, total_price, total_loss, total_usage, True  # 飞机损失越少适应度越高
            elif opt_type == OptimizationType.AIRCRAFT_USAGE:
                return -total_usage, total_price, total_loss, total_usage, True  # 出动飞机数量越少适应度越高
            else:
                return -total_price, total_price, total_loss, total_usage, True  # 价格越低适应度越高
        else:
            return float('-inf'), float('inf'), float('inf'), float('inf'), False

    def _selection(self, fitness_scores):
        """
        使用轮盘赌选择一个个体

        参数:
        fitness_scores: 包含(individual, fitness, price, loss, valid)元组的列表

        返回:
        selected_individual: 被选中的个体
        """
        # 找出最小适应度值
        min_fitness = min(fs[1] for fs in fitness_scores)

        # 计算适应度总和（将所有适应度值平移，使最小值变为正数）
        offset = abs(min_fitness) + 1  # 加1确保所有值都是正的
        total_fitness = sum(fs[1] + offset for fs in fitness_scores)

        # 生成随机值
        r = random.uniform(0, total_fitness)

        # 轮盘赌选择
        current_sum = 0
        for individual, fitness, _, _, _, _ in fitness_scores:
            current_sum += (fitness + offset)
            if current_sum >= r:
                return individual

        # 如果没有选中任何个体（理论上不应该发生），返回第一个
        return fitness_scores[0][0]

    def _crossover(self, parent1, parent2):
        """
        对两个父代个体进行交叉操作
        
        参数:
        parent1, parent2: 两个父代个体
        
        返回:
        child: 子代个体
        """
        # 单点交叉
        if len(parent1) <= 1:
            return parent1.copy()

        crossover_point = random.randint(1, len(parent1) - 1)
        child = parent1[:crossover_point] + parent2[crossover_point:]

        # 修复子代，确保每个位置的值都在对应策略的有效替换选项范围内
        for i in range(len(child)):
            strategy_id = list(self.replacement_options.keys())[i]
            max_option = len(self.replacement_options.get(strategy_id, []))
            if child[i] > max_option:
                child[i] = random.randint(0, max_option)  # 如果超出范围，随机选择一个有效值

        return child

    def _mutation(self, individual, mutation_rate):
        """
        对个体进行变异操作
        
        参数:
        individual: 待变异的个体
        mutation_rate: 变异率
        
        返回:
        mutated_individual: 变异后的个体
        """
        mutated = individual.copy()

        for i in range(len(mutated)):
            # 以mutation_rate的概率进行变异
            if random.random() < mutation_rate:
                strategy_id = list(self.replacement_options.keys())[i]
                max_option = len(self.replacement_options.get(strategy_id, []))
                # 随机选择一个不同的值
                current_value = mutated[i]
                new_value = random.randint(0, max_option)
                while new_value == current_value and max_option > 0:
                    new_value = random.randint(0, max_option)
                mutated[i] = new_value

        return mutated

    def _decode_individual(self, individual, replaceable_strategies):
        """
        将个体（染色体）解码为替换方案
        
        参数:
        individual: 个体（染色体）
        replaceable_strategies: 可替换策略ID列表
        
        返回:
        combination: 替换方案，字典，键为策略ID，值为替换后的策略
        """
        combination = {}

        for i, strategy_id in enumerate(replaceable_strategies):
            option_index = individual[i]
            # 如果option_index为0，表示不替换
            if option_index > 0 and option_index <= len(self.replacement_options.get(strategy_id, [])):
                replacement = self.replacement_options[strategy_id][option_index - 1]
                combination[strategy_id] = replacement

        return combination

    def __str__(self):
        return f"ActionList (行动数: {len(self.actions)})"


# 从JSON文件加载测试用例
def load_test_case(file_path):
    """
    从JSON文件加载测试用例
    
    参数:
    file_path: JSON文件路径
    
    返回:
    action_list: 构建好的ActionList对象
    aircraft_constraints: 载机约束
    ammunition_constraints: 弹药约束
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 创建策略对象
        strategies = {}
        for strategy_id, strategy_data in data['strategies'].items():
            aircraft = {k: tuple(v) for k, v in strategy_data.get('aircraft', {}).items()}
            ammunition = {k: tuple(v) for k, v in strategy_data.get('ammunition', {}).items()}
            strategies[strategy_id] = Strategy(
                strategy_id,
                strategy_data.get('replaceable', False),
                aircraft=aircraft,
                ammunition=ammunition
            )

        # 创建行动对象
        actions = {}
        for action_id, strategy_ids in data['actions'].items():
            action = Action(action_id)
            for strategy_id in strategy_ids:
                if strategy_id in strategies:
                    action.add_strategy(strategies[strategy_id])
                else:
                    logger.debug(f"警告: 策略 {strategy_id} 未在策略列表中定义")
            actions[action_id] = action

        # 创建作战行动清单
        action_list = ActionList()
        for action in actions.values():
            action_list.add_action(action)

        # 添加替换选项
        for strategy_id, replacement_ids in data.get('replacement_options', {}).items():
            replacement_strategies = [strategies[rid] for rid in replacement_ids if rid in strategies]
            if replacement_strategies:
                action_list.add_replacement_option(strategy_id, replacement_strategies)

        # 获取约束条件
        constraints = data.get('constraints', {})
        aircraft_constraints = constraints.get('aircraft', {})
        ammunition_constraints = constraints.get('ammunition', {})

        return action_list, aircraft_constraints, ammunition_constraints

    except Exception as e:
        logger.debug(f"加载测试用例 {file_path} 时出错: {e}")
        return None, None, None


def run_optimize(action_list, aircraft_constraints, ammunition_constraints, plot_convergence, solution_count=1,
                 time_limit=None, opt_type=OptimizationType.PRICE):
    """
    [TOP] 优化算法顶层调用，传入实例化的action_list，及约束条件，输出优化结果
    :param action_list: 行动列表对象
    :param aircraft_constraints: 飞机资源约束
    :param ammunition_constraints: 弹药资源约束
    :param plot_convergence: 是否绘制收敛曲线
    :param solution_count: 返回的解决方案数量
    :param time_limit: 算法运行时间限制
    :param opt_type: 优化类型，默认为价格优化
    :return: 最优替换方案列表，总价格列表，总飞机损失列表
    """
    # 优化，并传入plot_convergence参数和优化类型
    best_combinations, total_prices, total_losses, total_usages = action_list.optimize(
        aircraft_constraints,
        ammunition_constraints,
        plot_convergence=plot_convergence,
        solution_count=solution_count,
        time_limit=time_limit,
        opt_type=opt_type
    )
    logger.debug("-" * 50)
    return best_combinations, total_prices, total_losses, total_usages


# 运行单个测试用例
def run_test_case(file_path, plot_convergence=True):
    """
    运行单个测试用例

    参数:
    file_path: 测试用例文件路径
    plot_convergence: 是否绘制收敛曲线
    """
    logger.debug(f"\n运行测试用例: {os.path.basename(file_path)}")
    logger.debug("-" * 50)

    action_list, aircraft_constraints, ammunition_constraints = load_test_case(file_path)
    if not action_list or not aircraft_constraints or not ammunition_constraints:
        logger.debug(f"无法加载测试用例: {file_path}")
        return

    # 调用优化算法
    run_optimize(action_list, aircraft_constraints, ammunition_constraints, plot_convergence)


# 主函数
def main():
    """
    主函数，运行所有测试用例
    """
    test_case_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'testcases')
    test_case_files = glob.glob(os.path.join(test_case_dir, '*.json'))

    if not test_case_files:
        logger.debug(f"未找到测试用例文件，请确保 {test_case_dir} 目录下有 .json 文件")
        return

    logger.debug(f"找到 {len(test_case_files)} 个测试用例文件")

    # 添加命令行参数解析
    import argparse
    parser = argparse.ArgumentParser(description='基于遗传算法的策略优化')
    parser.add_argument('--no-plot', action='store_true', help='不绘制收敛曲线')
    args = parser.parse_args()

    for file_path in test_case_files:
        run_test_case(file_path, plot_convergence=not args.no_plot)


# 运行测试
if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    logger.debug(f"程序执行时间: {end_time - start_time} s")

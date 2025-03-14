# 基于遗传算法的策略优化实现
import json
import os
import glob
import random
import copy
from typing import Dict, List, Tuple, Any, Set

class Strategy:
    def __init__(self, id, replaceable=False, aircraft=None, ammunition=None, price=0):
        """
        初始化策略对象
        
        参数:
        id: 策略ID
        replaceable: 是否可替换
        aircraft: 字典，键为载机种类，值为(数量, 单价)元组
        ammunition: 字典，键为弹药种类，值为(数量, 单价)元组
        price: 策略总价格
        """
        self.id = id
        self.replaceable = replaceable
        self.aircraft = aircraft if aircraft else {}
        self.ammunition = ammunition if ammunition else {}

        # 如果没有提供价格，则根据载机和弹药计算总价格
        if price == 0:
            self.price = self.calculate_price()
        else:
            self.price = price

    def calculate_price(self):
        """
        计算策略的总价格
        """
        aircraft_price = sum(count * price for count, price in self.aircraft.values())
        ammunition_price = sum(count * price for count, price in self.ammunition.values())
        return aircraft_price + ammunition_price

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

    def optimize(self, aircraft_constraints, ammunition_constraints):
        """
        使用遗传算法优化作战行动清单，找出在资源约束下总价格最低的替换方案
        
        参数:
        aircraft_constraints: 字典，键为载机种类，值为最大可用数量
        ammunition_constraints: 字典，键为弹药种类，值为最大可用数量
        
        返回:
        best_combination: 最优替换方案，字典，键为策略ID，值为替换后的策略
        total_price: 最优方案的总价格
        """
        # 检查初始方案是否满足资源约束
        initial_aircraft_usage = {}
        initial_ammunition_usage = {}
        initial_price = 0
        
        for action in self.actions:
            for strategy in action.strategies:
                aircraft_usage, ammunition_usage = strategy.get_resource_usage()
                initial_price += strategy.price
                
                for aircraft_type, count in aircraft_usage.items():
                    initial_aircraft_usage[aircraft_type] = initial_aircraft_usage.get(aircraft_type, 0) + count
                
                for ammo_type, count in ammunition_usage.items():
                    initial_ammunition_usage[ammo_type] = initial_ammunition_usage.get(ammo_type, 0) + count
        
        # 检查初始方案是否超出资源约束
        resource_exceeded = False
        exceeded_resources = []
        
        for aircraft_type, count in initial_aircraft_usage.items():
            if aircraft_type in aircraft_constraints and count > aircraft_constraints[aircraft_type]:
                resource_exceeded = True
                exceeded_resources.append(f"载机 {aircraft_type}: {count}/{aircraft_constraints[aircraft_type]}")
        
        for ammo_type, count in initial_ammunition_usage.items():
            if ammo_type in ammunition_constraints and count > ammunition_constraints[ammo_type]:
                resource_exceeded = True
                exceeded_resources.append(f"弹药 {ammo_type}: {count}/{ammunition_constraints[ammo_type]}")
        
        if resource_exceeded:
            print("警告: 初始方案已超出资源约束限制:")
            for resource in exceeded_resources:
                print(f"  - {resource}")
            print("尝试寻找满足约束的替换方案...")
        
        # 获取所有可替换策略
        replaceable_strategies = []
        for action in self.actions:
            for strategy in action.strategies:
                if strategy.replaceable and strategy.id in self.replacement_options:
                    replaceable_strategies.append(strategy.id)
        
        # 如果没有可替换策略，直接返回初始方案
        if not replaceable_strategies:
            print("没有可替换的策略，保持原方案不变")
            return {}, initial_price
        
        # 使用遗传算法找出最优替换方案
        best_combination, best_price = self._genetic_algorithm_optimize(
            replaceable_strategies, 
            aircraft_constraints, 
            ammunition_constraints,
            initial_price
        )
        
        # 检查是否找到了满足约束的方案
        if best_price == float('inf'):
            print("无法找到满足所有资源约束的方案。")
            return {}, 0
        else:
            if resource_exceeded:
                # 检查是否真的找到了新的替换方案
                if not best_combination:
                    print("无法找到满足资源约束的替换方案。")
                    return {}, 0
                else:
                    print(f"找到满足资源约束的替换方案，总价格: {best_price}")
                    if best_price < initial_price:
                        print(f"新方案比原方案节省: {initial_price - best_price}")
                    else:
                        print(f"新方案比原方案增加: {best_price - initial_price}")
            else:
                if best_price < initial_price:
                    print(f"找到更优方案，总价格: {best_price}，节省: {initial_price - best_price}")
                else:
                    print("未找到更优方案，保持原方案不变")
        
        return best_combination, best_price
    
    def _genetic_algorithm_optimize(self, replaceable_strategies, aircraft_constraints, ammunition_constraints, initial_price):
        """
        使用遗传算法寻找最优替换方案
        
        参数:
        replaceable_strategies: 可替换策略ID列表
        aircraft_constraints: 载机约束
        ammunition_constraints: 弹药约束
        initial_price: 初始方案总价格
        
        返回:
        best_combination: 最优替换方案
        best_price: 最优方案总价格
        """
        # 遗传算法参数
        population_size = 50  # 种群大小
        generations = 200     # 迭代代数
        mutation_rate = 0.1   # 变异率
        elite_size = 5        # 精英数量
        
        # 初始化种群
        population = self._initialize_population(replaceable_strategies, population_size)
        
        # 记录最优解
        best_individual = None
        best_fitness = float('-inf')
        best_price = float('inf')
        best_combination = {}
        
        # 迭代进化
        for generation in range(generations):
            # 评估种群适应度
            fitness_scores = []
            for individual in population:
                fitness, price, valid = self._evaluate_fitness(individual, replaceable_strategies, aircraft_constraints, ammunition_constraints)
                fitness_scores.append((individual, fitness, price, valid))
            
            # 排序，适应度高的在前面
            fitness_scores.sort(key=lambda x: x[1], reverse=True)
            
            # 更新最优解
            for individual, fitness, price, valid in fitness_scores:
                if valid and price < best_price:
                    best_individual = individual
                    best_fitness = fitness
                    best_price = price
                    best_combination = self._decode_individual(individual, replaceable_strategies)
            
            # 如果已经找到满足约束的解，且价格低于初始方案，可以提前结束
            if best_price < initial_price and generation > 10:
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
        
        # 如果没有找到满足约束的解，返回空方案
        if best_price == float('inf'):
            return {}, float('inf')
        
        return best_combination, best_price
    
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
    
    def _evaluate_fitness(self, individual, replaceable_strategies, aircraft_constraints, ammunition_constraints):
        """
        评估个体的适应度
        
        参数:
        individual: 个体（染色体）
        replaceable_strategies: 可替换策略ID列表
        aircraft_constraints: 载机约束
        ammunition_constraints: 弹药约束
        
        返回:
        fitness: 适应度分数
        price: 总价格
        valid: 是否满足约束
        """
        # 解码个体，获取替换方案
        combination = self._decode_individual(individual, replaceable_strategies)
        
        # 计算资源使用情况和总价格
        aircraft_usage = {}
        ammunition_usage = {}
        total_price = 0
        
        for action in self.actions:
            for strategy in action.strategies:
                # 如果策略被替换，使用替换后的策略
                if strategy.replaceable and strategy.id in combination:
                    strategy_to_use = combination[strategy.id]
                else:
                    strategy_to_use = strategy
                
                # 累加价格
                total_price += strategy_to_use.price
                
                # 累加资源使用
                aircraft_usage_part, ammunition_usage_part = strategy_to_use.get_resource_usage()
                for aircraft_type, count in aircraft_usage_part.items():
                    aircraft_usage[aircraft_type] = aircraft_usage.get(aircraft_type, 0) + count
                
                for ammo_type, count in ammunition_usage_part.items():
                    ammunition_usage[ammo_type] = ammunition_usage.get(ammo_type, 0) + count
        
        # 检查是否满足约束
        valid = True
        constraint_violation = 0
        
        for aircraft_type, count in aircraft_usage.items():
            if aircraft_type in aircraft_constraints and count > aircraft_constraints[aircraft_type]:
                valid = False
                constraint_violation += count - aircraft_constraints[aircraft_type]
        
        for ammo_type, count in ammunition_usage.items():
            if ammo_type in ammunition_constraints and count > ammunition_constraints[ammo_type]:
                valid = False
                constraint_violation += count - ammunition_constraints[ammo_type]
        
        # 计算适应度
        # 如果方案有效，适应度为价格的负值（价格越低适应度越高）
        # 如果方案无效，适应度为一个很大的负值减去约束违反程度
        if valid:
            fitness = -total_price
        else:
            fitness = -1000000 - constraint_violation * 10000
        
        return fitness, total_price, valid
    
    def _selection(self, fitness_scores):
        """
        使用轮盘赌选择一个个体
        
        参数:
        fitness_scores: 包含(individual, fitness, price, valid)元组的列表
        
        返回:
        selected_individual: 被选中的个体
        """
        # 计算适应度总和（只考虑正值，负值设为0）
        total_fitness = sum(max(0.01, fs[1] + 1000000) for fs in fitness_scores)
        
        # 生成随机值
        r = random.uniform(0, total_fitness)
        
        # 轮盘赌选择
        current_sum = 0
        for individual, fitness, _, _ in fitness_scores:
            current_sum += max(0.01, fitness + 1000000)
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
                    print(f"警告: 策略 {strategy_id} 未在策略列表中定义")
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
        print(f"加载测试用例 {file_path} 时出错: {e}")
        return None, None, None

# 运行单个测试用例
def run_test_case(file_path):
    """
    运行单个测试用例
    
    参数:
    file_path: 测试用例文件路径
    """
    print(f"\n运行测试用例: {os.path.basename(file_path)}")
    print("-" * 50)
    
    action_list, aircraft_constraints, ammunition_constraints = load_test_case(file_path)
    if not action_list or not aircraft_constraints or not ammunition_constraints:
        print(f"无法加载测试用例: {file_path}")
        return
    
    # 优化
    best_combination, total_price = action_list.optimize(aircraft_constraints, ammunition_constraints)
    
    # 打印原始策略
    print("\n原始策略:")
    for action in action_list.actions:
        print(f"行动 {action.id}:")
        for strategy in action.strategies:
            print(f"  - {strategy}")
    
    # 打印最优替换方案
    print("\n最优替换方案:")
    print(f"总价格: {total_price}")
    
    for action in action_list.actions:
        print(f"行动 {action.id}:")
        for strategy in action.strategies:
            if strategy.replaceable and strategy.id in best_combination:
                replacement = best_combination[strategy.id]
                print(f"  - 策略 {strategy.id} 替换为 {replacement.id} (价格: {replacement.price})")
            else:
                print(f"  - {strategy} {'(不可替换)' if not strategy.replaceable else '(未替换)'}")
    
    # 打印资源使用情况
    print("\n资源使用情况:")
    total_aircraft_usage = {}
    total_ammunition_usage = {}
    
    for action in action_list.actions:
        for strategy in action.strategies:
            if strategy.replaceable and strategy.id in best_combination:
                strategy = best_combination[strategy.id]
            
            aircraft_usage, ammunition_usage = strategy.get_resource_usage()
            
            for aircraft_type, count in aircraft_usage.items():
                total_aircraft_usage[aircraft_type] = total_aircraft_usage.get(aircraft_type, 0) + count
            
            for ammo_type, count in ammunition_usage.items():
                total_ammunition_usage[ammo_type] = total_ammunition_usage.get(ammo_type, 0) + count
    
    print("载机使用:")
    for aircraft_type, count in total_aircraft_usage.items():
        print(f"  - {aircraft_type}: {count}/{aircraft_constraints.get(aircraft_type, '无限制')}")
    
    print("弹药使用:")
    for ammo_type, count in total_ammunition_usage.items():
        print(f"  - {ammo_type}: {count}/{ammunition_constraints.get(ammo_type, '无限制')}")
    
    print("-" * 50)

# 主函数
def main():
    """
    主函数，运行所有测试用例
    """
    test_case_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'testcases')
    test_case_files = glob.glob(os.path.join(test_case_dir, '*.json'))
    
    if not test_case_files:
        print(f"未找到测试用例文件，请确保 {test_case_dir} 目录下有 .json 文件")
        return
    
    print(f"找到 {len(test_case_files)} 个测试用例文件")
    
    for file_path in test_case_files:
        run_test_case(file_path)

# 运行测试
if __name__ == "__main__":
    main()
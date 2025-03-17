# 策略优化算法实现
import json
import os
import glob

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
        优化作战行动清单，找出在资源约束下总价格最低的替换方案
        
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
        
        # 使用回溯法找出最优替换方案
        best_combination = {}
        best_price = float('inf')
        solution_found = False

        def backtrack(index, current_combination, current_aircraft_usage, current_ammunition_usage):
            nonlocal best_combination, best_price

            # 如果已经处理完所有可替换策略，检查是否是更优解
            if index == len(replaceable_strategies):
                # 计算当前组合的总价格
                total_price = 0
                for action in self.actions:
                    for strategy in action.strategies:
                        if strategy.replaceable and strategy.id in current_combination:
                            total_price += current_combination[strategy.id].price
                        else:
                            total_price += strategy.price

                # 如果价格更低，更新最优解
                if total_price < best_price:
                    best_price = total_price
                    best_combination = current_combination.copy()
                return

            # 获取当前处理的策略ID
            strategy_id = replaceable_strategies[index]

            # 尝试不替换当前策略
            original_strategy = None
            for action in self.actions:
                for strategy in action.strategies:
                    if strategy.id == strategy_id:
                        original_strategy = strategy
                        break
                if original_strategy:
                    break

            # 检查不替换是否满足资源约束
            aircraft_usage, ammunition_usage = original_strategy.get_resource_usage()
            new_aircraft_usage = current_aircraft_usage.copy()
            new_ammunition_usage = current_ammunition_usage.copy()

            # 更新资源使用情况
            for aircraft_type, count in aircraft_usage.items():
                new_aircraft_usage[aircraft_type] = new_aircraft_usage.get(aircraft_type, 0) + count

            for ammo_type, count in ammunition_usage.items():
                new_ammunition_usage[ammo_type] = new_ammunition_usage.get(ammo_type, 0) + count

            # 检查是否满足约束
            valid = True
            for aircraft_type, count in new_aircraft_usage.items():
                if aircraft_type in aircraft_constraints and count > aircraft_constraints[aircraft_type]:
                    valid = False
                    break

            if valid:
                for ammo_type, count in new_ammunition_usage.items():
                    if ammo_type in ammunition_constraints and count > ammunition_constraints[ammo_type]:
                        valid = False
                        break

            if valid:
                # 不替换，继续处理下一个策略
                backtrack(index + 1, current_combination, new_aircraft_usage, new_ammunition_usage)

            # 尝试替换当前策略
            for replacement in self.replacement_options[strategy_id]:
                # 检查替换是否满足资源约束
                aircraft_usage, ammunition_usage = replacement.get_resource_usage()
                new_aircraft_usage = current_aircraft_usage.copy()
                new_ammunition_usage = current_ammunition_usage.copy()

                # 更新资源使用情况
                for aircraft_type, count in aircraft_usage.items():
                    new_aircraft_usage[aircraft_type] = new_aircraft_usage.get(aircraft_type, 0) + count

                for ammo_type, count in ammunition_usage.items():
                    new_ammunition_usage[ammo_type] = new_ammunition_usage.get(ammo_type, 0) + count

                # 检查是否满足约束
                valid = True
                for aircraft_type, count in new_aircraft_usage.items():
                    if aircraft_type in aircraft_constraints and count > aircraft_constraints[aircraft_type]:
                        valid = False
                        break

                if valid:
                    for ammo_type, count in new_ammunition_usage.items():
                        if ammo_type in ammunition_constraints and count > ammunition_constraints[ammo_type]:
                            valid = False
                            break

                if valid:
                    # 替换，继续处理下一个策略
                    current_combination[strategy_id] = replacement
                    backtrack(index + 1, current_combination, new_aircraft_usage, new_ammunition_usage)
                    # 回溯
                    if strategy_id in current_combination:
                        del current_combination[strategy_id]

        # 开始回溯
        backtrack(0, {}, {}, {})
        
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

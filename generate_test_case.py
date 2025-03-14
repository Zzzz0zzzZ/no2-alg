import json
import random
import argparse
import sys
from typing import Dict, List, Tuple, Any

def generate_test_case(num_actions: int,
                     strategies_per_action: Dict[str, Tuple[int, int]],
                     replacements_per_strategy: Dict[str, int],
                     aircraft_types: List[str],
                     ammunition_types: List[str],
                     aircraft_count_range: Tuple[int, int],
                     ammunition_count_range: Tuple[int, int],
                     aircraft_price_range: Tuple[int, int],
                     ammunition_price_range: Tuple[int, int],
                     output_file: str):
    """
    生成测试样例并保存为JSON文件
    
    参数:
    num_actions: 行动数量
    strategies_per_action: 每个行动的策略数量，格式为 {action_id: (可变策略数, 不可变策略数)}
    replacements_per_strategy: 每个可变策略的替换策略数量，格式为 {strategy_id: 替换数量}
    aircraft_types: 载机类型列表
    ammunition_types: 弹药类型列表
    aircraft_count_range: 载机数量范围 (最小值, 最大值)
    ammunition_count_range: 弹药数量范围 (最小值, 最大值)
    aircraft_price_range: 载机价格范围 (最小值, 最大值)
    ammunition_price_range: 弹药价格范围 (最小值, 最大值)
    output_file: 输出文件路径
    """
    # 初始化数据结构
    test_case = {
        "strategies": {},
        "actions": {},
        "replacement_options": {},
        "constraints": {
            "aircraft": {},
            "ammunition": {}
        }
    }
    
    # 策略ID计数器
    strategy_id_counter = 1
    replacement_id_counter = 1  # 用字母作为替换策略的ID
    
    # 行动到策略的映射
    action_to_strategies = {}
    
    # 可变策略列表（用于后续添加替换选项）
    replaceable_strategies = []
    
    # 生成行动和策略
    for action_idx in range(1, num_actions + 1):
        action_id = str(action_idx)
        action_to_strategies[action_id] = []
        
        # 获取当前行动的策略配置
        replaceable_count, non_replaceable_count = strategies_per_action.get(
            action_id, (1, 1))  # 默认每个行动1个可变策略和1个不可变策略
        
        # 生成不可变策略
        for _ in range(non_replaceable_count):
            strategy_id = str(strategy_id_counter)
            strategy_id_counter += 1
            
            # 生成策略内容
            strategy = generate_strategy(strategy_id, False, aircraft_types, ammunition_types,
                                        aircraft_count_range, ammunition_count_range,
                                        aircraft_price_range, ammunition_price_range)
            
            test_case["strategies"][strategy_id] = strategy
            action_to_strategies[action_id].append(strategy_id)
        
        # 生成可变策略
        for _ in range(replaceable_count):
            strategy_id = str(strategy_id_counter)
            strategy_id_counter += 1
            
            # 生成策略内容
            strategy = generate_strategy(strategy_id, True, aircraft_types, ammunition_types,
                                        aircraft_count_range, ammunition_count_range,
                                        aircraft_price_range, ammunition_price_range)
            
            test_case["strategies"][strategy_id] = strategy
            action_to_strategies[action_id].append(strategy_id)
            replaceable_strategies.append(strategy_id)
    
    # 设置行动
    for action_id, strategy_ids in action_to_strategies.items():
        test_case["actions"][action_id] = strategy_ids
    
    # 生成替换选项
    for strategy_id in replaceable_strategies:
        # 获取当前策略的替换数量
        replacement_count = replacements_per_strategy.get(strategy_id, random.randint(1, 3))
        
        if replacement_count > 0:
            replacement_ids = []
            
            # 生成替换策略
            for _ in range(replacement_count):
                replacement_id = chr(96 + replacement_id_counter)  # 从'a'开始的字母
                replacement_id_counter += 1
                
                # 生成替换策略内容
                replacement = generate_strategy(replacement_id, False, aircraft_types, ammunition_types,
                                              aircraft_count_range, ammunition_count_range,
                                              aircraft_price_range, ammunition_price_range)
                
                test_case["strategies"][replacement_id] = replacement
                replacement_ids.append(replacement_id)
            
            test_case["replacement_options"][strategy_id] = replacement_ids
    
    # 生成约束条件
    # 计算所有策略中使用的资源总量，并设置略高于此值的约束
    aircraft_usage = {}
    ammunition_usage = {}
    
    for strategy in test_case["strategies"].values():
        for aircraft_type, (count, _) in strategy["aircraft"].items():
            aircraft_usage[aircraft_type] = aircraft_usage.get(aircraft_type, 0) + count
        
        for ammo_type, (count, _) in strategy["ammunition"].items():
            ammunition_usage[ammo_type] = ammunition_usage.get(ammo_type, 0) + count
    
    # 设置约束（略高于使用量的1.2-1.5倍）
    for aircraft_type, usage in aircraft_usage.items():
        test_case["constraints"]["aircraft"][aircraft_type] = int(usage * random.uniform(1.2, 1.5))
    
    for ammo_type, usage in ammunition_usage.items():
        test_case["constraints"]["ammunition"][ammo_type] = int(usage * random.uniform(1.2, 1.5))
    
    # 保存到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(test_case, f, ensure_ascii=False, indent=2)
    
    print(f"测试样例已生成并保存到: {output_file}")
    return test_case

def generate_strategy(strategy_id: str, replaceable: bool, 
                     aircraft_types: List[str], ammunition_types: List[str],
                     aircraft_count_range: Tuple[int, int],
                     ammunition_count_range: Tuple[int, int],
                     aircraft_price_range: Tuple[int, int],
                     ammunition_price_range: Tuple[int, int]) -> Dict[str, Any]:
    """
    生成单个策略的内容
    """
    # 选择2种载机类型（如果可用）
    selected_aircraft = random.sample(aircraft_types, min(2, len(aircraft_types)))
    
    # 选择2种弹药类型（如果可用）
    selected_ammunition = random.sample(ammunition_types, min(2, len(ammunition_types)))
    
    # 生成载机配置
    aircraft = {}
    for ac_type in selected_aircraft:
        count = random.randint(aircraft_count_range[0], aircraft_count_range[1])
        price = random.randint(aircraft_price_range[0], aircraft_price_range[1])
        aircraft[ac_type] = [count, price]
    
    # 生成弹药配置
    ammunition = {}
    for ammo_type in selected_ammunition:
        count = random.randint(ammunition_count_range[0], ammunition_count_range[1])
        price = random.randint(ammunition_price_range[0], ammunition_price_range[1])
        ammunition[ammo_type] = [count, price]
    
    return {
        "replaceable": replaceable,
        "aircraft": aircraft,
        "ammunition": ammunition
    }

def main():
    parser = argparse.ArgumentParser(description='生成策略优化测试样例')
    parser.add_argument('--num-actions', type=int, default=2, help='行动数量')
    parser.add_argument('--output', type=str, default='./testcases/test_case_generated.json', help='输出文件路径')
    
    # 高级选项
    parser.add_argument('--aircraft-types', type=str, default='A型,B型,C型', help='载机类型，逗号分隔')
    parser.add_argument('--ammunition-types', type=str, default='导弹X,炸弹Y,炸弹Z', help='弹药类型，逗号分隔')
    parser.add_argument('--aircraft-count', type=str, default='1,3', help='载机数量范围，格式为min,max')
    parser.add_argument('--ammunition-count', type=str, default='1,5', help='弹药数量范围，格式为min,max')
    parser.add_argument('--aircraft-price', type=str, default='1000,3000', help='载机价格范围，格式为min,max')
    parser.add_argument('--ammunition-price', type=str, default='300,500', help='弹药价格范围，格式为min,max')
    
    args = parser.parse_args()
    
    # 解析范围参数
    aircraft_count_range = tuple(map(int, args.aircraft_count.split(',')))
    ammunition_count_range = tuple(map(int, args.ammunition_count.split(',')))
    aircraft_price_range = tuple(map(int, args.aircraft_price.split(',')))
    ammunition_price_range = tuple(map(int, args.ammunition_price.split(',')))
    
    # 解析类型列表
    aircraft_types = args.aircraft_types.split(',')
    ammunition_types = args.ammunition_types.split(',')
    
    # 默认每个行动有1个可变策略和2个不可变策略
    strategies_per_action = {}
    for i in range(1, args.num_actions + 1):
        strategies_per_action[str(i)] = (2, 3)  # (可变策略数, 不可变策略数)
    
    # 默认每个可变策略有2个替换选项
    replacements_per_strategy = {}
    
    # 生成测试样例
    generate_test_case(
        args.num_actions,
        strategies_per_action,
        replacements_per_strategy,
        aircraft_types,
        ammunition_types,
        aircraft_count_range,
        ammunition_count_range,
        aircraft_price_range,
        ammunition_price_range,
        args.output
    )

# 交互式配置生成测试样例
def interactive_generate():
    print("=== 策略优化测试样例生成器 ===")
    print("请按照提示输入参数，生成自定义测试样例")
    
    # 基本参数
    num_actions = int(input("请输入行动数量: "))
    output_file = input("请输入输出文件路径 (默认: test_case_generated.json): ") or "test_case_generated.json"
    
    # 载机和弹药类型
    aircraft_types_input = input("请输入载机类型，用逗号分隔 (默认: A型,B型,C型): ") or "A型,B型,C型"
    ammunition_types_input = input("请输入弹药类型，用逗号分隔 (默认: 导弹X,炸弹Y,炸弹Z): ") or "导弹X,炸弹Y,炸弹Z"
    
    aircraft_types = aircraft_types_input.split(',')
    ammunition_types = ammunition_types_input.split(',')
    
    # 数量和价格范围
    aircraft_count_input = input("请输入载机数量范围，格式为min,max (默认: 1,3): ") or "1,3"
    ammunition_count_input = input("请输入弹药数量范围，格式为min,max (默认: 1,5): ") or "1,5"
    aircraft_price_input = input("请输入载机价格范围，格式为min,max (默认: 1000,3000): ") or "1000,3000"
    ammunition_price_input = input("请输入弹药价格范围，格式为min,max (默认: 300,500): ") or "300,500"
    
    aircraft_count_range = tuple(map(int, aircraft_count_input.split(',')))
    ammunition_count_range = tuple(map(int, ammunition_count_input.split(',')))
    aircraft_price_range = tuple(map(int, aircraft_price_input.split(',')))
    ammunition_price_range = tuple(map(int, ammunition_price_input.split(',')))
    
    # 每个行动的策略配置
    strategies_per_action = {}
    print("\n为每个行动配置策略数量:")
    for i in range(1, num_actions + 1):
        print(f"\n行动 {i}:")
        replaceable = int(input(f"  可变策略数量 (默认: 1): ") or "1")
        non_replaceable = int(input(f"  不可变策略数量 (默认: 2): ") or "2")
        strategies_per_action[str(i)] = (replaceable, non_replaceable)
    
    # 计算可变策略的总数
    total_replaceable = sum(count for count, _ in strategies_per_action.values())
    
    # 为每个可变策略配置替换选项
    replacements_per_strategy = {}
    if total_replaceable > 0:
        print("\n为可变策略配置替换选项:")
        strategy_id = 1
        for action_id, (replaceable_count, _) in strategies_per_action.items():
            for i in range(replaceable_count):
                current_strategy_id = str(strategy_id)
                strategy_id += 1
                print(f"\n行动 {action_id} 中的可变策略 {current_strategy_id}:")
                replacement_count = int(input(f"  替换策略数量 (默认: 2): ") or "2")
                replacements_per_strategy[current_strategy_id] = replacement_count
    
    # 生成测试样例
    generate_test_case(
        num_actions,
        strategies_per_action,
        replacements_per_strategy,
        aircraft_types,
        ammunition_types,
        aircraft_count_range,
        ammunition_count_range,
        aircraft_price_range,
        ammunition_price_range,
        output_file
    )
    
    print("\n测试样例生成完成！")

if __name__ == "__main__":
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        main()  # 使用命令行参数
    else:
        # 没有命令行参数，使用交互式模式
        interactive_generate()
#!/usr/bin/env python
# coding=utf-8

from strategy_filter import generate_army_specific_strategies
import json
import os

def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 设置文件路径 - 现在只需要test_case_3.json一个文件
    test_case_path = os.path.join(current_dir, 'test_case_3.json')
    output_path = os.path.join(current_dir, 'test_case_3_filtered.json')
    
    # 执行策略初筛
    print("开始执行策略初筛...")
    result = generate_army_specific_strategies(test_case_path, output_path)
    print("策略初筛完成！")
    
    # 输出统计信息
    print("\n==== 统计信息 ====")
    print(f"策略总数: {len(result['strategies'])}")
    
    # 检查策略资源是否都包含army信息
    all_resources_have_army = True
    strategy_by_army = {}  # 记录每个军队的策略数量
    replaceable_count = 0  # 记录可替换策略数量
    non_replaceable_count = 0  # 记录不可替换策略数量
    
    # 检查约束资源
    print("\n==== 约束资源检查 ====")
    aircraft_count = len(result['constraints']['aircraft'])
    ammunition_count = len(result['constraints']['ammunition'])
    print(f"约束中的飞机类型数量: {aircraft_count}")
    print(f"约束中的弹药类型数量: {ammunition_count}")
    
    # 检查资源名称中是否都包含军队信息
    aircraft_with_army = sum(1 for name in result['constraints']['aircraft'] if '-army' in name)
    ammunition_with_army = sum(1 for name in result['constraints']['ammunition'] if '-army' in name)
    
    print(f"带有军队信息的飞机类型数量: {aircraft_with_army} ({(aircraft_with_army/aircraft_count)*100 if aircraft_count else 0:.1f}%)")
    print(f"带有军队信息的弹药类型数量: {ammunition_with_army} ({(ammunition_with_army/ammunition_count)*100 if ammunition_count else 0:.1f}%)")
    
    # 遍历所有策略，检查其军队信息、资源信息和可替换属性
    for strategy_id, strategy in result['strategies'].items():
        # 检查格式是否为策略ID-army格式（至少包含一个连字符）
        parts = strategy_id.split('-')
        if len(parts) < 2:
            print(f"警告: 策略 {strategy_id} 没有army信息")
            continue
            
        # 提取军队ID（最后一部分是军队ID）
        army_id = parts[-1]
        strategy_by_army[army_id] = strategy_by_army.get(army_id, 0) + 1
        
        # 统计可替换和不可替换的策略
        if strategy.get('replaceable', False):
            replaceable_count += 1
        else:
            non_replaceable_count += 1
        
        # 检查策略中的资源名称是否包含军队信息
        has_resources_without_army = False
        
        # 检查飞机资源名称
        for aircraft_name in strategy['aircraft']:
            if '-army' not in aircraft_name:
                has_resources_without_army = True
                print(f"警告: 策略 {strategy_id} 的飞机资源 {aircraft_name} 没有army信息")
        
        # 检查弹药资源名称
        for ammo_name in strategy['ammunition']:
            if '-army' not in ammo_name:
                has_resources_without_army = True
                print(f"警告: 策略 {strategy_id} 的弹药资源 {ammo_name} 没有army信息")
        
        if has_resources_without_army:
            all_resources_have_army = False
    
    if all_resources_have_army:
        print("\n所有策略中的资源名称都包含army信息 ✓")
    
    print(f"\n可替换策略数量: {replaceable_count}")
    print(f"不可替换策略数量: {non_replaceable_count}")
    
    # 输出每个军队的策略数量
    print("\n各军队的策略数量:")
    for army_id, count in sorted(strategy_by_army.items()):
        print(f"  {army_id}: {count}个策略")
    
    # 检查替换选项
    print("\n==== 替换选项信息 ====")
    replacement_counts = {}  # 记录每个策略的替换选项数量
    same_strategy_different_army_counts = {}  # 记录每个策略不同军队版本的替换选项数量
    
    # 遍历所有替换选项
    for strategy_id, options in result['replacement_options'].items():
        # 检查策略ID是否包含军队信息
        parts = strategy_id.split('-')
        if len(parts) < 2:
            print(f"警告: 替换选项中的策略 {strategy_id} 没有army信息")
            continue
            
        # 提取策略基本ID（不含军队信息）和军队ID
        base_strategy_id = '-'.join(parts[:-1])  # 获取不带army的策略ID
        army_id = parts[-1]
        
        # 统计替换选项数量（options现在是一个数组）
        replacement_count = len(options)
        replacement_counts[strategy_id] = replacement_count
        
        # 分析替换选项类型（同一策略不同军队 vs 不同策略）
        same_strategy_count = 0  # 同一策略不同军队的数量
        different_strategy_count = 0  # 不同策略的数量
        
        # 遍历所有替换选项
        for replacement_id in options:
            # 检查替换选项是否包含军队信息
            replacement_parts = replacement_id.split('-')
            if len(replacement_parts) < 2:
                print(f"  警告: 替换策略 {replacement_id} 没有army信息")
                continue
                
            # 提取替换策略的基本ID（不含军队信息）
            replacement_base_id = '-'.join(replacement_parts[:-1])
            
            # 判断替换选项是否是同一策略的不同军队版本
            if replacement_base_id == base_strategy_id:
                same_strategy_count += 1
            else:
                different_strategy_count += 1
        
        # 记录同一策略不同军队的替换选项数量
        same_strategy_different_army_counts[strategy_id] = same_strategy_count
        
        # 输出替换选项统计信息
        print(f"策略 {strategy_id} 有 {replacement_count} 个可替换策略:")
        print(f"  - 同一策略不同军队: {same_strategy_count}个")
        print(f"  - 不同策略: {different_strategy_count}个")
        
    # 输出替换选项总数
    print(f"\n替换选项总数: {len(result['replacement_options'])}")
    
    # 计算每个策略平均有多少替换选项
    if replacement_counts:
        avg_replacements = sum(replacement_counts.values()) / len(replacement_counts)
        print(f"平均每个策略有 {avg_replacements:.2f} 个替换选项")
    
    # 计算有多少策略包含同一策略不同军队的替换选项
    strategies_with_same_different_army = sum(1 for count in same_strategy_different_army_counts.values() if count > 0)
    print(f"有 {strategies_with_same_different_army} 个策略包含同一策略不同军队的替换选项")
    
    # 检查行动列表
    print("\n==== 行动列表 ====")
    for action_id, strategy_ids in result['actions'].items():
        print(f"行动 {action_id} 包含 {len(strategy_ids)} 个策略")
        
        # 检查行动中的策略是否都有army信息
        all_actions_have_army = True
        for strategy_id in strategy_ids:
            parts = strategy_id.split('-')
            if len(parts) < 2:
                all_actions_have_army = False
                print(f"  警告: 行动中的策略 {strategy_id} 没有army信息")
        
        if all_actions_have_army:
            print(f"  所有行动中的策略都包含army信息 ✓")
            
    # 保存一个简化版的结果文件，方便查看
    simplified_result = {
        "strategies_count": len(result['strategies']),
        "actions_count": len(result['actions']),
        "replacement_options_count": len(result['replacement_options']),
        "replaceable_strategies_count": replaceable_count,
        "non_replaceable_strategies_count": non_replaceable_count,
        "aircraft_types_count": aircraft_count,
        "ammunition_types_count": ammunition_count,
        "sample_strategies": {},
        "sample_replacement": {},
        "sample_constraints": {
            "aircraft": dict(list(result['constraints']['aircraft'].items())[:5]),
            "ammunition": dict(list(result['constraints']['ammunition'].items())[:5])
        }
    }
    
    # 添加一些示例策略
    sample_count = 0
    for strategy_id, strategy in result['strategies'].items():
        if sample_count < 3:  # 只显示前3个策略
            simplified_result["sample_strategies"][strategy_id] = strategy
            sample_count += 1
    
    # 添加一些示例替换选项
    sample_count = 0
    for strategy_id, options in result['replacement_options'].items():
        if sample_count < 3:  # 只显示前3个替换选项
            simplified_result["sample_replacement"][strategy_id] = options
            sample_count += 1
    
    # 保存简化结果
    simplified_path = os.path.join(current_dir, 'test_case_3_summary.json')
    with open(simplified_path, 'w', encoding='utf-8') as f:
        json.dump(simplified_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n简化的统计结果已保存到 {simplified_path}")

if __name__ == "__main__":
    main()
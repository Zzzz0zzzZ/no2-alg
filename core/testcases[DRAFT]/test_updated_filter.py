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
    
    # 设置文件路径
    test_case_path = os.path.join(current_dir, 'test_case_3.json')
    armys_path = os.path.join(current_dir, 'armys.json')
    output_path = os.path.join(current_dir, 'test_case_3_filtered.json')
    
    # 执行策略初筛
    print("开始执行策略初筛...")
    result = generate_army_specific_strategies(test_case_path, armys_path, output_path)
    print("策略初筛完成！")
    
    # 输出统计信息
    print("\n==== 统计信息 ====")
    print(f"策略总数: {len(result['strategies'])}")
    
    # 检查策略是否都包含army信息
    all_have_army = True
    strategy_by_army = {}
    
    for strategy_id in result['strategies'].keys():
        if '-army' not in strategy_id:
            all_have_army = False
            print(f"警告: 策略 {strategy_id} 没有army信息")
        else:
            army_id = strategy_id.split('-')[-1]
            strategy_by_army[army_id] = strategy_by_army.get(army_id, 0) + 1
    
    if all_have_army:
        print("所有策略都包含army信息 ✓")
    
    # 输出每个军队的策略数量
    print("\n各军队的策略数量:")
    for army_id, count in sorted(strategy_by_army.items()):
        print(f"  {army_id}: {count}个策略")
    
    # 检查替换选项
    print("\n==== 替换选项信息 ====")
    replacement_counts = {}
    same_strategy_different_army_counts = {}
    
    for strategy_id, options in result['replacement_options'].items():
        if '-army' not in strategy_id:
            print(f"警告: 替换选项中的策略 {strategy_id} 没有army信息")
            continue
            
        base_strategy_id = strategy_id.rsplit('-', 1)[0]  # 获取不带army的策略ID
        army_id = strategy_id.split('-')[-1]
        
        # 统计替换选项数量
        replacement_count = len(options['可替换策略'])
        replacement_counts[strategy_id] = replacement_count
        
        # 统计同一策略不同军队的替换选项数量
        same_strategy_count = 0
        different_strategy_count = 0
        
        for replacement_id in options['可替换策略']:
            if '-army' not in replacement_id:
                print(f"  警告: 替换策略 {replacement_id} 没有army信息")
                continue
                
            replacement_base_id = replacement_id.rsplit('-', 1)[0]
            
            if replacement_base_id == base_strategy_id:
                same_strategy_count += 1
            else:
                different_strategy_count += 1
        
        same_strategy_different_army_counts[strategy_id] = same_strategy_count
        
        print(f"策略 {strategy_id} 有 {replacement_count} 个可替换策略:")
        print(f"  - 同一策略不同军队: {same_strategy_count}个")
        print(f"  - 不同策略: {different_strategy_count}个")
        
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
            if '-army' not in strategy_id:
                all_actions_have_army = False
                print(f"  警告: 行动中的策略 {strategy_id} 没有army信息")
        
        if all_actions_have_army:
            print(f"  所有行动中的策略都包含army信息 ✓")
            
    # 保存一个简化版的结果文件，方便查看
    simplified_result = {
        "strategies_count": len(result['strategies']),
        "actions_count": len(result['actions']),
        "replacement_options_count": len(result['replacement_options']),
        "sample_replacement": {}
    }
    
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
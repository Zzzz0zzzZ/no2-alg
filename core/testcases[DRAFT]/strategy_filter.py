#!/usr/bin/env python
# coding=utf-8

import json
import copy
import os

def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json_file(data, file_path):
    """保存JSON文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def check_strategy_feasible_for_army(strategy, army):
    """检查策略是否可以由指定的军队完成"""
    # 检查飞机资源是否满足
    for aircraft_type, count_price in strategy['aircraft'].items():
        required_count = count_price[0]
        # 检查军队是否有这种飞机
        if aircraft_type not in army['aircraft']:
            return False
        # 检查数量是否足够
        if army['aircraft'][aircraft_type]['数量'] < required_count:
            return False
    
    # 检查弹药资源是否满足
    for ammo_type, count_price in strategy['ammunition'].items():
        required_count = count_price[0]
        # 检查军队是否有这种弹药
        if ammo_type not in army['ammunition']:
            return False
        # 检查数量是否足够
        if army['ammunition'][ammo_type]['数量'] < required_count:
            return False
    
    # 所有资源检查通过，策略可行
    return True

def generate_army_specific_strategies(test_case_path, armys_path, output_path):
    """生成基于军队的特定策略"""
    # 加载测试用例和军队数据
    test_case = load_json_file(test_case_path)
    armys = load_json_file(armys_path)
    
    # 创建新测试用例的副本（但只保留部分结构）
    new_test_case = {
        "strategies": {},
        "actions": {},
        "replacement_options": {},
        "constraints": copy.deepcopy(test_case['constraints'])
    }
    
    # 存储新创建的策略ID映射
    new_strategy_ids = {}  # 原始ID -> [新ID列表]
    
    # 记录替换选项中的策略对应的初始军队
    strategy_to_army_init = {}
    for strategy_id, options in test_case['replacement_options'].items():
        strategy_to_army_init[strategy_id] = options['army_init']
    
    # 第一步：为每个策略创建特定军队版本
    for strategy_id, strategy in test_case['strategies'].items():
        new_strategy_ids[strategy_id] = []
        
        # 如果这个策略是可替换策略的初始策略，使用指定的初始军队
        if strategy_id in strategy_to_army_init:
            army_init = strategy_to_army_init[strategy_id]
            army = armys[army_init]
            
            # 检查策略是否可以由指定的初始军队完成
            if check_strategy_feasible_for_army(strategy, army):
                new_strategy_id = f"{strategy_id}-{army_init}"
                new_strategy_ids[strategy_id].append(new_strategy_id)
                
                # 创建新策略并添加到新测试用例中
                new_strategy = copy.deepcopy(strategy)
                new_test_case['strategies'][new_strategy_id] = new_strategy
            
        # 遍历其他所有军队
        for army_id, army in armys.items():
            # 如果是初始军队且已经处理过，则跳过
            if strategy_id in strategy_to_army_init and army_id == strategy_to_army_init[strategy_id]:
                continue
                
            # 检查策略是否可以由该军队完成
            if check_strategy_feasible_for_army(strategy, army):
                new_strategy_id = f"{strategy_id}-{army_id}"
                new_strategy_ids[strategy_id].append(new_strategy_id)
                
                # 创建新策略并添加到新测试用例中
                new_strategy = copy.deepcopy(strategy)
                new_test_case['strategies'][new_strategy_id] = new_strategy
    
    # 第二步：更新行动列表，只使用带有army信息的策略
    for action_id, strategy_ids in test_case['actions'].items():
        new_test_case['actions'][action_id] = []
        for strategy_id in strategy_ids:
            if strategy_id in new_strategy_ids and new_strategy_ids[strategy_id]:
                # 对于每个行动中的策略，如果是初始策略，使用初始军队版本
                if strategy_id in strategy_to_army_init:
                    army_init = strategy_to_army_init[strategy_id]
                    init_strategy_id = f"{strategy_id}-{army_init}"
                    if init_strategy_id in new_test_case['strategies']:
                        new_test_case['actions'][action_id].append(init_strategy_id)
                    else:
                        # 如果初始军队版本不可行，使用第一个可行的军队版本
                        new_test_case['actions'][action_id].append(new_strategy_ids[strategy_id][0])
                else:
                    # 对于非初始策略，使用第一个可行的军队版本
                    new_test_case['actions'][action_id].append(new_strategy_ids[strategy_id][0])
    
    # 第三步：更新替换选项，只使用带有army信息的策略
    for original_strategy_id, options in test_case['replacement_options'].items():
        replacement_ids = options['可替换策略']
        army_init = options['army_init']
        
        # 只为初始策略的初始军队版本创建替换选项
        init_strategy_id = f"{original_strategy_id}-{army_init}"
        
        # 确保这个初始策略的军队特定版本存在
        if init_strategy_id in new_test_case['strategies']:
            new_test_case['replacement_options'][init_strategy_id] = {
                "可替换策略": []
            }
            
            # 添加所有可行的替换策略（带有army信息）
            for replacement_id in replacement_ids:
                if replacement_id in new_strategy_ids:
                    # 添加所有可行的军队特定版本作为替换选项
                    new_test_case['replacement_options'][init_strategy_id]['可替换策略'].extend(
                        new_strategy_ids[replacement_id]
                    )
            
            # 添加原策略的其他军队版本作为替换选项
            for other_version_id in new_strategy_ids[original_strategy_id]:
                # 不要将策略自身添加为替换选项
                if other_version_id != init_strategy_id:
                    new_test_case['replacement_options'][init_strategy_id]['可替换策略'].append(other_version_id)
    
    # 创建输出目录（如果不存在）
    dir_name = os.path.dirname(output_path)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    
    # 保存新测试用例
    save_json_file(new_test_case, output_path)
    
    total_strategies = len(new_test_case['strategies'])
    print(f"生成了 {total_strategies} 个基于军队的策略")
    print(f"结果已保存到 {output_path}")
    
    return new_test_case

def main():
    """主函数"""
    # 路径配置
    test_case_path = 'core/testcases[DRAFT]/test_case_3.json'
    armys_path = 'core/testcases[DRAFT]/armys.json'
    output_path = 'core/testcases[DRAFT]/test_case_3_filtered.json'
    
    # 执行处理
    generate_army_specific_strategies(test_case_path, armys_path, output_path)

if __name__ == "__main__":
    main() 
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

def check_strategy_feasible_for_army(strategy, army, amended_strategy=None, army_id=None):
    """检查策略是否可以由指定的军队完成，并将策略中的资源修改为带有军队信息的版本"""
    # 检查飞机资源是否满足
    for aircraft_type, count_price in strategy['aircraft'].items():
        required_count = count_price[0]
        # 检查军队是否有这种飞机
        if aircraft_type not in army['aircraft']:
            return False
        # 检查数量是否足够
        if army['aircraft'][aircraft_type]['数量'] < required_count:
            return False
        
        # 如果需要修改策略资源名称，添加军队标识
        if amended_strategy is not None:
            # 创建带有军队ID的新资源名称
            # 使用传入的army_id，确保资源名称使用正确的军队ID
            new_aircraft_type = f"{aircraft_type}-{army_id}"
            
            # 在修改后的策略中使用新的资源名称
            if aircraft_type in strategy['aircraft']:
                amended_strategy['aircraft'][new_aircraft_type] = strategy['aircraft'][aircraft_type]
    
    # 检查弹药资源是否满足
    for ammo_type, count_price in strategy['ammunition'].items():
        required_count = count_price[0]
        # 检查军队是否有这种弹药
        if ammo_type not in army['ammunition']:
            return False
        # 检查数量是否足够
        if army['ammunition'][ammo_type]['数量'] < required_count:
            return False
        
        # 如果需要修改策略资源名称，添加军队标识
        if amended_strategy is not None:
            # 创建带有军队ID的新资源名称
            # 使用传入的army_id，确保资源名称使用正确的军队ID
            new_ammo_type = f"{ammo_type}-{army_id}"
            
            # 在修改后的策略中使用新的资源名称
            if ammo_type in strategy['ammunition']:
                amended_strategy['ammunition'][new_ammo_type] = strategy['ammunition'][ammo_type]
    
    # 所有资源检查通过，策略可行
    return True

def generate_resource_constraints(armies):
    """根据军队信息生成资源约束"""
    constraints = {
        "aircraft": {},
        "ammunition": {}
    }
    
    # 遍历所有军队，为每个资源添加军队标识
    for army_id, army in armies.items():
        # 处理飞机资源
        for aircraft_type, details in army['aircraft'].items():
            new_aircraft_type = f"{aircraft_type}-{army_id}"
            constraints["aircraft"][new_aircraft_type] = details['数量']
        
        # 处理弹药资源
        for ammo_type, details in army['ammunition'].items():
            new_ammo_type = f"{ammo_type}-{army_id}"
            constraints["ammunition"][new_ammo_type] = details['数量']
    
    return constraints

def generate_army_specific_strategies(test_case_path, output_path):
    """生成基于军队的特定策略"""
    # 加载测试用例数据
    test_case = load_json_file(test_case_path)
    
    # 从test_case中获取armies信息，而不是从单独的文件加载
    armies = test_case.get('armies', {})
    
    # 创建新测试用例的副本（但只保留部分结构）
    new_test_case = {
        "strategies": {},          # 存储所有策略（带军队信息）
        "actions": {},             # 存储行动列表（引用的是带军队信息的策略）
        "replacement_options": {}, # 存储替换选项（只含可替换策略）
        "constraints": generate_resource_constraints(armies)  # 根据armies信息生成新的约束
    }
    
    # 存储新创建的策略ID映射
    new_strategy_ids = {}  # 原始ID -> [新ID列表]
    
    # 第一步：为每个策略创建特定军队版本
    # 注意：对于不可替换的策略(replaceable=false)，只创建初始军队版本
    for strategy_id, strategy in test_case['strategies'].items():
        new_strategy_ids[strategy_id] = []
        
        # 获取策略的初始军队信息
        army_init = strategy.get('army_init', 'army1')
        is_replaceable = strategy.get('replaceable', False)  # 默认不可替换
        
        # 对于不可替换的策略，只创建初始军队版本
        if not is_replaceable:
            # 检查策略是否可以由指定的初始军队完成
            army = armies.get(army_init, {})
            
            # 创建修改后的策略副本
            new_strategy = copy.deepcopy(strategy)
            new_strategy['aircraft'] = {}  # 清空原始资源
            new_strategy['ammunition'] = {}  # 清空原始资源
            
            if check_strategy_feasible_for_army(strategy, army, new_strategy, army_init):
                # 创建带有军队ID的新策略ID
                new_strategy_id = f"{strategy_id}-{army_init}"
                new_strategy_ids[strategy_id].append(new_strategy_id)
                
                # 移除army_init字段，因为它已经在ID中体现
                if 'army_init' in new_strategy:
                    del new_strategy['army_init']
                
                # 保持replaceable字段为false
                new_strategy['replaceable'] = False
                
                # 添加到新测试用例中
                new_test_case['strategies'][new_strategy_id] = new_strategy
            
        # 对于可替换的策略，创建所有可行的军队版本
        else:
            # 首先，创建初始军队版本
            army = armies.get(army_init, {})
            
            # 创建修改后的策略副本
            new_strategy = copy.deepcopy(strategy)
            new_strategy['aircraft'] = {}  # 清空原始资源
            new_strategy['ammunition'] = {}  # 清空原始资源
            
            if check_strategy_feasible_for_army(strategy, army, new_strategy, army_init):
                # 创建带有军队ID的新策略ID
                new_strategy_id = f"{strategy_id}-{army_init}"
                new_strategy_ids[strategy_id].append(new_strategy_id)
                
                # 移除army_init字段，因为它已经在ID中体现
                if 'army_init' in new_strategy:
                    del new_strategy['army_init']
                
                # 初始军队版本仍然是可替换的
                new_strategy['replaceable'] = True
                
                # 添加到新测试用例中
                new_test_case['strategies'][new_strategy_id] = new_strategy
            
            # 然后，创建其他军队版本
            for other_army_id, other_army in armies.items():
                # 如果是初始军队且已经处理过，则跳过
                if other_army_id == army_init:
                    continue
                
                # 创建修改后的策略副本
                other_new_strategy = copy.deepcopy(strategy)
                other_new_strategy['aircraft'] = {}  # 清空原始资源
                other_new_strategy['ammunition'] = {}  # 清空原始资源
                
                # 检查策略是否可以由该军队完成
                if check_strategy_feasible_for_army(strategy, other_army, other_new_strategy, other_army_id):
                    # 创建带有军队ID的新策略ID
                    new_strategy_id = f"{strategy_id}-{other_army_id}"
                    new_strategy_ids[strategy_id].append(new_strategy_id)
                    
                    # 移除army_init字段，因为它已经在ID中体现
                    if 'army_init' in other_new_strategy:
                        del other_new_strategy['army_init']
                    
                    # 非初始军队版本不可替换
                    other_new_strategy['replaceable'] = False
                    
                    # 添加到新测试用例中
                    new_test_case['strategies'][new_strategy_id] = other_new_strategy
    
    # 第二步：更新行动列表，使用带有army信息的策略
    for action_id, strategy_ids in test_case['actions'].items():
        new_test_case['actions'][action_id] = []
        for strategy_id in strategy_ids:
            if strategy_id in new_strategy_ids and new_strategy_ids[strategy_id]:
                # 获取该策略的初始军队
                strategy = test_case['strategies'][strategy_id]
                army_init = strategy.get('army_init', 'army1')
                init_strategy_id = f"{strategy_id}-{army_init}"
                
                # 优先使用初始军队版本
                if init_strategy_id in new_test_case['strategies']:
                    new_test_case['actions'][action_id].append(init_strategy_id)
                else:
                    # 如果初始军队版本不可行，使用第一个可行的军队版本
                    new_test_case['actions'][action_id].append(new_strategy_ids[strategy_id][0])
    
    # 第三步：更新替换选项，只为可替换策略(replaceable=true)创建替换选项
    for original_strategy_id, replacement_ids in test_case['replacement_options'].items():
        # 确保原策略存在于测试用例中
        if original_strategy_id in test_case['strategies']:
            # 获取原策略信息
            strategy = test_case['strategies'][original_strategy_id]
            army_init = strategy.get('army_init', 'army1')
            
            # 创建原策略的初始军队版本ID
            init_strategy_id = f"{original_strategy_id}-{army_init}"
            
            # 确保这个策略的军队特定版本存在，且该策略是可替换的
            if init_strategy_id in new_test_case['strategies'] and new_test_case['strategies'][init_strategy_id].get('replaceable', False):
                # 创建替换选项数组
                new_test_case['replacement_options'][init_strategy_id] = []
                
                # 添加所有可行的替换策略（带有军队信息）
                for replacement_id in replacement_ids:
                    if replacement_id in new_strategy_ids:
                        # 添加所有可行的军队特定版本作为替换选项
                        new_test_case['replacement_options'][init_strategy_id].extend(
                            new_strategy_ids[replacement_id]
                        )
                
                # 添加原策略的其他军队版本作为替换选项
                for other_version_id in new_strategy_ids[original_strategy_id]:
                    # 不要将策略自身添加为替换选项
                    if other_version_id != init_strategy_id:
                        new_test_case['replacement_options'][init_strategy_id].append(other_version_id)
    
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
    # 路径配置 - 现在只需要test_case_3.json一个文件
    test_case_path = 'core/testcases[DRAFT]/test_case_3.json'
    output_path = 'core/testcases[DRAFT]/test_case_3_filtered.json'
    
    # 执行处理
    generate_army_specific_strategies(test_case_path, output_path)

if __name__ == "__main__":
    main()
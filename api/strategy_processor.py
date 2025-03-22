#!/usr/bin/env python
# coding=utf-8

import json
import copy
import os
from pathlib import Path

# ----------------------------- 核心处理函数 -----------------------------

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
            # 使用传入的army_id创建带有军队ID的新资源名称
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
            # 使用传入的army_id创建带有军队ID的新资源名称
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

def generate_army_specific_strategies(test_case_data, output_path=None):
    """基于输入的TestCaseDTO数据生成特定军队策略
    
    Args:
        test_case_data: TestCaseDTO格式的数据对象或者文件路径
        output_path: 可选，如果需要保存处理结果到文件，则提供输出路径
        
    Returns:
        用于优化的数据结构
    """
    # 处理输入参数 - 支持文件路径或直接数据对象
    if isinstance(test_case_data, str):
        # 如果是文件路径，加载测试用例数据
        test_case = load_json_file(test_case_data)
    else:
        # 如果是数据对象，转换为字典
        if hasattr(test_case_data, 'dict'):
            test_case = test_case_data.dict()
        else:
            test_case = test_case_data
    
    # 从test_case中获取armies信息
    armies = test_case.get('armies', {})
    
    # 创建新测试用例的副本（但只保留部分结构）
    new_test_case = {
        "strategies": {},          # 存储所有策略（带军队信息）
        "actions": {},             # 存储行动列表（引用的是带军队信息的策略）
        "replacement_options": {}, # 存储替换选项（只含可替换策略）
        "constraints": generate_resource_constraints(armies)  # 根据armies信息生成新的约束
    }
    
    # 保留其他可能存在的字段，如time_limit和solution_count
    for field in ['time_limit', 'solution_count']:
        if field in test_case:
            new_test_case[field] = test_case[field]
    
    # 存储新创建的策略ID映射
    new_strategy_ids = {}  # 原始ID -> [新ID列表]
    
    # 第一步：为每个策略创建特定军队版本
    # 注意：对于不可替换的策略(replaceable=false)，只创建初始军队版本
    # 对于可替换的策略(replaceable=true)，创建所有可行的军队版本
    for strategy_id, strategy in test_case['strategies'].items():
        new_strategy_ids[strategy_id] = []
        
        # 获取策略的初始军队信息
        # army_init = strategy.get('army_init', 'army1')
        is_replaceable = strategy.get('replaceable', False)  # 默认不可替换

        if not is_replaceable:
            # 检查策略是否可以由指定的初始军队完成
            # army = armies.get(army_init, {})
            
            # # 创建修改后的策略副本
            # new_strategy = copy.deepcopy(strategy)
            # new_strategy['aircraft'] = {}  # 清空原始资源
            # new_strategy['ammunition'] = {}  # 清空原始资源
            #
            # if check_strategy_feasible_for_army(strategy, army, new_strategy, army_init):
            #     # 创建带有军队ID的新策略ID
            #     new_strategy_id = f"{strategy_id}-{army_init}"
            #     new_strategy_ids[strategy_id].append(new_strategy_id)
            #
            #     # 移除army_init字段，因为它已经在ID中体现
            #     if 'army_init' in new_strategy:
            #         del new_strategy['army_init']
            #
            #     # 保持replaceable字段为false
            #     new_strategy['replaceable'] = False
            #
            #     # 添加到新测试用例中
            #     new_test_case['strategies'][new_strategy_id] = new_strategy
            for other_army_id, other_army in armies.items():
                # 如果是初始军队且已经处理过，则跳过
                # if other_army_id == army_init:
                #     continue

                # 创建修改后的策略副本
                other_new_strategy = copy.deepcopy(strategy)
                other_new_strategy['aircraft'] = {}  # 清空原始资源
                other_new_strategy['ammunition'] = {}  # 清空原始资源

                # 检查策略是否可以由该军队完成
                if check_strategy_feasible_for_army(strategy, other_army, other_new_strategy, other_army_id):
                    # 创建带有军队ID的新策略ID
                    new_strategy_id = f"{strategy_id}-{other_army_id}"
                    new_strategy_ids[strategy_id].append(new_strategy_id)

                    # # 移除army_init字段，因为它已经在ID中体现
                    # if 'army_init' in other_new_strategy:
                    #     del other_new_strategy['army_init']

                    # 非初始军队版本不可替换
                    other_new_strategy['replaceable'] = False

                    # 添加到新测试用例中
                    new_test_case['strategies'][new_strategy_id] = other_new_strategy
        
        # 对于可替换的策略，创建所有可行的军队版本
        else:
            # 首先，创建初始军队版本
            army_init = strategy.get('army_init', 'army1')
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
                if(strategy.get('replaceable', True)):
                    army_init = strategy.get('army_init', 'army1')
                    init_strategy_id = f"{strategy_id}-{army_init}"
                    
                    # 优先使用初始军队版本
                    if init_strategy_id in new_test_case['strategies']:
                        new_test_case['actions'][action_id].append(init_strategy_id)
                    else:
                        # 如果初始军队版本不可行，使用第一个可行的军队版本
                        new_test_case['actions'][action_id].append(new_strategy_ids[strategy_id][0])
    
    # 第三步：更新替换选项，只为可替换策略(replaceable=true)创建替换选项
    # 确保包含原始替换策略的所有可行军队版本
    for original_strategy_id, replacement_ids in test_case['replacement_options'].items():
        # 确保原策略存在于测试用例中
        if original_strategy_id in test_case['strategies']:
            # 获取原策略信息
            strategy = test_case['strategies'][original_strategy_id]
            if(strategy.get('replaceable', True)):
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
                            # 找到所有可行的军队特定版本
                            replacement_versions = new_strategy_ids[replacement_id]
                            
                            # 获取替换策略本身的信息
                            replacement_strategy = test_case['strategies'][replacement_id]
                            # 添加替换策略的所有其他可行军队版本
                            for version_id in replacement_versions:
                                new_test_case['replacement_options'][init_strategy_id].append(version_id)
                            
                            # 递归添加替换策略的替换选项（如果存在）
                            # if replacement_id in test_case['replacement_options']:
                            #     for nested_replacement_id in test_case['replacement_options'][replacement_id]:
                            #         if nested_replacement_id in new_strategy_ids:
                            #             # 添加嵌套替换策略的所有可行军队版本
                            #             new_test_case['replacement_options'][init_strategy_id].extend(
                            #                 new_strategy_ids[nested_replacement_id]
                            #             )
                    
                    # 添加原策略的其他军队版本作为替换选项
                    for other_version_id in new_strategy_ids[original_strategy_id]:
                        # 不要将策略自身添加为替换选项
                        if other_version_id != init_strategy_id:
                            new_test_case['replacement_options'][init_strategy_id].append(other_version_id)
                    
                    # 去除重复的替换选项
                    new_test_case['replacement_options'][init_strategy_id] = list(set(new_test_case['replacement_options'][init_strategy_id]))
    
    # 如果提供了输出路径，保存处理结果
    if output_path:
        # 创建输出目录（如果不存在）
        dir_name = os.path.dirname(output_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name)
            
        # 保存新测试用例
        save_json_file(new_test_case, output_path)
        
        total_strategies = len(new_test_case['strategies'])
        print(f"生成了 {total_strategies} 个基于军队的策略")
        print(f"结果已保存到 {output_path}")

    # 统计信息
    analyze_filtered_result(new_test_case)

    return new_test_case

# ----------------------------- 结果分析函数 -----------------------------

def analyze_filtered_result(result):
    """分析处理后的结果，输出统计信息和检查资源命名"""
    print("\n==== 统计信息 ====")
    print(f"策略总数: {len(result['strategies'])}")
    
    # 显示特殊配置字段
    if 'time_limit' in result:
        print(f"时间限制: {result['time_limit']}秒")
    if 'solution_count' in result:
        print(f"解决方案数量: {result['solution_count']}")
    
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
    
    # 所有检查完成后返回统计信息
    stats = {
        "strategies_count": len(result['strategies']),
        "actions_count": len(result['actions']),
        "replacement_options_count": len(result['replacement_options']),
        "replaceable_strategies_count": replaceable_count,
        "non_replaceable_strategies_count": non_replaceable_count,
        "aircraft_types_count": aircraft_count,
        "ammunition_types_count": ammunition_count
    }
    
    # 添加特殊字段到统计中
    for field in ['time_limit', 'solution_count']:
        if field in result:
            stats[field] = result[field]
    
    return stats

def generate_summary(result, output_dir):
    """生成结果摘要并保存到指定目录"""
    stats = analyze_filtered_result(result)
    
    # 创建简化的结果摘要
    simplified_result = {
        **stats,
        "sample_strategies": {},
        "sample_replacement": {},
        "sample_constraints": {
            "aircraft": dict(list(result['constraints']['aircraft'].items())[:5]),
            "ammunition": dict(list(result['constraints']['ammunition'].items())[:5])
        }
    }
    
    # 保留特殊字段
    for field in ['time_limit', 'solution_count']:
        if field in result:
            simplified_result[field] = result[field]
    
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
    simplified_path = os.path.join(output_dir, 'test_case_3_summary.json')
    save_json_file(simplified_result, simplified_path)
    
    print(f"\n简化的统计结果已保存到 {simplified_path}")
    
    return simplified_result

# ----------------------------- API路由函数 -----------------------------

def process_strategy_file(input_file_path, output_dir=None):
    """处理策略文件，生成带有军队信息的策略和约束
    
    参数:
        input_file_path: 输入文件路径
        output_dir: 输出目录，如果为None则使用输入文件所在目录
        
    返回:
        处理结果的字典
    """
    # 确保输入文件存在
    if not os.path.exists(input_file_path):
        raise FileNotFoundError(f"找不到输入文件: {input_file_path}")
    
    # 设置输出目录
    if output_dir is None:
        output_dir = os.path.dirname(input_file_path)
    
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 生成输出文件路径
    input_filename = os.path.basename(input_file_path)
    filename_without_ext = os.path.splitext(input_filename)[0]
    output_file_path = os.path.join(output_dir, f"{filename_without_ext}_filtered.json")
    
    # 处理策略文件
    print(f"开始处理策略文件: {input_file_path}")
    result = generate_army_specific_strategies(input_file_path, output_file_path)
    
    # 生成摘要
    summary = generate_summary(result, output_dir)
    
    print("处理完成!")
    return {
        "result": result,
        "summary": summary,
        "output_file": output_file_path
    }

# ----------------------------- 主函数 -----------------------------

def main():
    """主函数"""
    # 获取当前脚本所在的根目录
    root_dir = Path(__file__).resolve().parent.parent
    
    # 默认输入文件路径
    test_case_path = os.path.join(root_dir, 'core', 'testcases[DRAFT]', 'test_case_3.json')
    
    # 获取输出目录
    output_dir = os.path.join(root_dir, 'core', 'testcases[DRAFT]')
    
    # 处理策略文件
    try:
        process_strategy_file(test_case_path, output_dir)
        print("处理成功!")
    except Exception as e:
        print(f"处理过程中出错: {str(e)}")

if __name__ == "__main__":
    main() 
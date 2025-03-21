#!/usr/bin/env python
# coding=utf-8

from strategy_filter import generate_army_specific_strategies
import os

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 设置文件路径
test_case_path = os.path.join(current_dir, 'test_case_3.json')
armys_path = os.path.join(current_dir, 'armys.json')
output_path = os.path.join(current_dir, 'test_case_3_filtered.json')

# 执行策略初筛
print("开始执行策略初筛...")
generate_army_specific_strategies(test_case_path, armys_path, output_path)
print("策略初筛完成！") 
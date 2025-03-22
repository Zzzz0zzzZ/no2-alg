# 策略优化算法

## 目录结构

```shell
.
├── README.md
├── api # 对外提供API
│   ├── __init__.py
│   ├── models.py # 实体类，入参格式
│   └── routes.py # 主接口 /alg/optimize，接收入参，调用apicall.py
├── api.log
├── core  # 算法实现
│   ├── __init__.py
│   ├── apicall.py  # 供api调用的算法顶层函数
│   ├── generate.sh # [废弃]生成测试样例脚本，调用generate_test_case.py
│   ├── generate_test_case.py # [废弃]生成测试样例
│   ├── genetic_strategy_optimization.py  # 遗传算法实现（核心算法）
│   ├── preprocessor.py # 预处理器，根据策略库扩充分队级策略
│   ├── output
│   │   └── convergence_curve.png # 遗传算法收敛曲线（通过API调用时默认不绘制）
│   ├── strategy_optimization.py  # [废弃]回溯算法实现（暂时没用）
│   ├── testcases # 测试样例（单独运行genetic_strategy_optimization.py读取的测试样例）
│   │   └── test_case_generated.json
│   └── testcases[DRAFT]  # 测试样例备份
│       ├── test_case_1.json
│       ├── test_case_2.json
│       └── test_case_3.json
└── main.py # 算法服务启动，入口文件
```

## 算法核心接口调用链路
1. **入口点**: `/alg/optimize` API接口
   - 位于 `routes.py` 中的 `optimize` 函数
   - 接收 `TestCaseDTO` 类型的请求数据

2. **预处理阶段**:
   - 调用 `apicall.py` 中的 `apicall` 函数
   - `apicall` 函数首先调用 `preprocessor.py` 中的 `generate_army_specific_strategies` 函数
   - 该函数根据策略库信息扩充分队级策略，处理分队资源约束

3. **优化阶段**:
   - `apicall` 函数将预处理后的数据转换为 `OptimizeDTO` 对象
   - 创建 `Strategy` 对象和 `ActionList` 对象
   - 调用 `genetic_strategy_optimization.py` 中的 `run_optimize` 函数
   - 该函数使用遗传算法寻找最优策略组合

4. **结果处理阶段**:
   - `apicall` 函数处理优化结果，计算资源使用情况
   - 生成详细的替换方案和描述
   - 返回包含算法耗时、方案数量、最优价格和具体方案详情的结果

5. **响应返回**:
   - `optimize` 函数将结果包装为 `CommonResponse` 对象返回给客户端

## 数据流转图

```
客户端请求 → /alg/optimize API → apicall() → generate_army_specific_strategies() → 
                                                ↓
                                            run_optimize() → 
                                                ↓
                                            结果处理 → CommonResponse → 客户端响应
```

## 核心接口 `/alg/optimize`
### 入参说明
```json
{
  "strategies": {  // 策略字典，键为策略ID
    "策略1": {  // 策略ID，唯一标识一个策略
      "replaceable": true,  // 是否可替换，true表示该策略可以被替换策略替代
      "army_init": "分队1",  // 初始执行该策略的分队ID
      "aircraft": {  // 该策略需要的载机资源
        "A型": [1, 1000],  // 键为载机类型ID，值为[数量, 单价]
        "B型": [1, 2000]
      },
      "ammunition": {  // 该策略需要的弹药资源
        "导弹X": [1, 500],  // 键为弹药类型ID，值为[数量, 单价]
        "炸弹Y": [1, 300]
      }
    },
    "策略1的替换策略-1": {  // 替换策略ID
      "replaceable": false,  // 替换策略通常不可再被替换，防止递归替换
      "aircraft": {  // 替换策略需要的载机资源
        "A型-1": [1, 1000],
        "B型-1": [1, 2000]
      },
      "ammunition": {  // 替换策略需要的弹药资源
        "导弹X-1": [1, 300],
        "炸弹Y-1": [1, 300]
      }
    }
  },
  "actions": {  // 行动字典，键为行动ID
    "行动1": ["策略1"]  // 键为行动ID，值为该行动包含的策略ID列表
  },
  "replacement_options": {  // 替换选项字典
    "策略1": ["策略1的替换策略-1"]  // 键为可替换策略ID，值为可用于替换的策略ID列表
  },
  "armies": {  // 分队资源字典，键为分队ID
    "分队1":{  // 分队ID
      "aircraft":{  // 该分队拥有的载机资源
        "A型":{  // 载机类型ID
          "数量":4  // 该分队拥有的该类型载机数量
        },
        "B型":{
          "数量":4
        }
      },
      "ammunition":{  // 该分队拥有的弹药资源
        "导弹X":{  // 弹药类型ID
          "数量":4  // 该分队拥有的该类型弹药数量
        },
        "炸弹Y":{
          "数量":4
        }
      }
    },
    "分队2":{...},
    ...
  },
  "time_limit": 10,  // 算法执行时间限制(秒)，传0表示无时间约束，默认迭代200轮
  "solution_count": 3  // 返回的最优方案个数，默认返回1个
}
```

## 返回值说明
```json
{
  "code": 200,  // 状态码，200表示成功
  "msg": "优化成功",  // 状态消息
  "data": {  // 返回数据
    "elapsed_time": 0.86,  // 算法执行耗时(秒)
    "solution_count": 2,  // 返回的方案数量
    "original_price": 3800,  // 原始方案总价格
    "price_difference": 200,  // 最优方案与原始方案的价格差
    "is_saving": true,  // 是否节省了费用
    "best_price": 3600,  // 最优方案的总价格
    "solutions": [  // 方案列表，按优化程度排序
      {
        "sort": 1,  // 方案最优排序，从1开始
        "total_price": 3600,  // 该方案的总价格
        "price_difference": 200,  // 与原始方案的价格差
        "is_saving": true,  // 是否节省了费用
        "strategy_details": [  // 策略替换详情列表
          {
            "from_strategy_id": "策略1",  // 原策略ID
            "from_army_id": "分队1",  // 原执行分队ID
            "to_strategy_id": "策略1的替换策略-1",  // 替换后的策略ID
            "to_army_id": "分队2",  // 替换后的执行分队ID
            "from_strategy_details": {  // 原策略详情
              "aircraft": {  // 原策略需要的载机资源
                "A型": [1, 1000],  // [数量, 单价]
                "B型": [1, 2000]
              },
              "ammunition": {  // 原策略需要的弹药资源
                "导弹X": [1, 500],  // [数量, 单价]
                "炸弹Y": [1, 300]
              },
              "price": 3800  // 原策略总价格
            },
            "to_strategy_details": {  // 替换策略详情
              "aircraft": {  // 替换策略需要的载机资源
                "A型-1": [1, 1000],
                "B型-1": [1, 2000]
              },
              "ammunition": {  // 替换策略需要的弹药资源
                "导弹X-1": [1, 300],
                "炸弹Y-1": [1, 300]
              },
              "price": 3600  // 替换策略总价格
            },
            "price_difference": 200,  // 替换前后的价格差
            "is_saving": true,  // 替换是否节省了费用
            "desc": "在阶段[行动1]中，用分队[分队1]执行任务[策略1]替换为用分队[分队2]执行任务[策略1的替换策略-1]，节省200元"  // 替换描述
          }
        ],
        "resource_usage": {  // 各分队资源使用情况
          "分队2": {  // 分队ID
            "aircraft": {  // 载机资源使用情况
              "A型-1": {  // 载机类型
                "total": 4,  // 总数量
                "used": 1,  // 已使用数量
                "remaining": 3  // 剩余数量
              },
              "B型-1": {
                "total": 4,
                "used": 1,
                "remaining": 3
              }
            },
            "ammunition": {  // 弹药资源使用情况
              "导弹X-1": {
                "total": 4,
                "used": 1,
                "remaining": 3
              },
              "炸弹Y-1": {
                "total": 4,
                "used": 1,
                "remaining": 3
              }
            }
          },
          "分队1": {
            "aircraft": {
              "A型": {
                "total": 4,
                "used": 0,
                "remaining": 4
              },
              "B型": {
                "total": 4,
                "used": 0,
                "remaining": 4
              }
            },
            "ammunition": {
              "导弹X": {
                "total": 4,
                "used": 0,
                "remaining": 4
              },
              "炸弹Y": {
                "total": 4,
                "used": 0,
                "remaining": 4
              }
            }
          },
          "分队3": {
            "aircraft": {
              "A型-1": {
                "total": 4,
                "used": 0,
                "remaining": 4
              },
              "B型-1": {
                "total": 4,
                "used": 0,
                "remaining": 4
              }
            },
            "ammunition": {
              "导弹X-1": {
                "total": 4,
                "used": 0,
                "remaining": 4
              },
              "炸弹Y-1": {
                "total": 0,
                "used": 0,
                "remaining": 0
              }
            }
          },
          "分队4": {
            "aircraft": {
              "A型": {
                "total": 4,
                "used": 0,
                "remaining": 4
              },
              "B型": {
                "total": 4,
                "used": 0,
                "remaining": 4
              }
            },
            "ammunition": {
              "导弹X": {
                "total": 4,
                "used": 0,
                "remaining": 4
              },
              "炸弹Y": {
                "total": 4,
                "used": 0,
                "remaining": 4
              }
            }
          }
        },
        "replacement_type": 1,  // 替换类型：0-原方案，1-优化后价格节省，2-优化后价格不变但兵力派遣改变
        "replacement_desc": "本方案为优化后方案，价格节省200元，兵力派遣改变"  // 方案描述
      },
      {
        "sort": 2,  // 第二个方案
        "total_price": 3800,
        "price_difference": 0,
        "is_saving": false,
        "strategy_details": [
          {
            "from_strategy_id": "策略1",
            "from_army_id": "分队1",
            "to_strategy_id": "策略1",
            "to_army_id": "分队4",
            "from_strategy_details": {
              "aircraft": {
                "A型": [1, 1000],
                "B型": [1, 2000]
              },
              "ammunition": {
                "导弹X": [1, 500],
                "炸弹Y": [1, 300]
              },
              "price": 3800
            },
            "to_strategy_details": {
              "aircraft": {
                "A型": [1, 1000],
                "B型": [1, 2000]
              },
              "ammunition": {
                "导弹X": [1, 500],
                "炸弹Y": [1, 300]
              },
              "price": 3800
            },
            "price_difference": 0,
            // 此处省略部分内容...
          }
        ]
        // 此处省略部分内容...
      }
    ]
  }
}
```
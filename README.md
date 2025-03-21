* 目录结构
```shell
.
├── README.md
├── api # 对外提供API
│   ├── __init__.py
│   ├── models.py # 实体类，入参格式
│   └── routes.py # 主接口 /alg/optimize，接收入参，调用apicall.py
├── api.log
├── core  # 算法实现
│   ├── __init__.py
│   ├── __pycache__
│   ├── apicall.py  # 供api调用的算法顶层函数
│   ├── generate.sh # 生成测试样例脚本，调用generate_test_case.py
│   ├── generate_test_case.py # 生成测试样例
│   ├── genetic_strategy_optimization.py  # 遗传算法实现（核心算法）
│   ├── output
│   │   └── convergence_curve.png # 遗传算法收敛曲线（通过API调用时默认不绘制）
│   ├── strategy_optimization.py  # 回溯算法实现（暂时没用）
│   ├── testcases # 测试样例（单独运行genetic_strategy_optimization.py读取的测试样例）
│   │   └── test_case_generated.json
│   └── testcases[DRAFT]  # 测试样例备份
│       ├── test_case_1.json
│       ├── test_case_2.json
│       └── test_case_3.json
└── main.py # 算法服务启动，入口文件
```

* 算法输入字段说明
> 可以看下：
> * 到底是用 唯一ID（需要额外维护一个ID-名称字典，在返回结果时转成名称）
> * 还是 唯一名称（要确保名称唯一性）
```json
{ 
  "time_limit": 50, // 不传或传0：默认无时间约束，迭代200轮
  "solution_count": 3 // 返回的最优方案个数：不传默认1个
  "strategies": { // strategies 字典形式
    "策略1": {  // "策略1"为策略ID或唯一名称，策略的唯一标识
      "replaceable": true,  // 是否可替换(判断用户输入的策略是否可替换(查策略库),若可替换，则注意添加可替换策略列表，列表中的策略都是不可再替换的，防止递归)
      "aircraft": { // 载机的类型、数量
        "A型": [1, 1000],  // "载机类型(typeid/或唯一名称)": [数量, 价格],
        "B型": [1, 2000]
      },
      "ammunition": { // 弹药类型、数量
        "导弹X": [1, 500],  // "弹药类型(typeid/或唯一名称)": [数量, 价格]
        "炸弹Y": [1, 300]
      }
    },
    "策略2": {
      "replaceable": true,
      "aircraft": {
        "A型": [1, 1000],
        "B型": [1, 2000]
      },
      "ammunition": {
        "导弹X": [1, 500],
        "炸弹Y": [1, 300]
      }
    },
    "策略1的替换策略-1": { 
      "replaceable": false, // 替换策略的replaceable就不能再为true了
      "aircraft": {
        "A型-G": [2, 499],
        "B型": [1, 2000]
      },
      "ammunition": {
        "导弹X": [1, 500],
        "炸弹Y": [1, 300]
      }
    },
    "策略1的替换策略-2": {
      "replaceable": false,
      "aircraft": {
        "A型-G-1": [3, 299],
        "B型": [1, 2000]
      },
      "ammunition": {
        "导弹X": [1, 500],
        "炸弹Y": [1, 300]
      }
    },
    "策略2的替换策略-1": {
      "replaceable": false,
      "aircraft": {
        "A型": [1, 1000],
        "B型": [1, 2000]
      },
      "ammunition": {
        "导弹X-G": [2, 249],
        "炸弹Y": [1, 300]
      }
    },
    "策略2-1": {
      "replaceable": false,
      "aircraft": {
        "A型": [1, 1000],
        "B型": [1, 2000]
      },
      "ammunition": {
        "导弹X": [1, 500],
        "炸弹Y": [1, 300]
      }
    },
    "策略2-2": {
      "replaceable": false,
      "aircraft": {
        "A型": [1, 1000],
        "B型": [1, 2000]
      },
      "ammunition": {
        "导弹X": [1, 500],
        "炸弹Y": [1, 300]
      }
    },
    "策略2-3": {
      "replaceable": true,
      "aircraft": {
        "A型": [1, 1000],
        "B型": [1, 2000]
      },
      "ammunition": {
        "导弹X": [1, 500],
        "炸弹Y": [1, 300]
      }
    },
    "策略2-3的替换策略-1": {
      "replaceable": false,
      "aircraft": {
        "A型": [1, 1000],
        "B型": [1, 2000]
      },
      "ammunition": {
        "导弹X-G": [2, 249],
        "炸弹Y": [1, 300]
      }
    }
  },
  "actions": {
    "行动1": ["策略1", "策略2"],  // 哪个行动下有哪些策略  "行动id/唯一名称": ["策略ID/唯一名称(与strategies中对应)"]
    "行动2": ["策略2-1", "策略2-2", "策略2-3"]
  },
  "replacement_options": {  // 每个可替换策略的替换列表
    "策略1": ["策略1的替换策略-1", "策略1的替换策略-2"],  // "策略ID/唯一名称"： ["策略ID/唯一名称", "策略ID/唯一名称"]
    "策略2": ["策略2的替换策略-1"],
    "策略2-3": ["策略2-3的替换策略-1"]
  },
  "constraints": {  // 约束
    "aircraft": { 
      "A型": 5,  // "载机typeid/唯一名称": 数量
      "B型": 5,
      "A型-G": 2,
      "A型-G-1": 3
    },
    "ammunition": {
      "导弹X": 3, // "弹药typeid/唯一名称": 数量
      "炸弹Y": 5,
      "导弹X-G": 4
    }
  }
}
```
# 策略优化算法

## 目录结构
```shell
./
├── README.md // 项目说明
├── api // API模块
│   ├── __init__.py
│   ├── models.py // 实体类
│   └── routes.py // 主接口 /alg/optimize，接收入参，调用apicall.py
├── core  // 算法模块
│   ├── __init__.py
│   ├── apicall.py  // 分队级样本扩充调用 + 算法调用
│   ├── genetic_strategy_optimization.py // 遗传算法实现三个优化目标
│   ├── output  // 收敛曲线，api调用默认不提供
│   │   └── convergence_curve.png
│   ├── preprocessor.py // 分队级样本扩充
│   └── testcases // 测试用例
├── main.py // 算法服务入口
└── static  // swagger-ui静态文件
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
### 版本：第二次对接 [待集成]
> 涉及版本：
> * 20250421-出动bingli最少优化
> * 20250420-效损比优化
> * 20250419-考虑战损的效费比优化
> * 20250416-考虑时间片资源限制
#### 更新说明
1. 针对效费比优化模型，新增「战损」和「任务出动时序」对于模型优化的影响。策略费用计算逻辑由「飞机费用+dan费用」改为：「损失飞机费用+dan费用」。
2. 新增效损比优化模型，优化目标为总飞机损失数量最少。
3. 新增出动bingli最少优化模型，优化目标为总出动飞机架次最少。

#### 接口变动
##### 20250421-出动bingli最少优化

「入参」

- opt_type字段，新增优化类型，2 - 出动bingli最少优化。

    ```python
    class OptimizationType(IntEnum):
        PRICE = 0  # 效费比优化，价格最低
        AIRCRAFT_LOSS = 1  # 效损比优化，飞机损失最少
    [+] AIRCRAFT_USAGE = 2  # 出动兵力最少（总出动飞机数量最少）
    ```

「返回值」

- data     

    [+] original_bingli: int 原始方案兵力数量     

    [+] saved_bingli: int 节省的兵力(原始-最优)    

    [+] best_bingli: int  最优方案的兵力     

    [+] is_saving_bingli: boolean 是否节省出动兵力   

- data.solutions     

    [+] total_bingli: int 当前方案总出动兵力     

    [+] bingli_difference: int 出动兵力差异(原始-当前)     

    [+] is_saving_bingli: boolean 是否节省出动兵力  

- data.solutions.strategy_details     

    [+] bingli_difference: int 替换后出动兵力差异     

    [+] is_saving_bingli: 是否节省出动兵力   

- data.solutions.strategy_details.from_strategy_details     

    [+] total_bingli 原策略的总出动兵力   

- data.solutions.strategy_details.to_strategy_details     

    [+] total_bingli 替换策略的总出动兵力

##### 20250420-效损比优化

「入参」

- 新增opt_type字段，代表优化类型。0 - 效费比优化 1 - 效损比优化。

    ```python
    class TestCaseDTO(BaseModel):
        strategies: Dict[str, Strategy]  # 键为策略ID，值为策略详情
        actions: Dict[str, List[str]]  # 键为行动ID，值为策略ID列表
        replacement_options: Dict[str, List[str]]  # 键为可替换策略ID，值为替换策略ID列表
        armies: Dict[str, ArmyResource]  # 键为军队ID，值为军队资源
        stage: Optional[List[str]] = []  # 需要优化的阶段(传空列表，代表优化全部，否则只优化列表中的阶段)
        time_limit: Optional[int] = None  # 算法执行时间限制
        solution_count: Optional[int] = None  # 返回几种优化方案
    [+] opt_type: Optional[OptimizationType] = OptimizationType.PRICE  # 优化类型，默认为价格优化
    ```

    ```python
    class OptimizationType(IntEnum):
        PRICE = 0  # 效费比优化，价格最低
    [+] AIRCRAFT_LOSS = 1  # 效损比优化，飞机损失最少
    ```

「返回值」

- data     

    [+] original_loss: int 原始方案飞机损失    

    [+] saved_loss: int 节省的飞机损失(原始-最优)     

    [+] best_loss: int  最优方案的飞机损失    

    [+] is_saving_loss: boolean 是否节省飞机损失     

    [+] opt_type: IntEnum   

- data.solutions     

    [+] total_loss: int 当前方案总飞机损失     

    [+] loss_difference: int 飞机损失差异(原始-当前)     

    [+] is_saving_loss: boolean 是否节省飞机损失   

- data.solutions.strategy_details     

    [+] loss_difference: int 当前策略飞机损失差异     

    [+] is_saving_loss: 是否节省飞机损失

##### 20250419-考虑战损的效费比优化

「入参」

- strategies.策略ID对应的策略详情中，新增 penetration_rate 突防率 字段。

    > 原策略、替换策略均需要具备此字段，代表突防成功的概率。飞机损失计算逻辑为：飞机数量 * （1 - 突防率）

    ```python
    class Strategy(BaseModel):
        replaceable: bool
        aircraft: Dict[str, List[int]]  # 键为载机类型，值为[数量, 单价]列表
        ammunition: Dict[str, List[int]]  # 键为弹药类型，值为[数量, 单价]列表
        army_init: Optional[str] = None  # 策略初始军队 - 「只有原始草案中的策略携带该参数」
        time_range: Optional[List[int]] = None  # 策略的时间范围 [开始时间, 结束时间] - 「只有原始草案中的策略携带该参数」
    [+] penetration_rate: Optional[float] = 0.8  # 突防率，0.0~1.0之间，默认0.8
    ```

「返回值」

- solutions.resource_usage

     [+] loss 飞机损毁数量  

-  solutions.strategy_details.from_strategy_details     

     [+] aircraft_loss: Dict[aircraft_type, count] 区分飞机类型的损毁数(字典)     

     [+] total_aircraft_loss: int 不区分飞机类型的总损毁数    

     [+] penetration_rate: float 突防率(回传)   

-  solutions.strategy_details.to_strategy_details      

     [+] aircraft_loss: Dict[aircraft_type, count] 区分飞机类型的损毁数(字典)     

     [+] total_aircraft_loss: int 不区分飞机类型的总损毁数     

     [+] penetration_rate: float 突防率(回传)

##### 20250416-考虑时间片资源限制

「入参」

- stategies.策略ID对应的策略详情中，新增 time_range字段。

    > 原始方案中的策略，必须携带time_range字段；替换策略一般不带time_range字段，会继承原策略的time_range。

```python
class Strategy(BaseModel):
    replaceable: bool
    aircraft: Dict[str, List[int]]  # 键为载机类型，值为[数量, 单价]列表
    ammunition: Dict[str, List[int]]  # 键为弹药类型，值为[数量, 单价]列表
    army_init: Optional[str] = None  # 策略初始军队 - 「只有原始草案中的策略携带该参数」
[+] time_range: Optional[List[int]] = None  # 策略的时间范围 [开始时间, 结束时间] - 「只有原始草案中的策略携带该参数」
```

「返回值」

- data.solutions.strategy_details.from_strategy_details

​       [+] time_range

- data.solutions.strategy_details.to_strategy_details

   [+] time_range

#### 请求示例

##### 入参

```json
{
  "opt_type": 2,	// 新增
  "strategies": {
    "策略1": {
      "replaceable": true,
      "army_init": "军队1",
      "aircraft": {
        "C型": [30, 1000]
      },
      "ammunition": {
        "导弹X": [1, 500]
      },
      "time_range": [0, 90],	// 新增
      "penetration_rate": 0.9	// 新增
    },
    "策略1-t1": {
      "replaceable": false,
      "aircraft": {
        "C-t1型": [20, 500]
      },
      "ammunition": {
        "导弹X": [1, 500]
      },
      "penetration_rate": 0.8	// 新增
    },
    "策略1-t2": {
      "replaceable": false,
      "aircraft": {
        "C-t2型": [10, 2000]
      },
      "ammunition": {
        "导弹X": [1, 500]
      },
      "penetration_rate": 0.5	// 新增
    }
  },
  "actions": {
    "行动1": ["策略1"]
  },
  "replacement_options": {
    "策略1": ["策略1-t1", "策略1-t2"]
  },
  "stage": ["行动1"],
  "armies": { 
    "军队1":{
      "aircraft":{
        "C型":{
          "数量":30
        },
        "C-t1型":{
          "数量":20
        },
        "C-t2型":{
          "数量":10
        }
      },
      "ammunition":{
        "导弹X":{
          "数量":12
        }
      }
    }
    },
  "time_limit": 60,
  "solution_count": 3
}
```

##### 返回值

> 说明：根据不同的opt_type查看不同的优化结果（data下的第一级字段），如opt_type == 1，效损比优化，就看loss相关的字段；出动bingli优化，就看bingli相关的字段，不要全看。

```json
{
  "code": 200,	// 200成功，201成功但找不到更优解，400参数错误，500服务器错误
  "msg": "优化成功",
  "data": {
    "elapsed_time": 2.58,
    "solution_count": 3,
    "original_price": 3500,
    "price_difference": 7000,
    "is_saving": false,
    "best_price": 10500,
    "original_loss": 3,	// 新增
    "saved_loss": -2,	// 新增
    "best_loss": 5,	// 新增
    "is_saving_loss": false,	// 新增
    "original_bingli": 30,	// 新增
    "saved_bingli": 20,	// 新增
    "best_bingli": 10,	// 新增
    "is_saving_bingli": true,	// 新增
    "opt_type": 2,	// 新增
    "solutions": [
      {
        "sort": 1,
        "total_price": 10500,
        "price_difference": 7000,
        "is_saving": false,
        "total_loss": 5,	// 新增
        "loss_difference": 2,	// 新增
        "is_saving_loss": false,	// 新增
        "total_bingli": 10,	// 新增
        "bingli_difference": 20,	// 新增
        "is_saving_bingli": true,	// 新增
        "strategy_details": [
          {
            "from_strategy_id": "策略1",
            "from_army_id": "军队1",
            "to_strategy_id": "策略1-t2",
            "to_army_id": "军队1",
            "from_strategy_details": {
              "aircraft": {
                "C型": [
                  30,
                  1000
                ]
              },
              "ammunition": {
                "导弹X": [
                  1,
                  500
                ]
              },
              "price": 3500,
              "time_range": [
                0,
                90
              ],
              "aircraft_loss": {	// 新增
                "C型": 3
              },
              "total_aircraft_loss": 3,	// 新增
              "penetration_rate": 0.9,	// 新增
              "total_bingli": 30	// 新增
            },
            "to_strategy_details": {
              "aircraft": {
                "C-t2型": [
                  10,
                  2000
                ]
              },
              "ammunition": {
                "导弹X": [
                  1,
                  500
                ]
              },
              "price": 10500,
              "time_range": [
                0,
                90
              ],
              "aircraft_loss": {	// 新增
                "C-t2型": 5
              },
              "total_aircraft_loss": 5,	// 新增
              "penetration_rate": 0.9,	// 新增
              "total_bingli": 10	// 新增
            },
            "price_difference": 7000,
            "is_saving": false,
            "loss_difference": 2,	// 新增
            "is_saving_loss": false,	// 新增
            "bingli_difference": 20,	// 新增
            "is_saving_bingli": true,	// 新增
            "desc": "在阶段[行动1]中，用分队[军队1]执行任务[策略1]替换为用分队[军队1]执行任务[策略1-t2]，减少20兵力派遣"
          }
        ],
        "resource_usage": {
          "军队1": {
            "aircraft": {
              "C型": {
                "total": 30,
                "used": 0,
                "loss": 0,	// 新增
                "remaining": 30
              },
              "C-t1型": {
                "total": 20,
                "used": 0,
                "loss": 0,	// 新增
                "remaining": 20
              },
              "C-t2型": {
                "total": 10,
                "used": 10,
                "loss": 5,	// 新增
                "remaining": 5
              }
            },
            "ammunition": {
              "导弹X": {
                "total": 12,
                "used": 1,
                "remaining": 11
              }
            }
          }
        },
        "replacement_type": 1,	
        "replacement_desc": "本方案为优化后方案，价格节省-7000元，兵力派遣改变"
      },
      {...省略...}
  }
}
```



### 版本：第一次对接 [已集成]
> 涉及版本：
> * 20250323-效费比优化
#### 入参说明
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
  "stage": ["行动1"], // 需要优化的阶段，传哪个阶段，优化哪个阶段
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

#### 返回值说明
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
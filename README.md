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
│   ├── converter.py // 接口参数转换
│   ├── testcases // 测试用例[废弃]
│   └── testcasesnew // 测试用例[新数据结构]
├── main.py // 算法服务入口
└── static  // swagger-ui静态文件
```

## 算法核心接口调用链路
1. **入口点**: `/alg/optimize` API接口
   - 位于 `routes.py` 中的 `optimize` 函数
   - 接收 `TestCaseNewDTO` 类型的请求数据

2. **预处理阶段**:
   - 调用 `apicall.py` 中的 `apicall` 函数
   - `apicall` 函数首先调用 `converter.py` 中的 `convert_to_old_format` 函数，将`TestCaseNewDTO`转换为内部的`TestCaseDTO`
   - 转换后，初始化战斗参数缓存，并校验原始草案中行动的时间范围
   - 处理需要优化的阶段信息，如果指定了需要优化的阶段，将不在列表中的阶段的策略设置为不可替换
   - 调用 `preprocessor.py` 中的 `generate_army_specific_strategies` 函数
   - 该函数根据策略库信息扩充分队级策略，处理分队资源约束

3. **优化阶段**:
   - `apicall` 函数将预处理后的数据转换为 `OptimizeDTO` 对象
   - 创建 `Strategy` 对象和 `ActionList` 对象，构建算法入参
   - 调用 `genetic_strategy_optimization.py` 中的 `run_optimize` 函数
   - 该函数使用遗传算法根据指定的优化类型(效费比、效损比或出动兵力最少)寻找最优策略组合
   - 在计算策略的价格和损失时，通过 `simulate.py` 中的 `calculate_aircraft_losses` 函数模拟空中和地面作战，
     计算不同策略的战损情况，考虑空中交战交换比和地面防空因素

4. **结果处理阶段**:
   - `apicall` 函数处理优化结果，计算资源使用情况
   - 生成替换方案的详细描述
   - 返回包含算法耗时、方案数量、最优价格/损失/兵力和具体方案详情的结果

## 核心接口 `/alg/optimize`

### 版本：根据「空中力量」+「地面力量」计算战损

#### 更新说明

1. 战损不再根据 penetration_rate计算，而根据执行行动过程中可能遇到的敌人计算。**原字段penetration_rate删除。**
2. 飞机交换比和地面防空力量的能力值，在数据库中配置。

#### 接口变动

* strategies列表内，每个strategy，增加enemies字段。

> **注意：**
>
> **1. 原行动草案中的行动strategy，需要传enemies字段。如果enemies字段为空，则认为没有拦截力量。**
>
> **2. 行动的替换方案，即replacement_options中的替换列表中的行动replacement_strategies，可以不传enemies字段，会继承原行动草案中的enemies字段。**

```python
class EnemyAircraft(BaseModel):
    aircraft_type: int
    count: int

class EnemyGround(BaseModel):
    ground_type: int
    count: int

class Enemies(BaseModel):
    air: Optional[List[EnemyAircraft]] = []
    ground: Optional[List[EnemyGround]] = []

# strategies下的每个strategy，增加enemies字段
class StrategyNew(BaseModel):
    strategy_id: int
    replaceable: bool
    army_init: Optional[int] = None
    aircraft: List[AircraftNew]
    ammunition: List[AmmunitionNew]
    time_range: Optional[TimeRange] = None
[-] penetration_rate: Optional[float] = 0.8  # 废弃字段，删除，将由算法根据enemies计算
[+] enemies: Optional[Enemies] = None  # 新增字段：策略执行过程中遇到的敌人
```

「入参」

```json
{
  "opt_type": 2,
  "strategies": [
    {
      "strategy_id": 1,
      "replaceable": true,
      "army_init": 100,
      "aircraft": [{
        "aircraft_type": 10001,
        "count": 30,
        "price": 1000
      }],
      "ammunition": [{
        "ammunition_type": 1000,
        "count": 1,
        "price": 500
      }],
      "time_range": {
        "start": 0,
        "end":  90
      },
      // 【新增字段】执行行动过程中，会遇到的敌人
      "enemies": {
        // 空中敌人(各种飞机型号等)
        "air": [
            {
                "aircraft_type": 100001,
                "count": 3,
            },
            {
                "aircraft_type": 100002,
                "count": 5,
            }
        ],
        // 地面敌人(雷达、防空编队等)
        "ground": [
            {
                "ground_type": 200001,  // 具体敌人的类型，可能有很多。这里只是举个例子。
                "count": 2,
            },
            {
                "ground_type": 200002,
                "count": 7,
            }
        ]
    },
    {
      "strategy_id": 2,
      "replaceable": false,
      "army_init": null,
      "aircraft": [
          {
              "aircraft_type": 10002,
              "count": 20,
              "price": 500
          }
      ],
      "ammunition": [
          {
              "ammunition_type": 1000,
              "count": 1,
              "price": 500
          }
      ],
      "time_range": {
          "start": null,
          "end": null
      }
  },
  {
      "strategy_id": 3,
      "replaceable": false,
      "army_init": null,
      "aircraft": [
          {
              "aircraft_type": 10003,
              "count": 10,
              "price": 2000
          }
      ],
      "ammunition": [
          {
              "ammunition_type": 1000,
              "count": 1,
              "price": 500
          }
      ],
      "time_range": {
          "start": null,
          "end": null
      }
  }],
  "actions": [
        {
            "action_id": 10,
            "strategies": [1]
        }
    ],
    "replacement_options": [
        {
            "original_strategy": 1,
            "replacement_strategies": [2, 3]
        }
    ],
    "stage": [10],
    "armies": [
        {
            "army_id": 100,
            "aircraft": [
                {
                    "aircraft_type": 10001,
                    "count": 30
                },
                {
                    "aircraft_type": 10002,
                    "count": 20
                },
                {
                    "aircraft_type": 10003,
                    "count": 10
                }
            ],
            "ammunition": [
                {
                    "ammunition_type": 1000,
                    "count": 12
                }
            ]
        }
    ],
  "time_limit": 60,
  "solution_count": 3
}
```

「返回值」

返回字段不变。

### 版本：修改接口入参、反参格式 [已集成]

#### 接口变动

「入参」

```json
{
  "opt_type": 2,	// 0-效费比 1-效损比 2-最少出动兵力
  "strategies": [	// 策略列表
    {
      "strategy_id": 1,	// 策略ID
      "replaceable": true,	// 是否为可替换策略（替换策略列表中的策略，一定是false，原始草案中可能true/false，取决于有无可替换策略）
      "army_init": 100,		// 初始执行编队ID（替换策略列表中的策略，无初始化军队）
      "aircraft": [{	// 计划出动载机
        "aircraft_type": 10001,	// 载机ID
        "count": 30,	// 数量
        "price": 1000	// 造价
      }],
      "ammunition": [{	// 计划挂载弹
        "ammunition_type": 1000,	// 弹ID
        "count": 1,	// 数量
        "price": 500	// 造价
      }],
      "time_range": {	// 出动时间（如：T+0, T+90）
        "start": 0,	// 开始时间
        "end":  90	// 结束时间
      },
      "penetration_rate": 0.9	// 策略执行的飞机突防率
    },
    {
      "strategy_id": 2,
      "replaceable": false,	// 替换策略列表中的策略，一定是false
      "army_init": null,	// 替换策略列表中的策略，一定没有初始化军队
      "aircraft": [
          {
              "aircraft_type": 10002,
              "count": 20,
              "price": 500
          }
      ],
      "ammunition": [
          {
              "ammunition_type": 1000,
              "count": 1,
              "price": 500
          }
      ],
      "time_range": {	// 替换策略列表中的策略，一定没有任务执行时间，算法会从原策略继承
          "start": null,
          "end": null
      },
      "penetration_rate": 0.8	// 替换策略列表中的策略，一定是有突防率的
  },
  {
      "strategy_id": 3,
      "replaceable": false,
      "army_init": null,
      "aircraft": [
          {
              "aircraft_type": 10003,
              "count": 10,
              "price": 2000
          }
      ],
      "ammunition": [
          {
              "ammunition_type": 1000,
              "count": 1,
              "price": 500
          }
      ],
      "time_range": {
          "start": null,
          "end": null
      },
      "penetration_rate": 0.5
  }],
  "actions": [	// 行动-策略 （可以对应为阶段-任务）
        {
            "action_id": 10,	// 行动ID（阶段ID）
            "strategies": [1]	// 原始草案中的任务ID（策略ID）
        }
    ],
    "replacement_options": [	// 可替换策略列表
        {
            "original_strategy": 1,	// 草案中，原策略ID
            "replacement_strategies": [2, 3]	// 可替换策略列表，策略ID
        }
    ],
    "stage": [10],	// 优化阶段（传哪个阶段ID，优化哪个，可以优化多个）
    "armies": [	// 兵力编成数据
        {
            "army_id": 100,	// 分队ID
            "aircraft": [	// 分队载机情况（分队由多少载机）
                {
                    "aircraft_type": 10001,	// 载机type
                    "count": 30	// 数量
                },
                {
                    "aircraft_type": 10002,
                    "count": 20
                },
                {
                    "aircraft_type": 10003,
                    "count": 10
                }
            ],
            "ammunition": [	// 分队 弹情况 （分队有多少弹）
                {
                    "ammunition_type": 1000,	// 弹type
                    "count": 12	// 数量
                }
            ]
        }
    ],
  "time_limit": 60,	// 算法执行时间限制 (s)
  "solution_count": 3	// 返回几种最优的优化方案
}
```

「返回值」

```json
{
  "code": 200,	// 200-优化成功 201-找不到更优解 400-入参错误 500-算法错误
  "msg": "优化成功",
  "data": {
    "elapsed_time": 2.66,	// 算法执行时间
    "solution_count": 3,	// 返回的实际优化方案数（用户想要10种，可能只有3种）
    "original_price": 3500,	// 原方案价格
    "price_difference": 7000,	//	优化前后价格差异 
    "is_saving": false,	// 是否节省了价格
    "best_price": 10500,	// 最优价格
    "original_loss": 3,	// 原方案兵力损失
    "loss_difference": 2,	// 优化前后兵力损失差异
    "best_loss": 5,	// 最少损失兵力
    "is_saving_loss": false,	// 是否节省了兵力损失
    "original_bingli": 30,	// 原方案出动兵力
    "bingli_difference": 20,		// 优化前后出动兵力差异
    "best_bingli": 10,	// 最少出动兵力
    "is_saving_bingli": true,	// 是否节省了出动兵力
    "opt_type": 2,	// 优化类型 (透传)
    "solutions": [	// 优化方案
      {
        "sort": 1,	// 最优排序
        "total_price": 10500,	// 总价
        "price_difference": 7000,	// 价格差异
        "is_saving": false,	// 是否节省
        "total_loss": 5,	// 总损
        "loss_difference": 2,	// 损差异
        "is_saving_loss": false,	// 是否节省
        "total_bingli": 10,	// 总出动兵力
        "bingli_difference": 20,	// 兵力差异
        "is_saving_bingli": true,	// 是否节省
        "strategy_details": [	// 替换详情
          {
            "from_strategy_id": 1,	// 原策略ID
            "from_army_id": 100,	// 原分队ID
            "to_strategy_id": 3,	// 替换到的策略ID
            "to_army_id": 100,	// 替换到的分队ID
            "from_strategy_details": {	// 原策略详情（基本上与入参一致，加了几个字段）
              "aircraft": [
                {
                  "aircraft_type": 10001,
                  "count": 30,
                  "price": 1000
                }
              ],
              "ammunition": [
                {
                  "ammunition_type": 1000,
                  "count": 1,
                  "price": 500
                }
              ],
              "price": 3500,	// 当前策略价格
              "time_range": {
                "start": 0,
                "end": 90
              },
              "aircraft_loss": [	// 当前策略的损失
                {
                  "aircraft_type": 10001,
                  "count": 3
                }
              ],
              "total_aircraft_loss": 3,	// 不考虑飞机类型的总损失数量
              "penetration_rate": 0.9,	
              "total_bingli": 30	// 当前策略的总出动兵力
            },
            "to_strategy_details": {	// 与from_strategy_details结构相同
              "aircraft": [
                {
                  "aircraft_type": 10003,
                  "count": 10,
                  "price": 2000
                }
              ],
              "ammunition": [
                {
                  "aircraft_type": 1000,
                  "count": 1,
                  "price": 500
                }
              ],
              "price": 10500,
              "time_range": {
                "start": 0,
                "end": 90
              },
              "aircraft_loss": [
                {
                  "aircraft_type": 10003,
                  "count": 5
                }
              ],
              "total_aircraft_loss": 5,
              "penetration_rate": 0.9,
              "total_bingli": 10
            },
            "price_difference": 7000,	// 当前策略替换前后，价格差异
            "is_saving": false,	// 当前策略替换前后，是否节省
            "loss_difference": 2,	// 当前策略替换前后，兵力损失数量差异
            "is_saving_loss": false,	// 当前策略替换前后，是否节省
            "bingli_difference": 20,	// 当前策略替换前后，兵力出动数量差异
            "is_saving_bingli": true,	// 当前策略替换前后，是否节省
            "desc": "在阶段[10]中，用分队[100]执行任务[1]替换为用分队[100]执行任务[3]，减少20兵力派遣"
          }
        ],
        "resource_usage": [	// 本替换方案的总资源使用情况
          {
            "army_id": 100,	// 分队ID
            "aircraft": [	// 分队载机使用情况
              {
                "aircraft_type": 10001,
                "total": 30,	// 总
                "used": 0,	// 出动了多少架次
                "loss": 0,	// 损失了多少架
                "remaining": 30	// 剩余多少架
              },
              {
                "aircraft_type": 10002,
                "total": 20,
                "used": 0,
                "loss": 0,
                "remaining": 20
              },
              {
                "aircraft_type": 10003,
                "total": 10,
                "used": 10,
                "loss": 5,
                "remaining": 5
              }
            ],
            "ammunition": [	// 分队弹使用情况
              {
                "ammunition_type": 1000,
                "total": 12,	// 总
                "used": 1,	// 用了多少
                "remaining": 11	// 剩余多少
              }
            ]
          }
        ],
        "replacement_type": 1,	// 0-原方案未优化 1-已优化方案
        "replacement_desc": "已优化方案"
      },
      ...
    ]
  }
}
```



### ~~版本：第二次对接 [待集成]~~
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
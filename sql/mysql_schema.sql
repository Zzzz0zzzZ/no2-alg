-- 创建数据库
CREATE DATABASE IF NOT EXISTS combat_simulation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE combat_simulation;

-- 创建空中交换比表
CREATE TABLE IF NOT EXISTS air_exchange_ratios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    our_aircraft_type VARCHAR(20) NOT NULL COMMENT '我方飞机类型',
    enemy_aircraft_type VARCHAR(20) NOT NULL COMMENT '敌方飞机类型',
    our_aircraft_ratio FLOAT NOT NULL COMMENT '我方损失比例',
    enemy_aircraft_ratio FLOAT NOT NULL COMMENT '敌方损失比例',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_aircraft_pair (our_aircraft_type, enemy_aircraft_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='空中飞机交换比数据';

-- 创建地面防御率表
CREATE TABLE IF NOT EXISTS ground_defense_rates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ground_type VARCHAR(20) NOT NULL COMMENT '地面防空设施类型',
    detection_hit_rate FLOAT NOT NULL COMMENT '命中率/发现率',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_ground_type (ground_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='地面防空设施命中率数据';

-- 插入一些示例数据
INSERT INTO air_exchange_ratios (our_aircraft_type, enemy_aircraft_type, our_aircraft_ratio, enemy_aircraft_ratio)
VALUES 
('10001', '100001', 1.0, 1.2),
('10001', '100002', 1.0, 1.1),
('10002', '100001', 1.0, 1.3),
('10002', '100002', 1.0, 1.2),
('10003', '100001', 1.0, 1.4),
('10003', '100002', 1.0, 1.3);

INSERT INTO ground_defense_rates (ground_type, detection_hit_rate)
VALUES 
('200001', 0.15),
('200002', 0.25); 
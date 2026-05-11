from __future__ import annotations


# 退改费率档位: (距起飞天数阈值, 退票费率, 改签费率)
REFUND_FEE_TIERS = [
    (30, 0.00, 0.00),
    (7, 0.20, 0.20),
    (3, 0.40, 0.40),
    (1, 0.60, 0.50),
    (0, 0.80, 0.60),
]

# 中转规则
TRANSIT_MIN_MINUTES = 120
TRANSIT_MAX_MINUTES = 360

# 临近机场距离上限
NEARBY_DISTANCE_MAX_KM = 300

# 航班实例初始化时经济舱标准票库存占比
ECONOMY_STANDARD_RATIO = 0.9

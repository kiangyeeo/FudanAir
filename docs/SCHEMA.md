# FudanAir航空票务管理数据库系统 — 数据库设计文档（SCHEMA）

| 项目名称 | 航空票务管理数据库系统                                       |
| -------- | ------------------------------------------------------------ |
| 文档版本 | v2.0                                                         |
| 编写日期 | 2026-05-10                                                   |
| 数据库   | MySQL 8.0+ / InnoDB                                          |
| 字符集   | utf8mb4 / utf8mb4_unicode_ci                                 |
| 配套文档 | PRD.md（业务规则）、ARCHITECTURE.md（应用层并发方案）、API.md（接口） |

---

## 0. 阅读指南

本文档是**数据库 schema 的唯一权威来源**。任何代码层面的字段名、类型、约束都必须与本文档一致；如有不一致以本文档为准。

文档结构：

- 第 1 节：全局约定（命名、类型、字符集）
- 第 2 节：实体清单（表 → 用途的映射表）
- 第 3 节：表结构详细定义（按"航班侧 / 用户侧 / 管理员侧"分组，逐表给出字段、约束、索引、典型查询）
- 第 4 节：跨表完整性约束（外键拓扑、应用层补充约束）
- 第 5 节：状态机字段枚举值映射
- 第 6 节：索引总览
- 第 7 节：视图建议
- 第 8 节：典型业务 SQL（防超卖、退改、中转推荐）
- 第 9 节：DDL 建表脚本（完整可执行）

---

## 1. 全局约定

### 1.1 命名规范

| 对象     | 命名风格                                             | 示例                                               |
| -------- | ---------------------------------------------------- | -------------------------------------------------- |
| 表名     | 全小写 + 下划线，单数                                | `user`, `flight_instance`, `admin_permission`      |
| 字段名   | 全小写 + 下划线                                      | `flight_no`, `created_at`, `actual_price`          |
| 主键     | 单字段时为 `id` 或业务键名；复合键由 PK 自身字段组成 | `user_id`, `(instance_id, cabin_class, fare_type)` |
| 外键字段 | 与被引用表主键同名，或加前缀                         | `user_id`, `dep_airport_code`                      |
| 索引     | `idx_<表>_<字段...>`；唯一索引 `uk_<表>_<字段>`      | `idx_ticket_order`, `uk_user_phone`                |
| 枚举值   | 中文（与业务术语一致，便于演示）                     | '经济舱', '已支付'                                 |

### 1.2 数据类型约定

| 语义                 | 推荐类型                           | 备注                                 |
| -------------------- | ---------------------------------- | ------------------------------------ |
| 整型主键（自增）     | `BIGINT UNSIGNED AUTO_INCREMENT`   | user_id, refund_id, notification_id  |
| 业务编号字符串       | `VARCHAR(32)`                      | order_no, ticket_no, instance_id     |
| IATA 二字码 / 三字码 | `CHAR(2)` / `CHAR(3)`              | airline.iata_code, airport.iata_code |
| 金额                 | `DECIMAL(10,2)` 或 `DECIMAL(12,2)` | 总额用 12,2，单价用 10,2             |
| 距离                 | `DECIMAL(6,2)`                     | 单位 km                              |
| 座位数（库存）       | `SMALLINT UNSIGNED`                | 经济舱最多约 850 座，足够            |
| 名称 / 标题          | `VARCHAR(64)` 或 `VARCHAR(128)`    | 视长度需求                           |
| 密码哈希             | `VARCHAR(255)`                     | bcrypt 哈希长度 60，留 buffer        |
| 时间戳               | `DATETIME`                         | 不使用 TIMESTAME（不区分时区）       |
| 日期                 | `DATE`                             | flight_date, birth_date              |
| 时刻                 | `TIME`                             | scheduled_departure                  |
| 布尔                 | `BOOLEAN`（即 TINYINT(1)）         | is_read                              |
| 枚举                 | `ENUM('值1','值2',...)`            | 状态字段、舱位等                     |

### 1.3 通用规则

- 所有表使用 **InnoDB** 引擎，支持事务与行锁。
- 字符集：`utf8mb4`，排序规则 `utf8mb4_unicode_ci`。
- 所有时间字段精确到秒（`DATETIME`）。
- 货币字段一律 `DECIMAL`，禁止使用 `FLOAT`/`DOUBLE`。
- 所有表都有明确的 PK；不允许"无主键表"。
- 删除策略以**软语义**为主：业务相关表通过状态字段标记作废（如 `ticket.status='已退'`），不直接物理删除；基础数据表（city、airport 等）允许物理删除，但应在应用层校验是否被引用。

---

## 2. 实体清单

系统共 **16** 张表，分三组：

### 2.1 航班侧（10 张）

| #    | 表名              | 中文名         | 主键                                    | 用途                              |
| ---- | ----------------- | -------------- | --------------------------------------- | --------------------------------- |
| 1    | `city`            | 城市表         | `city_name`                             | 国内城市的主数据                  |
| 2    | `city_near_apt`   | 城市临近机场表 | `(city_name, iata_code)`                | 表达"苏州→上海虹桥"等跨城临近关系 |
| 3    | `airport`         | 机场表         | `iata_code`                             | 机场基础信息                      |
| 4    | `airline`         | 航空公司表     | `iata_code`                             | 航司基础信息                      |
| 5    | `aircraft_type`   | 机型表         | `model`                                 | 机型与座位配置                    |
| 6    | `flight`          | 航班表         | `flight_no`                             | 抽象航线计划（不含日期）          |
| 7    | `flight_weekday`  | 航班飞行日表   | `(flight_no, weekday)`                  | 航班每周哪几天执行                |
| 8    | `flight_stopover` | 航班经停表     | `(flight_no, stop_order)`               | 中间经停机场                      |
| 9    | `flight_instance` | 航班实例表     | `instance_id`                           | 某航班在某日的执行                |
| 10   | `cabin_price`     | 舱位定价表     | `(instance_id, cabin_class, fare_type)` | 舱位 × 票价类型 × 库存与价格      |

### 2.2 用户侧（5 张）

| #    | 表名            | 中文名     | 主键        | 用途                 |
| ---- | --------------- | ---------- | ----------- | -------------------- |
| 11   | `user`          | 用户表     | `user_id`   | 系统注册旅客         |
| 12   | `passenger`     | 乘客表     | `id_no`     | 乘机人（按证件号）   |
| 13   | `aptorder`      | 订单表     | `order_no`  | 一次购买行为（容器） |
| 14   | `ticket`        | 客票表     | `ticket_no` | 单张乘机凭证         |
| 15   | `refund_change` | 退改记录表 | `refund_id` | 退票/改签操作日志    |

### 2.3 管理员侧（1 张）

| #    | 表名    | 中文名   | 主键       | 用途         |
| ---- | ------- | -------- | ---------- | ------------ |
| 16   | `admin` | 管理员表 | `admin_id` | 后台运营人员 |

---

## 3. 表结构详细定义

### 3.1 航班侧

#### 3.1.1 `city` 城市表

| 字段      | 类型        | 键/约束 | 可空 | 默认 | 说明                |
| --------- | ----------- | ------- | ---- | ---- | ------------------- |
| city_name | VARCHAR(32) | PK      | 否   | —    | 城市名（如 "北京"） |

**索引**：仅主键。

**示例数据**：`('北京')`, `('上海')`, `('苏州')`, `('昆山')`

---

#### 3.1.2 `airport` 机场表

| 字段         | 类型         | 键/约束                                          | 可空 | 默认 | 说明               |
| ------------ | ------------ | ------------------------------------------------ | ---- | ---- | ------------------ |
| iata_code    | CHAR(3)      | PK                                               | 否   | —    | 三字码（如 "PEK"） |
| airport_name | VARCHAR(128) | NOT NULL                                         | 否   | —    | 机场全称           |
| city_name    | VARCHAR(32)  | FK → city(city_name) ON UPDATE CASCADE, NOT NULL | 否   | —    | 所属城市           |

**示例数据**：`('PEK','北京首都国际机场','北京')`, `('PVG','上海浦东国际机场','上海')`

---

#### 3.1.3 `city_near_apt` 城市临近机场表

| 字段      | 类型         | 键/约束                                             | 可空 | 默认 | 说明                                         |
| --------- | ------------ | --------------------------------------------------- | ---- | ---- | -------------------------------------------- |
| city_name | VARCHAR(32)  | PK, FK → city(city_name) ON DELETE CASCADE          | 否   | —    | 城市名                                       |
| iata_code | CHAR(3)      | PK, FK → airport(iata_code) ON DELETE CASCADE       | 否   | —    | 临近机场三字码                               |
| distance  | DECIMAL(6,2) | NOT NULL, CHECK (distance >= 0 AND distance <= 300) | 否   | —    | 距离 km，当前城市的机场设定距离为0，上限 300 |

**业务约束**：

- `distance = 0` 表示该机场即位于该城市，是判定"该城市拥有机场"的统一查询入口。
- 同一城市的自有机场（`distance = 0`）记录可有多条（一城多机场场景，如上海有 SHA、PVG）。
- **一致性约束**：`distance = 0` 的记录必须与 `airport.city_name` 保持一致——即对每条 `airport(iata_code, city_name)`，`city_near_apt` 中必须存在对应的 `(city_name, iata_code, 0)`；反之亦然。该一致性由 `airport service` 在 create / update / delete 时双写维护。

**索引**：

- 主键复合索引自动建立
- `idx_near_apt_iata` ON `(iata_code)` — 反查"哪些城市把 SHA 视为临近机场"

**示例数据**：`('苏州','SHA',98.50)`, `('苏州','PVG',102.30)`, `('昆山','SHA',58.20)`

---

#### 3.1.4 `airline` 航空公司表

| 字段         | 类型         | 键/约束          | 可空 | 默认 | 说明                   |
| ------------ | ------------ | ---------------- | ---- | ---- | ---------------------- |
| iata_code    | CHAR(2)      | PK               | 否   | —    | IATA 二字码（如 "CA"） |
| airline_name | VARCHAR(128) | NOT NULL, UNIQUE | 否   | —    | 航司全称               |

**索引**：

- 主键
- `uk_airline_name` ON `(airline_name)` — 名称唯一

**示例数据**：`('CA','中国国际航空')`, `('MU','中国东方航空')`, `('CZ','中国南方航空')`

---

#### 3.1.5 `aircraft_type` 机型表

| 字段          | 类型              | 键/约束                              | 可空 | 默认 | 说明              |
| ------------- | ----------------- | ------------------------------------ | ---- | ---- | ----------------- |
| model         | VARCHAR(32)       | PK                                   | 否   | —    | 型号（如 "B738"） |
| economy_seats | SMALLINT UNSIGNED | NOT NULL, CHECK (economy_seats >= 0) | 否   | —    | 经济舱座位数      |
| first_seats   | SMALLINT UNSIGNED | NOT NULL, CHECK (first_seats >= 0)   | 否   | —    | 头等舱座位数      |

**业务约束**：`economy_seats + first_seats` 应大于 0（表层不约束，应用校验）。

**示例数据**：`('B738', 162, 8)`, `('A320', 150, 8)`, `('B77W', 311, 36)`

---

#### 3.1.6 `flight` 航班表

| 字段                | 类型          | 键/约束                               | 可空 | 默认 | 说明                  |
| ------------------- | ------------- | ------------------------------------- | ---- | ---- | --------------------- |
| flight_no           | VARCHAR(8)    | PK                                    | 否   | —    | 航班号（如 "CA1234"） |
| scheduled_departure | TIME          | NOT NULL                              | 否   | —    | 计划起飞时刻          |
| scheduled_arrival   | TIME          | NOT NULL                              | 否   | —    | 计划到达时刻          |
| fuel_infra_fee      | DECIMAL(10,2) | NOT NULL, CHECK (fuel_infra_fee >= 0) | 否   | 0.00 | 燃油基建附加费        |
| dep_airport_code    | CHAR(3)       | FK → airport(iata_code), NOT NULL     | 否   | —    | 起飞机场              |
| dep_terminal        | VARCHAR(8)    | —                                     | 是   | NULL | 起飞航站楼（如 "T3"） |
| arr_airport_code    | CHAR(3)       | FK → airport(iata_code), NOT NULL     | 否   | —    | 到达机场              |
| arr_terminal        | VARCHAR(8)    | —                                     | 是   | NULL | 到达航站楼            |
| airline_code        | CHAR(2)       | FK → airline(iata_code), NOT NULL     | 否   | —    | 所属航司              |
| aircraft_model      | VARCHAR(32)   | FK → aircraft_type(model), NOT NULL   | 否   | —    | 采用机型              |

**业务约束**：

- 应用层校验：`dep_airport_code != arr_airport_code`（起降不能同机场）。
- 应用层校验：`scheduled_arrival > scheduled_departure` 在不跨日的情况下，跨日由飞行时长字段（如有）判断；本项目暂以**简化处理**：到达时刻可早于起飞时刻表示次日到达。

**索引**：

- `idx_flight_route` ON `(dep_airport_code, arr_airport_code)` — 按航线查航班（**直飞搜索的核心索引**）
- `idx_flight_airline` ON `(airline_code)` — 按航司查
- `idx_flight_aircraft` ON `(aircraft_model)` — 按机型查（管理员维护时用）

**示例数据**：`('CA1234','08:00:00','10:30:00',50.00,'PEK','T3','SHA','T2','CA','B738')`

---

#### 3.1.7 `flight_weekday` 航班飞行日表

| 字段      | 类型       | 键/约束                                      | 可空 | 默认 | 说明                     |
| --------- | ---------- | -------------------------------------------- | ---- | ---- | ------------------------ |
| flight_no | VARCHAR(8) | PK, FK → flight(flight_no) ON DELETE CASCADE | 否   | —    | 航班号                   |
| weekday   | TINYINT    | PK, CHECK (weekday BETWEEN 1 AND 7)          | 否   | —    | 星期几（1=周一, 7=周日） |

**索引**：

- 主键复合索引
- `idx_weekday_flight` ON `(weekday, flight_no)` — 按星期反查（生成实例时用）

**示例数据**：`('CA1234',1)`, `('CA1234',3)`, `('CA1234',5)` — 表示周一三五

---

#### 3.1.8 `flight_stopover` 航班经停表

| 字段         | 类型             | 键/约束                                      | 可空 | 默认 | 说明     |
| ------------ | ---------------- | -------------------------------------------- | ---- | ---- | -------- |
| flight_no    | VARCHAR(8)       | PK, FK → flight(flight_no) ON DELETE CASCADE | 否   | —    | 航班号   |
| stop_order   | TINYINT UNSIGNED | PK, CHECK (stop_order >= 1)                  | 否   | —    | 经停顺序 |
| airport_code | CHAR(3)          | FK → airport(iata_code), NOT NULL            | 否   | —    | 经停机场 |

**业务约束**：

- 应用层校验：经停机场不能是起飞或到达机场。
- 同一航班内 `stop_order` 必须连续（从 1 起）。

**索引**：

- 主键
- `idx_stopover_airport` ON `(airport_code)` — 反查"哪些航班经停某机场"

---

#### 3.1.9 `flight_instance` 航班实例表

| 字段         | 类型                                                  | 键/约束                             | 可空 | 默认   | 说明                                                         |
| ------------ | ----------------------------------------------------- | ----------------------------------- | ---- | ------ | ------------------------------------------------------------ |
| instance_id  | VARCHAR(32)                                           | PK                                  | 否   | —      | 实例 ID（建议格式：`{flight_no}_{yyyymmdd}`，如 `CA1234_20260510`） |
| flight_no    | VARCHAR(8)                                            | FK → flight(flight_no), NOT NULL    | 否   | —      | 航班号                                                       |
| flight_date  | DATE                                                  | NOT NULL                            | 否   | —      | 执行日期                                                     |
| economy_left | SMALLINT UNSIGNED                                     | NOT NULL, CHECK (economy_left >= 0) | 否   | —      | 经济舱剩余座位（汇总值，= 该实例下经济舱所有 fare_type 的 available_seats 之和） |
| first_left   | SMALLINT UNSIGNED                                     | NOT NULL, CHECK (first_left >= 0)   | 否   | —      | 头等舱剩余座位（汇总值）                                     |
| status       | ENUM('计划','可订','已起飞','已到达','已取消','延误') | NOT NULL                            | 否   | '计划' | 航班实例状态                                                 |

**业务约束**：

- `UNIQUE(flight_no, flight_date)` — 同一航班同日只能一个实例。
- 初始化时：`economy_left ≤ aircraft_type.economy_seats`，`first_left ≤ aircraft_type.first_seats`（应用层校验）。
- `economy_left + first_left ≤ 机型总座位数`（应用层校验）。

**索引**：

- 主键 `instance_id`
- `uk_instance_flight_date` UNIQUE ON `(flight_no, flight_date)`
- `idx_instance_date_status` ON `(flight_date, status)` — 按日期查可订航班（搜索高频）

**示例数据**：`('CA1234_20260510','CA1234','2026-05-10',150,8,'可订')`

---

#### 3.1.10 `cabin_price` 舱位定价表

| 字段            | 类型                    | 键/约束                                                 | 可空 | 默认   | 说明                 |
| --------------- | ----------------------- | ------------------------------------------------------- | ---- | ------ | -------------------- |
| instance_id     | VARCHAR(32)             | PK, FK → flight_instance(instance_id) ON DELETE CASCADE | 否   | —      | 航班实例 ID          |
| cabin_class     | ENUM('经济舱','头等舱') | PK                                                      | 否   | —      | 舱位等级             |
| fare_type       | ENUM('标准','特价')     | PK                                                      | 否   | '标准' | 票价类型             |
| price           | DECIMAL(10,2)           | NOT NULL, CHECK (price >= 0)                            | 否   | —      | 该档位售价           |
| available_seats | SMALLINT UNSIGNED       | NOT NULL, CHECK (available_seats >= 0)                  | 否   | 0      | 该档位剩余可售座位数 |

**业务约束**：

- 头等舱通常没有"特价"档；应用层可校验（不强制）。
- 同一 `(instance_id, cabin_class)` 下，所有 `fare_type` 的 `available_seats` 之和应等于 `flight_instance` 的对应余票汇总字段。

**索引**：

- 主键 `(instance_id, cabin_class, fare_type)`
- `idx_cabin_price_instance` ON `(instance_id)` — 单独索引便于按实例查所有档位

**示例数据**：

```
('CA1234_20260510','经济舱','标准',  800.00, 145)
('CA1234_20260510','经济舱','特价',  500.00,   5)
('CA1234_20260510','头等舱','标准', 3000.00,   8)
```

---

### 3.2 用户侧

#### 3.2.1 `user` 用户表

| 字段          | 类型            | 键/约束            | 可空 | 默认 | 说明        |
| ------------- | --------------- | ------------------ | ---- | ---- | ----------- |
| user_id       | BIGINT UNSIGNED | PK, AUTO_INCREMENT | 否   | —    | 用户唯一 ID |
| user_password | VARCHAR(255)    | NOT NULL           | 否   | —    | bcrypt 哈希 |
| name          | VARCHAR(64)     | NOT NULL           | 否   | —    | 昵称        |
| phone         | VARCHAR(20)     | NOT NULL, UNIQUE   | 否   | —    | 手机号      |

**业务约束**：手机号格式校验在应用层（中国大陆 11 位）。

**索引**：

- 主键
- `uk_user_phone` UNIQUE ON `(phone)` — 登录用

---

#### 3.2.2 `passenger` 乘客表

| 字段       | 类型        | 键/约束  | 可空 | 默认 | 说明     |
| ---------- | ----------- | -------- | ---- | ---- | -------- |
| id_no      | VARCHAR(32) | PK       | 否   | —    | 证件号   |
| real_name  | VARCHAR(64) | NOT NULL | 否   | —    | 真实姓名 |
| birth_date | DATE        | NOT NULL | 否   | —    | 出生日期 |

> **设计说明**：乘客表与用户表是**多对多**关系（一个用户可绑定多位乘机人，一位乘机人可被多个用户绑定——例如父亲和儿子都把妈妈作为常用乘机人）。**当前设计未显式建立 user-passenger 关联表**，乘机人的归属通过 `ticket` 表的 `(order_no→user_id, passenger_id)` 间接表达。如需"我的常用乘机人"功能，需增加 `user_passenger(user_id, id_no)` 关联表。**本项目暂不实现该关联表**，"我的乘机人"通过查询历史订单中出现过的乘机人去重得到。

---

#### 3.2.3 `aptorder` 订单表

| 字段         | 类型                                                         | 键/约束                             | 可空 | 默认              | 说明                                             |
| ------------ | ------------------------------------------------------------ | ----------------------------------- | ---- | ----------------- | ------------------------------------------------ |
| order_no     | VARCHAR(32)                                                  | PK                                  | 否   | —                 | 订单号（建议格式：`O{yyyymmddHHmmss}{随机6位}`） |
| user_id      | BIGINT UNSIGNED                                              | FK → user(user_id), NOT NULL        | 否   | —                 | 下单用户                                         |
| total_amount | DECIMAL(12,2)                                                | NOT NULL, CHECK (total_amount >= 0) | 否   | —                 | 订单总金额                                       |
| status       | ENUM('待支付','已支付','已取消','已完成','部分退款','已完成退款') | NOT NULL                            | 否   | '待支付'          | 订单状态                                         |
| created_at   | DATETIME                                                     | NOT NULL                            | 否   | CURRENT_TIMESTAMP | 下单时间                                         |

**索引**：

- 主键
- `idx_order_user_created` ON `(user_id, created_at DESC)` — 我的订单（按时间倒序）
- `idx_order_status_created` ON `(status, created_at)` — **超时订单扫描的核心索引**（找出 `status='待支付' AND created_at < now()-15min` 的订单）

> 设计说明：订单状态相比 PPT 增加了 `'已完成退款'`，对应 PRD §7.1 的状态机终态。

---

#### 3.2.4 `ticket` 客票表

| 字段         | 类型                                      | 键/约束                             | 可空 | 默认   | 说明                                                         |
| ------------ | ----------------------------------------- | ----------------------------------- | ---- | ------ | ------------------------------------------------------------ |
| ticket_no    | VARCHAR(32)                               | PK                                  | 否   | —      | 票号（建议格式：`T{yyyymmdd}{递增9位}`）                     |
| order_no     | VARCHAR(32)                               | FK → aptorder(order_no), NOT NULL   | 否   | —      | 所属订单                                                     |
| passenger_id | VARCHAR(32)                               | FK → passenger(id_no), NOT NULL     | 否   | —      | 乘机人                                                       |
| instance_id  | VARCHAR(32)                               | FK 组合, NOT NULL                   | 否   | —      | 航班实例                                                     |
| cabin_class  | ENUM('经济舱','头等舱')                   | FK 组合, NOT NULL                   | 否   | —      | 舱位等级                                                     |
| fare_type    | ENUM('标准','特价')                       | FK 组合, NOT NULL                   | 否   | '标准' | 票价类型                                                     |
| actual_price | DECIMAL(10,2)                             | NOT NULL, CHECK (actual_price >= 0) | 否   | —      | 成交价（下单时刻 cabin_price.price+对应flight表中航班的燃油基建fuel_infra_fee） |
| status       | ENUM('有效','已退','已改签作废','已使用') | NOT NULL                            | 否   | '有效' | 客票状态                                                     |

**复合外键**：

```
FOREIGN KEY (instance_id, cabin_class, fare_type)
  REFERENCES cabin_price(instance_id, cabin_class, fare_type)
```

**业务约束**（应用层）：

- 同一乘客在同一航班实例上仅能有一张 `status='有效'` 的客票（防止重复购票；状态过滤无法直接用 UNIQUE 表达，应用校验）。

**索引**：

- 主键
- `idx_ticket_order` ON `(order_no)` — 按订单查所有票
- `idx_ticket_passenger` ON `(passenger_id)` — 反查乘客行程
- `idx_ticket_instance_status` ON `(instance_id, status)` — 查"某实例下还有多少有效票"

---

#### 3.2.5 `refund_change` 退改记录表

| 字段          | 类型                | 键/约束                          | 可空 | 默认              | 说明                                      |
| ------------- | ------------------- | -------------------------------- | ---- | ----------------- | ----------------------------------------- |
| refund_id     | BIGINT UNSIGNED     | PK, AUTO_INCREMENT               | 否   | —                 | 记录 ID                                   |
| ticket_no     | VARCHAR(32)         | FK → ticket(ticket_no), NOT NULL | 否   | —                 | 关联（旧）客票                            |
| op_type       | ENUM('退票','改签') | NOT NULL                         | 否   | —                 | 操作类型                                  |
| fee           | DECIMAL(10,2)       | NOT NULL, CHECK (fee >= 0)       | 否   | 0.00              | 手续费                                    |
| new_ticket_no | VARCHAR(32)         | FK → ticket(ticket_no)           | 是   | NULL              | 改签生成的新票号；退票为 NULL             |
| price_diff    | DECIMAL(10,2)       | NOT NULL                         | 否   | 0.00              | 改签差价（新成交价 − 旧成交价）；退票为 0 |
| op_time       | DATETIME            | NOT NULL                         | 否   | CURRENT_TIMESTAMP | 操作时间                                  |

**业务约束**（应用层）：

- `op_type='改签' ⇒ new_ticket_no IS NOT NULL`
- `op_type='退票' ⇒ new_ticket_no IS NULL AND price_diff = 0`

**索引**：

- 主键
- `idx_refund_ticket` ON `(ticket_no)` — 查某票退改历史
- `idx_refund_optime` ON `(op_time DESC)` — 时间倒序

---

### 3.3 管理员侧

#### 3.3.1 `admin` 管理员表

| 字段           | 类型         | 键/约束  | 可空 | 默认 | 说明           |
| -------------- | ------------ | -------- | ---- | ---- | -------------- |
| admin_id       | VARCHAR(32)  | PK       | 否   | —    | 管理员唯一编号 |
| admin_password | VARCHAR(255) | NOT NULL | 否   | —    | bcrypt 哈希    |
| admin_name     | VARCHAR(64)  | NOT NULL | 否   | —    | 管理员姓名     |

---

## 4. 跨表完整性约束

### 4.1 外键拓扑

```
city ──< city_near_apt >── airport
                                │
                                ├──< flight (dep_airport, arr_airport)
                                ├──< flight_stopover
                                │
airline ──< flight                   aircraft_type ──< flight
                                                          │
                                          flight ──< flight_weekday
                                          flight ──< flight_instance
                                                          │
                                          flight_instance ──< cabin_price
                                                                    │
user ──< aptorder ──< ticket >── passenger                          │
                          │                                          │
                          │ (instance_id, cabin_class, fare_type)──>┘
                          │
                          └──< refund_change >── (new_ticket_no → ticket)
```

### 4.2 应用层补充约束（无法/不便用 SQL 表达）

下列约束需在业务逻辑层强制执行，写入测试用例覆盖：

| 编号 | 约束                                                         | 强制位置                                                     |
| ---- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| AC-1 | 同一乘客在同一航班实例上仅能有 1 张有效客票                  | 下单时 SELECT 校验                                           |
| AC-2 | `cabin_price.available_seats` 之和 = `flight_instance.economy_left/first_left` | 事务内同步更新                                               |
| AC-3 | 改签记录的 `new_ticket_no` 不能等于 `ticket_no`（不能改到自己） | 应用层校验                                                   |
| AC-4 | `airport.city_name` 与 `city_near_apt` 中 `distance=0` 的记录表达同一语义"机场归属城市"，二者必须保持一致 | `airport service` 在 create/update/delete 时双写同步；新增 `city_near_apt` 记录时若 `distance=0` 校验是否与 `airport.city_name` 匹配 |
| AC-5 | `flight.dep_airport_code != flight.arr_airport_code`         | 维护时校验                                                   |
| AC-6 | `flight_instance.flight_date` 必须落在 `flight_weekday` 的允许日内 | 创建实例时校验                                               |
| AC-7 | `flight_stopover.airport_code` 不能是该航班的起飞或到达机场  | 维护时校验                                                   |
| AC-8 | 已起飞/已到达的实例不可再下单；已退/已改签作废的票不可再退改 | 业务流程校验                                                 |

---

## 5. 状态字段枚举值映射

### 5.1 `aptorder.status`

| 值         | 含义                     | 终态 |
| ---------- | ------------------------ | ---- |
| 待支付     | 已下单未支付，库存已锁定 | 否   |
| 已支付     | 已扣款                   | 否   |
| 已取消     | 超时未支付或主动取消     | 是   |
| 部分退款   | 订单内部分票已退         | 否   |
| 已完成退款 | 订单内所有票已退         | 是   |
| 已完成     | 所有票已乘机             | 是   |

### 5.2 `ticket.status`

| 值         | 含义                                                    | 终态 |
| ---------- | ------------------------------------------------------- | ---- |
| 有效       | 可用于乘机                                              | 否   |
| 已退       | 退票后                                                  | 是   |
| 已改签作废 | 改签的旧票（在 refund_change.new_ticket_no 中关联新票） | 是   |
| 已使用     | 已乘机                                                  | 是   |

### 5.3 `flight_instance.status`

| 值     | 含义                     | 终态 |
| ------ | ------------------------ | ---- |
| 计划   | 已生成实例，未开放售票   | 否   |
| 可订   | 开放售票                 | 否   |
| 已起飞 | 已起飞                   | 否   |
| 已到达 | 已到达                   | 是   |
| 已取消 | 航班取消（触发批量退款） | 是   |

---

## 6. 索引总览

### 6.1 索引清单

| 表              | 索引名                     | 字段                                 | 类型 | 用途             |
| --------------- | -------------------------- | ------------------------------------ | ---- | ---------------- |
| airport         | idx_airport_city           | city_name                            | 普通 | 按城市查机场     |
| city_near_apt   | idx_near_apt_iata          | iata_code                            | 普通 | 反查临近关系     |
| airline         | uk_airline_name            | airline_name                         | 唯一 | 名称唯一         |
| flight          | idx_flight_route           | (dep_airport_code, arr_airport_code) | 普通 | **直飞搜索**     |
| flight          | idx_flight_airline         | airline_code                         | 普通 | 按航司查         |
| flight          | idx_flight_aircraft        | aircraft_model                       | 普通 | 按机型查         |
| flight_weekday  | idx_weekday_flight         | (weekday, flight_no)                 | 普通 | 生成实例         |
| flight_stopover | idx_stopover_airport       | airport_code                         | 普通 | 反查经停         |
| flight_instance | uk_instance_flight_date    | (flight_no, flight_date)             | 唯一 | 同航班同日唯一   |
| flight_instance | idx_instance_date_status   | (flight_date, status)                | 普通 | **搜索可订航班** |
| cabin_price     | idx_cabin_price_instance   | instance_id                          | 普通 | 按实例聚合档位   |
| user            | uk_user_phone              | phone                                | 唯一 | 登录             |
| aptorder        | idx_order_user_created     | (user_id, created_at DESC)           | 普通 | 我的订单         |
| aptorder        | idx_order_status_created   | (status, created_at)                 | 普通 | **超时扫描**     |
| ticket          | idx_ticket_order           | order_no                             | 普通 | 订单详情         |
| ticket          | idx_ticket_passenger       | passenger_id                         | 普通 | 乘客行程         |
| ticket          | idx_ticket_instance_status | (instance_id, status)                | 普通 | 实例剩余有效票   |
| refund_change   | idx_refund_ticket          | ticket_no                            | 普通 | 退改历史         |
| refund_change   | idx_refund_optime          | op_time DESC                         | 普通 | 时序查询         |

### 6.2 索引设计原则

- **覆盖高频查询**：直飞搜索 `idx_flight_route`、超时扫描 `idx_order_status_created` 是最关键的两个索引。
- **避免过度索引**：写多读少的库存字段（`available_seats`、`economy_left`）不建索引——下单时是按主键定位，改完即写回。
- **复合索引顺序**：等值条件在前，范围条件在后；最常用的等值在最前。

---

## 7. 视图建议

为简化复杂查询，建议创建以下视图：

### 7.1 `v_flight_search` 航班搜索视图

```sql
CREATE VIEW v_flight_search AS
SELECT
    fi.instance_id,
    fi.flight_no,
    fi.flight_date,
    fi.status              AS instance_status,
    f.scheduled_departure,
    f.scheduled_arrival,
	f.fuel_infra_fee,
    f.dep_airport_code,
    dep_apt.city_name      AS dep_city,
    f.arr_airport_code,
    arr_apt.city_name      AS arr_city,
    f.airline_code,
    al.airline_name,
    f.aircraft_model,
    fi.economy_left,
    fi.first_left
FROM flight_instance fi
JOIN flight    f       ON fi.flight_no       = f.flight_no
JOIN airport   dep_apt ON f.dep_airport_code = dep_apt.iata_code
JOIN airport   arr_apt ON f.arr_airport_code = arr_apt.iata_code
JOIN airline   al      ON f.airline_code     = al.iata_code
WHERE fi.status IN ('可订');
```

> 用途：直飞搜索基础视图，避免多表 JOIN 重复书写。

### 7.2 `v_order_summary` 订单汇总视图

```sql
CREATE VIEW v_order_summary AS
SELECT
    o.order_no,
    o.user_id,
    u.name             AS user_name,
    o.total_amount,
    o.status,
    o.created_at,
    COUNT(t.ticket_no)                                              AS ticket_count,
    SUM(CASE WHEN t.status = '有效' THEN 1 ELSE 0 END)              AS active_count,
    SUM(CASE WHEN t.status = '已退' THEN 1 ELSE 0 END)              AS refunded_count
FROM aptorder o
JOIN user u   ON o.user_id  = u.user_id
LEFT JOIN ticket t ON o.order_no = t.order_no
GROUP BY o.order_no, o.user_id, u.name, o.total_amount, o.status, o.created_at;
```

> 用途：订单列表展示。

---

## 8. 典型业务 SQL

### 8.1 防超卖的下单事务

```sql
START TRANSACTION;

-- 1. 锁定目标档位行
SELECT available_seats, price
FROM cabin_price
WHERE instance_id = :instance_id
  AND cabin_class = :cabin_class
  AND fare_type   = :fare_type
FOR UPDATE;

-- 2. 应用层检查 available_seats >= :需求数；若不足则 ROLLBACK

-- 3. 扣减档位库存
UPDATE cabin_price
SET available_seats = available_seats - :n
WHERE instance_id = :instance_id
  AND cabin_class = :cabin_class
  AND fare_type   = :fare_type
  AND available_seats >= :n;
-- 校验影响行数 = 1，否则 ROLLBACK

-- 4. 同步汇总库存
UPDATE flight_instance
SET economy_left = economy_left - :n   -- 或 first_left
WHERE instance_id = :instance_id;

-- 5. 插入订单
INSERT INTO aptorder (order_no, user_id, total_amount, status, created_at)
VALUES (:order_no, :user_id, :amount, '待支付', NOW());

-- 6. 插入客票（每位乘机人一条）
INSERT INTO ticket (ticket_no, order_no, passenger_id, instance_id, cabin_class, fare_type, actual_price, status)
VALUES (:ticket_no, :order_no, :passenger_id, :instance_id, :cabin_class, :fare_type, :price, '有效');

COMMIT;
```

### 8.2 超时订单回补库存

```sql
-- 后台任务每分钟执行：
-- 找出超时未支付的订单
SELECT order_no
FROM aptorder
WHERE status = '待支付'
  AND created_at < NOW() - INTERVAL 15 MINUTE;

-- 对每个订单（事务内）：
START TRANSACTION;

-- 1. 改订单状态
UPDATE aptorder SET status = '已取消' WHERE order_no = :order_no AND status = '待支付';

-- 2. 改客票状态
UPDATE ticket SET status = '已退'
WHERE order_no = :order_no AND status = '有效';

-- 3. 回补 cabin_price 库存
UPDATE cabin_price cp
JOIN (
    SELECT instance_id, cabin_class, fare_type, COUNT(*) AS cnt
    FROM ticket WHERE order_no = :order_no AND status = '已退'
    GROUP BY instance_id, cabin_class, fare_type
) t ON cp.instance_id = t.instance_id
   AND cp.cabin_class = t.cabin_class
   AND cp.fare_type   = t.fare_type
SET cp.available_seats = cp.available_seats + t.cnt;

-- 4. 回补 flight_instance 汇总
-- （类似聚合更新，按 cabin_class 分组）

COMMIT;
```

### 8.3 中转推荐（核心 SQL，对应 PRD §4.6 C2）

```sql
-- 查询 :dep_city → :arr_city 在 :date 的中转方案
-- 约束：MCT 120 分钟，最大衔接 6 小时

SELECT
    leg1.instance_id  AS leg1_id,
    leg1.flight_no    AS leg1_flight,
    leg1.dep_airport_code AS leg1_dep,
    leg1.arr_airport_code AS transit_apt,
    leg1.scheduled_departure AS leg1_dep_time,
    leg1.scheduled_arrival   AS leg1_arr_time,
    leg2.instance_id  AS leg2_id,
    leg2.flight_no    AS leg2_flight,
    leg2.arr_airport_code AS leg2_arr,
    leg2.scheduled_departure AS leg2_dep_time,
    leg2.scheduled_arrival   AS leg2_arr_time,
    TIMESTAMPDIFF(MINUTE,
        TIMESTAMP(leg1.flight_date, leg1.scheduled_arrival),
        TIMESTAMP(leg2.flight_date, leg2.scheduled_departure)
    ) AS transit_minutes
FROM v_flight_search leg1
JOIN v_flight_search leg2
  ON leg1.arr_airport_code = leg2.dep_airport_code        -- 衔接机场相同
 AND leg1.dep_city  = :dep_city
 AND leg2.arr_city  = :arr_city
 AND leg1.flight_date = :date
 AND leg2.flight_date IN (:date, DATE_ADD(:date, INTERVAL 1 DAY))   -- 允许跨日
 AND TIMESTAMPDIFF(MINUTE,
        TIMESTAMP(leg1.flight_date, leg1.scheduled_arrival),
        TIMESTAMP(leg2.flight_date, leg2.scheduled_departure)
     ) BETWEEN 120 AND 360                                  -- 衔接时间窗口
WHERE leg1.economy_left > 0 AND leg2.economy_left > 0     -- 两段都有座
ORDER BY leg1.scheduled_departure;
```

> 这是数据库课的高分点：自连接 + 时间窗口约束 + 视图复用。

### 8.4 临近机场替代搜索

```sql
-- 当 :dep_city → :arr_city 无直飞时，扩展为"临近机场起飞"
-- 思路：UNION 出发城市 ∪ 出发城市的临近机场所属城市

SELECT * FROM v_flight_search
WHERE flight_date = :date
  AND (
        dep_city = :dep_city
     OR dep_airport_code IN (
            SELECT iata_code FROM city_near_apt WHERE city_name = :dep_city
        )
      )
  AND (
        arr_city = :arr_city
     OR arr_airport_code IN (
            SELECT iata_code FROM city_near_apt WHERE city_name = :arr_city
        )
      );
```

---

## 9. DDL 建表脚本

> 完整可执行脚本，按外键依赖顺序排列。复制粘贴可直接建库。

```sql
-- ============================================================
-- Airline Ticketing DB Schema
-- MySQL 8.0+ / InnoDB / utf8mb4
-- ============================================================

CREATE DATABASE IF NOT EXISTS airline_ticketing
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE airline_ticketing;

SET FOREIGN_KEY_CHECKS = 0;

-- ---------- 航班侧基础数据 ----------

CREATE TABLE city (
    city_name VARCHAR(32) NOT NULL,
    PRIMARY KEY (city_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE airport (
    iata_code     CHAR(3)       NOT NULL,
    airport_name  VARCHAR(128)  NOT NULL,
    city_name     VARCHAR(32)   NOT NULL,
    PRIMARY KEY (iata_code),
    KEY idx_airport_city (city_name),
    CONSTRAINT fk_airport_city FOREIGN KEY (city_name)
        REFERENCES city(city_name) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE city_near_apt (
    city_name  VARCHAR(32)  NOT NULL,
    iata_code  CHAR(3)      NOT NULL,
    distance   DECIMAL(6,2) NOT NULL,
    PRIMARY KEY (city_name, iata_code),
    KEY idx_near_apt_iata (iata_code),
    CONSTRAINT fk_near_city    FOREIGN KEY (city_name)
        REFERENCES city(city_name) ON DELETE CASCADE,
    CONSTRAINT fk_near_airport FOREIGN KEY (iata_code)
        REFERENCES airport(iata_code) ON DELETE CASCADE,
    CONSTRAINT chk_near_distance CHECK (distance >= 0 AND distance <= 300)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE airline (
    iata_code     CHAR(2)       NOT NULL,
    airline_name  VARCHAR(128)  NOT NULL,
    PRIMARY KEY (iata_code),
    UNIQUE KEY uk_airline_name (airline_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE aircraft_type (
    model           VARCHAR(32)        NOT NULL,
    economy_seats   SMALLINT UNSIGNED  NOT NULL,
    first_seats     SMALLINT UNSIGNED  NOT NULL,
    PRIMARY KEY (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- 航班 ----------

CREATE TABLE flight (
    flight_no             VARCHAR(8)     NOT NULL,
    scheduled_departure   TIME           NOT NULL,
    scheduled_arrival     TIME           NOT NULL,
    fuel_infra_fee        DECIMAL(10,2)  NOT NULL DEFAULT 0.00,
    dep_airport_code      CHAR(3)        NOT NULL,
    dep_terminal          VARCHAR(8)     DEFAULT NULL,
    arr_airport_code      CHAR(3)        NOT NULL,
    arr_terminal          VARCHAR(8)     DEFAULT NULL,
    airline_code          CHAR(2)        NOT NULL,
    aircraft_model        VARCHAR(32)    NOT NULL,
    PRIMARY KEY (flight_no),
    KEY idx_flight_route    (dep_airport_code, arr_airport_code),
    KEY idx_flight_airline  (airline_code),
    KEY idx_flight_aircraft (aircraft_model),
    CONSTRAINT fk_flight_dep      FOREIGN KEY (dep_airport_code) REFERENCES airport(iata_code),
    CONSTRAINT fk_flight_arr      FOREIGN KEY (arr_airport_code) REFERENCES airport(iata_code),
    CONSTRAINT fk_flight_airline  FOREIGN KEY (airline_code)     REFERENCES airline(iata_code),
    CONSTRAINT fk_flight_aircraft FOREIGN KEY (aircraft_model)   REFERENCES aircraft_type(model),
    CONSTRAINT chk_flight_fee CHECK (fuel_infra_fee >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE flight_weekday (
    flight_no  VARCHAR(8)  NOT NULL,
    weekday    TINYINT     NOT NULL,
    PRIMARY KEY (flight_no, weekday),
    KEY idx_weekday_flight (weekday, flight_no),
    CONSTRAINT fk_fw_flight FOREIGN KEY (flight_no)
        REFERENCES flight(flight_no) ON DELETE CASCADE,
    CONSTRAINT chk_weekday CHECK (weekday BETWEEN 1 AND 7)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE flight_stopover (
    flight_no     VARCHAR(8)         NOT NULL,
    stop_order    TINYINT UNSIGNED   NOT NULL,
    airport_code  CHAR(3)            NOT NULL,
    PRIMARY KEY (flight_no, stop_order),
    KEY idx_stopover_airport (airport_code),
    CONSTRAINT fk_fs_flight  FOREIGN KEY (flight_no)
        REFERENCES flight(flight_no) ON DELETE CASCADE,
    CONSTRAINT fk_fs_airport FOREIGN KEY (airport_code) REFERENCES airport(iata_code),
    CONSTRAINT chk_stop_order CHECK (stop_order >= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE flight_instance (
    instance_id    VARCHAR(32)         NOT NULL,
    flight_no      VARCHAR(8)          NOT NULL,
    flight_date    DATE                NOT NULL,
    economy_left   SMALLINT UNSIGNED   NOT NULL,
    first_left     SMALLINT UNSIGNED   NOT NULL,
    status         ENUM('计划','可订','已起飞','已到达','已取消') NOT NULL DEFAULT '计划',
    PRIMARY KEY (instance_id),
    UNIQUE KEY uk_instance_flight_date (flight_no, flight_date),
    KEY idx_instance_date_status (flight_date, status),
    CONSTRAINT fk_fi_flight FOREIGN KEY (flight_no) REFERENCES flight(flight_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cabin_price (
    instance_id      VARCHAR(32)         NOT NULL,
    cabin_class      ENUM('经济舱','头等舱')  NOT NULL,
    fare_type        ENUM('标准','特价')    NOT NULL DEFAULT '标准',
    price            DECIMAL(10,2)       NOT NULL,
    available_seats  SMALLINT UNSIGNED   NOT NULL DEFAULT 0,
    PRIMARY KEY (instance_id, cabin_class, fare_type),
    KEY idx_cabin_price_instance (instance_id),
    CONSTRAINT fk_cp_instance FOREIGN KEY (instance_id)
        REFERENCES flight_instance(instance_id) ON DELETE CASCADE,
    CONSTRAINT chk_cp_price CHECK (price >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- 用户 / 乘客 ----------

CREATE TABLE user (
    user_id        BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
    user_password  VARCHAR(255)     NOT NULL,
    name           VARCHAR(64)      NOT NULL,
    phone          VARCHAR(20)      NOT NULL,
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_user_phone (phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE passenger (
    id_no       VARCHAR(32)  NOT NULL,
    real_name   VARCHAR(64)  NOT NULL,
    birth_date  DATE         NOT NULL,
    PRIMARY KEY (id_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- 订单 / 客票 / 退改 ----------

CREATE TABLE aptorder (
    order_no      VARCHAR(32)      NOT NULL,
    user_id       BIGINT UNSIGNED  NOT NULL,
    total_amount  DECIMAL(12,2)    NOT NULL,
    status        ENUM('待支付','已支付','已取消','已完成','部分退款','已完成退款') NOT NULL DEFAULT '待支付',
    created_at    DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_no),
    KEY idx_order_user_created   (user_id, created_at),
    KEY idx_order_status_created (status, created_at),
    CONSTRAINT fk_order_user FOREIGN KEY (user_id) REFERENCES user(user_id),
    CONSTRAINT chk_order_amount CHECK (total_amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE ticket (
    ticket_no      VARCHAR(32)      NOT NULL,
    order_no       VARCHAR(32)      NOT NULL,
    passenger_id   VARCHAR(32)      NOT NULL,
    instance_id    VARCHAR(32)      NOT NULL,
    cabin_class    ENUM('经济舱','头等舱')   NOT NULL,
    fare_type      ENUM('标准','特价')     NOT NULL DEFAULT '标准',
    actual_price   DECIMAL(10,2)    NOT NULL,
    status         ENUM('有效','已退','已改签作废','已使用') NOT NULL DEFAULT '有效',
    PRIMARY KEY (ticket_no),
    KEY idx_ticket_order            (order_no),
    KEY idx_ticket_passenger        (passenger_id),
    KEY idx_ticket_instance_status  (instance_id, status),
    CONSTRAINT fk_ticket_order      FOREIGN KEY (order_no)     REFERENCES aptorder(order_no),
    CONSTRAINT fk_ticket_passenger  FOREIGN KEY (passenger_id) REFERENCES passenger(id_no),
    CONSTRAINT fk_ticket_cabinprice FOREIGN KEY (instance_id, cabin_class, fare_type)
        REFERENCES cabin_price(instance_id, cabin_class, fare_type),
    CONSTRAINT chk_ticket_price CHECK (actual_price >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE refund_change (
    refund_id      BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
    ticket_no      VARCHAR(32)      NOT NULL,
    op_type        ENUM('退票','改签') NOT NULL,
    fee            DECIMAL(10,2)    NOT NULL DEFAULT 0.00,
    new_ticket_no  VARCHAR(32)      DEFAULT NULL,
    price_diff     DECIMAL(10,2)    NOT NULL DEFAULT 0.00,
    op_time        DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (refund_id),
    KEY idx_refund_ticket  (ticket_no),
    KEY idx_refund_optime  (op_time),
    CONSTRAINT fk_rc_ticket     FOREIGN KEY (ticket_no)     REFERENCES ticket(ticket_no),
    CONSTRAINT fk_rc_new_ticket FOREIGN KEY (new_ticket_no) REFERENCES ticket(ticket_no),
    CONSTRAINT chk_rc_fee CHECK (fee >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- 管理员 ----------

CREATE TABLE admin (
    admin_id        VARCHAR(32)   NOT NULL,
    admin_password  VARCHAR(255)  NOT NULL,
    admin_name      VARCHAR(64)   NOT NULL,
    PRIMARY KEY (admin_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- ---------- 视图 ----------

CREATE OR REPLACE VIEW v_flight_search AS
SELECT
    fi.instance_id,
    fi.flight_no,
    fi.flight_date,
    fi.status              AS instance_status,
    f.scheduled_departure,
    f.scheduled_arrival,
    f.dep_airport_code,
    dep_apt.city_name      AS dep_city,
    f.arr_airport_code,
    arr_apt.city_name      AS arr_city,
    f.airline_code,
    al.airline_name,
    f.aircraft_model,
    fi.economy_left,
    fi.first_left
FROM flight_instance fi
JOIN flight    f       ON fi.flight_no       = f.flight_no
JOIN airport   dep_apt ON f.dep_airport_code = dep_apt.iata_code
JOIN airport   arr_apt ON f.arr_airport_code = arr_apt.iata_code
JOIN airline   al      ON f.airline_code     = al.iata_code
WHERE fi.status IN ('可订','延误');

CREATE OR REPLACE VIEW v_order_summary AS
SELECT
    o.order_no,
    o.user_id,
    u.name             AS user_name,
    o.total_amount,
    o.status,
    o.created_at,
    COUNT(t.ticket_no)                                 AS ticket_count,
    SUM(CASE WHEN t.status = '有效' THEN 1 ELSE 0 END) AS active_count,
    SUM(CASE WHEN t.status = '已退' THEN 1 ELSE 0 END) AS refunded_count
FROM aptorder o
JOIN user u    ON o.user_id  = u.user_id
LEFT JOIN ticket t ON o.order_no = t.order_no
GROUP BY o.order_no, o.user_id, u.name, o.total_amount, o.status, o.created_at;

-- ---------- 管理员账号硬编码 ----------
-- 密码 'admin123' 的 bcrypt 哈希，仅用于演示
INSERT INTO admin (admin_id, admin_password, admin_name) VALUES
    ('A001', '$2b$12$XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX', '系统管理员');
```

---



---

## 附录 ：变更记录

| 版本 | 日期       | 修订人 | 变更说明                                                     |
| ---- | ---------- | ------ | ------------------------------------------------------------ |
| v1.0 | 2026-05-09 | 王铿轶 | 基于 PRD v1.0 与期中 PPT 编写。相比期中 PPT 的主要变化：cabin_price 主键扩展为三元组 + 新增 available_seats；ticket 加 status/fare_type；refund_change 加 new_ticket_no/price_diff；删除 6 张 admin_manage_* 表，合并为 admin_permission；flight_instance 新增唯一约束 (flight_no, flight_date) |
| v2.0 | 2026-05-10 | 王铿轶 | 根据 PRD v2.0同步：删除 `admin_permission` 表；删除 AC-4 应用层约束；`flight_instance.status` 移除"延误"；ticket.actual_price 明确含燃油基建费；视图 `v_flight_search` 改 JOIN 来源并新增 fuel_infra_fee 字段；DDL 末尾新增管理员账号硬编码 |
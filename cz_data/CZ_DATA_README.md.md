# 南方航空模拟航线数据说明

本数据集共包含三个文件，用于演示航班计划、机型配置及每周运营日。**机型和航站楼（`dep_terminal` / `arr_terminal`）均为随机生成**，仅供测试或开发使用。

## 文件列表

| 文件名 | 说明 |
|--------|------|
| `China_Southern_Airlines_all_routes.csv` | 航班计划数据（航线、时刻、费用、机型、航站楼） |
| `机型.csv` | 机型座位配置（头等舱/经济舱座位数） |
| `每周飞行日2.csv` | 航班每周执飞日期（星期几） |

---

## 1. 航线数据 (`China_Southern_Airlines_all_routes.csv`)

### 字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `flight_no` | string | 航班号（如 CZ1520） |
| `scheduled_departure` | time | 计划起飞时间（本地时间） |
| `scheduled_arrival` | time | 计划到达时间（本地时间） |
| `fuel_infra_fee` | int | 燃油及基础设施费（单位：元） |
| `dep_airport_code` | string | 起飞机场三字码（如 TFU） |
| **`dep_terminal`** | string | **随机生成**的出发航站楼（如 T1, T2, T3） |
| `arr_airport_code` | string | 到达机场三字码 |
| **`arr_terminal`** | string | **随机生成**的到达航站楼 |
| `airline_code` | string | 航空公司代码（固定 CZ） |
| **`aircraft_model`** | string | **随机生成**的机型（如 C919, A321） |

### 数据示例

```csv
flight_no,scheduled_departure,scheduled_arrival,fuel_infra_fee,dep_airport_code,dep_terminal,arr_airport_code,arr_terminal,airline_code,aircraft_model
CZ1520,14:40:00,16:50:00,50,TFU,T1,BKK,T3,CZ,C919
CZ7008,14:55:00,18:15:00,50,JNH,T2,CTU,T1,CZ,A321
```
⚠️ 注意：dep_terminal、arr_terminal 及 aircraft_model 字段内容均为程序随机生成，与实际航班无必然对应关系。


## 2. 机型座位配置 (`机型.csv`)

### 字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `model` | string | 机型代码（与航线表中的 `aircraft_model` 对应） |
| `first_seats` | int | 头等舱座位数 |
| `economy_seats` | int | 经济舱座位数 |

### 数据示例
```
csv
model,first_seats,economy_seats
A388,428,78
B788,200,28
C919,156,8
```
## 3. 每周飞行日 (`每周飞行日2.csv`)

### 字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `flight_no` | string | 航班号 |
| `weekday` | int | 星期几（1 = 周一，7 = 周日） |

### 数据示例

```csv
flight_no,weekday
CZ1520,7
CZ7008,7
CZ32,7
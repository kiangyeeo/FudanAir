# FudanAir航空票务管理数据库系统 — 接口定义文档（API）

| 项目名称 | 航空票务管理数据库系统                                       |
| -------- | ------------------------------------------------------------ |
| 文档版本 | v2.0                                                         |
| 编写日期 | 2026-05-10                                                   |
| 协议     | HTTP/1.1 + JSON                                              |
| 基地址   | `http://localhost:8000`（开发）                              |
| 认证     | JWT via httpOnly Cookie                                      |
| 配套文档 | PRD.md、SCHEMA.md、ARCHITECTURE.md                           |

---

## 0. 阅读指南

本文档是前后端协作的**唯一接口契约**。

- §1 给所有接口共享的通用约定（认证、错误格式、分页、时间）
- §2 给接口清单总表（一张表索引所有接口）
- §3–§12 按模块分组，给每个接口的详细定义
- §13 给关键业务流程的接口调用序列（购票主流程、退改流程）
- §14 给错误码总览

**约定**：本文档中所有"必填"指请求体或查询参数中**必须传**；所有响应字段除非标注 `nullable`，否则一定有值。

---

## 1. 通用约定

### 1.1 认证

- **认证机制**：JWT，token 通过 **httpOnly cookie** 传递，前端不感知 token 内容。
- 登录成功后，后端通过 `Set-Cookie` 设置 `access_token`：

  ```
  Set-Cookie: access_token=<jwt>; HttpOnly; SameSite=Lax; Path=/; Max-Age=86400
  ```

- 后续请求由浏览器自动携带 cookie，前端无需手动注入 `Authorization` 头。
- token 过期或无效 → 返回 `401 Unauthorized`，前端跳转登录页。
- token payload：`{ sub, role, exp }`，`role ∈ {"user", "admin"}`。
- **跨域 cookie**：前端开发服务器（5173）与后端（8000）跨域时，axios 请求需设置 `withCredentials: true`；后端 CORS 中间件需 `allow_credentials=True` 且 `allow_origins` 明确指定为 `CORS_ORIGINS` 列表（不能用 `*`）。

### 1.2 角色与权限

每个接口标记三种访问要求：

| 标记         | 含义                              |
| ------------ | --------------------------------- |
| 🌐 `Public`   | 无需登录                          |
| 👤 `User`     | 需登录、role=user                 |
| 🛡️ `Admin`    | 需登录、role=admin                |

管理员权限不再分资源类型，所有管理员对所有基础数据有同等增删改查权限（参见 PRD §3.1）。

### 1.3 请求与响应

- **Content-Type**：所有请求/响应一律 `application/json; charset=utf-8`。
- **请求体**：POST、PUT、PATCH 使用 JSON body；GET 使用 query string。
- **响应体**：
  - 成功：直接返回数据对象或数组（不再包一层 `{data: ...}`）。
  - 失败：统一错误格式（见 §1.4）。

### 1.4 错误响应格式

所有 4xx/5xx 响应统一格式：

```json
{
  "code": "INSUFFICIENT_STOCK",
  "message": "available=2, need=3"
}
```

`code` 是机器可读的错误码（见 §14 总览）；`message` 是人类可读的描述，可直接展示给最终用户。

### 1.5 分页

列表型接口统一使用：

**请求**（query string）：

| 参数        | 类型 | 默认 | 说明                  |
| ----------- | ---- | ---- | --------------------- |
| `page`      | int  | 1    | 页码，从 1 起         |
| `page_size` | int  | 20   | 每页条数，上限 100    |

**响应**：

```json
{
  "items": [ ... ],
  "total": 156,
  "page": 1,
  "page_size": 20
}
```

### 1.6 时间格式

- 后端发送：ISO 8601 字符串。
  - 日期：`"2026-05-10"`
  - 时刻：`"08:00:00"`
  - 时间戳：`"2026-05-10T08:00:00"`（不带时区，默认 Asia/Shanghai）
- 前端收到后用 `utils/date.ts` 本地化展示。

### 1.7 金额格式

- 类型：`number`（JSON number），保留两位小数。
- 单位：人民币元，例如 `1234.50`。
- 前端展示前缀 `¥` 由前端处理。
- **成交价构成**：成交价 = `cabin_price.price` + `flight.fuel_infra_fee`（PRD §6.3）。下单时 `actual_price` 是这两项的瞬时快照。

### 1.8 ID 与编号格式

| 实体     | 字段         | 类型      | 格式示例               |
| -------- | ------------ | --------- | ---------------------- |
| 用户     | `user_id`    | int       | `12345`                |
| 管理员   | `admin_id`   | string    | `"A001"`               |
| 城市     | `city_name`  | string    | `"北京"`               |
| 机场     | `iata_code`  | string(3) | `"PEK"`                |
| 航司     | `iata_code`  | string(2) | `"CA"`                 |
| 航班     | `flight_no`  | string    | `"CA1234"`             |
| 航班实例 | `instance_id`| string    | `"CA1234_20260510"`    |
| 订单     | `order_no`   | string    | `"O20260509142301X3K9"`|
| 客票     | `ticket_no`  | string    | `"T20260510000001"`    |

---

## 2. 接口清单总表

| #   | 模块     | 方法   | 路径                                                         | 权限       | 简述                              |
| --- | -------- | ------ | ------------------------------------------------------------ | ---------- | --------------------------------- |
| 1   | 认证     | POST   | `/api/auth/register`                                         | 🌐         | 用户注册                          |
| 2   | 认证     | POST   | `/api/auth/login`                                            | 🌐         | 用户登录（签发 user cookie）      |
| 3   | 认证     | POST   | `/api/auth/admin-login`                                      | 🌐         | 管理员登录（签发 admin cookie）   |
| 4   | 认证     | POST   | `/api/auth/logout`                                           | 👤🛡️         | 登出（清除 cookie）               |
| 5   | 认证     | GET    | `/api/auth/me`                                               | 👤🛡️         | 当前身份信息                      |
| 6   | 用户     | GET    | `/api/users/me`                                              | 👤         | 获取个人信息                      |
| 7   | 用户     | PATCH  | `/api/users/me`                                              | 👤         | 修改个人信息                      |
| 8   | 用户     | POST   | `/api/users/me/password`                                     | 👤         | 修改密码                          |
| 9   | 乘机人   | GET    | `/api/passengers`                                            | 👤         | 我的常用乘机人                    |
| 10  | 乘机人   | POST   | `/api/passengers`                                            | 👤         | 新增乘机人                        |
| 11  | 乘机人   | PUT    | `/api/passengers/{id_no}`                                    | 👤         | 修改乘机人                        |
| 12  | 乘机人   | DELETE | `/api/passengers/{id_no}`                                    | 👤         | 解绑乘机人                        |
| 13  | 城市     | GET    | `/api/cities`                                                | 🌐         | 城市列表                          |
| 14  | 城市     | POST   | `/api/cities`                                                | 🛡️         | 新增城市                          |
| 15  | 城市     | DELETE | `/api/cities/{name}`                                         | 🛡️         | 删除城市                          |
| 16  | 城市     | GET    | `/api/cities/{name}/near-airports`                           | 🌐         | 临近机场                          |
| 17  | 城市     | POST   | `/api/cities/{name}/near-airports`                           | 🛡️         | 新增临近关系                      |
| 18  | 城市     | DELETE | `/api/cities/{name}/near-airports/{iata}`                    | 🛡️         | 删除临近关系                      |
| 19  | 机场     | GET    | `/api/airports`                                              | 🌐         | 机场列表                          |
| 20  | 机场     | GET    | `/api/airports/{iata}`                                       | 🌐         | 机场详情                          |
| 21  | 机场     | POST   | `/api/airports`                                              | 🛡️         | 新增机场（双写 city_near_apt）    |
| 22  | 机场     | PUT    | `/api/airports/{iata}`                                       | 🛡️         | 修改机场                          |
| 23  | 机场     | DELETE | `/api/airports/{iata}`                                       | 🛡️         | 删除机场                          |
| 24  | 航司     | GET    | `/api/airlines`                                              | 🌐         | 航司列表                          |
| 25  | 航司     | POST   | `/api/airlines`                                              | 🛡️         | 新增                              |
| 26  | 航司     | PUT    | `/api/airlines/{iata}`                                       | 🛡️         | 修改                              |
| 27  | 航司     | DELETE | `/api/airlines/{iata}`                                       | 🛡️         | 删除                              |
| 28  | 机型     | GET    | `/api/aircraft-types`                                        | 🌐         | 机型列表                          |
| 29  | 机型     | POST   | `/api/aircraft-types`                                        | 🛡️         | 新增                              |
| 30  | 机型     | PUT    | `/api/aircraft-types/{model}`                                | 🛡️         | 修改                              |
| 31  | 机型     | DELETE | `/api/aircraft-types/{model}`                                | 🛡️         | 删除                              |
| 32  | 航班     | GET    | `/api/flights`                                               | 🌐         | 航班列表                          |
| 33  | 航班     | GET    | `/api/flights/{flight_no}`                                   | 🌐         | 航班详情（含经停、飞行日）        |
| 34  | 航班     | POST   | `/api/flights`                                               | 🛡️         | 新增航班                          |
| 35  | 航班     | PUT    | `/api/flights/{flight_no}`                                   | 🛡️         | 修改                              |
| 36  | 航班     | DELETE | `/api/flights/{flight_no}`                                   | 🛡️         | 删除                              |
| 37  | 航班实例 | GET    | `/api/flight-instances`                                      | 🌐         | 实例列表（按航班/日期筛）         |
| 38  | 航班实例 | GET    | `/api/flight-instances/{instance_id}`                        | 🌐         | 实例详情（含定价档位）            |
| 39  | 航班实例 | POST   | `/api/flight-instances`                                      | 🛡️         | 创建单个实例                      |
| 40  | 航班实例 | POST   | `/api/flight-instances/batch-generate`                       | 🛡️         | 按航班批量生成                    |
| 41  | 航班实例 | PATCH  | `/api/flight-instances/{instance_id}/status`                 | 🛡️         | 修改状态（取消等）                |
| 42  | 航班实例 | DELETE | `/api/flight-instances/{instance_id}`                        | 🛡️         | 删除                              |
| 43  | 舱位定价 | GET    | `/api/flight-instances/{instance_id}/cabin-prices`           | 🌐         | 某实例所有档位                    |
| 44  | 舱位定价 | PUT    | `/api/flight-instances/{instance_id}/cabin-prices`           | 🛡️         | 批量设置档位（替换）              |
| 45  | 搜索     | POST   | `/api/search/flights`                                        | 🌐         | 三类候选合并搜索                  |
| 46  | 搜索     | POST   | `/api/search/transit`                                        | 🌐         | 中转方案搜索（独立调用）          |
| 47  | 下单     | POST   | `/api/booking`                                               | 👤         | 下单（事务）                      |
| 48  | 下单     | POST   | `/api/booking/{order_no}/pay`                                | 👤         | 模拟支付                          |
| 49  | 下单     | POST   | `/api/booking/{order_no}/cancel`                             | 👤         | 主动取消（仅未支付）              |
| 50  | 订单     | GET    | `/api/orders`                                                | 👤         | 我的订单（分页）                  |
| 51  | 订单     | GET    | `/api/orders/{order_no}`                                     | 👤         | 订单详情（含客票）                |
| 52  | 订单     | GET    | `/api/admin/orders`                                          | 🛡️         | 管理员查所有订单                  |
| 53  | 退改     | POST   | `/api/refund/refund`                                         | 👤         | 退票                              |
| 54  | 退改     | POST   | `/api/refund/change`                                         | 👤         | 改签                              |
| 55  | 退改     | GET    | `/api/refund/quote`                                          | 👤         | 试算手续费/差价                   |
| 56  | 退改     | GET    | `/api/refund/records`                                        | 👤         | 我的退改记录                      |

> 共 **56** 个接口。下面按模块详细展开。

---

## 3. 认证模块

### 3.1 用户注册

`POST /api/auth/register` — 🌐 Public

**请求体**：

```json
{
  "phone": "13800138000",
  "password": "abc123456",
  "name": "张三"
}
```

| 字段     | 类型   | 必填 | 校验                          |
| -------- | ------ | ---- | ----------------------------- |
| phone    | string | ✅   | 中国大陆 11 位手机号          |
| password | string | ✅   | 长度 6–32                     |
| name     | string | ✅   | 长度 1–64                     |

**响应**：`200 OK`

```json
{ "user_id": 12345, "phone": "13800138000", "name": "张三" }
```

注册不自动登录，前端需引导跳转登录页。

**错误**：`PHONE_ALREADY_EXISTS`、`INVALID_PHONE_FORMAT`。

### 3.2 用户登录

`POST /api/auth/login` — 🌐 Public

**请求体**：

```json
{ "phone": "13800138000", "password": "abc123456" }
```

**响应**：`200 OK`，同时通过 `Set-Cookie` 注入 `access_token`（HttpOnly, role=user）。

```json
{ "user_id": 12345, "phone": "13800138000", "name": "张三", "role": "user" }
```

**错误**：`AUTHENTICATION_FAILED`。

### 3.3 管理员登录

`POST /api/auth/admin-login` — 🌐 Public

**请求体**：

```json
{ "admin_id": "A001", "password": "..." }
```

**响应**：`200 OK`，通过 `Set-Cookie` 注入 `access_token`（HttpOnly, role=admin）。

```json
{ "admin_id": "A001", "name": "系统管理员", "role": "admin" }
```

管理员账号由 `scripts/init_db.py` 初始化时硬编码注入，不开放运行时创建。

### 3.4 登出

`POST /api/auth/logout` — 👤🛡️

清除 `access_token` cookie。

**响应**：`204 No Content`。

### 3.5 当前身份

`GET /api/auth/me` — 👤🛡️

**响应**（user）：

```json
{ "role": "user", "user_id": 12345, "name": "张三", "phone": "13800138000" }
```

**响应**（admin）：

```json
{ "role": "admin", "admin_id": "A001", "name": "系统管理员" }
```

---

## 4. 用户与乘机人模块

### 4.1 获取个人信息

`GET /api/users/me` — 👤

**响应**：

```json
{ "user_id": 12345, "phone": "13800138000", "name": "张三" }
```

### 4.2 修改个人信息

`PATCH /api/users/me` — 👤

**请求体**（任一字段可选）：

```json
{ "name": "李四", "phone": "13900139000" }
```

### 4.3 修改密码

`POST /api/users/me/password` — 👤

```json
{ "old_password": "abc123456", "new_password": "newpass789" }
```

**错误**：`OLD_PASSWORD_MISMATCH`。

### 4.4 我的常用乘机人

`GET /api/passengers` — 👤

返回该用户历史订单中出现过的乘机人去重列表（参见 SCHEMA §3.2.2 设计说明）。

**响应**：

```json
[
  { "id_no": "110101199001011234", "real_name": "张三", "birth_date": "1990-01-01" },
  { "id_no": "110101199203033456", "real_name": "李四", "birth_date": "1992-03-03" }
]
```

### 4.5 新增乘机人

`POST /api/passengers` — 👤

```json
{ "id_no": "...", "real_name": "...", "birth_date": "1990-01-01" }
```

### 4.6 修改乘机人

`PUT /api/passengers/{id_no}` — 👤

### 4.7 解绑乘机人

`DELETE /api/passengers/{id_no}` — 👤

> 解绑仅清除"我的常用"语义，已开出的客票不受影响。

---

## 5. 城市与临近机场模块

### 5.1 城市列表

`GET /api/cities` — 🌐

**响应**：

```json
[ "北京", "上海", "广州", "苏州", "昆山" ]
```

### 5.2 新增城市

`POST /api/cities` — 🛡️

```json
{ "city_name": "杭州" }
```

### 5.3 删除城市

`DELETE /api/cities/{name}` — 🛡️

> 若城市仍有 `airport.city_name` 引用，返回 `RESOURCE_IN_USE`。

### 5.4 临近机场列表

`GET /api/cities/{name}/near-airports` — 🌐

**响应**：

```json
[
  { "iata_code": "SHA", "airport_name": "上海虹桥国际机场", "distance": 0.00 },
  { "iata_code": "PVG", "airport_name": "上海浦东国际机场", "distance": 0.00 },
  { "iata_code": "HGH", "airport_name": "杭州萧山国际机场", "distance": 165.50 }
]
```

`distance = 0` 表示该机场即位于该城市（PRD §6.5）。`distance` 取值范围 `[0, 300]`。

### 5.5 新增临近关系

`POST /api/cities/{name}/near-airports` — 🛡️

```json
{ "iata_code": "HGH", "distance": 165.50 }
```

> 若 `distance = 0`，必须满足 `airport(iata_code).city_name == name`，否则返回 `INCONSISTENT_AIRPORT_CITY`（参见 SCHEMA §3.1.3 一致性约束）。

### 5.6 删除临近关系

`DELETE /api/cities/{name}/near-airports/{iata}` — 🛡️

> 若拟删除的记录 `distance = 0` 且 `airport(iata).city_name == name`，须先修改或删除对应 airport 记录，否则返回 `INCONSISTENT_AIRPORT_CITY`。

---

## 6. 机场模块

### 6.1 机场列表

`GET /api/airports` — 🌐

**Query**：`?city=上海` 可选过滤。

**响应**：

```json
[
  { "iata_code": "PEK", "airport_name": "北京首都国际机场", "city_name": "北京" },
  { "iata_code": "PKX", "airport_name": "北京大兴国际机场", "city_name": "北京" }
]
```

### 6.2 机场详情

`GET /api/airports/{iata}` — 🌐

### 6.3 新增机场

`POST /api/airports` — 🛡️

```json
{ "iata_code": "HGH", "airport_name": "杭州萧山国际机场", "city_name": "杭州" }
```

> **双写规则**（事务内）：同时插入 `airport` 和 `city_near_apt(city_name, iata_code, 0)`，参见 ARCHITECTURE §5.7。

### 6.4 修改机场

`PUT /api/airports/{iata}` — 🛡️

若修改 `city_name`，事务内同步删除旧 `city_near_apt(old_city, iata, 0)` 并插入新 `city_near_apt(new_city, iata, 0)`。

### 6.5 删除机场

`DELETE /api/airports/{iata}` — 🛡️

> 若机场仍被 `flight` 引用为起飞/到达/经停机场，返回 `RESOURCE_IN_USE`。
> 删除成功后，`city_near_apt` 中所有引用该 iata_code 的记录由数据库 `ON DELETE CASCADE` 自动清理。

---

## 7. 航司与机型模块

### 7.1 航司列表 / CRUD

`GET / POST / PUT / DELETE /api/airlines` — GET 🌐，写操作 🛡️

```json
{ "iata_code": "CA", "airline_name": "中国国际航空" }
```

### 7.2 机型列表 / CRUD

`GET / POST / PUT / DELETE /api/aircraft-types` — GET 🌐，写操作 🛡️

```json
{ "model": "B738", "economy_seats": 162, "first_seats": 8 }
```

> 删除约束：若机型仍被 `flight.aircraft_model` 引用，返回 `RESOURCE_IN_USE`。

---

## 8. 航班与航班实例模块

### 8.1 航班列表

`GET /api/flights` — 🌐

**Query** 可选过滤：`airline`、`dep_airport`、`arr_airport`。

### 8.2 航班详情

`GET /api/flights/{flight_no}` — 🌐

**响应**：

```json
{
  "flight_no": "CA1234",
  "scheduled_departure": "08:00:00",
  "scheduled_arrival": "10:30:00",
  "fuel_infra_fee": 50.00,
  "dep_airport_code": "PEK",
  "dep_terminal": "T3",
  "arr_airport_code": "SHA",
  "arr_terminal": "T2",
  "airline_code": "CA",
  "airline_name": "中国国际航空",
  "aircraft_model": "B738",
  "weekdays": [1, 3, 5],
  "stopovers": []
}
```

### 8.3 新增航班

`POST /api/flights` — 🛡️

```json
{
  "flight_no": "CA1234",
  "scheduled_departure": "08:00:00",
  "scheduled_arrival": "10:30:00",
  "fuel_infra_fee": 50.00,
  "dep_airport_code": "PEK",
  "dep_terminal": "T3",
  "arr_airport_code": "SHA",
  "arr_terminal": "T2",
  "airline_code": "CA",
  "aircraft_model": "B738",
  "weekdays": [1, 3, 5],
  "stopovers": []
}
```

> 服务端校验：`dep_airport_code != arr_airport_code`；经停机场不能是起飞或到达机场（AC-5、AC-7）。

### 8.4 修改航班

`PUT /api/flights/{flight_no}` — 🛡️

### 8.5 删除航班

`DELETE /api/flights/{flight_no}` — 🛡️

> 级联：`flight_weekday`、`flight_stopover` 自动清理。但若已有 `flight_instance` 引用，返回 `RESOURCE_IN_USE`。

### 8.6 航班实例列表

`GET /api/flight-instances` — 🌐

**Query**：`flight_no`、`flight_date`、`status`。

### 8.7 航班实例详情

`GET /api/flight-instances/{instance_id}` — 🌐

**响应**：

```json
{
  "instance_id": "CA1234_20260510",
  "flight_no": "CA1234",
  "flight_date": "2026-05-10",
  "status": "可订",
  "economy_left": 145,
  "first_left": 8,
  "scheduled_departure": "08:00:00",
  "scheduled_arrival": "10:30:00",
  "fuel_infra_fee": 50.00,
  "dep_airport_code": "PEK",
  "arr_airport_code": "SHA",
  "airline_code": "CA",
  "airline_name": "中国国际航空",
  "cabin_prices": [
    { "cabin_class": "经济舱", "fare_type": "标准", "price": 800.00, "available_seats": 145 },
    { "cabin_class": "经济舱", "fare_type": "特价", "price": 500.00, "available_seats": 5 },
    { "cabin_class": "头等舱", "fare_type": "标准", "price": 3000.00, "available_seats": 8 }
  ]
}
```

### 8.8 创建单个实例

`POST /api/flight-instances` — 🛡️

```json
{ "flight_no": "CA1234", "flight_date": "2026-05-10" }
```

服务端按机型座位数初始化 `economy_left` / `first_left`，并按预设规则创建 `cabin_price` 档位。

### 8.9 按航班批量生成实例

`POST /api/flight-instances/batch-generate` — 🛡️

```json
{ "flight_no": "CA1234", "start_date": "2026-05-10", "end_date": "2026-08-10" }
```

服务端遍历日期区间，对落在 `flight_weekday` 内的日期创建实例。

### 8.10 修改航班实例状态

`PATCH /api/flight-instances/{instance_id}/status` — 🛡️

```json
{ "status": "已取消" }
```

| 允许值     | 说明                              |
| ---------- | --------------------------------- |
| `计划`     | 已生成实例，未开放售票            |
| `可订`     | 开放售票                          |
| `已起飞`   | 已起飞                            |
| `已到达`   | 已到达                            |
| `已取消`   | 航班取消，触发批量退款            |

> v2.0 已删除"延误"状态（PRD §7.3）。
> 若改为 `已取消`，服务端在事务内对所有该实例的有效客票发起退款流程。

### 8.11 删除航班实例

`DELETE /api/flight-instances/{instance_id}` — 🛡️

> 仅当实例下无任何客票时允许删除，否则返回 `RESOURCE_IN_USE`。

### 8.12 查询舱位定价

`GET /api/flight-instances/{instance_id}/cabin-prices` — 🌐

### 8.13 批量设置舱位定价

`PUT /api/flight-instances/{instance_id}/cabin-prices` — 🛡️

```json
{
  "cabin_prices": [
    { "cabin_class": "经济舱", "fare_type": "标准", "price": 800.00, "available_seats": 145 },
    { "cabin_class": "经济舱", "fare_type": "特价", "price": 500.00, "available_seats": 5 },
    { "cabin_class": "头等舱", "fare_type": "标准", "price": 3000.00, "available_seats": 8 }
  ]
}
```

> 服务端事务内同步刷新 `flight_instance.economy_left/first_left` 汇总值（参见 PRD §6.1 库存双重表达）。

---

## 9. 航班搜索模块

### 9.1 三类候选合并搜索

`POST /api/search/flights` — 🌐

**请求体**：

```json
{
  "dep_city": "上海",
  "arr_city": "北京",
  "flight_date": "2026-05-10",
  "filters": {
    "airline_code": null,
    "cabin_class": null,
    "departure_time_range": null,
    "include_stopover": true
  },
  "sort": { "field": "price", "order": "asc" }
}
```

| sort.field 可选 | 说明                |
| --------------- | ------------------- |
| `price`         | 按最低档价格排序    |
| `duration`      | 按总时长排序        |
| `departure`     | 按起飞时间排序      |

**响应**：

```json
{
  "direct": [
    {
      "type": "direct",
      "instance_id": "CA1234_20260510",
      "flight_no": "CA1234",
      "dep_airport_code": "PEK",
      "arr_airport_code": "SHA",
      "scheduled_departure": "08:00:00",
      "scheduled_arrival": "10:30:00",
      "airline_code": "CA",
      "airline_name": "中国国际航空",
      "min_price": 850.00,
      "economy_left": 145,
      "first_left": 8
    }
  ],
  "transit": [
    {
      "type": "transit",
      "leg1": { "instance_id": "...", "flight_no": "...", "..." : "..." },
      "leg2": { "instance_id": "...", "flight_no": "...", "..." : "..." },
      "transit_airport": "XIY",
      "transit_minutes": 180,
      "total_duration_minutes": 480,
      "total_min_price": 1200.00
    }
  ],
  "nearby": [
    {
      "type": "nearby",
      "replacement": "departure",
      "replaced_airport": "SHA",
      "actual_dep_city": "苏州",
      "instance_id": "...",
      "flight_no": "...",
      "...": "..."
    }
  ]
}
```

每条候选必须带 `type` 字段（`direct` / `transit` / `nearby`），前端据此分组展示（PRD §4.3 F1）。

`min_price` 含燃油基建费（`cabin_price.price` 最低档 + `flight.fuel_infra_fee`）。

### 9.2 中转方案搜索（独立调用）

`POST /api/search/transit` — 🌐

请求/响应格式同 §9.1 的 `transit` 部分。

中转规则（PRD §6.4）：
- 第一段到达机场 = 第二段起飞机场
- 衔接时间 ∈ [**120 分钟**, 360 分钟]
- 仅返回两段都有可售座位的组合
- 仅支持单次中转

---

## 10. 下单模块

### 10.1 创建订单

`POST /api/booking` — 👤

**请求体**：

```json
{
  "instance_id": "CA1234_20260510",
  "cabin_class": "经济舱",
  "fare_type": "标准",
  "passengers": [
    { "id_no": "110101199001011234", "real_name": "张三", "birth_date": "1990-01-01" },
    { "id_no": "110101199203033456", "real_name": "李四", "birth_date": "1992-03-03" }
  ]
}
```

**响应**：`201 Created`

```json
{
  "order_no": "O20260509142301X3K9",
  "status": "待支付",
  "total_amount": 1700.00,
  "amount_breakdown": {
    "ticket_price_per_seat": 800.00,
    "fuel_infra_fee_per_seat": 50.00,
    "seat_count": 2
  },
  "created_at": "2026-05-09T14:23:01",
  "expires_at": "2026-05-09T14:38:01",
  "tickets": [
    { "ticket_no": "T20260509000001", "passenger_id": "110101199001011234", "actual_price": 850.00 },
    { "ticket_no": "T20260509000002", "passenger_id": "110101199203033456", "actual_price": 850.00 }
  ]
}
```

> **金额计算**：`actual_price` = `cabin_price.price` + `flight.fuel_infra_fee`；`total_amount` = `actual_price` × 乘机人数。
> **事务**：步骤参见 PRD §4.4 O2。

**错误**：`INSUFFICIENT_STOCK`、`PASSENGER_DUPLICATE`（同乘机人在该实例已有有效票）、`INSTANCE_NOT_BOOKABLE`。

### 10.2 模拟支付

`POST /api/booking/{order_no}/pay` — 👤

**响应**：

```json
{ "order_no": "...", "status": "已支付", "paid_at": "2026-05-09T14:25:30" }
```

**错误**：`ORDER_NOT_PAYABLE`（已超时或非待支付状态）。

### 10.3 主动取消

`POST /api/booking/{order_no}/cancel` — 👤

仅允许 `status='待支付'` 的订单。事务内回补库存、订单状态 → `已取消`、客票状态 → `已退`。

---

## 11. 订单查询模块

### 11.1 我的订单

`GET /api/orders` — 👤

**Query**：`page`、`page_size`、`status`（可选筛选）。

**响应**：分页结构，每项含订单基础信息 + 票数汇总。

### 11.2 订单详情

`GET /api/orders/{order_no}` — 👤

**响应**：

```json
{
  "order_no": "O20260509142301X3K9",
  "user_id": 12345,
  "status": "已支付",
  "total_amount": 1700.00,
  "created_at": "2026-05-09T14:23:01",
  "tickets": [
    {
      "ticket_no": "T20260509000001",
      "passenger": { "id_no": "...", "real_name": "张三" },
      "instance_id": "CA1234_20260510",
      "flight_no": "CA1234",
      "flight_date": "2026-05-10",
      "scheduled_departure": "08:00:00",
      "dep_airport_code": "PEK",
      "arr_airport_code": "SHA",
      "adjustment_labels": ["起飞时间已调整"],
      "cabin_class": "经济舱",
      "fare_type": "标准",
      "actual_price": 850.00,
      "status": "有效"
    }
  ]
}
```

> `actual_price` 为成交价，含燃油基建费。
> `adjustment_labels` 仅在航班实例调整时间晚于订单创建时间时返回对应提示，可包含“起飞时间已调整”“降落时间已调整”“起飞机场已调整”“降落机场已调整”。

### 11.3 管理员查所有订单

`GET /api/admin/orders` — 🛡️

**Query**：`page`、`page_size`、`status`、`user_id`、`date_from`、`date_to`。

只读。

---

## 12. 退改签模块

### 12.1 试算手续费/差价

`GET /api/refund/quote` — 👤

**Query**：

| 参数               | 类型   | 必填 | 说明                                  |
| ------------------ | ------ | ---- | ------------------------------------- |
| `ticket_no`        | string | ✅   | 拟退改的客票号                        |
| `op_type`          | enum   | ✅   | `refund` / `change`                   |
| `new_instance_id`  | string | 改签时✅ | 改签的目标实例                    |
| `new_cabin_class`  | string | 改签时✅ |                                   |
| `new_fare_type`    | string | 改签时✅ |                                   |

**响应**（退票）：

```json
{
  "op_type": "refund",
  "actual_price": 850.00,
  "fee_rate": 0.20,
  "fee": 170.00,
  "refund_amount": 680.00,
  "tier": "7-30天"
}
```

**响应**（改签）：

```json
{
  "op_type": "change",
  "old_actual_price": 850.00,
  "new_actual_price": 1050.00,
  "fee_rate": 0.20,
  "fee": 170.00,
  "price_diff": 200.00,
  "amount_user_pays": 370.00,
  "tier": "7-30天"
}
```

**手续费档位**（PRD §6.2，基数 = 客票 `actual_price`）：

| 距起飞时间 | 退票手续费率 | 改签手续费率 |
| ---------- | ------------ | ------------ |
| ≥ 30 天    | 0%           | 0%           |
| 7–30 天    | 20%          | 20%          |
| 3–7 天     | 40%          | 40%          |
| 1–3 天     | 60%          | 50%          |
| < 1 天     | 80%          | 60%          |
| 已起飞     | 不可操作     | 不可操作     |

### 12.2 退票

`POST /api/refund/refund` — 👤

```json
{ "ticket_no": "T20260509000001" }
```

**响应**：

```json
{
  "refund_id": 1001,
  "ticket_no": "T20260509000001",
  "fee": 170.00,
  "refund_amount": 680.00,
  "ticket_status": "已退",
  "order_status": "部分退款"
}
```

事务步骤参见 PRD §5.2。

**错误**：`TICKET_NOT_REFUNDABLE`（已退/已改签作废/已使用，或距起飞时间不足）。

### 12.3 改签

`POST /api/refund/change` — 👤

```json
{
  "ticket_no": "T20260509000001",
  "new_instance_id": "CA1234_20260512",
  "new_cabin_class": "经济舱",
  "new_fare_type": "标准"
}
```

**响应**：

```json
{
  "refund_id": 1002,
  "old_ticket_no": "T20260509000001",
  "new_ticket_no": "T20260509000050",
  "fee": 170.00,
  "price_diff": 200.00,
  "amount_user_pays": 370.00,
  "old_ticket_status": "已改签作废",
  "new_ticket_status": "有效"
}
```

事务步骤参见 PRD §5.3。

**错误**：`TICKET_NOT_CHANGEABLE`、`INSUFFICIENT_STOCK`（新实例无票）、`SAME_TICKET_NOT_ALLOWED`（AC-3：不能改到自己）。

### 12.4 我的退改记录

`GET /api/refund/records` — 👤

**Query**：`page`、`page_size`。

**响应**：分页结构，每项含 `refund_id`、`ticket_no`、`op_type`、`fee`、`new_ticket_no`、`price_diff`、`op_time`。

---

## 13. 关键业务流程的接口调用序列

### 13.1 购票主流程

```
1. POST /api/auth/login                        → 浏览器获得 access_token cookie
2. POST /api/search/flights                    → 三类候选
3. GET  /api/flight-instances/{id}             → 实例详情(可选,看价格档位)
4. GET  /api/passengers                        → 我的常用乘机人(可选)
5. POST /api/booking                           → 创建订单(事务)
6. POST /api/booking/{order_no}/pay            → 模拟支付(15分钟内)
   ── 或 ──
   POST /api/booking/{order_no}/cancel         → 主动取消
   ── 或 ──
   超时被定时任务自动 → '已取消'
7. GET  /api/orders/{order_no}                 → 查看订单详情
```

### 13.2 退票流程

```
1. GET  /api/orders/{order_no}                 → 选定要退的客票
2. GET  /api/refund/quote?ticket_no=...&op_type=refund
                                               → 试算
3. POST /api/refund/refund                     → 提交退票(事务)
4. GET  /api/refund/records                    → 查看退改记录
```

### 13.3 改签流程

```
1. GET  /api/orders/{order_no}                 → 选定要改的客票
2. POST /api/search/flights                    → 搜索新航班
3. GET  /api/refund/quote?ticket_no=...&op_type=change&new_instance_id=...&...
                                               → 试算手续费 + 差价
4. POST /api/refund/change                     → 提交改签(事务)
5. GET  /api/orders/{order_no}                 → 查看新票
```

---

## 14. 错误码总览

| code                          | http | 含义                                           |
| ----------------------------- | ---- | ---------------------------------------------- |
| `AUTHENTICATION_FAILED`       | 401  | 登录失败                                       |
| `UNAUTHORIZED`                | 401  | 未登录或 token 失效                            |
| `PERMISSION_DENIED`           | 403  | 无权限（角色不匹配）                           |
| `RESOURCE_NOT_FOUND`          | 404  | 资源不存在                                     |
| `RESOURCE_IN_USE`             | 409  | 资源被引用，无法删除                           |
| `PHONE_ALREADY_EXISTS`        | 409  | 手机号已注册                                   |
| `INVALID_PHONE_FORMAT`        | 400  | 手机号格式错误                                 |
| `OLD_PASSWORD_MISMATCH`       | 400  | 原密码错误                                     |
| `INCONSISTENT_AIRPORT_CITY`   | 400  | airport 与 city_near_apt distance=0 不一致     |
| `INSUFFICIENT_STOCK`          | 409  | 库存不足                                       |
| `PASSENGER_DUPLICATE`         | 409  | 同乘机人在该实例已有有效票（AC-1）             |
| `INSTANCE_NOT_BOOKABLE`       | 409  | 航班实例不可订（已起飞/已取消等）              |
| `ORDER_NOT_PAYABLE`           | 409  | 订单不可支付（已超时或非待支付）               |
| `ORDER_NOT_CANCELABLE`        | 409  | 订单不可取消                                   |
| `TICKET_NOT_REFUNDABLE`       | 409  | 客票不可退（终态或时间不允许）                 |
| `TICKET_NOT_CHANGEABLE`       | 409  | 客票不可改                                     |
| `SAME_TICKET_NOT_ALLOWED`     | 400  | 改签目标与原票相同（AC-3）                     |
| `VALIDATION_ERROR`            | 422  | 请求体格式校验失败（Pydantic 通用）            |
| `INTERNAL_ERROR`              | 500  | 服务端异常                                     |

---

## 附录：变更记录

| 版本 | 日期       | 修订人 | 变更说明                                                     |
| ---- | ---------- | ------ | ------------------------------------------------------------ |
| v1.0 | 2026-05-09 | 王铿轶 | 基于 PRD/SCHEMA/ARCHITECTURE v1.0 编写。                     |
| v2.0 | 2026-05-10 | 王铿轶 | 同步 PRD/SCHEMA/ARCHITECTURE v2.0：JWT 改为 httpOnly cookie 传递；删除资源级权限标记，统一为 `Admin`；删除接口 57-61；删除航班实例 延误状态枚举值；中转最小衔接时间 60 分钟 → 120 分钟，删除"最大总时长 12 小时"约束；退改费率档位完全更新为 5 档（30天/7-30/3-7/1-3/<1天）；订单总金额、客票成交价计算补充 `fuel_infra_fee` 燃油基建费；临近机场距离上限 200 → 300；新增三类候选搜索响应 `type` 字段约定；新增 `INCONSISTENT_AIRPORT_CITY` 错误码（airport 与 city_near_apt 双写一致性）；新增 CORS withCredentials 说明 |

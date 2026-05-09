# 航空票务管理数据库系统 — 接口定义文档（API）

| 项目名称 | 航空票务管理数据库系统             |
| -------- | ---------------------------------- |
| 文档版本 | v1.0                               |
| 编写日期 | 2026-05-09                         |
| 协议     | HTTP/1.1 + JSON                    |
| 基地址   | `http://localhost:8000`            |
| 认证     | Bearer JWT                         |
| 配套文档 | PRD.md、SCHEMA.md、ARCHITECTURE.md |

---

## 0. 阅读指南

本文档是前后端协作的**唯一接口契约**。

- §1 给所有接口共享的通用约定（认证、错误格式、分页、时间）
- §2 给接口清单总表（一张表索引所有接口）
- §3–§13 按模块分组，给每个接口的详细定义
- §14 给关键业务流程的接口调用序列（购票主流程、退改流程）
- §15 给错误码总览

**约定**：本文档中所有"必填"指请求体或查询参数中**必须传**；所有响应字段除非标注 `nullable`，否则一定有值。

---

## 1. 通用约定

### 1.1 认证

- 认证机制：**Bearer JWT**。客户端登录后保存 token；后续请求在请求头携带：

  ```
  Authorization: Bearer <token>
  ```

- token 过期或无效 → 返回 `401 Unauthorized`，前端跳转登录页。

- token 中携带 `sub`（用户/管理员 ID）与 `role`（`user` 或 `admin`）。

### 1.2 角色与权限

每个接口标记三种访问要求：

| 标记                  | 含义               |
| --------------------- | ------------------ |
| 🌐 `Public`            | 无需登录           |
| 👤 `User`              | 需登录、role=user  |
| 🛡️ `Admin: <资源类型>` | 需登录、role=admin |

资源类型枚举值（与 SCHEMA §3.3.2 一致）：`city / airport / airline / aircraft_type / flight / flight_instance / order / *`

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
  "code": "INSUFFICIENT_SEATS",
  "message": "available=2, need=3"
}
```

### 1.5 分页

列表型接口统一使用：

**请求**（query string）：

| 参数        | 类型 | 默认 | 说明               |
| ----------- | ---- | ---- | ------------------ |
| `page`      | int  | 1    | 页码，从 1 起      |
| `page_size` | int  | 20   | 每页条数，上限 100 |

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

### 1.8 ID 与编号格式

| 实体     | 字段          | 类型      | 格式示例                |
| -------- | ------------- | --------- | ----------------------- |
| 用户     | `user_id`     | int       | `12345`                 |
| 管理员   | `admin_id`    | string    | `"A001"`                |
| 城市     | `city_name`   | string    | `"北京"`                |
| 机场     | `iata_code`   | string(3) | `"PEK"`                 |
| 航司     | `iata_code`   | string(2) | `"CA"`                  |
| 航班     | `flight_no`   | string    | `"CA1234"`              |
| 航班实例 | `instance_id` | string    | `"CA1234_20260510"`     |
| 订单     | `order_no`    | string    | `"O20260509142301X3K9"` |
| 客票     | `ticket_no`   | string    | `"T20260510000001"`     |

---

## 2. 接口清单总表

| #    | 模块     | 方法   | 路径                                               | 权限              | 简述                       |
| ---- | -------- | ------ | -------------------------------------------------- | ----------------- | -------------------------- |
| 1    | 认证     | POST   | `/api/auth/register`                               | 🌐                 | 用户注册                   |
| 2    | 认证     | POST   | `/api/auth/login`                                  | 🌐                 | 用户登录                   |
| 3    | 认证     | POST   | `/api/auth/admin-login`                            | 🌐                 | 管理员登录                 |
| 4    | 认证     | POST   | `/api/auth/logout`                                 | 👤🛡️                | 登出                       |
| 5    | 认证     | GET    | `/api/auth/me`                                     | 👤🛡️                | 当前身份信息               |
| 6    | 用户     | GET    | `/api/users/me`                                    | 👤                 | 获取个人信息               |
| 7    | 用户     | PATCH  | `/api/users/me`                                    | 👤                 | 修改个人信息               |
| 8    | 用户     | POST   | `/api/users/me/password`                           | 👤                 | 修改密码                   |
| 9    | 乘机人   | GET    | `/api/passengers`                                  | 👤                 | 我的常用乘机人             |
| 10   | 乘机人   | POST   | `/api/passengers`                                  | 👤                 | 新增乘机人                 |
| 11   | 乘机人   | PUT    | `/api/passengers/{id_no}`                          | 👤                 | 修改乘机人                 |
| 12   | 乘机人   | DELETE | `/api/passengers/{id_no}`                          | 👤                 | 解绑乘机人                 |
| 13   | 城市     | GET    | `/api/cities`                                      | 🌐                 | 城市列表                   |
| 14   | 城市     | POST   | `/api/cities`                                      | 🛡️ city            | 新增城市                   |
| 15   | 城市     | DELETE | `/api/cities/{name}`                               | 🛡️ city            | 删除城市                   |
| 16   | 城市     | GET    | `/api/cities/{name}/near-airports`                 | 🌐                 | 临近机场                   |
| 17   | 城市     | POST   | `/api/cities/{name}/near-airports`                 | 🛡️ city            | 新增临近关系               |
| 18   | 城市     | DELETE | `/api/cities/{name}/near-airports/{iata}`          | 🛡️ city            | 删除临近关系               |
| 19   | 机场     | GET    | `/api/airports`                                    | 🌐                 | 机场列表                   |
| 20   | 机场     | GET    | `/api/airports/{iata}`                             | 🌐                 | 机场详情                   |
| 21   | 机场     | POST   | `/api/airports`                                    | 🛡️ airport         | 新增机场                   |
| 22   | 机场     | PUT    | `/api/airports/{iata}`                             | 🛡️ airport         | 修改机场                   |
| 23   | 机场     | DELETE | `/api/airports/{iata}`                             | 🛡️ airport         | 删除机场                   |
| 24   | 航司     | GET    | `/api/airlines`                                    | 🌐                 | 航司列表                   |
| 25   | 航司     | POST   | `/api/airlines`                                    | 🛡️ airline         | 新增                       |
| 26   | 航司     | PUT    | `/api/airlines/{iata}`                             | 🛡️ airline         | 修改                       |
| 27   | 航司     | DELETE | `/api/airlines/{iata}`                             | 🛡️ airline         | 删除                       |
| 28   | 机型     | GET    | `/api/aircraft-types`                              | 🌐                 | 机型列表                   |
| 29   | 机型     | POST   | `/api/aircraft-types`                              | 🛡️ aircraft_type   | 新增                       |
| 30   | 机型     | PUT    | `/api/aircraft-types/{model}`                      | 🛡️ aircraft_type   | 修改                       |
| 31   | 机型     | DELETE | `/api/aircraft-types/{model}`                      | 🛡️ aircraft_type   | 删除                       |
| 32   | 航班     | GET    | `/api/flights`                                     | 🌐                 | 航班列表                   |
| 33   | 航班     | GET    | `/api/flights/{flight_no}`                         | 🌐                 | 航班详情（含经停、飞行日） |
| 34   | 航班     | POST   | `/api/flights`                                     | 🛡️ flight          | 新增航班                   |
| 35   | 航班     | PUT    | `/api/flights/{flight_no}`                         | 🛡️ flight          | 修改                       |
| 36   | 航班     | DELETE | `/api/flights/{flight_no}`                         | 🛡️ flight          | 删除                       |
| 37   | 航班实例 | GET    | `/api/flight-instances`                            | 🌐                 | 实例列表（按航班/日期筛）  |
| 38   | 航班实例 | GET    | `/api/flight-instances/{instance_id}`              | 🌐                 | 实例详情（含定价档位）     |
| 39   | 航班实例 | POST   | `/api/flight-instances`                            | 🛡️ flight_instance | 创建单个实例               |
| 40   | 航班实例 | POST   | `/api/flight-instances/batch-generate`             | 🛡️ flight_instance | 按航班批量生成             |
| 41   | 航班实例 | PATCH  | `/api/flight-instances/{instance_id}/status`       | 🛡️ flight_instance | 修改状态（取消/延误）      |
| 42   | 航班实例 | DELETE | `/api/flight-instances/{instance_id}`              | 🛡️ flight_instance | 删除                       |
| 43   | 舱位定价 | GET    | `/api/flight-instances/{instance_id}/cabin-prices` | 🌐                 | 某实例所有档位             |
| 44   | 舱位定价 | PUT    | `/api/flight-instances/{instance_id}/cabin-prices` | 🛡️ flight_instance | 批量设置档位（替换）       |
| 45   | 搜索     | POST   | `/api/search/flights`                              | 🌐                 | 三类候选合并搜索           |
| 46   | 搜索     | POST   | `/api/search/transit`                              | 🌐                 | 中转方案搜索（独立调用）   |
| 47   | 下单     | POST   | `/api/booking`                                     | 👤                 | 下单（事务）               |
| 48   | 下单     | POST   | `/api/booking/{order_no}/pay`                      | 👤                 | 模拟支付                   |
| 49   | 下单     | POST   | `/api/booking/{order_no}/cancel`                   | 👤                 | 主动取消（仅未支付）       |
| 50   | 订单     | GET    | `/api/orders`                                      | 👤                 | 我的订单（分页）           |
| 51   | 订单     | GET    | `/api/orders/{order_no}`                           | 👤                 | 订单详情（含客票）         |
| 52   | 订单     | GET    | `/api/admin/orders`                                | 🛡️ order           | 管理员查所有订单           |
| 53   | 退改     | POST   | `/api/refund/refund`                               | 👤                 | 退票                       |
| 54   | 退改     | POST   | `/api/refund/change`                               | 👤                 | 改签                       |
| 55   | 退改     | GET    | `/api/refund/quote`                                | 👤                 | 试算手续费/差价            |
| 56   | 退改     | GET    | `/api/refund/records`                              | 👤                 | 我的退改记录               |
| 57   | 管理员   | GET    | `/api/admins`                                      | 🛡️ *               | 管理员列表                 |
| 58   | 管理员   | POST   | `/api/admins`                                      | 🛡️ *               | 新增管理员                 |
| 59   | 管理员   | DELETE | `/api/admins/{admin_id}`                           | 🛡️ *               | 删除管理员                 |
| 60   | 管理员   | GET    | `/api/admins/{admin_id}/permissions`               | 🛡️ *               | 查权限                     |
| 61   | 管理员   | PUT    | `/api/admins/{admin_id}/permissions`               | 🛡️ *               | 设置权限                   |

> 共 **61** 个接口。下面按模块详细展开。

---

## 3. 认证模块

### 3.1 用户注册

`POST /api/auth/register` — 🌐 Public

**请求体**：

| 字段     | 类型   | 必填 | 说明                     |
| -------- | ------ | ---- | ------------------------ |
| phone    | string | ✅    | 手机号（中国大陆 11 位） |
| password | string | ✅    | 6–32 位                  |
| name     | string | ✅    | 昵称，1–64 字符          |

**响应** `201`：

```json
{ "user_id": 12345, "phone": "13800000000", "name": "张三" }
```

**错误**：`PHONE_EXISTS`(409)、`INVALID_INPUT`(400)

---

### 3.2 用户登录

`POST /api/auth/login` — 🌐 Public

**请求体**：

| 字段     | 类型   | 必填 |
| -------- | ------ | ---- |
| phone    | string | ✅    |
| password | string | ✅    |

**响应** `200`：

```json
{
  "token": "eyJhbGciOi...",
  "expires_at": "2026-05-10T14:23:01",
  "user": { "user_id": 12345, "phone": "13800000000", "name": "张三" }
}
```

**错误**：`INVALID_CREDENTIALS`(401)

---

### 3.3 管理员登录

`POST /api/auth/admin-login` — 🌐 Public

**请求体**：

| 字段     | 类型   | 必填 |
| -------- | ------ | ---- |
| admin_id | string | ✅    |
| password | string | ✅    |

**响应** `200`：

```json
{
  "token": "...",
  "expires_at": "...",
  "admin": { "admin_id": "A001", "admin_name": "运营A" },
  "permissions": ["flight", "flight_instance", "order"]
}
```

**错误**：`INVALID_CREDENTIALS`(401)

---

### 3.4 登出

`POST /api/auth/logout` — 👤🛡️

**说明**：当前 JWT 是无状态的，登出由前端清除 token 实现；本接口仅做日志记录，**不强制调用**。

**响应** `204` 无内容

---

### 3.5 当前身份信息

`GET /api/auth/me` — 👤🛡️

**响应** `200`：

```json
{
  "role": "user",
  "user_id": 12345,
  "name": "张三",
  "phone": "138****0000"
}
```

或对管理员：

```json
{
  "role": "admin",
  "admin_id": "A001",
  "admin_name": "运营A",
  "permissions": ["flight", "*"]
}
```

---

## 4. 用户与乘机人模块

### 4.1 获取个人信息

`GET /api/users/me` — 👤

**响应**：同 §3.5 user 部分。

### 4.2 修改个人信息

`PATCH /api/users/me` — 👤

**请求体**（任一字段可选）：

| 字段  | 类型   | 说明                   |
| ----- | ------ | ---------------------- |
| name  | string | 昵称                   |
| phone | string | 新手机号（需未被占用） |

**响应**：更新后的用户对象。

**错误**：`PHONE_EXISTS`(409)

### 4.3 修改密码

`POST /api/users/me/password` — 👤

**请求体**：

| 字段         | 类型   | 必填 |
| ------------ | ------ | ---- |
| old_password | string | ✅    |
| new_password | string | ✅    |

**响应** `204`

**错误**：`INVALID_CREDENTIALS`(401)

### 4.4 我的常用乘机人

`GET /api/passengers` — 👤

**说明**：返回当前用户历史订单中出现过的所有乘机人去重（详见 SCHEMA §3.2.2 设计说明）。

**响应** `200`：

```json
[
  { "id_no": "110101199001011234", "real_name": "张三", "birth_date": "1990-01-01" }
]
```

### 4.5 新增乘机人

`POST /api/passengers` — 👤

**请求体**：

| 字段       | 类型         | 必填     |
| ---------- | ------------ | -------- |
| id_no      | string       | ✅ 证件号 |
| real_name  | string       | ✅        |
| birth_date | string(date) | ✅        |

**响应** `201`：完整乘机人对象。

**错误**：`PASSENGER_EXISTS`(409) — 证件号已存在且姓名不一致；如姓名一致，幂等返回已有记录。

### 4.6 修改乘机人

`PUT /api/passengers/{id_no}` — 👤

**说明**：仅允许修改 `real_name`、`birth_date`；证件号不可改（要改请删除后新增）。**注意**：如有进行中的客票引用该乘机人，禁止修改。

**错误**：`PASSENGER_IN_USE`(409)

### 4.7 解绑乘机人

`DELETE /api/passengers/{id_no}` — 👤

**说明**：当前设计未维护 `user_passenger` 关联表，"解绑"语义为：**仅当该乘机人无任何客票记录时**允许从全局删除。否则返回 `PASSENGER_IN_USE`。

---

## 5. 基础数据 — 城市与机场

### 5.1 城市列表

`GET /api/cities` — 🌐

**Query**：`q`（可选，模糊匹配城市名）

**响应**：

```json
[ { "city_name": "北京" }, { "city_name": "上海" } ]
```

### 5.2 新增城市

`POST /api/cities` — 🛡️ city

**请求体**：`{ "city_name": "苏州" }`

**响应** `201`

**错误**：`CITY_EXISTS`(409)

### 5.3 删除城市

`DELETE /api/cities/{name}` — 🛡️ city

**错误**：`CITY_IN_USE`(409) — 仍有机场或临近关系引用该城市。

### 5.4 获取临近机场

`GET /api/cities/{name}/near-airports` — 🌐

**响应**：

```json
[
  { "iata_code": "SHA", "airport_name": "上海虹桥国际机场", "distance": 98.50 }
]
```

### 5.5 新增临近关系

`POST /api/cities/{name}/near-airports` — 🛡️ city

**请求体**：

| 字段      | 类型      | 必填   |
| --------- | --------- | ------ |
| iata_code | string(3) | ✅      |
| distance  | number    | ✅ ≤200 |

**业务约束**：临近机场不能是该城市自己的机场（`AC-4`）；超出 200km 拒绝。

**错误**：`INVALID_NEAR_AIRPORT`(400)、`NEAR_RELATION_EXISTS`(409)

### 5.6 删除临近关系

`DELETE /api/cities/{name}/near-airports/{iata}` — 🛡️ city

---

### 5.7 机场 CRUD

| 方法   | 路径                   | 说明                         |
| ------ | ---------------------- | ---------------------------- |
| GET    | `/api/airports`        | 列表，query `city_name` 可筛 |
| GET    | `/api/airports/{iata}` | 详情                         |
| POST   | `/api/airports`        | 新增                         |
| PUT    | `/api/airports/{iata}` | 修改名称、所属城市           |
| DELETE | `/api/airports/{iata}` | 删除（被引用时拒绝）         |

**机场对象**：

```json
{ "iata_code": "PEK", "airport_name": "北京首都国际机场", "city_name": "北京" }
```

---

## 6. 基础数据 — 航司与机型

### 6.1 航司 CRUD

| 方法   | 路径                   |
| ------ | ---------------------- |
| GET    | `/api/airlines`        |
| POST   | `/api/airlines`        |
| PUT    | `/api/airlines/{iata}` |
| DELETE | `/api/airlines/{iata}` |

**对象**：`{ "iata_code": "CA", "airline_name": "中国国际航空" }`

### 6.2 机型 CRUD

| 方法   | 路径                          |
| ------ | ----------------------------- |
| GET    | `/api/aircraft-types`         |
| POST   | `/api/aircraft-types`         |
| PUT    | `/api/aircraft-types/{model}` |
| DELETE | `/api/aircraft-types/{model}` |

**对象**：

```json
{ "model": "B738", "economy_seats": 162, "first_seats": 8 }
```

**错误**：`AIRCRAFT_IN_USE`(409) — 被航班引用时不可删。

---

## 7. 航班管理模块

### 7.1 航班列表

`GET /api/flights` — 🌐

**Query**：

| 参数                      | 说明         |
| ------------------------- | ------------ |
| airline_code              | 按航司筛     |
| dep_airport / arr_airport | 按起降机场筛 |
| page / page_size          | 分页         |

**响应** `items` 元素：

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
  "aircraft_model": "B738"
}
```

### 7.2 航班详情

`GET /api/flights/{flight_no}` — 🌐

**响应** = 航班对象 + 关联：

```json
{
  "flight_no": "CA1234",
  "...": "上面所有字段",
  "weekdays": [1, 3, 5],
  "stopovers": [
    { "stop_order": 1, "airport_code": "TAO" }
  ],
  "airline_name": "中国国际航空",
  "dep_airport_name": "北京首都国际机场",
  "arr_airport_name": "上海虹桥国际机场"
}
```

### 7.3 创建航班

`POST /api/flights` — 🛡️ flight

**请求体**：航班所有字段 + `weekdays: number[]` + `stopovers: [{stop_order, airport_code}]`

**业务约束**（参见 SCHEMA §4.2）：

- `dep_airport_code != arr_airport_code`（AC-5）
- 经停机场不能等于起降机场（AC-7）
- weekday 范围 1–7

**错误**：`INVALID_INPUT`(400)、`FLIGHT_EXISTS`(409)

### 7.4 修改航班

`PUT /api/flights/{flight_no}` — 🛡️ flight

**说明**：全量替换，含 weekdays 与 stopovers。**已有 instance_id 引用的航班修改 dep/arr/aircraft 会拒绝**（防止历史实例数据矛盾）。

**错误**：`FLIGHT_IN_USE`(409)

### 7.5 删除航班

`DELETE /api/flights/{flight_no}` — 🛡️ flight

**错误**：`FLIGHT_IN_USE`(409) — 有 flight_instance 引用时拒绝。

---

## 8. 航班实例与定价模块

### 8.1 实例列表

`GET /api/flight-instances` — 🌐

**Query**：

| 参数             | 说明     |
| ---------------- | -------- |
| flight_no        | 按航班筛 |
| flight_date      | 按日期筛 |
| status           | 按状态筛 |
| page / page_size | 分页     |

**响应**：实例对象数组。

### 8.2 实例详情

`GET /api/flight-instances/{instance_id}` — 🌐

**响应**：

```json
{
  "instance_id": "CA1234_20260510",
  "flight_no": "CA1234",
  "flight_date": "2026-05-10",
  "economy_left": 145,
  "first_left": 8,
  "status": "可订",
  "flight": { "...": "航班详情对象" },
  "cabin_prices": [
    { "cabin_class": "经济舱", "fare_type": "标准", "price": 800.00, "available_seats": 145 },
    { "cabin_class": "经济舱", "fare_type": "特价", "price": 500.00, "available_seats": 5 },
    { "cabin_class": "头等舱", "fare_type": "标准", "price": 3000.00, "available_seats": 8 }
  ]
}
```

### 8.3 创建实例

`POST /api/flight-instances` — 🛡️ flight_instance

**请求体**：

| 字段         | 类型         | 必填 | 说明                               |
| ------------ | ------------ | ---- | ---------------------------------- |
| flight_no    | string       | ✅    | 必须存在                           |
| flight_date  | string(date) | ✅    | 必须落在该航班 weekdays 内（AC-6） |
| economy_left | int          | ❌    | 不传则用机型 economy_seats         |
| first_left   | int          | ❌    | 同上                               |
| status       | enum         | ❌    | 默认 `'计划'`                      |

**响应** `201`：实例对象（不含 cabin_prices；定价用 §8.7 单独设置）。

**错误**：`INSTANCE_EXISTS`(409)、`INVALID_FLIGHT_DATE`(400)

### 8.4 批量生成实例

`POST /api/flight-instances/batch-generate` — 🛡️ flight_instance

**请求体**：

| 字段              | 类型         | 必填        | 说明                             |
| ----------------- | ------------ | ----------- | -------------------------------- |
| flight_no         | string       | ✅           | 目标航班                         |
| date_from         | string(date) | ✅           | 起始日期（含）                   |
| date_to           | string(date) | ✅           | 结束日期（含），区间不超过 90 天 |
| default_status    | enum         | ❌           | 默认 `'计划'`                    |
| skip_existing     | bool         | ❌ 默认 true | 已存在的实例跳过                 |
| init_cabin_prices | object       | ❌           | 见下                             |

`init_cabin_prices` 形如：

```json
{
  "经济舱-标准": { "price": 800.00, "available_seats": 150 },
  "经济舱-特价": { "price": 500.00, "available_seats": 10 },
  "头等舱-标准": { "price": 3000.00, "available_seats": 8 }
}
```

**响应**：

```json
{
  "created": 28,
  "skipped": 2,
  "instance_ids": ["CA1234_20260510", "..."]
}
```

> **业务说明**：仅在 `flight_weekday` 中允许的星期才会生成；座位数默认按机型填充。

### 8.5 修改实例状态

`PATCH /api/flight-instances/{instance_id}/status` — 🛡️ flight_instance

**请求体**：`{ "status": "已取消" }`

**业务规则**：

- 状态机参见 SCHEMA §5.3。
- 改为 `'已取消'` 时**触发批量退款**：所有有效客票自动退票，库存回补，订单状态更新为 `'已完成退款'`。**这是一个事务**。
- 改为 `'延误'` 时仅更新状态，不影响订单。

**错误**：`ILLEGAL_STATE`(409)

### 8.6 删除实例

`DELETE /api/flight-instances/{instance_id}` — 🛡️ flight_instance

**错误**：`INSTANCE_IN_USE`(409) — 仍有客票引用时拒绝。

### 8.7 设置/查询舱位定价

`GET /api/flight-instances/{instance_id}/cabin-prices` — 🌐

**响应**：见 §8.2 中 `cabin_prices` 部分。

`PUT /api/flight-instances/{instance_id}/cabin-prices` — 🛡️ flight_instance

**说明**：**全量替换**该实例所有定价档位。

**请求体**：

```json
{
  "items": [
    { "cabin_class": "经济舱", "fare_type": "标准", "price": 800.00, "available_seats": 150 },
    { "cabin_class": "经济舱", "fare_type": "特价", "price": 500.00, "available_seats": 10 },
    { "cabin_class": "头等舱", "fare_type": "标准", "price": 3000.00, "available_seats": 8 }
  ]
}
```

**业务约束**：

- 每个 `(cabin_class, fare_type)` 组合最多一条。
- `available_seats` 之和按舱位汇总后必须等于 `flight_instance.economy_left/first_left`，否则同步更新汇总（AC-2）。
- 已有有效客票引用的档位 `available_seats` 不得低于已售数（应用层校验）。

**错误**：`PRICE_BELOW_SOLD`(409)

---

## 9. 航班搜索模块

### 9.1 三类候选合并搜索

`POST /api/search/flights` — 🌐

**请求体**：

| 字段            | 类型         | 必填        | 说明                                               |
| --------------- | ------------ | ----------- | -------------------------------------------------- |
| dep_city        | string       | ✅           | 出发城市                                           |
| arr_city        | string       | ✅           | 到达城市                                           |
| flight_date     | string(date) | ✅           | 出行日期                                           |
| cabin_class     | enum         | ❌           | 舱位偏好；不填返回全部                             |
| airline_code    | string       | ❌           | 仅指定航司                                         |
| include_transit | bool         | ❌ 默认 true | 是否包含中转方案                                   |
| include_nearby  | bool         | ❌ 默认 true | 是否包含临近机场方案                               |
| sort_by         | enum         | ❌           | `price` / `duration` / `dep_time`，默认 `dep_time` |
| sort_order      | enum         | ❌           | `asc` / `desc`，默认 `asc`                         |

**响应**：

```json
{
  "direct": [ /* 直飞航班实例数组 */ ],
  "transit": [ /* 中转方案数组 */ ],
  "nearby": [ /* 临近机场替代方案数组 */ ],
  "stats": { "direct_count": 5, "transit_count": 3, "nearby_count": 8 }
}
```

**direct 元素**：

```json
{
  "instance_id": "CA1234_20260510",
  "flight_no": "CA1234",
  "airline_code": "CA",
  "airline_name": "中国国际航空",
  "dep_airport_code": "PEK",
  "dep_airport_name": "北京首都国际机场",
  "dep_terminal": "T3",
  "arr_airport_code": "SHA",
  "arr_airport_name": "上海虹桥国际机场",
  "arr_terminal": "T2",
  "scheduled_departure": "08:00:00",
  "scheduled_arrival": "10:30:00",
  "duration_minutes": 150,
  "aircraft_model": "B738",
  "min_price": 500.00,
  "lowest_fare_type": "特价",
  "economy_left": 5,
  "first_left": 8,
  "has_stopover": false
}
```

**transit 元素**：

```json
{
  "leg1": { /* 同 direct 元素结构 */ },
  "leg2": { /* 同 direct 元素结构 */ },
  "transit_airport": "XIY",
  "transit_minutes": 90,
  "total_minutes": 320,
  "total_min_price": 950.00
}
```

**nearby 元素**：

```json
{
  "instance": { /* 同 direct 元素结构 */ },
  "substituted_side": "departure",
  "original_city": "苏州",
  "actual_city": "上海",
  "extra_distance_km": 98.50
}
```

**业务约束**（参见 PRD §6.4 中转规则）：

- 中转：60min ≤ 衔接 ≤ 6h；总时长 ≤ 12h；仅单次中转。
- 临近机场：使用 `city_near_apt` 表；距离 ≤200km。

### 9.2 中转方案搜索（独立）

`POST /api/search/transit` — 🌐

**说明**：与 §9.1 类似但只返回中转方案，可指定额外约束。

**额外参数**：

| 字段                | 类型 | 默认  | 说明         |
| ------------------- | ---- | ----- | ------------ |
| min_transit_minutes | int  | 60    |              |
| max_transit_minutes | int  | 360   |              |
| max_total_minutes   | int  | 720   |              |
| same_airline_only   | bool | false | 仅同航司中转 |

**响应**：transit 数组（同 §9.1）。

---

## 10. 下单与购票模块

### 10.1 下单

`POST /api/booking` — 👤

**请求体**：

| 字段        | 类型   | 必填 | 说明                  |
| ----------- | ------ | ---- | --------------------- |
| instance_id | string | ✅    | 航班实例              |
| cabin_class | enum   | ✅    | `'经济舱'`/`'头等舱'` |
| fare_type   | enum   | ✅    | `'标准'`/`'特价'`     |
| passengers  | array  | ✅    | 1–9 个乘客对象        |

**passenger 对象**：

| 字段       | 类型         | 必填 | 说明                     |
| ---------- | ------------ | ---- | ------------------------ |
| id_no      | string       | ✅    | 证件号；不存在时自动创建 |
| real_name  | string       | ✅    |                          |
| birth_date | string(date) | ✅    |                          |

**响应** `201`：

```json
{
  "order": {
    "order_no": "O20260509142301X3K9",
    "user_id": 12345,
    "total_amount": 1500.00,
    "status": "待支付",
    "created_at": "2026-05-09T14:23:01",
    "expires_at": "2026-05-09T14:38:01"
  },
  "tickets": [
    {
      "ticket_no": "T20260510000001",
      "passenger_id": "110...",
      "real_name": "张三",
      "instance_id": "CA1234_20260510",
      "cabin_class": "经济舱",
      "fare_type": "标准",
      "actual_price": 750.00,
      "status": "有效"
    }
  ]
}
```

**业务规则**（核心，参见 PRD §6.1）：

- 在单事务内完成：锁定 cabin_price → 校验余票 → 扣减 → 建订单 → 建客票。
- 余票不足返回 `INSUFFICIENT_SEATS`。
- 同一证件号不能在同一实例上重复购票（AC-1）。
- 订单 15 分钟未支付自动取消，由后台任务处理。

**错误**：

- `INSUFFICIENT_SEATS`(409)
- `DUPLICATE_BOOKING`(409) — 乘客已在该实例有有效客票
- `INSTANCE_NOT_BOOKABLE`(409) — 实例状态不是 `'可订'`/`'延误'`
- `INVALID_INPUT`(400) — passenger 数量超限或证件号格式错

### 10.2 模拟支付

`POST /api/booking/{order_no}/pay` — 👤

**说明**：本项目不接入真实支付，调用即视为支付成功。

**业务规则**：

- 仅 `status='待支付'` 且未超时的订单可支付。
- 成功后订单 `status='已支付'`；客票无需变化。

**响应** `200`：

```json
{ "order_no": "...", "status": "已支付", "paid_at": "..." }
```

**错误**：`ORDER_NOT_FOUND`(404)、`ILLEGAL_STATE`(409)、`ORDER_EXPIRED`(409)、`PERMISSION_DENIED`(403) 非本人订单

### 10.3 主动取消订单

`POST /api/booking/{order_no}/cancel` — 👤

**说明**：仅 `status='待支付'` 时可调用，效果等同于超时释放。

**响应** `200`：`{ "order_no": "...", "status": "已取消" }`

**错误**：`ILLEGAL_STATE`(409) — 已支付订单需走退票流程

---

## 11. 订单查询模块

### 11.1 我的订单列表

`GET /api/orders` — 👤

**Query**：

| 参数                | 说明                       |
| ------------------- | -------------------------- |
| status              | 按状态筛（多选用逗号分隔） |
| date_from / date_to | 按 created_at 区间         |
| page / page_size    | 分页                       |

**响应**（分页）：每个 item：

```json
{
  "order_no": "...",
  "total_amount": 1500.00,
  "status": "已支付",
  "created_at": "...",
  "ticket_count": 2,
  "active_count": 2,
  "first_dep_time": "2026-05-10T08:00:00",
  "first_route": "PEK → SHA"
}
```

### 11.2 订单详情

`GET /api/orders/{order_no}` — 👤

**说明**：返回订单 + 含每张客票的完整信息（航班实例、价格、状态、退改可能性）。

**响应**：

```json
{
  "order": { /* §10.1 中 order 部分 + 完整状态历史 */ },
  "tickets": [
    {
      "ticket_no": "...",
      "passenger": { "id_no": "...", "real_name": "..." },
      "instance": { /* §9.1 direct 元素结构 */ },
      "cabin_class": "经济舱",
      "fare_type": "标准",
      "actual_price": 750.00,
      "status": "有效",
      "refundable": true,
      "changeable": true
    }
  ]
}
```

**错误**：`ORDER_NOT_FOUND`(404)、`PERMISSION_DENIED`(403)

### 11.3 管理员查所有订单

`GET /api/admin/orders` — 🛡️ order

**Query**：在 §11.1 基础上增加：

| 参数                    | 说明          |
| ----------------------- | ------------- |
| user_id                 | 按用户筛      |
| flight_no / instance_id | 按航班/实例筛 |

**响应**：含 `user_name` 字段的订单列表。

---

## 12. 退改签模块

### 12.1 试算手续费/差价

`GET /api/refund/quote` — 👤

**Query**：

| 参数            | 必填 | 说明                  |
| --------------- | ---- | --------------------- |
| ticket_no       | ✅    | 目标客票              |
| op_type         | ✅    | `refund` 或 `change`  |
| new_instance_id | ❌    | op_type=change 时必填 |
| new_cabin_class | ❌    | 同上                  |
| new_fare_type   | ❌    | 同上                  |

**响应**：

```json
{
  "op_type": "change",
  "actual_price": 750.00,
  "fee_rate": 0.05,
  "fee": 37.50,
  "new_price": 900.00,
  "price_diff": 150.00,
  "user_pay": 187.50,
  "user_refund": 0.00,
  "hours_to_departure": 28,
  "is_eligible": true,
  "rejection_reason": null
}
```

**业务规则**（参见 PRD §6.2 费率表）：

- 距起飞 < 2h 不可退；< 2h 不可改。
- 已起飞、已退、已改签作废的票不可操作（AC-8）。

### 12.2 退票

`POST /api/refund/refund` — 👤

**请求体**：`{ "ticket_no": "..." }`

**响应** `200`：

```json
{
  "refund_id": 78901,
  "ticket_no": "...",
  "fee": 75.00,
  "refund_amount": 675.00,
  "order_status_after": "部分退款"
}
```

**业务规则**（事务内）：

- 校验客票状态、距起飞时间、是否本人订单。
- 客票 `status='已退'`；cabin_price 与 flight_instance 库存 +1；写 refund_change（op_type=退票，new_ticket_no=null，price_diff=0）。
- 订单状态联动：所有票退完→`'已完成退款'`；部分退→`'部分退款'`。

**错误**：`TICKET_NOT_FOUND`(404)、`PERMISSION_DENIED`(403)、`ILLEGAL_STATE`(409)、`NOT_REFUNDABLE`(409)

### 12.3 改签

`POST /api/refund/change` — 👤

**请求体**：

| 字段            | 类型   | 必填   |
| --------------- | ------ | ------ |
| ticket_no       | string | ✅ 旧票 |
| new_instance_id | string | ✅      |
| new_cabin_class | enum   | ✅      |
| new_fare_type   | enum   | ✅      |

**响应** `200`：

```json
{
  "refund_id": 78902,
  "old_ticket_no": "T20260510000001",
  "new_ticket_no": "T20260512000088",
  "fee": 37.50,
  "price_diff": 150.00,
  "user_pay": 187.50
}
```

**业务规则**（事务内）：

- 校验旧票可改、新实例有余票。
- 旧票 `status='已改签作废'`；旧 cabin_price 库存 +1。
- 新 cabin_price 库存 -1（含锁），新建客票 `status='有效'`，归属同一订单。
- 写 refund_change（op_type=改签，new_ticket_no=新票号，price_diff=新价-旧价）。

**错误**：`INSUFFICIENT_SEATS`(409)、`NOT_CHANGEABLE`(409)、`SAME_INSTANCE`(409) — 改到同一航班实例

### 12.4 我的退改记录

`GET /api/refund/records` — 👤

**Query**：`page / page_size / op_type`

**响应**（分页）：

```json
{
  "items": [
    {
      "refund_id": 78901,
      "ticket_no": "...",
      "op_type": "退票",
      "fee": 75.00,
      "price_diff": 0.00,
      "new_ticket_no": null,
      "op_time": "..."
    }
  ],
  "total": 5, "page": 1, "page_size": 20
}
```

---

## 13. 管理员管理模块

### 13.1 管理员列表

`GET /api/admins` — 🛡️ *

**响应**：管理员对象数组（不含密码）。

### 13.2 新增管理员

`POST /api/admins` — 🛡️ *

**请求体**：

| 字段        | 类型     | 必填      |
| ----------- | -------- | --------- |
| admin_id    | string   | ✅         |
| password    | string   | ✅         |
| admin_name  | string   | ✅         |
| permissions | string[] | ❌ 默认 [] |

**响应** `201`

### 13.3 删除管理员

`DELETE /api/admins/{admin_id}` — 🛡️ *

**业务约束**：禁止删除自己；禁止删除最后一个拥有 `'*'` 权限的管理员（应用层校验，避免锁死系统）。

**错误**：`LAST_SUPER_ADMIN`(409)

### 13.4 查看权限

`GET /api/admins/{admin_id}/permissions` — 🛡️ *

**响应**：`["flight", "flight_instance", "*"]`

### 13.5 设置权限

`PUT /api/admins/{admin_id}/permissions` — 🛡️ *

**请求体**：

```json
{ "permissions": ["flight", "flight_instance", "order"] }
```

**说明**：全量替换。`'*'` 与具体类型可共存（`'*'` 优先生效）。

---

## 14. 关键流程的接口调用序列

### 14.1 购票主流程（用户端）

```
1.  POST /api/auth/login                    → 拿 token
2.  POST /api/search/flights                → 拿三类候选
3.  GET  /api/flight-instances/{id}         → 看详情和定价档位
4.  GET  /api/passengers                    → 拉常用乘机人
5.  POST /api/booking                       → 下单(15min 倒计时开始)
        ↓ status='待支付'
6.  POST /api/booking/{order_no}/pay        → 模拟支付
        ↓ status='已支付'
7.  GET  /api/orders/{order_no}             → 查订单详情(出票成功)
```

### 14.2 退票流程

```
1.  GET  /api/orders/{order_no}             → 看哪些票可退
2.  GET  /api/refund/quote                  → 试算手续费
        ?ticket_no=...&op_type=refund
3.  POST /api/refund/refund                 → 提交退票
        ↓ ticket.status='已退'
        ↓ 库存回补
        ↓ 订单 status 联动('部分退款'或'已完成退款')
```

### 14.3 改签流程

```
1.  GET  /api/orders/{order_no}             → 选要改的票
2.  POST /api/search/flights                → 找新航班
3.  GET  /api/refund/quote                  → 试算手续费 + 差价
        ?ticket_no=...&op_type=change&new_instance_id=...
4.  POST /api/refund/change                 → 提交改签
        ↓ 旧票 '已改签作废'
        ↓ 新票生成 '有效'(同一 order)
        ↓ refund_change 串联两张票
```

### 14.4 管理员批量上架航班

```
1.  POST /api/auth/admin-login                                  → 管理员登录
2.  POST /api/airlines / /api/aircraft-types / /api/airports    → 维护基础数据
3.  POST /api/flights                                           → 创建航班(含 weekdays/stopovers)
4.  POST /api/flight-instances/batch-generate                   → 批量生成 30 天实例
5.  PUT  /api/flight-instances/{id}/cabin-prices                → 设置每个实例的定价档位
        (或在 batch-generate 时通过 init_cabin_prices 一并设置)
6.  PATCH /api/flight-instances/{id}/status                     → 改为 '可订'
```

---

## 15. 错误码总览

| code                                                         | HTTP | 触发场景                                       |
| ------------------------------------------------------------ | ---- | ---------------------------------------------- |
| `INVALID_INPUT`                                              | 400  | 请求参数格式错误、范围越界                     |
| `INVALID_CREDENTIALS`                                        | 401  | 登录密码错、token 无效                         |
| `PERMISSION_DENIED`                                          | 403  | 角色或资源权限不足、操作非本人订单             |
| `NOT_FOUND`                                                  | 404  | 资源不存在（通用）                             |
| `ORDER_NOT_FOUND`                                            | 404  | 订单不存在                                     |
| `TICKET_NOT_FOUND`                                           | 404  | 客票不存在                                     |
| `PHONE_EXISTS`                                               | 409  | 注册或修改手机号时重复                         |
| `CITY_EXISTS` / `FLIGHT_EXISTS` / `INSTANCE_EXISTS`          | 409  | 主键冲突                                       |
| `CITY_IN_USE` / `AIRPORT_IN_USE` / `AIRCRAFT_IN_USE` / `FLIGHT_IN_USE` / `INSTANCE_IN_USE` | 409  | 删除时被引用                                   |
| `PASSENGER_EXISTS`                                           | 409  | 乘机人证件号重复且姓名不一致                   |
| `PASSENGER_IN_USE`                                           | 409  | 乘机人有客票引用，不可删/改                    |
| `INVALID_NEAR_AIRPORT`                                       | 400  | 临近机场是该城市自己的机场或距离>200km         |
| `NEAR_RELATION_EXISTS`                                       | 409  | 临近关系已存在                                 |
| `INVALID_FLIGHT_DATE`                                        | 400  | 实例日期不在航班 weekdays 内                   |
| `INSUFFICIENT_SEATS`                                         | 409  | 余票不足（下单/改签）                          |
| `DUPLICATE_BOOKING`                                          | 409  | 同一乘客在同一实例已有有效票                   |
| `INSTANCE_NOT_BOOKABLE`                                      | 409  | 实例状态不允许下单                             |
| `ILLEGAL_STATE`                                              | 409  | 状态机不允许该操作（如已支付订单不可重复支付） |
| `ORDER_EXPIRED`                                              | 409  | 订单已超时                                     |
| `NOT_REFUNDABLE` / `NOT_CHANGEABLE`                          | 409  | 距起飞过近不允许退改                           |
| `SAME_INSTANCE`                                              | 409  | 改签到同一航班实例                             |
| `PRICE_BELOW_SOLD`                                           | 409  | 定价 available_seats 低于已售数                |
| `LAST_SUPER_ADMIN`                                           | 409  | 删除最后一个超管                               |
| `INTERNAL_ERROR`                                             | 500  | 服务端异常                                     |



## 附录 ：变更记录

| 版本 | 日期       | 修订人 | 变更说明                                                     |
| ---- | ---------- | ------ | ------------------------------------------------------------ |
| v1.0 | 2026-05-09 | 王铿轶 | 初版。共 61 个接口，按"认证 / 用户与乘客 / 城市机场 / 航司机型 / 航班 / 航班实例与定价 / 搜索 / 下单 / 订单 / 退改 / 管理员"11 模块组织。所有接口标注角色与资源权限，对齐 SCHEMA admin_permission。错误码统一为 24 类 |
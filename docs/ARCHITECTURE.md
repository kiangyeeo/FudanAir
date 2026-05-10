# FudanAir航空票务管理数据库系统 — 架构设计文档（ARCHITECTURE）

| 项目名称 | 航空票务管理数据库系统                                       |
| -------- | ------------------------------------------------------------ |
| 文档版本 | v2.2                                                         |
| 编写日期 | 2026-05-10                                                   |
| 配套文档 | PRD.md（业务需求）、SCHEMA.md（数据库设计）、API.md（接口定义） |

---

## 0. 阅读指南

本文档定义系统的**技术架构**：技术栈、目录结构、分层规范、关键工程实践。本文档不重复 PRD 的业务需求，也不重复 SCHEMA 的字段定义；遇到具体业务规则请回查 PRD.md，遇到字段约束请回查 SCHEMA.md。

文档结构：

- 第 1 节：技术栈总览
- 第 2 节：分层架构（关键 — 决定所有人写代码时把文件放哪）
- 第 3 节：后端目录结构（含数据准备、业务常量）
- 第 4 节：前端目录结构
- 第 5 节：数据库连接、事务规范、应用层约束执行位置
- 第 6 节：认证与权限
- 第 7 节：定时任务
- 第 8 节：错误处理与日志
- 第 9 节：前端设计原则
- 附录 A：完整领域包代码模板
- 附录 B：项目结构速查表
- 附录 C：给 AI 编码助手的提示词要点
- 附录 D：变更记录

---

## 1. 技术栈总览

### 1.1 选型清单

| 层          | 技术                      | 版本   | 选型理由                                           |
| ----------- | ------------------------- | ------ | -------------------------------------------------- |
| 数据库      | MySQL + InnoDB            | 8.0+   | 行锁、事务、外键完整；课程标准选择                 |
| 后端语言    | Python                    | 3.11+  | 团队熟悉、开发效率高                               |
| Web 框架    | FastAPI                   | 0.110+ | 自动生成 OpenAPI 文档、Pydantic 类型校验、异步支持 |
| ORM         | SQLAlchemy                | 2.0+   | Python 生态最成熟 ORM，支持原生 SQL 与 ORM 混用    |
| DB 驱动     | PyMySQL                   | 1.1+   | 纯 Python，跨平台，零编译                          |
| 数据校验    | Pydantic                  | 2.6+   | FastAPI 原生集成                                   |
| 密码哈希    | passlib[bcrypt]           | 1.7+   | 业界标准                                           |
| JWT         | python-jose[cryptography] | 3.3+   | FastAPI 官方推荐，token 通过 httpOnly cookie 传递  |
| 定时任务    | APScheduler               | 3.10+  | 进程内调度，零额外依赖                             |
| 测试        | pytest + httpx            | 最新   | API 测试 + 并发测试                                |
| 数据生成    | Faker                     | 最新   | 演示用户与乘机人随机数据                           |
| 前端框架    | Vue                       | 3.4+   | 工业风票务系统主流选择                             |
| 构建工具    | Vite                      | 5.0+   | 极快的开发服务器                                   |
| UI 组件库   | Element Plus              | 2.6+   | 默认样式即工业风，密度合适                         |
| 状态管理    | Pinia                     | 2.1+   | Vue 3 官方推荐                                     |
| 路由        | Vue Router                | 4.3+   | Vue 官方                                           |
| HTTP 客户端 | Axios                     | 1.6+   | 拦截器机制完整                                     |
| 前端语言    | TypeScript                | 5.3+   | 类型安全；与后端 Pydantic 契约对齐                 |

### 1.2 关键约束

- **复杂查询手写 SQL**：航班搜索、中转推荐、统计报表必须用 `text()` 写原生 SQL；CRUD 用 ORM。这是数据库课的展示需求，也是性能需求。
- **所有写操作走事务**：哪怕是单条 INSERT，也用 `with session.begin():` 显式包裹。
- **认证用 JWT**：通过 httpOnly cookie 传递，前后端分离适配良好。
- **前后端完全分离**：FastAPI 仅出 JSON，前端独立构建独立部署。
- **前端美学**：详见第 9 节。
- **库存双重表达的同步规则**：`cabin_price.available_seats` 与 `flight_instance.economy_left/first_left` 由 `flight.service` 封装为单一函数 `deduct_seat()` 与 `restore_seat()` 同步更新，禁止业务代码直接修改任一字段。
- **业务常量统一管理**：退改费率、中转衔接时间、距离上限等所有业务常量必须从 `core/constants.py` 读取，禁止在业务代码中出现魔法数字（详见 §3.4）。
- **ID 生成统一入口**：订单号、票号、航班实例 ID 必须调用 `core/id_generator.py` 中的函数，禁止业务代码自行拼接（详见 §3.1）。
- **应用层约束 AC-1 至 AC-8**：在 service 层强制执行，详见 §5.8。

---

## 2. 分层架构

### 2.1 三档架构

系统采用"**领域驱动 + 跨领域编排**"的分层架构。代码组织有三个层级，依赖方向严格自上而下：

```
┌──────────────────────────────────────────────────────────────┐
│  workflows/   跨领域编排层(Application Services)              │
│  - booking/   下单流程: 协调 flight + order + ticket         │
│  - refund/    退改流程: 协调 ticket + flight + order         │
│  - search/    航班搜索: 协调 flight + city_near_apt          │
│  ↓ 可调用 domains 和 core                                     │
├──────────────────────────────────────────────────────────────┤
│  domains/     业务领域层(Domain Services)                     │
│  - city/ airline/ flight/ user/ order/ ticket/ admin/        │
│  ↓ 各领域包之间互相不调用,只能调用 core                        │
├──────────────────────────────────────────────────────────────┤
│  core/        基础设施层(Infrastructure)                      │
│  - database / security / exceptions / scheduler / constants  │
│  - id_generator / logging                                    │
│  ↓ 不调用上层,只被上层调用                                    │
└──────────────────────────────────────────────────────────────┘
```

**铁律**：

- **domains 之间不直接互相调用**。`order` 不 import `flight`，`flight` 不 import `order`。
- **跨领域的事务必须放在 `workflows/`**。例如下单要扣 flight 库存 + 建 order + 建 ticket，这个流程属于 `workflows/booking/`，由它统一编排事务。
- **下层不依赖上层**。`core` 不 import `domains`，`domains` 不 import `workflows`。

### 2.2 单领域内部的四层

每个 `domains/<name>/` 包内部仍然分四层：

```
router.py      ↓ HTTP 入口,FastAPI 装饰器在这里
   ↓
service.py     ↓ 业务逻辑,事务边界,业务规则校验
   ↓
repository.py  ↓ 数据访问,只关心"取/存数据",不写业务规则
   ↓
models.py      ↓ SQLAlchemy ORM 实体类(对应数据库表)
schemas.py     旁挂  Pydantic DTO(请求/响应模型,与 ORM 解耦)
```

**各层职责**：

| 层              | 职责                                                         | 不该做的事                                    |
| --------------- | ------------------------------------------------------------ | --------------------------------------------- |
| `router.py`     | 接收 HTTP、解析参数、调用 service、返回响应                  | 写业务逻辑、直接 import models 操作 DB        |
| `service.py`    | 业务规则、事务边界、调用 repository、调用其他 domain 的 service | 直接 import 其他 domain 的 repository、写 SQL |
| `repository.py` | SQL/ORM 查询封装、参数化查询                                 | 写业务规则、调用其他 domain                   |
| `models.py`     | ORM 实体（与 SCHEMA.md 一一对应）                            | 包含业务方法                                  |
| `schemas.py`    | Pydantic DTO，请求体与响应体                                 | 与 ORM 类混用                                 |

### 2.3 跨领域调用规则

`workflows/` 调用 `domains/` 时，**只调对方的 service，不直接调对方的 repository**，不允许进行违反规则的操作。

```python
# 错误:跨领域直接 import repository
from app.domains.flight.repository import FlightRepo
flight_repo = FlightRepo(db)
flight_repo.deduct_stock(...)

# 正确:走对方的 service
from app.domains.flight.service import FlightService
flight_service = FlightService(db)
flight_service.deduct_stock(...)
```

---

## 3. 后端目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 实例、路由注册、CORS、生命周期
│   ├── config.py               # 配置(基于 pydantic_settings)
│   ├── deps.py                 # 全局依赖(get_db, get_current_user)
│   │
│   ├── core/                   # 基础设施(横切)
│   │   ├── __init__.py
│   │   ├── database.py         # engine、SessionLocal、Base
│   │   ├── security.py         # bcrypt、JWT 编解码
│   │   ├── exceptions.py       # AppException 及全部子类(详见 §3.1)
│   │   ├── id_generator.py     # 订单号、票号、实例号生成器(详见 §3.1)
│   │   ├── constants.py        # 业务常量(详见 §3.4)
│   │   ├── scheduler.py        # APScheduler 实例
│   │   └── logging.py          # 日志配置
│   │
│   ├── domains/                # 业务领域包
│   │   ├── city/               # 城市、机场、临近机场
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   ├── airline/            # 航司、机型
│   │   ├── flight/             # 航班、航班实例、舱位定价、库存扣减
│   │   ├── user/               # 用户、乘机人
│   │   ├── order/              # 订单 CRUD、状态机
│   │   ├── ticket/             # 客票 CRUD、状态机
│   │   └── admin/              # 管理员
│   │
│   ├── workflows/              # 跨领域编排
│   │   ├── booking/            # 下单
│   │   │   ├── service.py      # BookingService.create_order(...)
│   │   │   ├── schemas.py
│   │   │   └── router.py
│   │   ├── refund/             # 退改
│   │   └── search/             # 航班搜索(直飞+中转+临近)
│   │
│   ├── auth/                   # 认证(横切关注点,不属于任何领域)
│   │   ├── router.py           # POST /login, POST /register
│   │   ├── service.py
│   │   └── dependencies.py     # get_current_user, get_current_admin
│   │
│   └── jobs/                   # 定时任务
│       ├── __init__.py
│       ├── expire_orders.py    # 超时订单回补库存
│       └── generate_instances.py   # 每日生成 3 个月后那天的航班实例
│
├── tests/
│   ├── conftest.py
│   ├── test_booking_concurrency.py   # ★ 防超卖测试
│   ├── test_refund_flow.py
│   ├── test_search.py
│   └── test_admin_permission.py
│
├── data/                       # ★ CSV 基础数据(详见 §3.3)
│   ├── cities.csv
│   ├── airports.csv
│   ├── city_near_apt.csv
│   ├── airlines.csv
│   ├── aircraft_types.csv
│   ├── flights.csv
│   ├── flight_weekdays.csv
│   └── flight_stopovers.csv
│
├── scripts/
│   ├── schema.sql              # 纯 DDL,复用 SCHEMA.md §9
│   ├── init_db.py              # 主初始化脚本(详见 §3.3)
│   ├── load_csv.py             # CSV 加载工具函数
│   ├── generate_data.py        # 程序生成航班实例与舱位定价
│   └── generate_demo.py        # Faker 生成演示用户/乘机人/管理员
│
├── start.py                    # 后端启动脚本
├── .env.example                # 环境变量模板
├── .env                        # 本地配置(不进 git)
├── .gitignore
├── requirements.txt
└── README.md
```

### 3.1 关键文件说明

#### `app/main.py`

FastAPI 实例、CORS 中间件、路由注册、应用生命周期（启动调度器、关闭连接池）。
不包含任何业务逻辑。

#### `app/config.py`

基于 `pydantic_settings.BaseSettings`，从环境变量读取：

- `DB_URL`
- `JWT_SECRET`
- `JWT_EXPIRE_MINUTES`（默认 1440 = 24h）
- `ORDER_EXPIRE_MINUTES`（默认 15）
- `SCHEDULER_INTERVAL_SECONDS`（默认 60）
- `INSTANCE_GENERATION_HOUR`（默认 3，凌晨 3 点生成航班实例）
- `INSTANCE_AHEAD_DAYS`（默认 90，提前 90 天生成实例）
- `CORS_ORIGINS`

#### `app/deps.py`

全局依赖：

- `get_db()` 产出 SQLAlchemy Session
- `get_current_user(token)` 解析 JWT 返回当前用户
- `get_current_admin(token)` 解析 JWT 返回当前管理员
- `require_admin` 校验当前角色为管理员

#### `app/core/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine(
    settings.DB_URL,
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
```

#### `app/core/exceptions.py` —— 完整异常类清单

异常类与 API.md §14 错误码一一对应。**业务代码统一抛这些类，不要新建**：

```python
class AppException(Exception):
    code: str = "INTERNAL_ERROR"
    message: str = ""
    http_status: int = 500
    def __init__(self, message: str = ""):
        self.message = message or self.message
        super().__init__(self.message)

# 401
class AuthenticationError(AppException):       code, http_status = "AUTHENTICATION_FAILED", 401
class UnauthorizedError(AppException):         code, http_status = "UNAUTHORIZED", 401

# 403
class PermissionDeniedError(AppException):     code, http_status = "PERMISSION_DENIED", 403

# 404
class ResourceNotFoundError(AppException):     code, http_status = "RESOURCE_NOT_FOUND", 404

# 409
class ResourceInUseError(AppException):        code, http_status = "RESOURCE_IN_USE", 409
class PhoneAlreadyExistsError(AppException):   code, http_status = "PHONE_ALREADY_EXISTS", 409
class InsufficientStockError(AppException):    code, http_status = "INSUFFICIENT_STOCK", 409
class PassengerDuplicateError(AppException):   code, http_status = "PASSENGER_DUPLICATE", 409
class InstanceNotBookableError(AppException):  code, http_status = "INSTANCE_NOT_BOOKABLE", 409
class OrderNotPayableError(AppException):      code, http_status = "ORDER_NOT_PAYABLE", 409
class OrderNotCancelableError(AppException):   code, http_status = "ORDER_NOT_CANCELABLE", 409
class TicketNotRefundableError(AppException):  code, http_status = "TICKET_NOT_REFUNDABLE", 409
class TicketNotChangeableError(AppException):  code, http_status = "TICKET_NOT_CHANGEABLE", 409

# 400
class InvalidPhoneFormatError(AppException):       code, http_status = "INVALID_PHONE_FORMAT", 400
class OldPasswordMismatchError(AppException):      code, http_status = "OLD_PASSWORD_MISMATCH", 400
class InconsistentAirportCityError(AppException):  code, http_status = "INCONSISTENT_AIRPORT_CITY", 400
class SameTicketNotAllowedError(AppException):     code, http_status = "SAME_TICKET_NOT_ALLOWED", 400
```

#### `app/core/id_generator.py` —— ID 生成统一入口

所有业务编号必须调用本模块函数生成，禁止业务代码自行拼接：

```python
import random, string
from datetime import datetime, date

def gen_order_no() -> str:
    """O{yyyymmddHHmmss}{随机6位字母数字} - 例: O20260510142301X3K9"""
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"O{datetime.now():%Y%m%d%H%M%S}{suffix}"

def gen_ticket_no(seq: int) -> str:
    """T{yyyymmdd}{递增9位} - 例: T20260510000001
    seq 由调用方从数据库自增序列获取(每日重置)
    """
    return f"T{date.today():%Y%m%d}{seq:09d}"

def gen_instance_id(flight_no: str, flight_date: date) -> str:
    """{flight_no}_{yyyymmdd} - 例: CA1234_20260510"""
    return f"{flight_no}_{flight_date:%Y%m%d}"
```

> 注：`refund_id` 与 `user_id` 是 BIGINT AUTO_INCREMENT，由数据库自动产生，不需经此模块。

### 3.2 一个完整领域包的示例：`domains/flight/`

```
flight/
├── __init__.py
├── models.py        # Flight, FlightInstance, FlightWeekday, FlightStopover, CabinPrice
├── schemas.py       # FlightCreate, FlightUpdate, FlightResponse, InstanceResponse, ...
├── repository.py    # FlightRepository, FlightInstanceRepository, CabinPriceRepository
├── service.py       # FlightService 方法:
│                    #   - get_flight_by_no
│                    #   - create_instance
│                    #   - batch_generate_instances(flight_no, start_date, end_date)
│                    #   - lock_and_deduct_cabin(...)  ★ 防超卖核心
│                    #   - restore_cabin_stock(...)    ★ 退改回补
│                    #   - update_instance_status(...)
└── router.py        # /flights, /flights/{no}, /flights/{no}/instances, ...
```

`flight.service.lock_and_deduct_cabin` 提供给 `workflows/booking/` 调用，是防超卖的关键方法。

完整代码模板见**附录 A**。

### 3.3 数据准备与初始化（重要）

> 本节说明项目数据从准备到导入的完整流程。**新开发者拿到代码后，必须读懂本节才能让系统跑起来。**

#### 3.3.1 数据来源分类

系统共 16 张表，按数据来源分四类：

| 类别 | 表 | 来源 | 进 git |
| ---- | ---- | ------ | ---- |
| **真实基础数据**（CSV） | city, airport, city_near_apt, airline, aircraft_type | 公开数据手工整理 | ✅ |
| **半真实业务数据**（CSV） | flight, flight_weekday, flight_stopover | 参考真实航班号与航线编排 | ✅ |
| **程序生成数据** | flight_instance, cabin_price | 由 `generate_data.py` 按规则批量生成 | ❌ 运行时插入 |
| **演示与运行时数据** | admin, user, passenger, aptorder, ticket, refund_change | admin 硬编码、user/passenger 用 Faker、订单等运行时产生 | ❌ |

#### 3.3.2 CSV 文件清单

所有 CSV 放在 `backend/data/` 目录，必须 **UTF-8 无 BOM** 编码。每份 CSV 第一行为表头，与对应表字段一致：

| 文件                   | 列                                                           | 量级      |
| ---------------------- | ------------------------------------------------------------ | --------- |
| `cities.csv`           | city_name                                                    | ~250-300  |
| `airports.csv`         | iata_code, airport_name, city_name                           | ~250      |
| `city_near_apt.csv`    | city_name, iata_code, distance(用该值为0表示机场位于此城市)    | ~50-100   |
| `airlines.csv`         | iata_code, airline_name                                      | ~10-15    |
| `aircraft_types.csv`   | model, economy_seats, first_seats                            | ~10       |
| `flights.csv`          | flight_no, scheduled_departure, scheduled_arrival, fuel_infra_fee, dep_airport_code, dep_terminal, arr_airport_code, arr_terminal, airline_code, aircraft_model | ~50-150   |
| `flight_weekdays.csv`  | flight_no, weekday（一行一个 weekday，每个航班对应多行）     | ~300-1000 |
| `flight_stopovers.csv` | flight_no, stop_order, airport_code                          | ~10-20    |

**city_near_apt 完整性约定**：
- `distance = 0` 是判断“城市拥有机场”的唯一依据。
- 非 0 记录表示跨城临近机场关系，距离必须在 `[0, 300]`。

#### 3.3.3 init_db.py 调用链

`scripts/init_db.py` 是**统一的初始化入口**，按固定顺序执行：

```python
"""一键初始化数据库 - DROP 重建 → 建表 → 灌 CSV → 程序生成 → 创建演示账号"""
import pymysql
from app.config import settings
from scripts import load_csv, generate_data, generate_demo

def main():
    conn = pymysql.connect(
        host='localhost', user='root', password=...,  # 从 settings 读
        charset='utf8mb4'
    )
    cur = conn.cursor()
    
    # 1. 重建数据库
    cur.execute("DROP DATABASE IF EXISTS fudan_air")
    cur.execute("CREATE DATABASE fudan_air CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute("USE fudan_air")
    
    # 2. 建表(执行 schema.sql)
    with open('scripts/schema.sql', encoding='utf-8') as f:
        for stmt in f.read().split(';'):
            if stmt.strip():
                cur.execute(stmt)
    
    # 3. 灌真实基础数据(CSV → DB)
    load_csv.load_cities(cur)
    load_csv.load_airports(cur)          # 只导入 airport
    load_csv.load_city_near_apt(cur)     # 导入完整 city_near_apt，含 distance=0 自有机场记录
    load_csv.load_airlines(cur)
    load_csv.load_aircraft_types(cur)
    load_csv.load_flights(cur)
    load_csv.load_flight_weekdays(cur)
    load_csv.load_flight_stopovers(cur)
    
    # 4. 程序生成大批量数据
    generate_data.generate_flight_instances(cur)   # 按 flight_weekday 展开未来 90 天
    generate_data.generate_cabin_prices(cur)        # 每实例 2-3 档位
    
    # 5. 演示账号
    generate_demo.create_admins(cur)                # bcrypt 哈希后插入
    generate_demo.generate_demo_users(cur, n=20)
    generate_demo.generate_demo_passengers(cur, n=50)
    
    conn.commit()
    print("✅ 初始化完成")
```

#### 3.3.4 关键导入逻辑


**管理员密码 bcrypt 哈希**：

```python
# scripts/generate_demo.py
import bcrypt

def create_admins(cur):
    admins = [
        ('A001', 'admin123', '系统管理员'),
        ('A002', 'admin456', '运营管理员'),
    ]
    for admin_id, plain_pwd, name in admins:
        pwd_hash = bcrypt.hashpw(plain_pwd.encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO admin (admin_id, admin_password, admin_name) VALUES (%s, %s, %s)",
            (admin_id, pwd_hash, name)
        )
```

#### 3.3.5 重跑约定

`init_db.py` 第一步会 **DROP DATABASE** 重建，所有数据清空。**仅在 schema 改动或希望重置数据时执行**。运行时产生的真实订单数据不会保留。

### 3.4 业务常量统一存放

所有业务常量必须集中存放于 `core/constants.py`，业务代码从此模块读取，**禁止在 service 层出现魔法数字**。

```python
# core/constants.py
# === 退改费率(PRD §6.2)===
# 列表按"距起飞时间(天)"降序排列;查询时取首个满足 days_to_departure >= 阈值 的档位
# (阈值, 退票费率, 改签费率)
REFUND_FEE_TIERS = [
    (30, 0.00, 0.00),   # ≥30天:退0% / 改0%
    (7,  0.20, 0.20),   # 7-30天
    (3,  0.40, 0.40),   # 3-7天
    (1,  0.60, 0.50),   # 1-3天
    (0,  0.80, 0.60),   # <1天
]
# 已起飞: 不可操作(在 service 层判断,不在表里)

# === 中转规则(PRD §6.4)===
TRANSIT_MIN_MINUTES = 120   # 最小衔接时间 2 小时
TRANSIT_MAX_MINUTES = 360   # 最大衔接时间 6 小时

# === 临近机场(PRD §6.5 + SCHEMA §3.1.3)===
NEARBY_DISTANCE_MAX_KM = 300

# === 业务编号格式参考(实现在 core/id_generator.py)===
# order_no:    O{yyyymmddHHmmss}{随机6位}
# ticket_no:   T{yyyymmdd}{递增9位}
# instance_id: {flight_no}_{yyyymmdd}

# === 库存初始化默认分配比例 ===
# 经济舱-标准:经济舱-特价 = 9:1(可由管理员手动覆盖)
ECONOMY_STANDARD_RATIO = 0.9
```

> 订单超时（`ORDER_EXPIRE_MINUTES`）、调度器间隔（`SCHEDULER_INTERVAL_SECONDS`）等可调整的运行参数已在 `.env` 中通过 `settings` 读取，不放本文件。本文件存放的是"业务规则层面、原则上不应运行时调整"的常量。

#### `.env` 配置参考

```ini
# 数据库连接 - 把 YOUR_PASSWORD 改成自己的 MySQL root 密码
DB_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/fudan_air?charset=utf8mb4

# JWT 签名密钥 - 团队内可统一
JWT_SECRET=please-change-me-to-a-random-string-at-least-32-chars
JWT_EXPIRE_MINUTES=1440

# 业务配置 - 一般不改
ORDER_EXPIRE_MINUTES=15
SCHEDULER_INTERVAL_SECONDS=60
INSTANCE_GENERATION_HOUR=3
INSTANCE_AHEAD_DAYS=90

# CORS
CORS_ORIGINS=http://localhost:5173
```

---

## 4. 前端目录结构

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── main.ts                 # 应用入口
│   ├── App.vue                 # 根组件
│   ├── router/
│   │   └── index.ts            # 路由配置(用户端 + 管理端两套)
│   ├── stores/                 # Pinia stores
│   │   ├── auth.ts             # 当前用户、token
│   │   ├── search.ts           # 搜索条件持久化
│   │   └── booking.ts          # 下单流程的多步状态
│   │
│   ├── api/                    # ★ HTTP 客户端,按后端 domain 分组
│   │   ├── client.ts           # axios 实例 + 拦截器(注入 JWT,统一错误)
│   │   ├── auth.ts
│   │   ├── flight.ts
│   │   ├── order.ts
│   │   ├── booking.ts
│   │   ├── search.ts
│   │   └── admin.ts
│   │
│   ├── types/                  # 后端 schema 对应的 TS 类型
│   │   ├── flight.ts
│   │   ├── order.ts
│   │   └── ...
│   │
│   ├── views/                  # ★ 页面组件,按业务功能分
│   │   ├── public/
│   │   │   ├── HomeView.vue           # 主页(搜索框)
│   │   │   ├── LoginView.vue
│   │   │   └── RegisterView.vue
│   │   ├── user/                      # 用户端页面
│   │   │   ├── SearchResultView.vue   # 三类候选合并展示
│   │   │   ├── BookingView.vue        # 录乘机人、下单
│   │   │   ├── PaymentView.vue        # 模拟支付(15分钟倒计时)
│   │   │   ├── OrderListView.vue      # 我的订单
│   │   │   ├── OrderDetailView.vue
│   │   │   ├── RefundView.vue
│   │   │   ├── ChangeView.vue         # 改签
│   │   │   └── ProfileView.vue        # 个人信息、乘机人管理
│   │   └── admin/                     # 管理端页面
│   │       ├── DashboardView.vue
│   │       ├── CityManageView.vue
│   │       ├── AirportManageView.vue
│   │       ├── AirlineManageView.vue
│   │       ├── AircraftManageView.vue
│   │       ├── FlightManageView.vue
│   │       ├── InstanceManageView.vue
│   │       ├── PriceManageView.vue
│   │       └── OrderManageView.vue
│   │
│   ├── components/             # 可复用组件
│   │   ├── common/
│   │   │   ├── AppHeader.vue
│   │   │   ├── AppFooter.vue
│   │   │   └── EmptyState.vue
│   │   ├── flight/
│   │   │   ├── FlightCard.vue           # 一条航班的展示卡片
│   │   │   ├── DirectFlightList.vue     # 直飞列表
│   │   │   ├── TransitFlightList.vue    # 中转列表
│   │   │   ├── NearbyFlightList.vue     # 临近机场列表
│   │   │   └── FilterPanel.vue          # 筛选面板
│   │   └── order/
│   │       ├── PassengerForm.vue
│   │       ├── OrderTimeline.vue        # 订单状态时间线
│   │       └── PaymentCountdown.vue
│   │
│   ├── layouts/                # 布局
│   │   ├── UserLayout.vue      # 用户端外壳
│   │   ├── AdminLayout.vue     # 管理端外壳(侧边栏)
│   │   └── BlankLayout.vue     # 登录/注册页
│   │
│   ├── styles/
│   │   ├── tokens.scss         # 设计令牌(色彩、间距、字号)
│   │   ├── element-overrides.scss   # 覆盖 Element Plus 默认变量
│   │   └── global.scss
│   │
│   └── utils/
│       ├── format.ts           # 日期、金额、时长格式化
│       └── validators.ts
│
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
└── README.md
```

### 4.1 `api/` 目录的职责

每个 `api/<name>.ts` 文件对应一个后端 domain 的 HTTP 调用集合。例如：

```typescript
// api/flight.ts
import { http } from './client'
import type { FlightInstance, FlightSearchParams } from '@/types/flight'

export const flightApi = {
  getInstance: (id: string) => http.get<FlightInstance>(`/flights/instances/${id}`),
  listInstances: (params: { flightNo: string }) => http.get<FlightInstance[]>('/flights/instances', { params }),
}
```

**好处**：

- 视图组件只 import `flightApi`，不直接写 axios。
- 后端 API 改了，只改 `api/` 这一层，组件不动。
- 配合 TypeScript 类型，IDE 能自动补全字段。

### 4.2 路由分两套

`router/index.ts` 中维护两条路由树，分别走 `UserLayout` 和 `AdminLayout`：

```typescript
const routes = [
  { path: '/login',     component: LoginView,    meta: { layout: 'blank' } },
  { path: '/register',  component: RegisterView, meta: { layout: 'blank' } },
  // 用户端
  { path: '/',          component: HomeView,     meta: { layout: 'user' } },
  { path: '/search',    component: SearchResultView, meta: { layout: 'user' } },
  { path: '/booking',   component: BookingView,  meta: { layout: 'user',  requiresAuth: true } },
  { path: '/orders',    component: OrderListView, meta: { layout: 'user', requiresAuth: true } },
  // ...
  // 管理端
  { path: '/admin',           component: DashboardView,    meta: { layout: 'admin', requiresAdmin: true } },
  { path: '/admin/cities',    component: CityManageView,   meta: { layout: 'admin', requiresAdmin: true } },
  // ...
]
```

路由守卫在 `router/index.ts` 中根据 `meta.requiresAuth` / `requiresAdmin` 校验 token。

---

## 5. 数据库连接与事务规范

### 5.1 连接池配置

见 §3.1 的 `core/database.py`。关键参数：

| 参数            | 值   | 说明                                                      |
| --------------- | ---- | --------------------------------------------------------- |
| `pool_size`     | 10   | 常驻连接数                                                |
| `max_overflow`  | 10   | 突发额外连接数                                            |
| `pool_pre_ping` | True | 取连接前 ping 一下，防止连接被 MySQL 超时关闭             |
| `pool_recycle`  | 3600 | 1 小时回收连接，避免 MySQL `wait_timeout` 默认 8 小时问题 |

### 5.2 Session 生命周期

每个 HTTP 请求一个 Session，请求结束自动关闭：

```python
# deps.py
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

业务代码通过依赖注入获取：

```python
# router.py
@router.get("/orders/{order_no}")
def get_order(order_no: str, db: Session = Depends(get_db)):
    return OrderService(db).get(order_no)
```

### 5.3 事务边界

**事务由 service 层显式开启与提交，repository 层不管理事务**。

#### 单领域内的简单事务

```python
# domains/order/service.py
class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OrderRepository(db)

    def cancel_order(self, order_no: str):
        with self.db.begin():               # 开启事务
            order = self.repo.lock_for_update(order_no)   # SELECT ... FOR UPDATE
            if order.status != "待支付":
                raise OrderNotCancelableError("订单状态不允许取消")
            order.status = "已取消"
        # with 块结束自动 commit;异常自动 rollback
```

#### 跨领域的复合事务（在 workflows 层）

```python
# workflows/booking/service.py
class BookingService:
    def __init__(self, db: Session):
        self.db = db
        self.flight_svc = FlightService(db)
        self.order_svc = OrderService(db)
        self.ticket_svc = TicketService(db)

    def create_order(self, user_id: int, payload: BookingRequest) -> str:
        with self.db.begin():               # ★ 跨领域事务由 workflow 统一开启
            # 1. 锁定并扣减 cabin_price 库存
            self.flight_svc.lock_and_deduct_cabin(
                instance_id=payload.instance_id,
                cabin_class=payload.cabin_class,
                fare_type=payload.fare_type,
                count=len(payload.passengers),
            )
            # 2. 创建订单
            order = self.order_svc.create(user_id, payload.total_amount)
            # 3. 为每位乘机人创建客票
            for p in payload.passengers:
                self.ticket_svc.create(
                    order_no=order.order_no,
                    passenger_id=p.id_no,
                    ...
                )
            return order.order_no
```

**关键点**：

- 三个 service 共享同一个 `db` Session，因此共享同一个事务。
- `flight_svc.lock_and_deduct_cabin` 内部不开事务（嵌套），由调用方控制。
- 任何一步抛异常，整个事务回滚。

### 5.4 防超卖：`SELECT ... FOR UPDATE`

```python
# domains/flight/repository.py
from sqlalchemy import select

class CabinPriceRepository:
    def lock_for_update(self, instance_id: str, cabin_class: str, fare_type: str):
        stmt = (
            select(CabinPrice)
            .where(
                CabinPrice.instance_id == instance_id,
                CabinPrice.cabin_class == cabin_class,
                CabinPrice.fare_type == fare_type,
            )
            .with_for_update()           # ★ 翻译为 SELECT ... FOR UPDATE
        )
        return self.db.execute(stmt).scalar_one_or_none()
```

```python
# domains/flight/service.py
class FlightService:
    def lock_and_deduct_cabin(self, instance_id, cabin_class, fare_type, count):
        cp = self.cabin_price_repo.lock_for_update(instance_id, cabin_class, fare_type)
        if cp is None:
            raise ResourceNotFoundError("舱位不存在")
        if cp.available_seats < count:
            raise InsufficientStockError(f"剩余 {cp.available_seats}, 申请 {count}")
        cp.available_seats -= count

        # 同步汇总库存(双重表达,详见 §5.7)
        instance = self.instance_repo.get(instance_id)
        if cabin_class == "经济舱":
            instance.economy_left -= count
        else:
            instance.first_left -= count
```

**为什么用悲观锁而不是乐观锁**：MySQL 行锁在 InnoDB 下是高效实现；在春运并发场景下，悲观锁的"先来先得"语义更直观；课程评分时讲解事务隔离级别也更顺畅。

### 5.5 复杂查询用原生 SQL

航班搜索、中转推荐、统计报表必须手写 SQL。模式：

```python
# workflows/search/service.py
from sqlalchemy import text
from app.core.constants import TRANSIT_MIN_MINUTES, TRANSIT_MAX_MINUTES

class SearchService:
    def find_transit_flights(self, dep_city: str, arr_city: str, date: date):
        sql = text("""
            SELECT
                leg1.instance_id   AS leg1_id,
                leg1.flight_no     AS leg1_flight,
                leg1.arr_airport_code AS transit_apt,
                leg2.instance_id   AS leg2_id,
                leg2.flight_no     AS leg2_flight,
                TIMESTAMPDIFF(MINUTE, ...) AS transit_minutes
            FROM v_flight_search leg1
            JOIN v_flight_search leg2 ON ...
            WHERE leg1.dep_city = :dep_city
              AND leg2.arr_city = :arr_city
              AND leg1.flight_date = :date
              AND TIMESTAMPDIFF(MINUTE, ...) BETWEEN :min_t AND :max_t
        """)
        rows = self.db.execute(sql, {
            "dep_city": dep_city, "arr_city": arr_city, "date": date,
            "min_t": TRANSIT_MIN_MINUTES, "max_t": TRANSIT_MAX_MINUTES,
        }).mappings().all()
        return [dict(r) for r in rows]
```

**强制要求**：

- 用 `text(...)` 显式声明原生 SQL，不要字符串拼接业务参数。
- 用 `:param` 绑定参数，杜绝 SQL 注入。
- 业务常量（如中转时间）从 `core/constants.py` 导入，不在 SQL 中硬编码。

### 5.6 隔离级别

MySQL InnoDB 默认 `REPEATABLE READ`，本项目不修改。关键事务（下单、退改）使用 `SELECT ... FOR UPDATE` 加行锁，天然防止幻读与丢失更新。

### 5.7 关键事务规范

**库存同步规则**（强制）：

- 任何修改 `cabin_price.available_seats` 的地方，必须同时修改 `flight_instance.economy_left`（经济舱）或 `first_left`（头等舱）
- 实现方式：`flight.service.deduct_seat(instance_id, cabin_class, fare_type, count)` 在事务内执行 UPDATE 两张表，业务代码统一调此函数
- 反向操作：`flight.service.restore_seat(...)` 用于退改和超时回补

**airport-city_near_apt 双写规则**（强制，但不适用于初始化 CSV 导入）：

- `airport.service.create(iata, name, city_name)`：事务内同时插入 `airport` 和 `city_near_apt(city_name, iata, 0)`
- `airport.service.update_city(iata, new_city)`：事务内更新 `airport.city_name`、删除旧 distance=0 记录、插入新 distance=0 记录
- 删除 airport 由 `city_near_apt.iata_code` 上的 `ON DELETE CASCADE` 自动处理
- 任何外部调用 `city_near_apt` 增删的入口：若 distance=0，必须先校验对应 `airport(iata).city_name == city_name`，否则抛 `InconsistentAirportCityError`

### 5.8 应用层约束执行位置

SCHEMA.md §4.2 列出 8 条应用层约束，下表给出每条**在代码中的强制位置**。新增 service 方法时务必对照本表确认覆盖到位：

| 编号 | 约束 | 强制位置 | 抛出异常 |
| --- | --- | --- | --- |
| AC-1 | 同一乘客在同一航班实例上仅 1 张有效客票 | `BookingService.create_order` 在锁定 cabin_price 后、INSERT ticket 前查询 `ticket WHERE passenger_id=? AND instance_id=? AND status='有效'` | `PassengerDuplicateError` |
| AC-2 | `cabin_price.available_seats` 与 `flight_instance.economy_left/first_left` 同步 | `FlightService.deduct_seat / restore_seat` 内部双 UPDATE | — |
| AC-3 | 改签 `new_ticket_no ≠ ticket_no` | `RefundService.change_ticket` 生成新票号后校验 | `SameTicketNotAllowedError` |
| AC-4 | `airport.city_name` 与 `city_near_apt` distance=0 一致 | `AirportService.create / update_city / delete` 事务内双写；`CityNearAptService.create / delete` 入口校验 | `InconsistentAirportCityError` |
| AC-5 | `flight.dep_airport_code != flight.arr_airport_code` | `FlightService.create_flight / update_flight` 入口校验 | `AppException("起降不能同机场")` |
| AC-6 | `flight_instance.flight_date` 必须落在 `flight_weekday` 内 | `FlightInstanceService.create_instance` 校验 weekday | `AppException("日期不在飞行日内")` |
| AC-7 | `flight_stopover.airport_code` 不能是该航班起飞或到达机场 | `FlightService.create_flight / add_stopover` 校验 | `AppException("经停机场冲突")` |
| AC-8 | 已起飞/已到达/已取消的实例不可再下单；已退/已改签作废/已使用的票不可再退改 | `BookingService.create_order` 入口校验 instance.status；`RefundService.refund/change` 入口校验 ticket.status | `InstanceNotBookableError` / `TicketNotRefundableError` / `TicketNotChangeableError` |

> 这些校验**必须在 service 层显式编写**，不能依赖前端校验或数据库约束兜底。

---

## 6. 认证与权限

**认证方式**：JWT，token 通过 httpOnly cookie 传递。

**角色判定**：JWT payload 中的 `role` 字段，取值 `"user"` 或 `"admin"`。两类登录入口分别签发对应 role 的 token：

- `POST /api/auth/login` 签发 role=user
- `POST /api/auth/admin-login` 签发 role=admin

**依赖注入**：

- `get_current_user` — 解析 token，要求 role=user，否则 403
- `get_current_admin` — 解析 token，要求 role=admin，否则 403
- 所有用户接口加 `Depends(get_current_user)`，所有管理接口加 `Depends(get_current_admin)`

**管理员账号来源**：由 `scripts/init_db.py` 在初始化时通过 bcrypt 生成密码哈希后插入；不开放运行时创建。

---

## 7. 定时任务

### 7.1 启动调度器

```python
# core/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

def start_scheduler():
    from app.jobs.expire_orders import expire_orders_job
    from app.jobs.generate_instances import generate_instances_daily
    
    scheduler.add_job(
        expire_orders_job,
        trigger="interval",
        seconds=settings.SCHEDULER_INTERVAL_SECONDS,
        id="expire_orders",
        max_instances=1,         # 不允许同一任务并发执行
        coalesce=True,           # 错过的执行合并为一次
    )
    scheduler.add_job(
        generate_instances_daily,
        trigger="cron",
        hour=settings.INSTANCE_GENERATION_HOUR,
        id="generate_instances",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
```

```python
# main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
```

### 7.2 超时订单回补任务

```python
# jobs/expire_orders.py
def expire_orders_job():
    with SessionLocal() as db:
        expired_orders = db.execute(text("""
            SELECT order_no FROM aptorder
            WHERE status = '待支付'
              AND created_at < NOW() - INTERVAL :mins MINUTE
        """), {"mins": settings.ORDER_EXPIRE_MINUTES}).scalars().all()

        for order_no in expired_orders:
            try:
                BookingService(db).expire_order(order_no)   # 内部用事务
                logger.info(f"订单 {order_no} 已超时取消并回补库存")
            except Exception as e:
                logger.exception(f"订单 {order_no} 超时处理失败: {e}")
```

`BookingService.expire_order` 在事务内：

1. 锁定订单，校验仍是"待支付"；
2. 改订单状态为"已取消"；
3. 改所有客票状态为"已退"；
4. 回补 `cabin_price.available_seats`；
5. 回补 `flight_instance.economy_left/first_left`。

### 7.3 自动放票机制

```python
# jobs/generate_instances.py
def generate_instances_daily():
    """每天凌晨生成 90 天后那一天的航班实例"""
    target_date = date.today() + timedelta(days=settings.INSTANCE_AHEAD_DAYS)
    weekday = target_date.isoweekday()  # 1-7
    with SessionLocal() as db:
        flights = db.execute(
            text("SELECT flight_no FROM flight_weekday WHERE weekday = :w"),
            {"w": weekday}
        ).scalars().all()
        for flight_no in flights:
            FlightService(db).create_instance(flight_no, target_date)  # 含舱位定价初始化
```

幂等性：`flight_instance` 的 `(flight_no, flight_date)` 唯一约束保证重复执行不会插入重复行。

详细 SQL 见 SCHEMA.md §8.2。

---

## 8. 错误处理与日志

### 8.1 异常 → HTTP 响应映射

```python
# main.py
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(AppException)
async def app_exc_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "message": exc.message},
    )
```

业务代码只 `raise InsufficientStockError("...")`，框架层自动转为：

```json
{ "code": "INSUFFICIENT_STOCK", "message": "剩余 0,申请 2" }
```

异常类完整清单见 §3.1。**禁止业务代码自行 `raise HTTPException` 或抛裸 Exception**。

### 8.2 日志规范

- 使用 Python 标准库 `logging`，配置在 `core/logging.py`。
- 关键节点必打日志：登录、下单（含订单号 + 用户 + 实例 + 数量）、支付、退改、超时取消。
- 格式：`[时间] [级别] [模块] [trace_id] 内容`。
- 不打印密码、token、银行卡号等敏感字段。

### 8.3 前端错误处理

axios 拦截器统一处理：

- HTTP 401 → 跳登录页（cookie 失效，无需手动清 token）
- HTTP 403 → 显示"无权限"提示
- HTTP 4xx → 显示后端 `message` 字段
- HTTP 5xx → 显示"系统繁忙"

```typescript
// api/client.ts
http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const { status, data } = err.response ?? {}
    if (status === 401) {
      router.push('/login')
    } else if (data?.message) {
      ElMessage.error(data.message)
    } else {
      ElMessage.error('系统繁忙,请稍后重试')
    }
    return Promise.reject(err)
  }
)
```

---

## 9. 前端设计原则

这一节是项目的"风格宪法"。**任何前端 PR 都应该过这一节的检查**。

### 9.1 工业风票务系统的视觉特征

参考样本：携程、飞猪、12306（新版）、Skyscanner、Google Flights。这些网站的共同特征：

- **极高的信息密度**：一屏要能看 6–8 个航班选项 + 筛选条件 + 排序，不允许大留白。
- **白底为主**：背景几乎都是 `#FFFFFF` 或 `#F5F7FA`。
- **单一品牌色**：一个主色（蓝或橙），全站强调元素只用这一色。
- **黑色或深灰文字**：标题用 `#1F2329` 级别的深色，不用纯黑，不用浅灰。
- **窄圆角**：卡片圆角 4–8px，按钮 4px。**绝不**使用 16px 以上圆角。
- **细描边胜过阴影**：分隔用 `1px solid #E5E6EB`，不用 box-shadow。
- **数字用等宽字体**：价格、时间、航班号用 `font-feature-settings: 'tnum'` 等宽数字。

### 9.2 严格禁止清单

以下元素一旦出现就要返工：

| 禁止                            | 为什么是 AI 味              | 替代方案              |
| ------------------------------- | --------------------------- | --------------------- |
| 紫色渐变 / 青色渐变             | ChatGPT 配色                | 单一品牌色实色        |
| 毛玻璃（backdrop-filter: blur） | 现代 AI 产品标志            | 实色背景              |
| Emoji 作为图标 (✈️ 🎫 ✨)          | AI 工具偏爱                 | Element Plus 内置图标 |
| 16px+ 大圆角                    | 移动端 AI 产品风            | 4–8px                 |
| 浅灰文字（#999 以下）           | 低对比度，AI 喜爱的"高级感" | 深灰 #1F2329          |
| 紫蓝粉混合配色                  | "AI 渐变三件套"             | 单色                  |
| "AI 闪烁光标"装饰               | 显眼的 AI 暗示              | 无                    |
| 装饰性浮动球（floating orb）    | 大语言模型产品 UI 通病      | 无装饰                |
| 卡片大量阴影叠加                | 拟物的 AI 风                | 边框替代              |
| 全屏 hero 大图 + 大标题         | SaaS 落地页风               | 直接展示搜索框        |

### 9.3 关键页面的设计参考

| 页面          | 参考对象                     | 关键点                                                       |
| ------------- | ---------------------------- | ------------------------------------------------------------ |
| 主页 / 搜索框 | 携程首页                     | 顶部巨大搜索框 + 下方推荐城市，不要 hero 图                  |
| 搜索结果      | 携程 / Google Flights        | 左侧筛选 + 右侧三类候选纵向列表，每条航班 80–100px 高        |
| 航班卡片      | 飞猪                         | 起飞时间(大字) + 航司 logo + 时长(等宽字) + 价格(右侧大红字) |
| 下单页        | 携程                         | 表格化乘机人录入，每行一个                                   |
| 支付页        | 携程                         | 顶部 15 分钟倒计时(纯文字),不要花哨动画                      |
| 订单列表      | 12306                        | 表格式或卡片式皆可，但要展示 5+ 列信息                       |
| 管理端        | Element Plus 默认 admin 模板 | 左侧导航 + 顶部面包屑 + 中央表格                             |

---

## 附录 A：完整领域包代码模板

以 `domains/airline/` 为例，给出五个文件的完整代码，**新建任何 domain 包都应模仿此模板的层次划分**：

### A.1 `models.py`

```python
from sqlalchemy import Column, String
from app.core.database import Base

class Airline(Base):
    __tablename__ = "airline"
    iata_code = Column(String(2), primary_key=True)
    airline_name = Column(String(128), nullable=False, unique=True)
```

### A.2 `schemas.py`

```python
from pydantic import BaseModel, Field

class AirlineCreate(BaseModel):
    iata_code: str = Field(..., min_length=2, max_length=2)
    airline_name: str = Field(..., max_length=128)

class AirlineUpdate(BaseModel):
    airline_name: str = Field(..., max_length=128)

class AirlineResponse(BaseModel):
    iata_code: str
    airline_name: str
    model_config = {"from_attributes": True}
```

### A.3 `repository.py`

```python
from sqlalchemy.orm import Session
from .models import Airline

class AirlineRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, iata_code: str) -> Airline | None:
        return self.db.get(Airline, iata_code)

    def list_all(self) -> list[Airline]:
        return self.db.query(Airline).all()

    def create(self, **data) -> Airline:
        obj = Airline(**data)
        self.db.add(obj)
        self.db.flush()
        return obj

    def update(self, iata_code: str, **data) -> Airline:
        obj = self.get(iata_code)
        for k, v in data.items():
            setattr(obj, k, v)
        self.db.flush()
        return obj

    def delete(self, iata_code: str) -> None:
        obj = self.get(iata_code)
        if obj:
            self.db.delete(obj)
            self.db.flush()
```

### A.4 `service.py`

```python
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .repository import AirlineRepository
from .schemas import AirlineCreate, AirlineUpdate
from app.core.exceptions import (
    ResourceNotFoundError, ResourceInUseError, AppException
)

class AirlineService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AirlineRepository(db)

    def get_or_404(self, iata_code: str):
        obj = self.repo.get(iata_code)
        if not obj:
            raise ResourceNotFoundError(f"航司 {iata_code} 不存在")
        return obj

    def list_all(self):
        return self.repo.list_all()

    def create(self, payload: AirlineCreate):
        if self.repo.get(payload.iata_code):
            raise AppException(f"航司代码 {payload.iata_code} 已存在")
        with self.db.begin():
            return self.repo.create(**payload.model_dump())

    def update(self, iata_code: str, payload: AirlineUpdate):
        self.get_or_404(iata_code)
        with self.db.begin():
            return self.repo.update(iata_code, **payload.model_dump())

    def delete(self, iata_code: str):
        self.get_or_404(iata_code)
        try:
            with self.db.begin():
                self.repo.delete(iata_code)
        except IntegrityError:
            raise ResourceInUseError(f"航司 {iata_code} 被引用,无法删除")
```

### A.5 `router.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.deps import get_db
from app.auth.dependencies import get_current_admin
from .service import AirlineService
from .schemas import AirlineCreate, AirlineUpdate, AirlineResponse

router = APIRouter(prefix="/airlines", tags=["airline"])

@router.get("/", response_model=list[AirlineResponse])
def list_airlines(db: Session = Depends(get_db)):
    return AirlineService(db).list_all()

@router.post("/", response_model=AirlineResponse,
             dependencies=[Depends(get_current_admin)])
def create_airline(payload: AirlineCreate, db: Session = Depends(get_db)):
    return AirlineService(db).create(payload)

@router.put("/{iata_code}", response_model=AirlineResponse,
            dependencies=[Depends(get_current_admin)])
def update_airline(iata_code: str, payload: AirlineUpdate, db: Session = Depends(get_db)):
    return AirlineService(db).update(iata_code, payload)

@router.delete("/{iata_code}", status_code=204,
               dependencies=[Depends(get_current_admin)])
def delete_airline(iata_code: str, db: Session = Depends(get_db)):
    AirlineService(db).delete(iata_code)
```

### A.6 `main.py` 注册路由

```python
from fastapi import FastAPI
from app.domains.city.router       import router as city_router
from app.domains.airline.router    import router as airline_router
# ...
from app.workflows.booking.router  import router as booking_router
from app.workflows.search.router   import router as search_router
from app.auth.router               import router as auth_router

app = FastAPI(lifespan=lifespan, title="FudanAir API")

app.include_router(auth_router,    prefix="/api/auth")
app.include_router(city_router,    prefix="/api")
app.include_router(airline_router, prefix="/api")
# ...
app.include_router(booking_router, prefix="/api/booking")
app.include_router(search_router,  prefix="/api/search")
```

---

## 附录 B：项目结构速查表

新增功能时，按下表确认代码该放哪：

### B.1 任务 → 文件映射

**任务：实现一个新的基础数据 CRUD（如机型）**
1. `domains/<name>/models.py` —— 加 ORM 类
2. `domains/<name>/schemas.py` —— 加 Pydantic DTO
3. `domains/<name>/repository.py` —— 加查询方法
4. `domains/<name>/service.py` —— 加业务方法（开事务）
5. `domains/<name>/router.py` —— 加 FastAPI 端点
6. `app/main.py` —— 注册路由
7. 前端 `api/<name>.ts` —— 加对应 axios 函数
8. 前端 `views/admin/<Name>ManageView.vue` —— 加管理页面

**任务：实现一个跨领域业务流程（下单/退改/搜索）**
1. `workflows/<name>/service.py` —— 编排逻辑（开事务）
2. 调用 `domains/*/service.py` 的方法，**不直接调 repository**
3. `workflows/<name>/router.py` —— HTTP 入口
4. `workflows/<name>/schemas.py` —— 请求/响应 DTO

**任务：实现一个新的查询接口**
- 简单 CRUD（按主键 / 单表过滤）→ `domains/<name>/repository.py` 用 ORM
- 复杂联表（多表 JOIN / 聚合 / 中转搜索）→ `workflows/<name>/service.py` 用 `text()` 写原生 SQL

**任务：添加一个定时任务**
1. `jobs/<name>.py` —— 任务函数
2. `core/scheduler.py` —— 在 `start_scheduler()` 中注册

**任务：添加一个新的业务异常**
1. `core/exceptions.py` —— 加 AppException 子类
2. API.md §14 错误码表 —— 同步

**任务：添加一个新的业务常量**
- `core/constants.py` —— 集中存放，不要散落

### B.2 不该做的事

| ❌ 不该做 | ✅ 应该做 |
| --- | --- |
| `domains/order` 直接 `import domains/flight` | 在 `workflows/booking` 里同时调用两边的 service |
| 在 `repository.py` 写 `with db.begin()` | 事务在 `service.py` 开 |
| 在 `service.py` 直接 `db.execute(text(...))` 写 SQL | 简单查询走 ORM；复杂 SQL 抽到 repository 或 workflow |
| 在 `router.py` 写业务校验 | 校验放 service |
| 直接 INSERT 到 `cabin_price` 不更新 `flight_instance` | 调用 `FlightService.deduct_seat / restore_seat` |
| 直接 INSERT 到 `airport` 不写 `city_near_apt` | 调用 `AirportService.create` |
| 业务代码写魔法数字（如 `if days >= 7`） | 从 `core/constants.py` 导入 |
| 业务代码自己拼 `f"O{datetime.now()}..."` | 调用 `core/id_generator.py` 函数 |
| 业务代码 `raise HTTPException(400, ...)` | 抛 `core/exceptions.py` 中的子类 |

---

## 附录 C：提示词

```
本项目为「FudanAir 航空票务管理数据库系统」。请遵守:

1. 必须先读完 PRD.md, SCHEMA.md, ARCHITECTURE.md, API.md 四份文档,
   再开始写代码。业务规则以 PRD 为准,字段约束以 SCHEMA 为准,
   接口契约以 API 为准,目录结构与代码风格以 ARCHITECTURE 为准。

2. 跨领域逻辑必须放 workflows/, domains 之间不互相 import。
   事务边界在 service 层显式 with db.begin(), repository 不开事务。
   复杂查询用 text() 写原生 SQL, 简单 CRUD 用 ORM。

3. 任何修改 cabin_price.available_seats 必须同步 
   flight_instance.economy_left / first_left, 通过
   FlightService.deduct_seat / restore_seat 函数完成。

4. 任何修改 airport 表必须同步 city_near_apt 表的 distance=0 记录,
   通过 AirportService.create / update_city / delete 完成。

5. 业务常量从 core/constants.py 读取(退改费率/中转时间/距离上限),
   不要在代码里写魔法数字。

6. 业务编号统一调用 core/id_generator.py 的函数生成
   (gen_order_no / gen_ticket_no / gen_instance_id), 不要自行拼接。

7. 抛异常用 core/exceptions.py 中已定义的子类
   (InsufficientStockError / TicketNotRefundableError 等),
   不要新建异常类, 不要 raise HTTPException, 不要抛裸 Exception。

8. 应用层约束 AC-1 至 AC-8 必须在 service 层显式校验
   (见 ARCHITECTURE §5.8 表格)。

9. 新建领域包请参考附录 A 的 airline 模板, 保持 5 个文件分层一致。

10. 决定文件位置前查附录 B 的速查表。
```

---

## 附录 D：变更记录

| 版本 | 日期       | 修订人 | 变更说明                                                     |
| ---- | ---------- | ------ | ------------------------------------------------------------ |
| v1.0 | 2026-05-09 | 王铿轶 | 基于 PRD v1.0 与 SCHEMA v1.0 编写。技术栈：FastAPI + SQLAlchemy + Vue 3 + Element Plus + JWT + APScheduler。架构：三档分层(workflows/domains/core),领域包内部四层(router/service/repository/models)。前端美学设计。 |
| v2.0 | 2026-05-10 | 王铿轶 | 根据 PRD/SCHEMA v2.0同步：删除 admin_permission 资源级权限，统一为 role-based 单一管理员角色；新增"每日生成 3 个月后航班实例"定时任务；新增 airport-city_near_apt 双写规则；新增库存双重表达的事务同步规则；删除 Alembic 迁移工具；JWT 改为 httpOnly cookie 传递。 |
| v2.1 | 2026-05-10 | 王铿轶 | 为新 AI 上下文交接补全代码约束：新增 §3.3 数据准备与初始化（CSV 目录、init_db.py 调用链、双写约束）；新增 §3.4 业务常量统一存放（core/constants.py）；§3.1 完整化异常类清单（与 API.md §14 一一对应）和 ID 生成器代码；新增 §5.8 应用层约束 AC-1 至 AC-8 的代码强制位置；新增附录 A 完整领域包代码模板；新增附录 B 项目结构速查表；新增附录 C 提示词。 | v2.2 | 2026-05-10 | 王铿轶 | 城市临近机场逻辑更正，初始化数据会默认将distance为0视为城市拥有机场。
|

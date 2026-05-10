# FudanAir航空票务管理数据库系统 — 架构设计文档（ARCHITECTURE）

| 项目名称 | 航空票务管理数据库系统                                       |
| -------- | ------------------------------------------------------------ |
| 文档版本 | v2.0                                                         |
| 编写日期 | 2026-05-10                                                   |
| 配套文档 | PRD.md（业务需求）、SCHEMA.md（数据库设计）、API.md（接口定义） |

---

## 0. 阅读指南

本文档定义系统的**技术架构**：技术栈、目录结构、分层规范、关键工程实践。本文档不重复 PRD 的业务需求，也不重复 SCHEMA 的字段定义；遇到具体业务规则请回查 PRD.md，遇到字段约束请回查 SCHEMA.md。

文档结构：

- 第 1 节：技术栈总览
- 第 2 节：分层架构（关键 — 决定所有人写代码时把文件放哪）
- 第 3 节：后端目录结构
- 第 4 节：前端目录结构
- 第 5 节：数据库连接与事务规范
- 第 6 节：认证与权限
- 第 7 节：定时任务
- 第 8 节：错误处理与日志
- 第 9 节：前端设计原则
- 第 10 节：开发与协作规范
- 第 11 节：环境与部署

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
| 前端框架    | Vue                       | 3.4+   | 工业风票务系统主流选择                             |
| 构建工具    | Vite                      | 5.0+   | 极快的开发服务器                                   |
| UI 组件库   | Element Plus              | 2.6+   | 默认样式即工业风，密度合适                         |
| 状态管理    | Pinia                     | 2.1+   | Vue 3 官方推荐                                     |
| 路由        | Vue Router                | 4.3+   | Vue 官方                                           |
| HTTP 客户端 | Axios                     | 1.6+   | 拦截器机制完整，便于注入 JWT                       |
| 前端语言    | TypeScript                | 5.3+   | 类型安全；与后端 Pydantic 契约对齐                 |

### 1.2 关键约束

- **复杂查询手写 SQL**：航班搜索、中转推荐、统计报表必须用 `text()` 写原生 SQL；CRUD 用 ORM。这是数据库课的展示需求，也是性能需求。
- **所有写操作走事务**：哪怕是单条 INSERT，也用 `with session.begin():` 显式包裹。
- **认证用 JWT**：无状态，前后端分离适配良好。
- **前后端完全分离**：FastAPI 仅出 JSON，前端独立构建独立部署。
- **前端美学**：详见第 9 节。
- **库存双重表达的同步规则**：`cabin_price.available_seats` 与 `flight_instance.economy_left/first_left` 由 `flight.service` 封装为单一函数， `deduct_seat()` 与 `restore_seat()` 同步更新，禁止业务代码直接修改任一字段

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
│  - database / security / exceptions / scheduler              │
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
│   │   ├── exceptions.py       # AppException 及子类
│   │   ├── id_generator.py     # 订单号、票号生成器
│   │   └── scheduler.py        # APScheduler 实例
│   │
│   ├── domains/                # 业务领域包
│   │   ├── city/               # 城市、机场、临近机场
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   │
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
│       └── generate_instances.py   # 每日生成 3 个月后那天的航班实例（每天凌晨）
│
├── tests/
│   ├── conftest.py
│   ├── test_booking_concurrency.py   # ★ 防超卖测试
│   ├── test_refund_flow.py
│   ├── test_search.py
│   └── test_admin_permission.py
│
├── scripts/
│   ├── schema.sql              # 纯 DDL,复用 SCHEMA.md §9
│   ├── init_db.py              # 主初始化脚本(执行 schema.sql + 灌种子 + 创建管理员)
│   └── seed_data.py            # 种子数据(被 init_db.py 调用)
│
├── start.py                    # 后端启动脚本
├── .env.example                # 环境变量模板
├── requirements.txt            # 依赖与工具配置
├── README.md                   # 启动说明
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
- INSTANCE_GENERATION_HOUR（默认 3，凌晨 3 点生成航班实例）
- INSTANCE_AHEAD_DAYS（默认 90，提前 90 天生成实例）

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

#### `app/core/exceptions.py`

统一异常类型，配合 `main.py` 的 exception handler 转为标准 JSON 错误响应：

```python
class AppException(Exception):
    code: str
    message: str
    http_status: int = 400

class InsufficientStockError(AppException): ...   # 库存不足
class TicketNotRefundableError(AppException): ...   # 票不可退
class PermissionDeniedError(AppException): ...
class AuthenticationError(AppException): ...
```

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

`flight.service.lock_and_deduct_cabin` 提供给 `workflows/booking/` 调用，是防超卖的关键方法。具体代码模式见第 5 节。



补充：`.env`文件，大致配置：

```
# 数据库连接 - 请把 YOUR_PASSWORD 改成自己的 MySQL root 密码
DB_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/fudan_air?charset=utf8mb4

# JWT 签名密钥 - 随便填一段长字符串即可，团队内可统一
JWT_SECRET=please-change-me-to-a-random-string-at-least-32-chars
JWT_EXPIRE_MINUTES=1440

# 业务配置 - 一般不需要改
ORDER_EXPIRE_MINUTES=15
SCHEDULER_INTERVAL_SECONDS=60
INSTANCE_GENERATION_HOUR=3
INSTANCE_AHEAD_DAYS=90

# CORS 允许的前端来源
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
                raise AppException("订单状态不允许取消")
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
            raise AppException("舱位不存在")
        if cp.available_seats < count:
            raise InsufficientStockError(f"剩余 {cp.available_seats}, 申请 {count}")
        cp.available_seats -= count

        # 同步汇总库存
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
              ...
        """)
        rows = self.db.execute(sql, {"dep_city": dep_city, "arr_city": arr_city, "date": date}).mappings().all()
        return [dict(r) for r in rows]
```

**强制要求**：

- 用 `text(...)` 显式声明原生 SQL，不要字符串拼接业务参数。
- 用 `:param` 绑定参数，杜绝 SQL 注入。
- 复杂 SQL 单独抽到 `sql/` 子目录的 `.sql` 文件，便于版本管理（可选实践）。

### 5.6 隔离级别

MySQL InnoDB 默认 `REPEATABLE READ`，本项目不修改。关键事务（下单、退改）使用 `SELECT ... FOR UPDATE` 加行锁，天然防止幻读与丢失更新。

### 5.7 关键事务规范

**库存同步规则**（强制）：

- 任何修改 `cabin_price.available_seats` 的地方，必须同时修改 `flight_instance.economy_left`（经济舱）或 `first_left`（头等舱）
- 实现方式：`flight.service.deduct_seat(instance_id, cabin_class, fare_type, count)` 在事务内执行 UPDATE 两张表，业务代码统一调此函数
- 反向操作：`flight.service.restore_seat(...)` 用于退改和超时回补

**airport-city_near_apt 双写规则**（强制）：

- `airport.service.create(iata, name, city_name)`：事务内同时插入 `airport` 和 `city_near_apt(city_name, iata, 0)`
- `airport.service.update_city(iata, new_city)`：事务内更新 `airport.city_name`、删除旧 distance=0 记录、插入新 distance=0 记录
- 删除 airport 由 `city_near_apt.iata_code` 上的 `ON DELETE CASCADE` 自动处理
- 任何外部调用 `city_near_apt` 增删的入口：若 distance=0，必须先校验对应 `airport(iata).city_name == city_name`，否则抛 `IntegrityError`

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
    scheduler.add_job(
        expire_orders_job,
        trigger="interval",
        seconds=settings.SCHEDULER_INTERVAL_SECONDS,
        id="expire_orders",
        max_instances=1,         # 不允许同一任务并发执行
        coalesce=True,           # 错过的执行合并为一次
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
@scheduler.scheduled_job('cron', hour=settings.INSTANCE_GENERATION_HOUR)
def generate_instances_daily():
    """每天凌晨生成 90 天后那一天的航班实例"""
    target_date = date.today() + timedelta(days=settings.INSTANCE_AHEAD_DAYS)
    weekday = target_date.isoweekday()  # 1-7
    flights = query("SELECT flight_no FROM flight_weekday WHERE weekday = :w", w=weekday)
    for flight_no in flights:
        create_instance(flight_no, target_date)  # 含舱位定价初始化
```

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
{ "code": "INSUFFICIENT_STOCK", "message": "剩余 0,申请 2", ... }
```

### 8.2 日志规范

- 使用 Python 标准库 `logging`，配置在 `core/logging.py`。
- 关键节点必打日志：登录、下单（含订单号 + 用户 + 实例 + 数量）、支付、退改、超时取消。
- 格式：`[时间] [级别] [模块] [trace_id] 内容`。
- 不打印密码、token、银行卡号等敏感字段。

### 8.3 前端错误处理

axios 拦截器统一处理：

- HTTP 401 → 清除 token，跳登录页
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
      authStore.clear()
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

## 附录 ：变更记录

| 版本 | 日期       | 修订人 | 变更说明                                                     |
| ---- | ---------- | ------ | ------------------------------------------------------------ |
| v1.0 | 2026-05-09 | 王铿轶 | 基于 PRD v1.0 与 SCHEMA v1.0 编写。技术栈：FastAPI + SQLAlchemy + Vue 3 + Element Plus + JWT + APScheduler。架构：三档分层(workflows/domains/core),领域包内部四层(router/service/repository/models)。前端美学设计 |
| v2.0 | 2026-05-10 | 王铿轶 | 根据 PRD/SCHEMA v2.0同步：删除 admin_permission 资源级权限，统一为 role-based 单一管理员角色；新增"每日生成 3 个月后航班实例"定时任务；新增 airport-city_near_apt 双写规则；新增库存双重表达的事务同步规则；删除 Alembic 迁移工具；JWT 改为 httpOnly cookie 传递；前端 TS 改为可选 |
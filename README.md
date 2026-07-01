## 快速开始：系统安装与使用

1. **克隆仓库**

```bash
git clone https://github.com/kiangyeeo/FudanAir.git
cd FudanAir
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

3. **确保本地MySQL服务正在运行，并创建私有 `.env`**

```bash
cp .env.example .env
```

 `.env` 中需要替换自己的MySQL密码。

4. **初始化数据库**

```bash
python backend/scripts/init_db.py 
```

5. **启动后端**

```bash
cd backend
python start.py
```

6. **启动前端**

```bash
cd frontend
npm install
npm run dev
```



## 系统测试说明

1. **前端功能验收**

   ```
   前端：http://localhost:5173
   后端：http://localhost:8000
   ```

   - **用户注册与登录**
     注册测试用户，再进入 `/login` 登录。
   - **航班搜索**
     在首页输入出发城市、到达城市和日期，验证直飞、临近机场、中转方案和价格筛选结果。
   - **购票主流程**
     选择航班，填写乘机人，下单，进入支付页完成模拟支付；然后在“我的订单”和“我的机票”中查看订单状态与客票信息。
   - **退票与改签**
     对已支付客票进行退票试算、提交退票；另选可改签航班完成改签，检查原客票状态和新客票生成情况。
   - **管理员后台**
     使用初始化管理员账号登录, 验证管理概览、城市、机场、航司、机型、航班、航班实例、票价和订单查询等后台页面。

   ```
   账号：A001
   密码：admin123
   ```

2. **并发抢票测试**
   运行以下指令，测试8个并发请求同时购买1张票，最后仅有1个请求购买成功。

   ```
   python backend/scripts/demo_concurrent_booking.py
   ```

3. **后端自动化测试**
   使用 `pytest` 进行后端功能测试，覆盖注册登录、航班搜索、下单支付、退改签、用户中心、管理员权限、后台统计和基础数据约束等核心功能。

   ```bash
   cd backend
   python -m pytest tests -q
   ```

   测试文件说明：

   | 测试文件                                                     | 验证内容                             |
   | ------------------------------------------------------------ | ------------------------------------ |
   | `test_login_validation.py` , `test_register_validation.py`   | 登录注册参数校验、错误提示           |
   | `test_search.py`                                             | 直飞、中转、临近机场、价格筛选       |
   | `test_booking_flow.py`                                       | 下单、扣库存、支付、取消、库存恢复   |
   | `test_booking_concurrency.py`                                | 并发抢票、防止超卖、订单超时释放库存 |
   | `test_refund_flow.py`                                        | 退票、改签、手续费试算、异常拦截     |
   | `test_user_center.py`                                        | 个人信息、密码、常用乘机人           |
   | `test_admin_permission.py` , `test_admin_dashboard.py`       | 管理员权限、后台统计                 |
   | `test_airport_iata_update.py` , `test_airline_update.py` , `test_aircraft_type_update.py` | 基础数据修改约束                     |


# 航空票务系统 - 开发规范

## 文档位置
- 需求文档: docs/PRD.md
- 数据库设计: docs/SCHEMA.md  
- 架构设计: docs/ARCHITECTURE.md
- 接口定义: docs/API.md
- 修改任何功能前先查阅对应文档

## 分层规则
- controllers/: 参数校验 + 调用 service，不写业务逻辑
- services/: 业务逻辑，不直接写 SQL
- repositories/: 所有数据库操作，SQL 集中在此
- 禁止跨层调用

## 数据库规范
- SQL 一律使用参数化查询
- 涉及库存变更的操作必须在事务内完成
- 座位售卖必须使用 SELECT ... FOR UPDATE
- 所有表包含 created_at, updated_at 字段

## 代码风格
- 函数不超过 30 行
- 所有函数写 docstring
- 不使用魔法数字，常量定义在 constants.py
- 异常使用 exceptions/ 下的自定义异常类

## 测试
- 每个 service 方法必须有对应的单元测试
- 并发相关功能必须有并发测试
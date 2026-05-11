[English](./README.md) | 简体中文

## 快速开始

1. **克隆仓库**

```bash
git clone https://github.com/kiangyeeo/FudanAir.git
cd FudanAir
```

2. **安装依赖**

```bash
conda activate ... % Recommend using a virtual environment.
pip install -r requirements.txt
```

3. **确保本地MySQL服务正在运行，并创建私有 `.env`**

```bash
cp .env.example .env
```

 `.env` 中需要更新自己的MySQL密码。

4. **初始化数据库**

如果第一次运行，或者你更换了数据，则运行：

```bash
python scripts/init_db.py 
```

5. **启动后端**

```bash
cd backend
python start.py
```

6. **启动前端**

如果第一次使用，运行 `npm install` 。

```bash
cd frontend
npm install
npm run dev
```


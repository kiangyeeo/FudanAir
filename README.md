<div align="left">
    <img src="assets/research_simulation.png" alt=usecase1>
    <img src="assets/interaction.png" alt=usecase2>
   <a href="http://www.matrix.eigent.ai">
    <img src="assets/content_creation.png" alt=usecase3>
   </a>
    <img src="assets/prediction.png" alt=usecase4>
</div>

## Quick Start

1. **Clone the repository**

```bash
git clone https://github.com/kiangyeeo/FudanAir.git
cd FudanAir
```

2. **Install dependencies**

```bash
conda activate ... % Recommend using a virtual environment.
pip install -r requirements.txt
```

3. **Make sure your MySQL service is running and copy the example environment file**

```bash
cp .env.example .env
```

Update your own  `.env` with your MySQL-password.

4. **Initialize the database schema**

Run this command if this is your first time starting the project, or if the data has been updated.

```bash
python scripts/init_db.py 
```

5. **Start the backend**

```bash
cd backend
python start.py
```

6. **Start the frontend**

Run `npm install` the first time you set up the frontend.

```bash
cd frontend
npm install
npm run dev
```


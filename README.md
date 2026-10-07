# AgriShare Full Dataset Demo - Final

This package combines the V3 dataset mapping code with the missing project/dependency files required to run it locally.

## Backend

PowerShell:

```powershell
cd backend
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --port 8001
```

## Frontend

Open a second PowerShell:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/`.

The backend uses the MongoDB settings in `backend/.env`. Do not publish that file or commit its credentials.

## DBMS Review 2 Features

- MongoDB aggregation reports: order-status summary, top farmers by quantity sold, and produce demand.
- Query optimization: application creates indexes for frequent order, booking, produce, and farmer queries and exposes an optimization summary.
- AI-assisted search: natural-language phrases are mapped to predefined MongoDB filters/aggregation pipelines.

Suggested demo phrases:
- `cancelled orders`
- `top farmers by quantity`
- `produce demand`

The application also provides CRUD operations, search/filtering, and the full MongoDB-backed modules.

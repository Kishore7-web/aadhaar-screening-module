Write-Host "Starting DAKSH P3 Backend..." -ForegroundColor Cyan
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/setup_models.py
python scripts/generate_test_documents.py
uvicorn backend.app.main:app --reload --port 8000

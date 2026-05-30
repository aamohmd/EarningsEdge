.PHONY: install backend frontend cache clean

# Install dependencies for both backend and frontend
install:
	pip install -r requirements.txt
	cd frontend && npm install

# Start the FastAPI backend server on port 8000
backend:
	PYTHONPATH=. uvicorn api.main:app --reload --port 8000

# Start the React Vite frontend server on port 5173
frontend:
	cd frontend && npm run dev

# Pre-populate the cache with demo tickers
cache:
	PYTHONPATH=. python api/cache.py

# Clean up build artifacts and cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf frontend/node_modules
	rm -rf frontend/dist

git init
git remote add origin https://github.com/aseesmakkar45/build-with-bharat.git
git checkout -b main

# 1. Initial Docs
git add docs/ .gitignore
git commit -m "Initial commit: Add project documentation and architecture specs"

# 2. Core Backend Setup
git add backend/main.py backend/requirements.txt
git commit -m "feat: Setup FastAPI backend core and requirements"

# 3. AI Services
git add backend/services/ backend/copilot.py
git commit -m "feat: Implement AI copilot and forecasting services"

# 4. Hardware Simulation
git add backend/simulator.py backend/serial_bridge.py
git commit -m "feat: Add hardware simulator and serial communication bridge"

# 5. ML Pipeline
git add backend/train_models.py backend/get_papers.py backend/evaluate.py backend/optimizer.py
git commit -m "feat: Integrate ML training pipeline and energy optimization logic"

# 6. Remaining Backend
git add backend/
git commit -m "chore: Add remaining backend configuration and utilities"

# 7. Frontend Config
git add frontend/package.json frontend/vite.config.js frontend/postcss.config.js frontend/tailwind.config.js frontend/index.html
git commit -m "chore: Initialize Vite React frontend with Tailwind CSS config"

# 8. Global Styles
git add frontend/src/main.jsx frontend/src/index.css frontend/src/assets/
git commit -m "style: Setup global styles and frontend entry points"

# 9. Main UI
git add frontend/src/App.jsx
git commit -m "feat: Build main dashboard UI with animated energy flow and analytics"

# 10. Tests and Final Files
git add .
git commit -m "test: Add unit tests and finalize remaining workspace files"

git push -u origin main --force

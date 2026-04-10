# Stock Tracker Terminal

A premium, full-stack trading dashboard simulating a professional financial terminal. Built specifically to deliver high-performance, real-time market data with a sleek, dark-mode aesthetic. 

Features interactive candlestick charts, a simulated paper trading environment, live S&P 500 heatmaps, and AI-driven news sentiment analysis.

---

## ✨ Features

- **Live Market Data:** Real-time price updates streamed directly via WebSockets.
- **Interactive Charting:** High-performance candlestick charts powered by TradingView's `lightweight-charts`.
- **Paper Trading Simulator:** A sophisticated, stateful multi-step order flow allowing you to test trading strategies with real market prices. Tracks detailed unrealized/realized P&L.
- **S&P 500 Heatmap:** A visual overview of market performance, dynamically sizing blocks by market cap and formatting colors by daily price change.
- **Sentiment Analysis Engine:** Ingests market news from Finnhub and automatically runs VADER sentiment analysis to highlight bullish ✨ or bearish 🩸 momentum.
- **Alerts System:** (In Development) Set price targets and trigger notifications when thresholds are crossed.

## 🛠 Tech Stack

**Frontend:**
- [React 19](https://react.dev/) & [Vite](https://vitejs.dev/)
- [TypeScript](https://www.typescriptlang.org/)
- [Tailwind CSS](https://tailwindcss.com/) (Custom UI/UX without external component libraries)
- [TanStack Query v5](https://tanstack.com/query/latest) (Data fetching & caching)
- [Zustand](https://zustand-demo.pmnd.rs/) (Global state & WebSocket tracking)

**Backend:**
- [FastAPI](https://fastapi.tiangolo.com/) (High-performance async Python framework)
- [SQLAlchemy](https://www.sqlalchemy.org/) & SQLite (Relational database management)
- [Finnhub API](https://finnhub.io/) (Provider for REST quotes, company profiles, and WebSocket price streams)
- [VADER Sentiment](https://github.com/cjhutto/vaderSentiment) (Natural Language Processing for news headlines)

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- A free [Finnhub API Key](https://finnhub.io/register)

### 1. Clone the repository
```bash
git clone https://github.com/Nyxie12/stock-tracker.git
cd stock-tracker
```

### 2. Backend Setup
Navigate into the backend directory and set up your Python environment:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
```

Create an environment file using the provided example:
```bash
cp .env.example .env
```
Open `.env` and fill in your `FINNHUB_API_KEY`. 

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
Open a new terminal window, navigate to the frontend directory, and install dependencies:
```bash
cd frontend
npm install
```

Start the Vite development server:
```bash
npm run dev
```

The application will now be running on `http://localhost:5174/`.

---

## 🎨 Design Philosophy
This project purposefully avoids generic UI libraries (like MUI or Shadcn) to strictly enforce a bespoke "Bloomberg Terminal" aesthetic. It utilizes strict color theory, custom scrollbars, layout animations, and typography (`Inter` for UI, `JetBrains Mono` for data) to present dense financial data legibly and beautifully.


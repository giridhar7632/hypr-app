## Market Sentiment Dashboard

This is a market sentiment dashboard that uses real-time data from the market to provide insights into the current state of the market. The dashboard is built using React and provides a user-friendly interface for users to view the data.

## Tech stack

- frontend: React
- backend: Python, FastAPI

## Data source

- [Yahoo Finance](https://finance.yahoo.com/)

## Setup

backend:

```bash
python -m venv _venv
source _venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

frontend:

```bash
npm install
npm start
```


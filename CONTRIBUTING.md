# Contributing to Argus

Thanks for considering a contribution! Argus is early-stage, so almost any improvement helps.

## Ways to help

| Type                | Examples                                                            |
| ------------------- | ------------------------------------------------------------------- |
| 🐛 Bug reports      | UI glitches, indicator math errors, broken adapters                 |
| 🧠 New agents       | Add a new analyst persona (e.g. quantitative, options, dividend)    |
| 📡 New data sources | Wire up Tushare Pro, Futu, IBKR, Longbridge, etc.                   |
| 🌐 i18n             | Translate UI strings into another language                          |
| 📊 Indicators       | Add an indicator to `backend/argus/analysis/indicators.py`          |
| 🎨 UI polish        | Themes, animations, accessibility                                   |

## Development setup

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest

# Frontend
cd frontend
npm install
npm run dev
```

## Pull request checklist

- [ ] Code passes `ruff check .` and `pytest` on the backend
- [ ] Code passes `npm run build` on the frontend (no TS errors)
- [ ] New features include at least one test or screenshot
- [ ] No hard-coded API keys, no committed `.env`
- [ ] README / docs updated if behaviour changed

## Style

- Backend: Python 3.11, type-hinted, ruff-formatted
- Frontend: TypeScript strict mode, function components only
- Commits: imperative present tense (`Add`, `Fix`, `Refactor`)

## Code of conduct

Be kind. Assume good faith. No personal attacks, no harassment.

---

Discussions and design proposals → open a GitHub Discussion. Bugs → GitHub Issues.

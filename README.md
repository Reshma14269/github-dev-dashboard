# 📊 GitHub Developer Activity Dashboard

A Streamlit app that turns any public GitHub profile into a live activity dashboard —
language breakdown, top repos, and weekly commit trends, pulled straight from the
GitHub REST API and cleaned with pandas.

**[Live demo →](https://app-dev-dashboard-6cyzpghvyzvdatbx9e2jjd.streamlit.app/)**



## Why I built this

Most beginner dashboards use a generic dataset (weather, Titanic, crypto prices).
I wanted something that (a) shows a real end-to-end API → clean → visualize pipeline,
and (b) is useful and personal — anyone can point it at their own GitHub username
and see their own activity summarized.

## Features

- 🔍 **Any public GitHub username** — no login required
- 🥧 **Language breakdown** across original (non-forked) repos
- ⭐ **Top repos by stars**, sorted and visualized
- 📈 **Weekly commit activity** aggregated across the user's most recently active repos
- 📋 **Raw data table** for anyone who wants to dig into the numbers themselves

## Architecture

```
GitHub REST API  →  github_data.py (fetch + clean with pandas)  →  app.py (Streamlit UI + Plotly charts)
```

- `github_data.py` — all API calls and data-cleaning logic, kept separate from the UI
  so it's testable/reusable on its own
- `app.py` — Streamlit interface: takes a username, calls the data layer, renders charts

## Tech stack

- **Python** + **Streamlit** for the app/UI
- **Requests** for GitHub REST API calls
- **Pandas** for cleaning and shaping the data
- **Plotly** for interactive charts

## Setup

```bash
git clone <your-repo-url>
cd github-dev-dashboard
pip install -r requirements.txt

# optional but recommended — avoids the 60 req/hour rate limit
cp .env.example .env
# then add your GITHUB_TOKEN to .env

streamlit run app.py
```

## What I'd improve next

- Cache API responses (Streamlit's `@st.cache_data`) to avoid re-fetching on every rerun
- Add a contribution heatmap visual (GitHub's own calendar-style graph, rebuilt)
- Compare two usernames side by side
- Handle GitHub's rate-limit response with a clearer in-app message instead of a generic error

## License

MIT

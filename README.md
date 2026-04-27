# Movie Recommender Streamlit App

Simple movie recommendation web app built with Streamlit.

## Setup

1. Create and activate a virtual environment (recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the app

```bash
streamlit run app.py
```

Then open the URL shown in the terminal (usually `http://localhost:8501`).

## Project structure

- `app.py` – main Streamlit application.
- `data/` – raw data files such as `movies.csv` and `ratings.csv`.
- `models/` – recommendation logic (content-based / collaborative).
- `services/` – data loading and related helpers.
- `config/` – configuration such as paths and model parameters.
- `pages/` – additional Streamlit pages.
- `assets/` – images and custom styles.
- `tests/` – basic tests for recommendation logic.


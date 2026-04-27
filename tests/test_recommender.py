import pandas as pd

from models.recommender import get_recommendations


def test_get_recommendations_returns_dataframe():
    data = {
        "movieId": [1, 2, 3],
        "title": ["A", "B", "C"],
        "genres": ["Action", "Action|Comedy", "Drama"],
        "description": ["Action movie", "Action and Comedy movie", "Drama movie"],
    }
    df = pd.DataFrame(data)

    recs = get_recommendations("A", df, top_k=2)

    assert isinstance(recs, pd.DataFrame)
    assert not recs.empty
    assert set(recs.columns) == {"title", "genres"}


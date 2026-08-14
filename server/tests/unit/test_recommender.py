from app.intelligence.recommender.engine import Candidate, rank

def test_rank_orders_similarity():
    rows=rank([Candidate("a",.2),Candidate("b",.9)])
    assert rows[0][0].track_id == "b"

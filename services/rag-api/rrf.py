from collections import defaultdict
def reciprocal_rank_fusion(*ranked_lists, k=60):
    scores = defaultdict(float)
    for rl in ranked_lists:
        for rank, item in enumerate(rl[:k], start=1):
            scores[item['id']] += 1.0/(60 + rank)
    return scores

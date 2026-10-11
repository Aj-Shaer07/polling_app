from typing import List, Dict, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import MiniBatchKMeans


def cluster_explanations(explanations: List[str], max_clusters: int = 4) -> List[Dict[str, Any]]:
    """
    Groups semantically similar explanations using TF-IDF and KMeans clustering.
    Extracts representative sample explanations for each cluster.
    """
    cleaned = [e.strip() for e in explanations if e and len(e.strip()) > 3]
    if not cleaned:
        return []

    # If too few explanations, return as a single cluster
    if len(cleaned) <= 2:
        return [{
            "cluster_id": 0,
            "count": len(cleaned),
            "sample_quotes": cleaned[:3],
            "keywords": ["general"],
        }]

    n_clusters = min(max_clusters, max(2, len(cleaned) // 3))

    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=100)
        tfidf_matrix = vectorizer.fit_transform(cleaned)

        kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, batch_size=32, n_init="auto")
        labels = kmeans.fit_predict(tfidf_matrix)

        feature_names = vectorizer.get_feature_names_out()
        clusters_data: List[Dict[str, Any]] = []

        for cid in range(n_clusters):
            indices = np.where(labels == cid)[0]
            if len(indices) == 0:
                continue

            cluster_texts = [cleaned[i] for i in indices]

            # Top keywords in cluster center
            if len(feature_names) > 0:
                center = kmeans.cluster_centers_[cid]
                top_keyword_idx = center.argsort()[::-1][:4]
                keywords = [feature_names[idx] for idx in top_keyword_idx if center[idx] > 0]
            else:
                keywords = []

            # Representative quotes: pick shortest / most central
            sample_quotes = sorted(cluster_texts, key=len)[:3]

            clusters_data.append({
                "cluster_id": cid,
                "count": len(cluster_texts),
                "sample_quotes": sample_quotes,
                "keywords": keywords,
            })

        return clusters_data
    except Exception:
        # Fallback to simple bucketing
        return [{
            "cluster_id": 0,
            "count": len(cleaned),
            "sample_quotes": cleaned[:3],
            "keywords": ["student responses"],
        }]

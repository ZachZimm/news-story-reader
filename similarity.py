# similarity.py
# KNN similarity search module for story embeddings

import numpy as np

def calculate_cosine_similarity(emb1, emb2):
    """Calculate cosine similarity between two embedding vectors.
    
    Args:
        emb1: First embedding vector (list of floats)
        emb2: Second embedding vector (list of floats)
        
    Returns:
        float: Cosine similarity score between -1 and 1, or None if invalid
    """
    if not emb1 or not emb2:
        return None
    
    # Convert to numpy arrays for vectorized operations
    e1 = np.array(emb1, dtype=np.float32)
    e2 = np.array(emb2, dtype=np.float32)
    
    # Calculate cosine similarity using vectorized operations
    dot_product = np.dot(e1, e2)
    norm_emb1 = np.linalg.norm(e1)
    norm_emb2 = np.linalg.norm(e2)
    
    if norm_emb1 > 0 and norm_emb2 > 0:
        return float(dot_product / (norm_emb1 * norm_emb2))
    else:
        return None


def find_k_most_similar(query_embedding, candidate_embeddings, candidate_ids, k=5, exclude_query_id=None):
    """Find the k most similar stories to a query story using cosine similarity.
    
    Args:
        query_embedding: The embedding vector for the query story (list of floats)
        candidate_embeddings: Dictionary mapping story_id to embedding: {story_id: [float, ...], ...}
        candidate_ids: List of story IDs to search through (only these will be considered)
        k: Number of most similar stories to return
        exclude_query_id: Story ID to exclude from results (the query story itself)
        
    Returns:
        List of tuples: [(story_id, similarity_score), ...] sorted by similarity (descending)
    """
    if not query_embedding:
        return []
    
    similarity_scores = []
    
    for story_id in candidate_ids:
        # Skip the query story itself
        if exclude_query_id is not None and story_id == exclude_query_id:
            continue
        
        # Get embedding for this candidate
        candidate_emb = candidate_embeddings.get(story_id)
        if not candidate_emb:
            continue
        
        # Calculate similarity
        similarity = calculate_cosine_similarity(query_embedding, candidate_emb)
        if similarity is not None:
            similarity_scores.append((story_id, similarity))
    
    # Sort by similarity (descending) and take top k
    similarity_scores.sort(key=lambda x: x[1], reverse=True)
    return similarity_scores[:k]


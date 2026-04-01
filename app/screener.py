"""
screener.py — ML resume scoring using sentence-transformers.

Uses cosine similarity between embeddings of the job description
and resume text. No GPU required, runs on t2.micro Free Tier.
Model is downloaded once and cached inside the Docker image.
"""

from sentence_transformers import SentenceTransformer, util

# Load model once at import time (cached after first download)
_model = None

def warmup_model():
    """Load the model at startup so the first request isn't slow."""
    global _model
    print("Loading ML model...", flush=True)
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    print("ML model ready.", flush=True)


def score_resume(job_description: str, resume: str) -> dict:
    """
    Compare job_description and resume text.
    Returns a dict with score (0-100), match_level, and reasoning.
    """
    jd_embedding     = _model.encode(job_description, convert_to_tensor=True)
    resume_embedding = _model.encode(resume, convert_to_tensor=True)

    # Cosine similarity returns a value between -1 and 1
    similarity = util.cos_sim(jd_embedding, resume_embedding).item()

    # Convert to 0-100 scale
    score = round(max(0, min(100, similarity * 100)))

    # Classify match level
    if score >= 75:
        match_level = "strong"
        reasoning = (
            f"The resume closely matches the job description with a {score}% similarity score. "
            "The candidate's skills and experience align well with the role requirements."
        )
    elif score >= 50:
        match_level = "moderate"
        reasoning = (
            f"The resume partially matches the job description with a {score}% similarity score. "
            "Some relevant skills are present but there are gaps in key areas."
        )
    else:
        match_level = "weak"
        reasoning = (
            f"The resume shows low alignment with the job description at {score}% similarity. "
            "The candidate's profile does not closely match the role requirements."
        )

    return {
        "score":       score,
        "match_level": match_level,
        "reasoning":   reasoning,
    }

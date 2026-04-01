from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from prometheus_flask_exporter import PrometheusMetrics
from screener import score_resume, warmup_model
import os
import datetime

app = Flask(__name__)

# DB config — from env vars (K8s ConfigMap later, defaults for local dev)
DB_HOST = os.environ.get("DB_HOST", "mysql")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_NAME = os.environ.get("DB_NAME", "screenerdb")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASS = os.environ.get("DB_PASS", "password")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
metrics = PrometheusMetrics(app)
# Create tables and warm up ML model at startup
import time

# Wait for MySQL and create tables
def init_db():
    retries = 10
    while retries:
        try:
            with app.app_context():
                db.create_all()
            print("Database tables ready.", flush=True)
            return
        except Exception as e:
            print(f"DB not ready, retrying... ({e})", flush=True)
            retries -= 1
            time.sleep(3)
    raise RuntimeError("Could not connect to database after retries")

init_db()
warmup_model()


# Database model
class ScreeningResult(db.Model):
    __tablename__ = "screening_results"
    id            = db.Column(db.Integer, primary_key=True)
    job_title     = db.Column(db.String(200), nullable=True)
    score         = db.Column(db.Integer, nullable=False)
    match_level   = db.Column(db.String(20), nullable=False)   # strong / moderate / weak
    reasoning     = db.Column(db.Text, nullable=True)
    timestamp     = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id":          self.id,
            "job_title":   self.job_title,
            "score":       self.score,
            "match_level": self.match_level,
            "reasoning":   self.reasoning,
            "timestamp":   self.timestamp.isoformat(),
        }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """Kubernetes liveness/readiness probe."""
    return jsonify({"status": "healthy", "service": "resume-screener"}), 200


@app.route("/screen", methods=["POST"])
def screen():
    """
    Score a resume against a job description.

    Request body (JSON):
        job_description  str  required
        resume           str  required
        job_title        str  optional
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    jd     = data.get("job_description", "").strip()
    resume = data.get("resume", "").strip()

    if not jd or not resume:
        return jsonify({"error": "Both job_description and resume are required"}), 400

    # Run the ML screener
    result = score_resume(jd, resume)

    # Persist to MySQL
    record = ScreeningResult(
        job_title   = data.get("job_title", "Untitled"),
        score       = result["score"],
        match_level = result["match_level"],
        reasoning   = result["reasoning"],
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "score":       result["score"],
        "match_level": result["match_level"],
        "reasoning":   result["reasoning"],
        "stored_id":   record.id,
    }), 200


@app.route("/results", methods=["GET"])
def results():
    """Return the last 100 screening results."""
    rows = (
        ScreeningResult.query
        .order_by(ScreeningResult.timestamp.desc())
        .limit(100)
        .all()
    )
    return jsonify({"count": len(rows), "results": [r.to_dict() for r in rows]}), 200


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=False)

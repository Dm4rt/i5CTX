from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from CTFd.models import Challenges, Fails, Flags, Solves, db
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_user

global_submit = Blueprint(
    "global_submit",
    __name__,
    template_folder="templates",
    static_folder="assets",
)


def normalize_flag(value):
    return (value or "").strip()


@global_submit.route("/api/v1/global-submit", methods=["POST"])
@authed_only
def submit_global_flag():
    data = request.get_json(silent=True) or {}
    submission = normalize_flag(data.get("submission"))

    if not submission:
        return jsonify({"success": False, "message": "No flag provided"}), 400

    user = get_current_user()

    matched_flag = None
    for flag in Flags.query.all():
        try:
            if flag.compare(submission):
                matched_flag = flag
                break
        except Exception:
            continue

    if matched_flag is None:
        fail = Fails(
            user_id=user.id,
            provided=submission,
            ip=request.remote_addr,
            date=datetime.utcnow(),
        )
        db.session.add(fail)
        db.session.commit()

        return jsonify({"success": False, "message": "Incorrect flag"}), 200

    challenge = Challenges.query.get(matched_flag.challenge_id)
    if challenge is None:
        return jsonify({"success": False, "message": "Challenge not found"}), 404

    existing = Solves.query.filter_by(
        user_id=user.id,
        challenge_id=challenge.id,
    ).first()

    if existing:
        return jsonify({
            "success": True,
            "status": "already_solved",
            "challenge": challenge.name,
        }), 200

    solve = Solves(
        user_id=user.id,
        challenge_id=challenge.id,
        ip=request.remote_addr,
        provided=submission,
        date=datetime.utcnow(),
    )
    db.session.add(solve)
    db.session.commit()

    return jsonify({
        "success": True,
        "status": "correct",
        "challenge": challenge.name,
    }), 200


@global_submit.route("/global-submit", methods=["GET"])
def global_submit_page():
    return render_template("global_submit.html")


def load(app):
    app.register_blueprint(global_submit)
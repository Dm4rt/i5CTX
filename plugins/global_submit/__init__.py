from flask import Blueprint, jsonify, render_template, request, current_app
from CTFd.models import Challenges, Flags, Solves
from CTFd.plugins.challenges import get_chal_class
from CTFd.plugins.flags import get_flag_class
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_team, get_current_user
from CTFd.utils.modes import get_model
from CTFd.cache import clear_challenges, clear_standings

global_submit = Blueprint(
    "global_submit",
    __name__,
    template_folder="templates",
    static_folder="assets",
)


def normalize_flag(value):
    return (value or "").strip()


def parse_attempt_response(response):
    """
    Normalize various CTFd challenge attempt response formats.
    """
    if isinstance(response, tuple):
        status = response[0] if len(response) > 0 else None
        message = response[1] if len(response) > 1 else ""
        return status, message

    if isinstance(response, dict):
        data = response.get("data", {})
        status = data.get("status", response.get("status"))
        message = data.get("message", response.get("message", ""))
        return status, message

    status = getattr(response, "status", None)
    message = getattr(response, "message", "")
    return status, message


class RequestShim:
    def __init__(self, original_request, submission_value, challenge_id):
        self.remote_addr = original_request.remote_addr
        self.access_route = original_request.access_route
        self.headers = original_request.headers
        self.method = "POST"
        self.path = original_request.path
        self.args = original_request.args
        self.cookies = original_request.cookies
        self.form = {
            "submission": submission_value,
            "challenge_id": str(challenge_id),
        }
        self._json = {
            "submission": submission_value,
            "challenge_id": challenge_id,
        }
        self.is_json = True

    def get_json(self, *args, **kwargs):
        return self._json


@global_submit.route("/api/v1/global-submit", methods=["POST"])
@authed_only
def submit_global_flag():
    data = request.get_json(silent=True) or {}
    submission = normalize_flag(data.get("submission"))

    if not submission:
        return jsonify({
            "success": False,
            "data": {
                "status": "incorrect",
                "message": "No flag provided",
            },
        }), 400

    user = get_current_user()
    team = get_current_team()
    model = get_model()

    if model.__name__ == "Teams" and team is None:
        return jsonify({
            "success": False,
            "data": {
                "status": "authentication_required",
                "message": "You must be on a team to submit flags.",
            },
        }), 403

    matched_flag = None

    try:
        candidate_flags = Flags.query.filter(Flags.challenge_id.isnot(None))
        for flag in candidate_flags:
            try:
                flag_class = get_flag_class(flag.type)
                if flag_class and flag_class.compare(flag, submission):
                    matched_flag = flag
                    break
            except Exception:
                current_app.logger.exception(
                    "[global_submit] flag compare failed for flag_id=%s",
                    getattr(flag, "id", "unknown"),
                )
                continue
    except Exception:
        current_app.logger.exception("[global_submit] flag lookup failed")
        return jsonify({
            "success": False,
            "message": "Flag lookup failed",
        }), 500

    if matched_flag is None:
        return jsonify({
            "success": True,
            "data": {
                "status": "incorrect",
                "message": "Incorrect flag",
            },
        }), 200

    challenge = Challenges.query.filter_by(id=matched_flag.challenge_id).first()
    if challenge is None:
        return jsonify({
            "success": False,
            "message": "Challenge not found",
        }), 404

    challenge_state = getattr(challenge, "state", None)
    if challenge_state == "hidden":
        return jsonify({
            "success": False,
            "message": "Challenge not found",
        }), 404

    if challenge_state == "locked":
        return jsonify({
            "success": True,
            "data": {
                "status": "incorrect",
                "message": "Challenge is locked",
            },
        }), 403

    if model.__name__ == "Teams":
        existing = Solves.query.filter_by(team_id=team.id, challenge_id=challenge.id).first()
    else:
        existing = Solves.query.filter_by(user_id=user.id, challenge_id=challenge.id).first()

    if existing:
        return jsonify({
            "success": True,
            "data": {
                "status": "already_solved",
                "message": "Already solved",
                "challenge": challenge.name,
                "challenge_id": challenge.id,
            },
        }), 200

    chal_class = get_chal_class(challenge.type)
    if not chal_class:
        return jsonify({
            "success": False,
            "message": f"Unsupported challenge type: {challenge.type}",
        }), 500

    shim_request = RequestShim(request, submission, challenge.id)

    try:
        response = chal_class.attempt(challenge, shim_request)
        status, message = parse_attempt_response(response)
    except Exception:
        current_app.logger.exception(
            "[global_submit] challenge attempt failed for challenge_id=%s",
            challenge.id,
        )
        return jsonify({
            "success": False,
            "message": "Challenge attempt failed",
        }), 500

    if status == "correct" or status is True:
        try:
            chal_class.solve(
                user=user,
                team=team,
                challenge=challenge,
                request=shim_request,
            )
            clear_standings()
            clear_challenges()

            return jsonify({
                "success": True,
                "data": {
                    "status": "correct",
                    "message": message or "Correct",
                    "challenge": challenge.name,
                    "challenge_id": challenge.id,
                },
            }), 200
        except Exception:
            current_app.logger.exception(
                "[global_submit] solve failed for challenge_id=%s",
                challenge.id,
            )
            return jsonify({
                "success": False,
                "message": "Solve failed",
            }), 500

    if status == "partial":
        try:
            chal_class.partial(
                user=user,
                team=team,
                challenge=challenge,
                request=shim_request,
            )
            clear_standings()
            clear_challenges()
        except Exception:
            current_app.logger.exception(
                "[global_submit] partial handler failed for challenge_id=%s",
                challenge.id,
            )
            return jsonify({
                "success": False,
                "message": "Partial solve failed",
            }), 500

        return jsonify({
            "success": True,
            "data": {
                "status": "partial",
                "message": message or "Partial",
                "challenge": challenge.name,
                "challenge_id": challenge.id,
            },
        }), 200

    try:
        chal_class.fail(
            user=user,
            team=team,
            challenge=challenge,
            request=shim_request,
        )
        clear_standings()
        clear_challenges()
    except Exception:
        current_app.logger.exception(
            "[global_submit] fail handler failed for challenge_id=%s",
            challenge.id,
        )

    return jsonify({
        "success": True,
        "data": {
            "status": "incorrect",
            "message": message or "Incorrect flag",
        },
    }), 200


@global_submit.route("/global-submit", methods=["GET"])
@authed_only
def global_submit_page():
    return render_template("global_submit.html")


def load(app):
    app.register_blueprint(global_submit)
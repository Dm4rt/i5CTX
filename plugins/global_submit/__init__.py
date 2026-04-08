from flask import Blueprint, jsonify, render_template, request
from CTFd.models import Challenges, Flags
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


@global_submit.route("/api/v1/global-submit", methods=["POST"])
@authed_only
def submit_global_flag():
    data = request.get_json(silent=True) or {}
    submission = normalize_flag(data.get("submission"))

    if not submission:
        return jsonify({
            "success": True,
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
            "success": True,
            "data": {
                "status": "authentication_required",
                "message": "You must be on a team to submit flags.",
            },
        }), 403

    matched_flag = None

    for flag in Flags.query.all():
        try:
            flag_class = get_flag_class(flag.type)
            if flag_class and flag_class.compare(flag, submission):
                matched_flag = flag
                break
        except Exception as e:
            print(
                f"[global_submit] flag compare failed for flag "
                f"{getattr(flag, 'id', 'unknown')}: {e}"
            )
            continue

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

    if getattr(challenge, "state", None) == "hidden":
        return jsonify({
            "success": False,
            "message": "Challenge not found",
        }), 404

    if getattr(challenge, "state", None) == "locked":
        return jsonify({
            "success": True,
            "data": {
                "status": "incorrect",
                "message": "Challenge is locked",
            },
        }), 403

    chal_class = get_chal_class(challenge.type)

    class RequestShim:
        def __init__(self, original_request, submission_value, challenge_id):
            self.remote_addr = original_request.remote_addr
            self.headers = original_request.headers
            self.method = "POST"
            self.is_json = True
            self._json = {
                "submission": submission_value,
                "challenge_id": challenge_id,
            }
            self.form = self._json

        def get_json(self, *args, **kwargs):
            return self._json

    shim_request = RequestShim(request, submission, challenge.id)

    try:
        response = chal_class.attempt(challenge, shim_request)
    except Exception as e:
        print(f"[global_submit] challenge attempt failed for challenge {challenge.id}: {e}")
        return jsonify({
            "success": False,
            "message": "Challenge processing failed",
        }), 500

    if isinstance(response, tuple):
        status = response[0]
        message = response[1] if len(response) > 1 else ""
    else:
        status = getattr(response, "status", None)
        message = getattr(response, "message", "")

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

        except Exception as e:
            print(f"[global_submit] solve failed or already solved for challenge {challenge.id}: {e}")
            return jsonify({
                "success": True,
                "data": {
                    "status": "already_solved",
                    "message": message or "Already solved",
                    "challenge": challenge.name,
                    "challenge_id": challenge.id,
                },
            }), 200

    elif status == "partial":
        try:
            chal_class.partial(
                user=user,
                team=team,
                challenge=challenge,
                request=shim_request,
            )
            clear_standings()
            clear_challenges()
        except Exception as e:
            print(f"[global_submit] partial handler failed for challenge {challenge.id}: {e}")

        return jsonify({
            "success": True,
            "data": {
                "status": "partial",
                "message": message or "Partial",
                "challenge": challenge.name,
                "challenge_id": challenge.id,
            },
        }), 200

    else:
        try:
            chal_class.fail(
                user=user,
                team=team,
                challenge=challenge,
                request=shim_request,
            )
            clear_standings()
            clear_challenges()
        except Exception as e:
            print(f"[global_submit] fail handler failed for challenge {challenge.id}: {e}")

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
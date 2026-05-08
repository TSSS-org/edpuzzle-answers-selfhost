# Copyright (C) 2026 ading2210
# see README.md for more information

from flask import Flask, redirect, request, Response, render_template, jsonify
from flask_compress import Compress
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.serving import is_running_from_reloader
from curl_cffi import requests
from playwright.sync_api import sync_playwright

from modules import exceptions, utils, captions, ai
import threading, time, json, os
import pathlib

# ===== setup flask =====
print("Reading config...")
base_dir = pathlib.Path(__file__).resolve().parent
config_path = base_dir / "config" / "config.json"

config = json.loads(config_path.read_text())

# read config
utils.include_traceback = config["include_traceback"]
ai.config = config

# handle compression and rate limits
print("Preparing flask instance...")
app = Flask(__name__, static_folder="../dist", static_url_path="/")
limiter = Limiter(
  get_remote_address,
  app=app,
  storage_uri=config["limiter_storage_uri"],
  strategy="moving-window",
)

if config["gzip_responses"]:
  print("Response compression enabled.")
  app.config["COMPRESS_ALGORITHM"] = "gzip"
  app.config["COMPRESS_LEVEL"] = 9
  Compress(app)
else:
  print("Response compression disabled.")
CORS(app)

# flask proxy fix
if config["behind_proxy"]:
  app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# ===== token management =====

# lock so only one playwright login can run at a time
_token_lock = threading.Lock()

def save_token(token):
  """Save a token back to config.json so it persists across restarts."""
  config["teacher_token"] = token
  config_path.write_text(json.dumps(config, indent=2))

def get_teacher_token():
  """
  Open a real visible Chromium window so the user can log into their teacher
  account manually. Once the login cookie appears, grab it and save it.
  This bypasses the captcha entirely because a real human is doing the login.
  """
  with _token_lock:
    print("\n" + "="*50)
    print("  TEACHER LOGIN REQUIRED")
    print("="*50)
    print("A browser window will open. Log into your Edpuzzle")
    print("teacher account. The window will close automatically")
    print("once you're signed in.")
    print("="*50 + "\n")

    with sync_playwright() as p:
      browser = p.chromium.launch(headless=False, args=["--no-sandbox"])
      context = browser.new_context()
      page = context.new_page()
      page.goto("https://edpuzzle.com/login")

      # Wait until we navigate away from /login — means login succeeded.
      # We can't use document.cookie because the token cookie is HttpOnly
      # and invisible to JavaScript, so we watch the URL instead.
      try:
        page.wait_for_url(
          lambda url: "edpuzzle.com/login" not in url,
          timeout=180_000
        )
      except Exception:
        browser.close()
        raise RuntimeError("Login timed out after 3 minutes. Please restart and try again.")

      # Small wait to let Edpuzzle finish setting all cookies after redirect
      page.wait_for_timeout(2000)

      cookies = context.cookies()
      token = next((c["value"] for c in cookies if c["name"] == "token"), None)
      browser.close()

    if not token:
      raise RuntimeError("Could not find token cookie after login. Please try again.")

    print("Teacher token captured successfully.")
    save_token(token)
    return token

def get_current_token():
  """
  Return the stored teacher token from config.
  If it's missing or empty, trigger the Playwright login flow.
  """
  token = config.get("teacher_token", "").strip()
  if not token or token == "YOUR_TOKEN_HERE":
    token = get_teacher_token()
  return token

def create_session():
  session = requests.Session(impersonate="chrome")
  session.headers.update({
    "Content-Type": "application/json",
    "Referer": "https://edpuzzle.com/",
    "Accept": "application/json, text/plain, */*",
    "X-Edpuzzle-Preferred-Language": "en",
    "X-Edpuzzle-Referrer": "https://edpuzzle.com/"
  })
  return session

def verify_token(token):
  """Check if the stored token is still valid against Edpuzzle's API."""
  session = create_session()
  res = session.get("https://edpuzzle.com/api/v3/users/me", cookies={"token": token})
  return res.ok

def ensure_valid_token():
  """
  Return a working token, re-authenticating via Playwright if the current
  one has expired (401) or been rejected (403).
  """
  token = get_current_token()
  if not verify_token(token):
    print("Stored token is invalid or expired. Re-authenticating...")
    token = get_teacher_token()
  return token

# ===== utility functions =====

# handle 429
@app.errorhandler(429)
def handle_rate_limit(e):
  return utils.handle_exception(e, status_code=429)

# ===== api routes =====
@app.route("/api/captions/<id>")
@app.route("/api/captions/<id>/<language>")
@limiter.limit(config["rate_limit"]["captions"])
@utils.handle_exception
def get_captions(id, language="en"):
  timestamp = request.args.get("timestamp")
  count = request.args.get("count")
  return captions.get_captions(id)

@app.route("/api/models", methods=["GET"])
@utils.handle_exception
def get_models():
  return jsonify(ai.get_available_models())

@app.route("/api/generate", methods=["POST"])
@limiter.limit(config["rate_limit"]["generate"])
@utils.handle_exception
def generate():
  data = request.json

  if not "prompt" in data:
    raise exceptions.BadRequestError("Missing required parameter 'prompt'.")

  for arg in data:
    if not arg in ["prompt", "model"]:
      raise exceptions.BadRequestError(f"Unknown parameter '{arg}'.")

  if len(data["prompt"]) > ai.max_length:
    raise exceptions.BadRequestError("Prompt too long.")

  if not "model" in data:
    raise exceptions.BadRequestError("Missing required parameter 'model'.")

  def generator():
    try:
      for chunk in ai.generate(data):
        if chunk == data["prompt"]:
          continue
        yield json.dumps(chunk) + "\n"
    except Exception as e:
      exception = utils.handle_exception(e)[0]
      exception["status_code"] = exception["status"]
      exception["status"] = "error"
      yield json.dumps(exception)

  return Response(
    generator(),
    content_type="text/event-stream",
    headers={"X-Accel-Buffering": "no"},
  )

@app.route("/api/media/<media_id>")
@limiter.limit(config["rate_limit"]["media"])
@utils.handle_exception
def media_proxy(media_id):
  session = create_session()
  token = get_current_token()

  session.cookies.update({"token": token})
  csrf_res = session.get("https://edpuzzle.com/api/v3/csrf")
  csrf_token = csrf_res.json()["CSRFToken"]

  res = session.get(
    f"https://edpuzzle.com/api/v3/media/{media_id}",
    cookies={"edpuzzleCSRF": csrf_token}
  )

  # Token expired or rejected — re-authenticate and retry once
  if res.status_code in (401, 403):
    print(f"Got {res.status_code} from Edpuzzle on media request. Re-authenticating...")
    token = get_teacher_token()
    session.cookies.update({"token": token})
    csrf_res = session.get("https://edpuzzle.com/api/v3/csrf")
    csrf_token = csrf_res.json()["CSRFToken"]
    res = session.get(
      f"https://edpuzzle.com/api/v3/media/{media_id}",
      cookies={"edpuzzleCSRF": csrf_token}
    )

  # If still failing after re-auth, give a clear error
  if res.status_code == 403:
    raise exceptions.BadGatewayError(
      "Got status code 403 from Edpuzzle.\n\n"
      "This means the assignment is private, so it is impossible to find the answers."
    )
  if res.status_code == 401:
    raise exceptions.BadGatewayError(
      "Got status code 401 from Edpuzzle after re-authentication. "
      "Please restart the server and log in again."
    )
  if res.status_code != 200:
    raise exceptions.BadGatewayError(f"Got status code {res.status_code} from Edpuzzle.")

  data = res.json()
  if data.get("error"):
    raise exceptions.BadGatewayError("Edpuzzle error: " + data["error"])

  return jsonify(data)

@app.route("/")
def homepage():
  return render_template("index.html", dev_mode=config["dev_mode"], origin=config["origin"])

@app.route("/discord")
@app.route("/discord.html")
def discord():
  return redirect("https://discord.com/invite/5kmVs8AqDQ")


# run the server
if __name__ == "__main__":
  if not is_running_from_reloader():
    # Validate token on startup — opens browser immediately if missing/expired
    print("Checking teacher token...")
    ensure_valid_token()
    print("Token OK. Starting server...")

  print("Starting flask...")
  app.run(
    host="0.0.0.0",
    port=config["server_port"],
    threaded=True,
    debug=config["dev_mode"],
  )
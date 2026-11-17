"""حماية المنظومة عند تشغيلها على سيرفر (سحابي) أو على الكمبيوتر.

- مفتاح الجلسات: من متغير البيئة، وإلا يُولَّد عشوائيًا مرة واحدة ويُحفظ بجانب البيانات. المفتاح الثابت القديم
  في الكود كان يسمح لأي شخص يعرفه بتزوير جلسة دخول (الدخول كمدير بدون كلمة مرور).
- CSRF: كل طلب يغيّر بيانات (POST) لازم يحمل رمزًا من جلسة المستخدم، حتى لا يستطيع موقع آخر
  تنفيذ عمليات باسم مستخدم مسجّل الدخول (حذف فاتورة، تغيير صلاحيات...).
- تقييد محاولات الدخول الخاطئة (منع تخمين كلمات المرور).
- إجبار تغيير كلمة المرور الافتراضية admin123.
- رؤوس أمان HTTP وكوكيز آمنة، ودعم التشغيل خلف بروكسي HTTPS.
"""
import hmac
import os
import secrets
import threading
import time
from urllib.parse import urlparse

from flask import abort, jsonify, redirect, request, session, url_for, flash


# ---------------------------------------------------------------------------
# مفتاح الجلسات
# ---------------------------------------------------------------------------
_OLD_DEFAULT_KEYS = {"", "change-this-secret-key-before-production"}


def load_secret_key(data_dir):
    env_key = os.getenv("ERP_SECRET_KEY", "")
    if env_key not in _OLD_DEFAULT_KEYS and len(env_key) >= 16:
        return env_key
    path = os.path.join(data_dir, "secret_key")
    try:
        with open(path, encoding="utf-8") as f:
            key = f.read().strip()
        if len(key) >= 32:
            return key
    except OSError:
        pass
    key = secrets.token_hex(32)
    os.makedirs(data_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(key)
    try:
        os.chmod(path, 0o600)  # على لينكس: لا يقرأه إلا مستخدم البرنامج
    except OSError:
        pass
    return key


def _env_flag(name):
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------
CSRF_FIELD = "_csrf_token"
CSRF_HEADER = "X-CSRF-Token"
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def csrf_token():
    token = session.get(CSRF_FIELD)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_FIELD] = token
    return token


def _csrf_exempt():
    # واجهة API برمز X-API-TOKEN (بدون كوكي جلسة) لا يمكن لموقع آخر تزويرها، وتسجيل دخولها لا جلسة فيه
    if request.path == "/api/login":
        return True
    return request.path.startswith("/api/") and request.headers.get("X-API-TOKEN") and not session.get("_user_id")


def _csrf_failed():
    wants_json = request.is_json or request.path.startswith(("/pos/", "/api/")) or \
        "application/json" in (request.headers.get("Accept") or "")
    msg = "انتهت صلاحية الصفحة أو الطلب غير موثوق. حدّث الصفحة (F5) وحاول مرة أخرى."
    if wants_json:
        return jsonify({"error": msg}), 400
    flash(msg, "danger")
    return redirect(_safe_url(request.referrer, url_for("dashboard")))


def check_csrf():
    if request.method not in _UNSAFE_METHODS or _csrf_exempt():
        return None
    sent = request.headers.get(CSRF_HEADER) or request.form.get(CSRF_FIELD) or ""
    expected = session.get(CSRF_FIELD) or ""
    if not expected or not hmac.compare_digest(sent, expected):
        return _csrf_failed()
    return None


# ---------------------------------------------------------------------------
# روابط الرجوع: لا نعيد التوجيه لموقع خارجي (Open Redirect)
# ---------------------------------------------------------------------------
def _safe_url(target, fallback):
    if not target:
        return fallback
    parsed = urlparse(target)
    if parsed.netloc and parsed.netloc != request.host:
        return fallback
    if parsed.scheme and parsed.scheme not in ("http", "https"):
        return fallback
    return target


safe_back = _safe_url


# ---------------------------------------------------------------------------
# تقييد محاولات الدخول
# ---------------------------------------------------------------------------
MAX_FAILURES = 5          # محاولات خاطئة متتالية
LOCK_SECONDS = 15 * 60    # مدة الإيقاف
_failures = {}
_lock = threading.Lock()


def _client_ip():
    return request.remote_addr or "?"


def login_blocked(username):
    """عدد الثواني المتبقية للإيقاف، أو 0. يُحسب لكل (IP) ولكل (اسم مستخدم) حتى لا يُخمَّن حساب من عدة أجهزة."""
    now = time.time()
    with _lock:
        for key in (("ip", _client_ip()), ("user", (username or "").lower())):
            count, until = _failures.get(key, (0, 0))
            if until > now:
                return int(until - now)
    return 0


def record_login_failure(username):
    now = time.time()
    with _lock:
        for key in (("ip", _client_ip()), ("user", (username or "").lower())):
            count, until = _failures.get(key, (0, 0))
            count = 0 if until and until <= now else count
            count += 1
            _failures[key] = (count, now + LOCK_SECONDS if count >= MAX_FAILURES else 0)
        if len(_failures) > 5000:  # حماية الذاكرة من سيل طلبات بأسماء عشوائية
            for k in [k for k, (_, u) in _failures.items() if u <= now][:2500]:
                _failures.pop(k, None)


def record_login_success(username):
    with _lock:
        _failures.pop(("ip", _client_ip()), None)
        _failures.pop(("user", (username or "").lower()), None)


# ---------------------------------------------------------------------------
# كلمة المرور الافتراضية
# ---------------------------------------------------------------------------
DEFAULT_PASSWORD = "admin123"
MIN_PASSWORD_LENGTH = 6
_PW_FREE_ENDPOINTS = {"change_password", "logout", "login", "static"}


def password_problem(new_pw):
    if len(new_pw or "") < MIN_PASSWORD_LENGTH:
        return f"كلمة المرور لازم تكون {MIN_PASSWORD_LENGTH} حروف/أرقام على الأقل."
    if new_pw == DEFAULT_PASSWORD:
        return "لا يمكن استعمال كلمة المرور الافتراضية."
    return None


def enforce_password_change(current_user):
    if not getattr(current_user, "is_authenticated", False) or not session.get("must_change_pw"):
        return None
    if request.endpoint in _PW_FREE_ENDPOINTS or request.path.startswith("/static/"):
        return None
    if request.is_json or request.path.startswith(("/pos/", "/api/")):
        return jsonify({"error": "غيّر كلمة المرور الافتراضية أولًا."}), 403
    flash("لحماية المنظومة: غيّر كلمة المرور الافتراضية (admin123) قبل المتابعة.", "warning")
    return redirect(url_for("change_password"))


# ---------------------------------------------------------------------------
# التهيئة
# ---------------------------------------------------------------------------
def init_security(app, data_dir, get_current_user):
    https = _env_flag("ERP_HTTPS")
    app.config.update(
        SECRET_KEY=load_secret_key(data_dir),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=https,
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_SECURE=https,
        PERMANENT_SESSION_LIFETIME=int(os.getenv("ERP_SESSION_HOURS", "12")) * 3600,
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,  # رفع ملفات استيراد كبيرة جدًا = استنزاف ذاكرة السيرفر
    )
    if _env_flag("ERP_BEHIND_PROXY"):
        # خلف Nginx/Caddy أو منصة استضافة: نأخذ عنوان الزبون وhttps من رؤوس البروكسي (بروكسي واحد فقط)
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def _security_checks():
        resp = check_csrf()
        if resp is not None:
            return resp
        return enforce_password_change(get_current_user())

    @app.after_request
    def _security_headers(resp):
        h = resp.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "SAMEORIGIN")
        h.setdefault("Referrer-Policy", "same-origin")
        h.setdefault("Permissions-Policy", "camera=(self), microphone=(), geolocation=()")
        h.setdefault("Content-Security-Policy",
                     "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
                     "script-src 'self' 'unsafe-inline'; font-src 'self' data:; connect-src 'self'; "
                     "frame-ancestors 'self'; base-uri 'self'; form-action 'self' https://accounts.google.com")
        if https:
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        # صفحات فيها بيانات مالية لا تُخزَّن في ذاكرة المتصفح/البروكسي المشترك
        if not request.path.startswith("/static/"):
            h.setdefault("Cache-Control", "no-store")
        return resp

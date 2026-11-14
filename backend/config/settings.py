import os
from pathlib import Path
try:
    import pymysql
    pymysql.version_info = (2, 2, 1, "final", 0)
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
env = os.environ.get
SECRET_KEY = env("SECRET_KEY", "dev-insecure-key")
DEBUG = env("DEBUG", "1") == "1"
ALLOWED_HOSTS = env("ALLOWED_HOSTS", "*").split(",")
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "rest_framework.authtoken", "corsheaders", "quiz",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True,
              "OPTIONS": {"context_processors": [
                  "django.template.context_processors.request",
                  "django.contrib.auth.context_processors.auth",
                  "django.contrib.messages.context_processors.messages"]}}]
if env("DB_NAME"):
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.mysql", "NAME": env("DB_NAME"), "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"), "HOST": env("DB_HOST", "localhost"), "PORT": env("DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"}}}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
AUTH_USER_MODEL = "quiz.User"
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"}]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
TIME_ZONE = env("TIME_ZONE", "Asia/Kolkata")
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
CORS_ALLOWED_ORIGINS = [o for o in env("CORS_ALLOWED_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500").split(",") if o]
CSRF_TRUSTED_ORIGINS = [o for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o]

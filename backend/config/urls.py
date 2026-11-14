from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

FRONTEND = settings.BASE_DIR.parent / "frontend"

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include("quiz.urls")),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
# Local convenience: serve the website from the same address (http://127.0.0.1:8000/).
# When the frontend is deployed separately (Netlify/Vercel) this folder is simply absent.
if FRONTEND.exists():
    urlpatterns += [
        path("", serve, {"path": "index.html", "document_root": FRONTEND}),
        re_path(r"^(?P<path>[\w-]+\.(?:html|css|js))$", serve, {"document_root": FRONTEND}),
    ]

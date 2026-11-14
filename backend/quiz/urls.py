from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views as v

router = DefaultRouter()
router.register("admin/users", v.UserViewSet, basename="users")
router.register("admin/classes", v.ClassViewSet, basename="classes")
router.register("admin/subjects", v.SubjectViewSet, basename="subjects")
router.register("teacher/quizzes", v.TeacherQuizViewSet, basename="tquizzes")

urlpatterns = [
    path("auth/login/", v.Login.as_view()),
    path("auth/logout/", v.Logout.as_view()),
    path("school/", v.SchoolView.as_view()),
    path("meta/", v.Meta.as_view()),
    path("notifications/", v.Notifications.as_view()),
    path("admin/stats/", v.AdminStats.as_view()),
    path("teacher/students/", v.TeacherStudents.as_view()),
    path("students/<int:pk>/performance/", v.StudentPerformance.as_view()),
    path("student/dashboard/", v.StudentDashboard.as_view()),
    path("quizzes/<int:pk>/start/", v.Start.as_view()),
    path("quizzes/<int:pk>/answers/", v.SaveAnswer.as_view()),
    path("quizzes/<int:pk>/submit/", v.Submit.as_view()),
] + router.urls

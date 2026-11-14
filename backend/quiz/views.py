from datetime import timedelta
from django.db import transaction
from django.db.models import Avg, Count, Max, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.crypto import get_random_string
from rest_framework import permissions, serializers, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import *

GRACE = 10  # seconds allowed after the deadline for the final auto-submit


def role(*roles):
    class P(permissions.BasePermission):
        def has_permission(self, request, view):
            u = request.user
            return bool(u and u.is_authenticated and u.role in roles)
    return P


def school_info(request=None):
    s = SchoolSettings.objects.first() or SchoolSettings.objects.create()
    logo = s.logo.url if s.logo else None
    if logo and request: logo = request.build_absolute_uri(logo)
    return {"name": s.name, "logo": logo, "address": s.address, "phone": s.phone, "email": s.email}


def err(msg, code=400): return Response({"detail": msg}, status=code)


# ---------- Auth ----------
class Login(APIView):
    authentication_classes = []
    permission_classes = []
    def post(self, request):
        r = request.data.get("role")
        ident = (request.data.get("identifier") or "").strip()
        pw = request.data.get("password") or ""
        if r not in ("admin", "teacher", "student") or not ident:
            return err("Invalid credentials.")
        field = "reg_no" if r == "student" else "email"
        u = User.objects.filter(role=r, **{field + "__iexact": ident}).first()
        if not u or not u.is_active or not u.check_password(pw):
            return err("Invalid credentials.")
        t, _ = Token.objects.get_or_create(user=u)
        return Response({"token": t.key, "role": u.role, "name": u.get_full_name() or u.username,
                         "school": school_info(request)})


class Logout(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({"detail": "Logged out."})


class Meta(APIView):
    def get(self, request):
        return Response({
            "classes": [{"id": c.id, "label": str(c)} for c in SchoolClass.objects.all()],
            "subjects": list(Subject.objects.values("id", "name")),
            "school": school_info(request)})


class SchoolView(APIView):
    authentication_classes = []
    permission_classes = []
    def get(self, request): return Response(school_info(request))
    def put(self, request):
        from rest_framework.authentication import TokenAuthentication
        auth = TokenAuthentication().authenticate(request)
        if not auth or auth[0].role != "admin": return err("Admin only.", 403)
        s = SchoolSettings.objects.first() or SchoolSettings.objects.create()
        for f in ("name", "address", "phone", "email"):
            if f in request.data: setattr(s, f, request.data[f])
        if request.FILES.get("logo"): s.logo = request.FILES["logo"]
        s.save()
        return Response(school_info(request))


class Notifications(APIView):
    def get(self, request):
        qs = request.user.notifications.all()[:30]
        return Response([{"id": n.id, "message": n.message, "read": n.read, "created_at": n.created_at} for n in qs])
    def post(self, request):
        request.user.notifications.update(read=True)
        return Response({"detail": "Marked as read."})


# ---------- Admin ----------
class UserS(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    class Meta:
        model = User
        fields = ["id", "role", "first_name", "last_name", "email", "reg_no", "school_class",
                  "teaching_classes", "subjects", "password", "is_active"]
        read_only_fields = ["reg_no"]
        extra_kwargs = {"email": {"required": False, "allow_null": True}}
    def validate(self, d):
        r = d.get("role", getattr(self.instance, "role", "student"))
        if r != "student" and not d.get("email", getattr(self.instance, "email", None)):
            raise serializers.ValidationError({"email": "Email is required for teachers and admins."})
        if r == "student": d["email"] = None
        if not self.instance and not d.get("password"):
            raise serializers.ValidationError({"password": "Password is required."})
        return d
    @transaction.atomic
    def create(self, d):
        pw = d.pop("password"); m2m = {k: d.pop(k) for k in ("teaching_classes", "subjects") if k in d}
        d["username"] = d.get("email") or "tmp" + get_random_string(12)
        u = User(**d); u.set_password(pw); u.save()
        if u.role == "student":
            u.reg_no = f"{timezone.now().year}{u.pk:05d}"; u.username = u.reg_no; u.save()
        for k, val in m2m.items(): getattr(u, k).set(val)
        return u
    def update(self, inst, d):
        pw = d.pop("password", None)
        u = super().update(inst, d)
        if pw: u.set_password(pw); u.save()
        return u


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [role("admin")]
    serializer_class = UserS
    def get_queryset(self):
        qs = User.objects.exclude(role="admin").order_by("-id")
        p = self.request.query_params
        if p.get("role"): qs = qs.filter(role=p["role"])
        if p.get("class"): qs = qs.filter(school_class_id=p["class"])
        if p.get("q"):
            q = p["q"]
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q) | Q(reg_no__icontains=q))
        return qs


class ClassS(serializers.ModelSerializer):
    class Meta: model = SchoolClass; fields = "__all__"
class SubjectS(serializers.ModelSerializer):
    class Meta: model = Subject; fields = "__all__"
class ClassViewSet(viewsets.ModelViewSet):
    permission_classes = [role("admin")]; serializer_class = ClassS; queryset = SchoolClass.objects.all()
class SubjectViewSet(viewsets.ModelViewSet):
    permission_classes = [role("admin")]; serializer_class = SubjectS; queryset = Subject.objects.all()


def perf(attempts):
    """Performance summary for a queryset of submitted attempts."""
    rows = [{"quiz": a.quiz.title, "subject": a.quiz.subject.name, "score": a.score, "total": a.total,
             "percentage": round(a.score * 100 / a.total, 1) if a.total else 0,
             "date": a.submitted_at} for a in attempts.select_related("quiz__subject").order_by("submitted_at")]
    subj = {}
    for r in rows: subj.setdefault(r["subject"], []).append(r["percentage"])
    pcts = [r["percentage"] for r in rows]
    return {"quizzes": rows, "average_percentage": round(sum(pcts) / len(pcts), 1) if pcts else 0,
            "highest_percentage": max(pcts) if pcts else 0,
            "subject_wise": [{"subject": k, "average": round(sum(v) / len(v), 1)} for k, v in subj.items()]}


class AdminStats(APIView):
    permission_classes = [role("admin")]
    def get(self, request):
        done = Attempt.objects.filter(submitted_at__isnull=False)
        return Response({
            "students": User.objects.filter(role="student").count(),
            "teachers": User.objects.filter(role="teacher").count(),
            "quizzes": Quiz.objects.count(),
            "attempts": done.count(),
            **{k: perf(done)[k] for k in ("average_percentage", "highest_percentage", "subject_wise")},
            "class_wise": self.class_wise(done)})
    @staticmethod
    def class_wise(done):
        agg = {}
        for a in done.select_related("quiz__school_class"):
            if a.total: agg.setdefault(str(a.quiz.school_class), []).append(a.score * 100 / a.total)
        return [{"class": k, "average": round(sum(v) / len(v), 1)} for k, v in agg.items()]


# ---------- Teacher ----------
class OptS(serializers.ModelSerializer):
    class Meta: model = Option; fields = ["id", "text", "is_correct"]
class QS(serializers.ModelSerializer):
    options = OptS(many=True, required=False)
    class Meta:
        model = Question
        fields = ["id", "qtype", "text", "code", "after", "prompt", "marks", "correct_text", "options"]
    def validate(self, d):
        t = d.get("qtype", "mcq"); o = d.get("options", [])
        if t == "mcq" and (len(o) < 2 or sum(x.get("is_correct", False) for x in o) != 1):
            raise serializers.ValidationError("MCQ needs at least 2 options and exactly one correct.")
        if t == "tf" and d.get("correct_text", "").lower() not in ("true", "false"):
            raise serializers.ValidationError("True/False needs correct_text 'true' or 'false'.")
        if t == "short" and not d.get("correct_text", "").strip():
            raise serializers.ValidationError("Short answer needs correct_text.")
        return d


class QuizS(serializers.ModelSerializer):
    questions = QS(many=True)
    total_marks = serializers.IntegerField(read_only=True)
    class Meta:
        model = Quiz
        fields = ["id", "title", "subject", "school_class", "start_at", "end_at", "duration_minutes",
                  "pass_percent", "questions", "total_marks"]
    def validate(self, d):
        s, e = d.get("start_at", getattr(self.instance, "start_at", None)), d.get("end_at", getattr(self.instance, "end_at", None))
        if s and e and e <= s:
            raise serializers.ValidationError("End time must be after start time.")
        if ("questions" in d or not self.instance) and not d.get("questions"):
            raise serializers.ValidationError("Add at least one question.")
        return d
    def _qs(self, quiz, qs):
        for i, q in enumerate(qs):
            opts = q.pop("options", [])
            qq = Question.objects.create(quiz=quiz, order=i, **q)
            Option.objects.bulk_create([Option(question=qq, **o) for o in opts])
    @transaction.atomic
    def create(self, d):
        qs = d.pop("questions")
        quiz = Quiz.objects.create(teacher=self.context["request"].user, **d)
        self._qs(quiz, qs)
        Notification.objects.bulk_create([Notification(user=s, message=f"New quiz: {quiz.title}")
                                          for s in quiz.school_class.students.all()])
        return quiz
    @transaction.atomic
    def update(self, inst, d):
        qs = d.pop("questions", None)
        if qs is not None:
            if inst.attempts.exists(): raise serializers.ValidationError("Questions can't change after students have attempted.")
            inst.questions.all().delete(); self._qs(inst, qs)
        for k, v in d.items(): setattr(inst, k, v)
        inst.save(); return inst


class TeacherQuizViewSet(viewsets.ModelViewSet):
    permission_classes = [role("teacher")]
    serializer_class = QuizS
    def get_queryset(self):
        qs = Quiz.objects.filter(teacher=self.request.user)
        q = self.request.query_params.get("q")
        return qs.filter(title__icontains=q) if q else qs
    @action(detail=True)
    def results(self, request, pk=None):
        quiz = self.get_object()
        done = quiz.attempts.filter(submitted_at__isnull=False).select_related("student")
        pcts = [a.score * 100 / a.total for a in done if a.total]
        return Response({
            "average_percentage": round(sum(pcts) / len(pcts), 1) if pcts else 0,
            "highest_percentage": round(max(pcts), 1) if pcts else 0,
            "attempts": [{"student_id": a.student_id, "name": a.student.get_full_name(), "reg_no": a.student.reg_no,
                          "score": a.score, "total": a.total, "correct": a.correct, "incorrect": a.incorrect,
                          "unattempted": a.unattempted, "submitted_at": a.submitted_at} for a in done]})


class TeacherStudents(APIView):
    permission_classes = [role("teacher")]
    def get(self, request):
        qs = User.objects.filter(role="student", school_class__in=request.user.teaching_classes.all())
        return Response([{"id": s.id, "name": s.get_full_name(), "reg_no": s.reg_no, "class": str(s.school_class)} for s in qs])


class StudentPerformance(APIView):
    permission_classes = [role("teacher", "admin")]
    def get(self, request, pk):
        s = get_object_or_404(User, pk=pk, role="student")
        if request.user.role == "teacher" and s.school_class not in request.user.teaching_classes.all():
            return err("Not your student.", 403)
        return Response(perf(s.attempts.filter(submitted_at__isnull=False)))


# ---------- Student ----------
def grade(att):
    """Server-side grading. Idempotent."""
    if att.submitted_at: return result(att)
    ans = {a.question_id: (a.answer or "").strip() for a in att.answers.all()}
    score = total = ok = bad = none = 0
    for q in att.quiz.questions.prefetch_related("options"):
        total += q.marks; a = ans.get(q.id, "")
        if not a: none += 1; continue
        right = any(str(o.id) == a and o.is_correct for o in q.options.all()) if q.qtype == "mcq" \
            else a.lower() == q.correct_text.strip().lower()
        if right: score += q.marks; ok += 1
        else: bad += 1
    att.score, att.total, att.correct, att.incorrect, att.unattempted = score, total, ok, bad, none
    att.submitted_at = timezone.now(); att.save()
    return result(att)


def result(att):
    pct = round(att.score * 100 / att.total, 1) if att.total else 0
    return {"obtained": att.score, "total": att.total, "percentage": pct, "passed": pct >= att.quiz.pass_percent,
            "correct": att.correct, "incorrect": att.incorrect, "unattempted": att.unattempted}


class StudentDashboard(APIView):
    permission_classes = [role("student")]
    def get(self, request):
        u, now = request.user, timezone.now()
        done = {a.quiz_id: a for a in u.attempts.filter(submitted_at__isnull=False).select_related("quiz__subject")}
        row = lambda q: {"id": q.id, "title": q.title, "subject": q.subject.name, "start_at": q.start_at,
                         "end_at": q.end_at, "duration_minutes": q.duration_minutes}
        quizzes = Quiz.objects.filter(school_class=u.school_class).select_related("subject") if u.school_class_id else []
        return Response({
            "student": {"name": u.get_full_name(), "reg_no": u.reg_no, "class": str(u.school_class) if u.school_class else None},
            "upcoming": [row(q) for q in quizzes if q.start_at > now],
            "available": [row(q) for q in quizzes if q.start_at <= now <= q.end_at and q.id not in done],
            "completed": [{**row(a.quiz), **result(a)} for a in done.values()],
            "performance": perf(u.attempts.filter(submitted_at__isnull=False))})


def open_attempt(request, pk, create=False):
    """Returns (attempt, error_response). Enforces class, schedule and deadline server-side."""
    quiz = get_object_or_404(Quiz, pk=pk, school_class=request.user.school_class)
    now = timezone.now()
    if now < quiz.start_at: return None, err("This quiz hasn't started yet.", 403)
    if now > quiz.end_at + timedelta(seconds=GRACE): return None, err("This quiz has ended.", 403)
    if create: att, _ = Attempt.objects.get_or_create(quiz=quiz, student=request.user)
    else: att = Attempt.objects.filter(quiz=quiz, student=request.user).first()
    if not att: return None, err("Start the quiz first.", 403)
    if att.submitted_at: return None, err("You have already submitted this quiz.", 403)
    if now > att.deadline() + timedelta(seconds=GRACE):
        grade(att); return None, err("Time is up; your answers were submitted automatically.", 403)
    return att, None


class Start(APIView):
    permission_classes = [role("student")]
    def get(self, request, pk):
        att, e = open_attempt(request, pk, create=True)
        if e: return e
        qs = [{"id": q.id, "type": q.qtype, "text": q.text, "code": q.code, "after": q.after, "prompt": q.prompt,
               "marks": q.marks, "options": [{"id": str(o.id), "text": o.text} for o in q.options.all()]}
              for q in att.quiz.questions.prefetch_related("options")]
        return Response({"title": att.quiz.title, "school_name": school_info()["name"], "ends_at": att.deadline(),
                         "duration_seconds": att.quiz.duration_minutes * 60, "questions": qs,
                         "saved_answers": {str(a.question_id): a.answer for a in att.answers.all()}})


class SaveAnswer(APIView):
    permission_classes = [role("student")]
    def post(self, request, pk):
        att, e = open_attempt(request, pk)
        if e: return e
        q = get_object_or_404(Question, pk=request.data.get("question"), quiz=att.quiz)
        Answer.objects.update_or_create(attempt=att, question=q, defaults={"answer": str(request.data.get("answer", ""))[:500]})
        return Response({"detail": "Saved."})


class Submit(APIView):
    permission_classes = [role("student")]
    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk, school_class=request.user.school_class)
        att = Attempt.objects.filter(quiz=quiz, student=request.user).first()
        if not att: return err("Start the quiz first.", 403)
        if att.submitted_at: return Response(result(att))
        if timezone.now() <= att.deadline() + timedelta(seconds=GRACE):
            valid = set(quiz.questions.values_list("id", flat=True))
            for qid, a in (request.data.get("answers") or {}).items():
                if str(qid).isdigit() and int(qid) in valid:
                    Answer.objects.update_or_create(attempt=att, question_id=int(qid), defaults={"answer": str(a)[:500]})
        return Response(grade(att))

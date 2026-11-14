from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.db import models


class SchoolClass(models.Model):
    name = models.CharField(max_length=50)
    section = models.CharField(max_length=10)
    class Meta:
        unique_together = ("name", "section")
        ordering = ["name", "section"]
    def __str__(self): return f"{self.name}-{self.section}"


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name


class User(AbstractUser):
    ROLES = [("admin", "Admin"), ("teacher", "Teacher"), ("student", "Student")]
    role = models.CharField(max_length=10, choices=ROLES, default="student")
    email = models.EmailField(unique=True, null=True, blank=True)
    reg_no = models.CharField(max_length=20, unique=True, null=True, blank=True)
    school_class = models.ForeignKey(SchoolClass, null=True, blank=True, on_delete=models.SET_NULL, related_name="students")
    teaching_classes = models.ManyToManyField(SchoolClass, blank=True, related_name="teachers")
    subjects = models.ManyToManyField(Subject, blank=True, related_name="teachers")
    def save(self, *a, **k):
        if self.is_superuser: self.role = "admin"
        super().save(*a, **k)


class SchoolSettings(models.Model):
    name = models.CharField(max_length=200, default="My School")
    logo = models.ImageField(upload_to="logo/", null=True, blank=True)
    address = models.CharField(max_length=300, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)


class Quiz(models.Model):
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="quizzes")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quizzes")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    pass_percent = models.PositiveIntegerField(default=40)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-start_at"]
    @property
    def total_marks(self): return sum(q.marks for q in self.questions.all())


class Question(models.Model):
    TYPES = [("mcq", "MCQ"), ("tf", "True/False"), ("short", "Short answer")]
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField(default=0)
    qtype = models.CharField(max_length=5, choices=TYPES, default="mcq")
    text = models.TextField()
    code = models.TextField(blank=True)
    after = models.TextField(blank=True)
    prompt = models.CharField(max_length=300, blank=True)
    marks = models.PositiveIntegerField(default=1)
    correct_text = models.CharField(max_length=300, blank=True)  # "true"/"false" or short-answer key
    class Meta: ordering = ["order", "id"]


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)


class Attempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attempts")
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    total = models.FloatField(null=True, blank=True)
    correct = models.PositiveIntegerField(default=0)
    incorrect = models.PositiveIntegerField(default=0)
    unattempted = models.PositiveIntegerField(default=0)
    class Meta: unique_together = ("quiz", "student")
    def deadline(self):
        return min(self.started_at + timedelta(minutes=self.quiz.duration_minutes), self.quiz.end_at)


class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.CharField(max_length=500, blank=True)
    class Meta: unique_together = ("attempt", "question")


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=300)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]

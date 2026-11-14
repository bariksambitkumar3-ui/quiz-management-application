from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from quiz.models import *
from quiz.views import grade


class Command(BaseCommand):
    help = "Create demo school, users, quizzes and results so every dashboard has data."

    def handle(self, *args, **kw):
        if User.objects.filter(email="asha@school.com").exists():
            return self.stdout.write("Demo data already exists.")
        now = timezone.now()
        s = SchoolSettings.objects.first() or SchoolSettings()
        s.name, s.address, s.phone, s.email = "Greenfield Public School", "12 Park Road, Kolkata", "033 5555 0101", "office@greenfield.edu"
        s.save()
        if not User.objects.filter(role="admin").exists():
            User.objects.create_superuser("admin", "admin@school.com", "Admin@12345")
        a, b = [SchoolClass.objects.get_or_create(name="Grade 8", section=x)[0] for x in "AB"]
        sci, mat = [Subject.objects.get_or_create(name=n)[0] for n in ("Science", "Mathematics")]

        t = User(username="asha@school.com", email="asha@school.com", first_name="Asha", last_name="Verma", role="teacher")
        t.set_password("Teacher@123"); t.save(); t.teaching_classes.set([a, b]); t.subjects.set([sci, mat])

        students = []
        for first, last, cls in [("Ravi", "Kumar", a), ("Meera", "Das", a), ("Arjun", "Sen", a), ("Sneha", "Roy", b)]:
            u = User(username="tmp" + first, first_name=first, last_name=last, role="student", school_class=cls)
            u.set_password("Student@123"); u.save()
            u.reg_no = f"{now.year}{u.pk:05d}"; u.username = u.reg_no; u.save(); students.append(u)

        def mk(title, subject, start, end, dur, questions):
            q = Quiz.objects.create(title=title, subject=subject, school_class=a, teacher=t, start_at=start, end_at=end, duration_minutes=dur)
            for i, (kind, text, marks, opts, right) in enumerate(questions):
                qq = Question.objects.create(quiz=q, order=i, qtype=kind, text=text, marks=marks, correct_text=right if kind != "mcq" else "")
                for j, o in enumerate(opts): Option.objects.create(question=qq, text=o, is_correct=(j == right))
            return q

        past = mk("Fractions", mat, now - timedelta(days=3), now - timedelta(days=3) + timedelta(hours=1), 20, [
            ("mcq", "What is 1/2 + 1/4?", 2, ["3/4", "2/6", "1/6", "1"], 0),
            ("mcq", "Which fraction is the largest?", 2, ["1/3", "2/5", "3/4", "1/2"], 2),
            ("tf", "2/4 is equal to 1/2.", 1, [], "true"),
            ("short", "Write 0.5 as a fraction (a/b).", 2, [], "1/2")])
        for n, u in enumerate(students[:3]):
            att = Attempt.objects.create(quiz=past, student=u)
            for q in past.questions.all():
                ans = ""
                if (q.id + n) % 3 != 0:      # a few wrong or skipped answers, so charts vary
                    ans = str(q.options.filter(is_correct=True).first().id) if q.qtype == "mcq" else q.correct_text
                if q.qtype == "mcq" and n == 2 and q.order == 0: ans = str(q.options.filter(is_correct=False).first().id)
                if ans: Answer.objects.create(attempt=att, question=q, answer=ans)
            grade(att); att.submitted_at = past.start_at + timedelta(minutes=15 + n); att.save()

        mk("Motion", sci, now - timedelta(hours=1), now + timedelta(days=3), 15, [
            ("mcq", "Which unit measures speed?", 1, ["m/s", "kg", "N", "J"], 0),
            ("mcq", "What do we call a change in position over time?", 1, ["Mass", "Motion", "Heat", "Light"], 1),
            ("tf", "A body at rest stays at rest unless a force acts on it.", 1, [], "true"),
            ("short", "Name the force that pulls objects towards Earth.", 2, [], "gravity")])
        mk("Reading Comprehension", sci, now + timedelta(days=1), now + timedelta(days=1, hours=2), 30, [
            ("mcq", "Sample question", 1, ["Yes", "No"], 0)])
        for u in students[:3]:
            Notification.objects.create(user=u, message="New quiz: Motion")

        self.stdout.write(self.style.SUCCESS(
            "Demo data created.\n  Admin:   admin@school.com / Admin@12345\n  Teacher: asha@school.com / Teacher@123\n"
            "  Student: " + students[0].reg_no + " / Student@123 (others: " + ", ".join(x.reg_no for x in students[1:]) + ")"))

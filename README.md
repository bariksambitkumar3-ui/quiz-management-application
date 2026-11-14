# Quiz Application and Students Performance Analysis System

- `backend/` Django + DRF REST API (MySQL in production, SQLite fallback locally)
- `frontend/` static HTML/CSS/JS (`quiz.html` = student quiz screen)

## Run the backend locally
```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # export the variables, or set them in your host
python manage.py makemigrations quiz
python manage.py migrate
python manage.py createsuperuser   # this account is the Admin (log in with its email)
python manage.py seed_demo         # optional: demo school, teacher, students, quizzes and results
python manage.py runserver
```
Then open http://127.0.0.1:8000/ (the backend also serves the website). `seed_demo` prints the demo logins.
Leave `DB_NAME` empty for SQLite; set `DB_*` for MySQL (create the database with utf8mb4 first).

## API (token auth: `Authorization: Token <key>`)
| Endpoint | Who | Purpose |
|---|---|---|
| POST `/api/auth/login/` `{role, identifier, password}` | all | identifier = email (admin/teacher) or registration number (student) |
| GET/PUT `/api/school/` | public / admin | school name, logo (multipart), details |
| `/api/admin/users/?role=&q=&class=` `/admin/classes/` `/admin/subjects/` | admin | CRUD; student reg. numbers are generated automatically |
| GET `/api/admin/stats/` | admin | totals, average, subject- and class-wise performance |
| `/api/teacher/quizzes/` (+ `/<id>/results/`) | teacher | create/edit/delete quizzes with nested questions; class results |
| GET `/api/teacher/students/`, `/api/students/<id>/performance/` | teacher | assigned students, individual analysis |
| GET `/api/student/dashboard/` | student | upcoming / available / completed, performance for Chart.js |
| GET `/api/quizzes/<id>/start/`, POST `.../answers/`, POST `.../submit/` | student | quiz flow used by `frontend/quiz.html` |

Quiz create body: `{title, subject, school_class, start_at, end_at, duration_minutes, pass_percent, questions:[{qtype:"mcq|tf|short", text, marks, options:[{text,is_correct}], correct_text}]}` (datetimes in ISO format).

Security: passwords hashed by Django; role checks on every endpoint; students can only open their own class's quizzes inside the schedule window; grading happens only on the server and correct answers are never sent to the browser.

## Deploy
**Backend (Render/Railway):** root `backend`; build `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`; start `gunicorn config.wsgi`. Set the variables from `.env.example` (`DEBUG=0`). Uploaded logos need a persistent disk or object storage.
**Frontend (Netlify/Vercel):** publish `frontend/`. Set `window.QUIZ_API_BASE = "https://your-api.onrender.com/api"` before the quiz script, and add the site URL to `CORS_ALLOWED_ORIGINS`.

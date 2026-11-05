import os
import secrets
from datetime import datetime
from functools import wraps

from flask import Flask, request, redirect, url_for, session, flash, render_template_string, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///stat_portal.db").replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024  # 1 MB request limit
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "true").lower() == "true"

db = SQLAlchemy(app)
csrf = CSRFProtect(app)

PHYSICAL_SERVICES = [
    "Предоставление статистической информации",
    "Получение статистических данных",
    "Заказ статистических справок",
    "Консультация по статистическим вопросам",
    "Другая услуга",
]
LEGAL_SERVICES = [
    "Предоставление статистической информации",
    "Получение статистических данных",
    "Предоставление статистической отчётности",
    "Получение статистических справок",
    "Консультация для организаций",
    "Другая услуга",
]
STATUSES = ["Получена", "В обработке", "Требуется уточнение", "Выполнена", "Отклонена"]

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket = db.Column(db.String(24), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    person_type = db.Column(db.String(30), nullable=False)
    service = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    organization = db.Column(db.String(250))
    business_id = db.Column(db.String(40))
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(200), nullable=False, index=True)
    address = db.Column(db.String(300))
    period = db.Column(db.String(100))
    region = db.Column(db.String(150))
    details = db.Column(db.Text)
    status = db.Column(db.String(40), default="Получена", nullable=False)

def page(content, title="Портал статистических услуг"):
    return render_template_string(BASE + content, title=title)

BASE = r"""
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }}</title>
<style>
:root{--blue:#174d78;--blue2:#236c9e;--ink:#1d2b38;--muted:#64748b;--line:#dce5ec;--bg:#f3f6f9}
*{box-sizing:border-box}body{margin:0;background:var(--bg);font-family:Arial,sans-serif;color:var(--ink)}
header{background:#fff;border-bottom:1px solid var(--line);padding:17px 5%;display:flex;justify-content:space-between;align-items:center}
.brand{font-weight:700;color:var(--blue);text-decoration:none}.nav a{margin-left:18px;color:var(--blue);text-decoration:none;font-size:14px}
main{max-width:1000px;margin:34px auto;padding:0 18px}.hero{background:linear-gradient(120deg,#123c69,#1d6598);color:#fff;padding:48px 28px;border-radius:16px;text-align:center}
.hero h1{font-size:34px;margin:10px 0}.hero p{font-size:19px;margin:12px 0 0;color:#edf5ff}
.panel{background:white;padding:26px;border:1px solid var(--line);border-radius:14px;margin:20px 0;box-shadow:0 5px 18px #17324d0a}
h2{color:var(--blue);margin-top:0}h3{color:var(--blue)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
label{display:block;font-size:14px;font-weight:600;margin:13px 0 6px}
input,select,textarea{width:100%;padding:12px;border:1px solid #cbd5df;border-radius:8px;font-size:15px;background:#fff}
textarea{min-height:110px;resize:vertical}.btn{display:inline-block;border:0;border-radius:8px;background:var(--blue2);color:white;padding:13px 21px;font-size:16px;text-decoration:none;cursor:pointer}
.btn.secondary{background:#e8f0f6;color:var(--blue)}.choice{display:block;padding:22px;border:1px solid var(--line);border-radius:12px;text-decoration:none;color:var(--blue);font-weight:700;background:#fff}
.choice:hover{border-color:var(--blue2);background:#f7fbff}.muted{color:var(--muted);font-size:14px}.alert{padding:13px;border-radius:8px;background:#fff4d6;margin:12px 0}.success{background:#e8f7ed}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:12px;border-bottom:1px solid var(--line);font-size:14px}
footer{text-align:center;color:var(--muted);padding:30px;font-size:13px}
@media(max-width:650px){.grid{grid-template-columns:1fr}.hero h1{font-size:27px}header{display:block}.nav{margin-top:12px}.nav a{margin:0 12px 0 0}}
</style>
</head><body>
<header><a class="brand" href="/">📊 Портал статистических услуг</a>
<nav class="nav"><a href="/">Главная</a><a href="/status">Проверить заявку</a><a href="/admin">Для сотрудников</a></nav></header>
<main>
{% with messages = get_flashed_messages() %}{% for m in messages %}<div class="alert">{{m}}</div>{% endfor %}{% endwith %}
""" + r"""{{ content|safe }}""" + r"""
</main><footer>Портал статистических услуг · Информационный сервис</footer></body></html>
"""

HOME = r"""
<section class="hero"><div style="font-size:42px">📊</div><h1>Портал статистических услуг</h1>
<p>Получите необходимые статистические услуги быстро и удобно</p></section>
<section class="panel"><h2>Выберите тип заявителя</h2>
<p class="muted">Выберите подходящий вариант, чтобы перейти к оформлению обращения.</p>
<div class="grid">
<a class="choice" href="/apply/individual">👤 Физическое лицо <div class="muted">Оформление заявки от имени гражданина</div></a>
<a class="choice" href="/apply/company">🏢 Юридическое лицо <div class="muted">Оформление заявки от имени организации</div></a>
</div></section>
<section class="panel"><h2>Полезная информация</h2><p>Перед подачей заявки подготовьте сведения, необходимые для выбранной услуги. Перечень услуг и обязательных документов должен быть утверждён владельцем портала.</p></section>
"""

@app.get("/")
def home():
    return page(HOME)

FORM = r"""
<section class="panel"><h2>{{ heading }}</h2>
<p class="muted">Поля со звёздочкой обязательны. Не вводите сведения, которые не требуются для выбранной услуги.</p>
<form method="post">
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
<label>Статистическая услуга *</label>
<select name="service" required>{% for s in services %}<option value="{{s}}">{{s}}</option>{% endfor %}</select>
{% if kind == 'individual' %}
<div class="grid">
<div><label>Фамилия и имя *</label><input name="full_name" required maxlength="200"></div>
<div><label>ИИН (только если официально необходим)</label><input name="business_id" maxlength="40"></div>
</div>
{% else %}
<label>Наименование организации *</label><input name="organization" required maxlength="250">
<div class="grid"><div><label>БИН (если необходим)</label><input name="business_id" maxlength="40"></div>
<div><label>ФИО представителя *</label><input name="full_name" required maxlength="200"></div></div>
{% endif %}
<div class="grid">
<div><label>Телефон *</label><input name="phone" required maxlength="50"></div>
<div><label>Электронная почта *</label><input name="email" type="email" required maxlength="200"></div>
</div>
<label>Адрес (при необходимости)</label><input name="address" maxlength="300">
<div class="grid">
<div><label>Период</label><input name="period" placeholder="Например, 2024–2025 гг." maxlength="100"></div>
<div><label>Регион</label><input name="region" maxlength="150"></div>
</div>
<label>Описание запроса</label><textarea name="details" maxlength="5000" placeholder="Опишите, какую статистическую информацию необходимо получить"></textarea>
<p class="muted">На этом этапе загрузка файлов отключена. Её следует подключать отдельно с проверкой типов файлов, антивирусной проверкой и защищённым хранилищем.</p>
<label style="font-weight:400"><input type="checkbox" name="consent" value="yes" required style="width:auto"> Я подтверждаю согласие на обработку данных в соответствии с опубликованной политикой конфиденциальности. *</label>
<br><button class="btn" type="submit">Отправить заявку</button>
<a class="btn secondary" href="/">Назад</a>
</form></section>
"""

@app.route("/apply/<kind>", methods=["GET", "POST"])
def apply(kind):
    if kind not in ("individual", "company"):
        abort(404)
    services = PHYSICAL_SERVICES if kind == "individual" else LEGAL_SERVICES
    heading = "Заявка физического лица" if kind == "individual" else "Заявка юридического лица"
    if request.method == "POST":
        f = request.form
        required = ["service", "full_name", "phone", "email"]
        if kind == "company":
            required += ["organization"]
        if any(not f.get(k, "").strip() for k in required) or f.get("consent") != "yes":
            flash("Пожалуйста, заполните обязательные поля и подтвердите согласие.")
            return redirect(url_for("apply", kind=kind))
        if f["service"] not in services:
            abort(400)
        ticket = "STAT-" + secrets.token_hex(4).upper()
        record = Application(
            ticket=ticket, person_type="Физическое лицо" if kind == "individual" else "Юридическое лицо",
            service=f["service"], full_name=f["full_name"].strip(),
            organization=f.get("organization", "").strip(),
            business_id=f.get("business_id", "").strip(),
            phone=f["phone"].strip(), email=f["email"].strip().lower(),
            address=f.get("address", "").strip(), period=f.get("period", "").strip(),
            region=f.get("region", "").strip(), details=f.get("details", "").strip()
        )
        db.session.add(record)
        db.session.commit()
        return page(f"""<section class="panel success"><h2>Заявка зарегистрирована</h2>
        <p>Номер вашей заявки: <strong>{ticket}</strong></p>
        <p>Сохраните номер. Проверить статус можно на странице проверки заявки.</p>
        <a class="btn" href="/status">Проверить статус</a></section>""")
    return render_template_string(BASE + FORM, title=heading, content="", heading=heading, services=services, kind=kind)

STATUS = r"""
<section class="panel"><h2>Проверить статус заявки</h2>
<form method="post"><input type="hidden" name="csrf_token" value="{{csrf_token()}}">
<label>Номер заявки</label><input name="ticket" required placeholder="STAT-XXXXXXXX">
<label>Электронная почта, указанная в заявке</label><input name="email" type="email" required>
<br><br><button class="btn">Проверить</button></form>
{% if record %}<hr><h3>Результат</h3><p><b>Номер:</b> {{record.ticket}}</p><p><b>Услуга:</b> {{record.service}}</p><p><b>Дата:</b> {{record.created_at.strftime('%d.%m.%Y %H:%M UTC')}}</p><p><b>Статус:</b> {{record.status}}</p>{% endif %}
</section>
"""

@app.route("/status", methods=["GET", "POST"])
def status():
    record = None
    if request.method == "POST":
        ticket = request.form.get("ticket", "").strip().upper()
        email = request.form.get("email", "").strip().lower()
        record = Application.query.filter_by(ticket=ticket, email=email).first()
        if not record:
            flash("Заявка с такими данными не найдена.")
    return render_template_string(BASE + STATUS, title="Проверить заявку", content="", record=record)

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper

LOGIN = r"""
<section class="panel"><h2>Вход для сотрудников</h2>
<form method="post"><input type="hidden" name="csrf_token" value="{{csrf_token()}}">
<label>Пароль администратора</label><input type="password" name="password" required>
<br><br><button class="btn">Войти</button></form></section>
"""

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        expected = os.environ.get("ADMIN_PASSWORD")
        supplied = request.form.get("password", "")
        if expected and secrets.compare_digest(supplied, expected):
            session["admin"] = True
            return redirect(url_for("admin"))
        flash("Неверный пароль. Проверьте переменную ADMIN_PASSWORD на хостинге.")
    return page(LOGIN, "Вход для сотрудников")

@app.get("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

ADMIN = r"""
<section class="panel"><h2>Заявки</h2><p><a class="btn secondary" href="/admin/logout">Выйти</a></p>
{% if records %}
<table><tr><th>Номер</th><th>Дата</th><th>Заявитель</th><th>Услуга</th><th>Статус</th><th>Изменить</th></tr>
{% for r in records %}
<tr><td>{{r.ticket}}</td><td>{{r.created_at.strftime('%d.%m.%Y')}}</td><td>{{r.full_name}}<br>{{r.organization}}</td><td>{{r.service}}</td><td>{{r.status}}</td>
<td><form method="post" action="/admin/status/{{r.id}}"><input type="hidden" name="csrf_token" value="{{csrf_token()}}">
<select name="status">{% for s in statuses %}<option {% if s==r.status %}selected{% endif %}>{{s}}</option>{% endfor %}</select><button class="btn">Сохранить</button></form></td></tr>
{% endfor %}</table>
{% else %}<p>Пока заявок нет.</p>{% endif %}</section>
"""

@app.get("/admin")
@admin_required
def admin():
    records = Application.query.order_by(Application.created_at.desc()).all()
    return render_template_string(BASE + ADMIN, title="Административная панель", content="", records=records, statuses=STATUSES)

@app.post("/admin/status/<int:record_id>")
@admin_required
def update_status(record_id):
    record = db.session.get(Application, record_id)
    if not record:
        abort(404)
    new_status = request.form.get("status")
    if new_status not in STATUSES:
        abort(400)
    record.status = new_status
    db.session.commit()
    flash("Статус заявки обновлён.")
    return redirect(url_for("admin"))

@app.get("/health")
def health():
    return {"status": "ok"}

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)

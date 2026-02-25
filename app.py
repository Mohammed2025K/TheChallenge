import os # to read environment variables
import secrets # to generate a secret key
from datetime import datetime 
from functools import wraps  # to use decorators

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for 
from flask_migrate import Migrate # for database migrations
from flask_sqlalchemy import SQLAlchemy 
from werkzeug.security import check_password_hash, generate_password_hash # for password hashing and verification


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32) # generate a secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///theChallenge.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # to avoid warnings
app.config['SESSION_COOKIE_HTTPONLY'] = True # to prevent cookie theft
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' # to prevent cookie theft
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true' # if true, the cookie will only be sent over HTTPS
db = SQLAlchemy(app) 
migrate = Migrate(app, db) # for database migrations


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)

    challenges = db.relationship('Challenge', backref='user', cascade='all, delete-orphan') # one-to-many relationship, cascade deletes challenges when user is deleted


class Challenge(db.Model):
    __tablename__ = 'challenge'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)

    tasks = db.relationship('Task', backref='challenge', cascade='all, delete-orphan')


class Task(db.Model):
    __tablename__ = 'task'
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)
    is_fixed = db.Column(db.Boolean, default=False, nullable=False)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)


def is_ajax_request():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def json_or_redirect(message=None, endpoint='login', status_code=401, flash_message=False):
    if is_ajax_request():
        return jsonify({'error': message or 'غير مصرح لك'}), status_code
    if flash_message and message:
        flash(message)
    return redirect(url_for(endpoint))


def parse_int(value, min_value=None, max_value=None):
    parsed = int(value)
    if min_value is not None and parsed < min_value:
        raise ValueError('القيمة أقل من الحد الأدنى')
    if max_value is not None and parsed > max_value:
        raise ValueError('القيمة أعلى من الحد الأقصى')
    return parsed


def get_current_day_number(challenge):
    delta = datetime.now().date() - challenge.start_date
    return delta.days + 1


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            return json_or_redirect('غير مصرح لك')
        return view_func(*args, **kwargs)

    return wrapped


def get_owned_challenge_or_404(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    if challenge.user_id != session.get('user_id'):
        return None
    return challenge


def get_owned_task_or_404(task_id):
    task = Task.query.get_or_404(task_id)
    challenge = Challenge.query.get(task.challenge_id)
    if challenge is None or challenge.user_id != session.get('user_id'):
        return None, None
    return task, challenge


def ensure_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(32)
    return session['_csrf_token']


@app.context_processor
def inject_csrf_token():
    return {'csrf_token': ensure_csrf_token()}


@app.before_request
def verify_csrf():
    ensure_csrf_token()
    if request.method not in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        return

    provided = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
    if not provided or provided != session.get('_csrf_token'):
        if is_ajax_request():
            return jsonify({'error': 'رمز الحماية غير صالح'}), 400
        flash('رمز الحماية غير صالح، حاول مرة أخرى.')
        return redirect(request.referrer or url_for('home'))


@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('تم تهيئة قاعدة البيانات بنجاح.')


@app.route('/')
@login_required
def home():
    current_date = datetime.now().strftime('%Y-%m-%d')
    challenges = Challenge.query.filter_by(user_id=session['user_id']).order_by(Challenge.id.desc()).all()
    return render_template('home.html', current_date=current_date, challenges=challenges)


@app.route('/view_challenge/<int:challenge_id>')
@login_required
def view_challenge(challenge_id):
    challenge = get_owned_challenge_or_404(challenge_id)
    if challenge is None:
        return 'غير مصرح لك', 403

    current_day_number = get_current_day_number(challenge)
    is_finished = current_day_number > challenge.duration_days

    all_tasks = Task.query.filter_by(challenge_id=challenge.id).all()
    tasks_by_day = {}
    for task in all_tasks:
        tasks_by_day.setdefault(task.day_number, []).append(task)

    daily_progress_data = []
    for day in range(1, challenge.duration_days + 1):
        tasks = tasks_by_day.get(day, [])
        if not tasks:
            daily_progress_data.append(0)
            continue
        completed = len([t for t in tasks if t.is_completed])
        percent = int((completed / len(tasks)) * 100)
        daily_progress_data.append(percent)

    return render_template(
        'challenge_detail.html',
        challenge=challenge,
        tasks_by_day=tasks_by_day,
        current_date=datetime.now().strftime('%Y-%m-%d'),
        current_day_number=current_day_number,
        daily_progress_data=daily_progress_data,
        is_finished=is_finished,
    )


@app.route('/delete_challenge/<int:challenge_id>', methods=['POST'])
@login_required
def delete_challenge(challenge_id):
    challenge = get_owned_challenge_or_404(challenge_id)
    if challenge is None:
        return jsonify({'error': 'غير مصرح لك'}), 403

    db.session.delete(challenge)
    db.session.commit()
    flash('تم حذف التحدي بنجاح.')
    return redirect(url_for('home'))


@app.route('/create_challenge', methods=['POST'])
@login_required
def create_challenge():
    name = request.form.get('name', '').strip()
    start_date_str = request.form.get('start_date', '').strip()

    try:
        duration = parse_int(request.form.get('duration', ''), min_value=1, max_value=365)
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        flash('بيانات التحدي غير صالحة.')
        return redirect(url_for('home'))

    fixed_tasks = [task.strip() for task in request.form.getlist('fixed_tasks[]') if task.strip()]
    if not name or len(name) > 100:
        flash('اسم التحدي يجب أن يكون بين 1 و100 حرف.')
        return redirect(url_for('home'))
    if not fixed_tasks:
        flash('أضف مهمة ثابتة واحدة على الأقل.')
        return redirect(url_for('home'))

    new_challenge = Challenge(
        user_id=session['user_id'],
        name=name,
        start_date=start_date,
        duration_days=duration,
    )
    db.session.add(new_challenge)
    db.session.commit()

    tasks_to_add = []
    for day in range(1, duration + 1):
        for task_name in fixed_tasks:
            tasks_to_add.append(
                Task(
                    challenge_id=new_challenge.id,
                    name=task_name[:200],
                    day_number=day,
                    is_fixed=True,
                    is_completed=False,
                )
            )

    db.session.add_all(tasks_to_add)
    db.session.commit()
    flash('تم إنشاء التحدي بنجاح.')
    return redirect(url_for('home'))


@app.route('/add_daily_task', methods=['POST'])
@login_required
def add_daily_task():
    task_name = request.form.get('task_name', '').strip()

    try:
        challenge_id = parse_int(request.form.get('challenge_id', ''), min_value=1)
        day_number = parse_int(request.form.get('day_number', ''), min_value=1)
    except (TypeError, ValueError):
        return jsonify({'error': 'بيانات التحدي أو اليوم غير صالحة'}), 400

    challenge = get_owned_challenge_or_404(challenge_id)
    if challenge is None:
        return jsonify({'error': 'غير مصرح لك'}), 403

    current_day_number = get_current_day_number(challenge)
    if day_number != current_day_number or day_number > challenge.duration_days:
        return jsonify({'error': 'يمكن إضافة المهام لليوم الحالي فقط'}), 400
    if not task_name:
        return jsonify({'error': 'اسم المهمة مطلوب'}), 400

    new_task = Task(
        challenge_id=challenge_id,
        name=task_name[:200],
        day_number=day_number,
        is_fixed=False,
        is_completed=False,
    )
    db.session.add(new_task)
    db.session.commit()

    return jsonify(
        {
            'success': True,
            'task': {
                'id': new_task.id,
                'name': new_task.name,
                'is_fixed': new_task.is_fixed,
                'is_completed': new_task.is_completed,
            },
        }
    )


@app.route('/toggle_task/<int:task_id>', methods=['POST'])
@login_required
def toggle_task(task_id):
    task, challenge = get_owned_task_or_404(task_id)
    if task is None:
        return jsonify({'error': 'غير مصرح لك'}), 403

    current_day_number = get_current_day_number(challenge)
    if task.day_number != current_day_number:
        return jsonify({'error': 'يمكن تعديل مهام اليوم الحالي فقط'}), 400

    task.is_completed = not task.is_completed
    db.session.commit()
    return jsonify({'success': True, 'is_completed': task.is_completed})


@app.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    task, challenge = get_owned_task_or_404(task_id)
    if task is None:
        return jsonify({'error': 'غير مصرح لك'}), 403

    current_day_number = get_current_day_number(challenge)
    if task.day_number != current_day_number:
        return jsonify({'error': 'يمكن تعديل مهام اليوم الحالي فقط'}), 400
    if task.is_fixed:
        return jsonify({'error': 'لا يمكن حذف المهام الثابتة'}), 400

    db.session.delete(task)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    flash('تم تسجيل الخروج بنجاح.')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session and request.method == 'GET':
        return redirect(url_for('home'))

    if request.method == 'POST':
        is_ajax = is_ajax_request()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or len(username) > 50:
            error = 'اسم المستخدم يجب أن يكون بين 1 و50 حرفًا'
            if is_ajax:
                return jsonify({'error': error}), 400
            flash(error)
            return redirect(url_for('register'))
        if '@' not in email or len(email) > 100:
            error = 'أدخل بريدًا إلكترونيًا صالحًا'
            if is_ajax:
                return jsonify({'error': error}), 400
            flash(error)
            return redirect(url_for('register'))
        if len(password) < 8:
            error = 'كلمة المرور يجب أن تكون 8 أحرف على الأقل'
            if is_ajax:
                return jsonify({'error': error}), 400
            flash(error)
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            if is_ajax:
                return jsonify({'error': 'البريد الإلكتروني مسجل مسبقًا'}), 400
            flash('البريد الإلكتروني مسجل مسبقًا')
            return redirect(url_for('register'))

        if password != confirm_password:
            if is_ajax:
                return jsonify({'error': 'كلمتا المرور غير متطابقتين'}), 400
            flash('كلمتا المرور غير متطابقتين')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        session['user_id'] = new_user.id
        flash(f'مرحبًا {username}، تم إنشاء الحساب بنجاح.')
        if is_ajax:
            return jsonify({'success': True, 'redirect': url_for('home')})
        return redirect(url_for('home'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session and request.method == 'GET':
        return redirect(url_for('home'))

    if request.method == 'POST':
        is_ajax = is_ajax_request()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            if is_ajax:
                return jsonify({'error': 'بيانات الدخول غير صحيحة'}), 400
            flash('بيانات الدخول غير صحيحة')
            return redirect(url_for('login'))

        session['user_id'] = user.id
        flash(f'مرحبًا بعودتك، {user.username}!')
        if is_ajax:
            return jsonify({'success': True, 'redirect': url_for('home')})
        return redirect(url_for('home'))

    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')

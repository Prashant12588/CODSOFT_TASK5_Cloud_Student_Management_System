import csv
import io
import os
from functools import wraps

from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from models import Course, Enrollment, Student, User, db


app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
os.makedirs(DATABASE_DIR, exist_ok=True)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "change-this-secret-key-before-deployment",
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(DATABASE_DIR, 'student_management.db')}"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def role_required(*roles):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                flash("You are not authorized to access this page.", "danger")
                return redirect(url_for("dashboard"))

            return function(*args, **kwargs)

        return wrapper

    return decorator


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")

        login_user(user)
        flash("Login successful.", "success")
        return redirect(url_for("dashboard"))

    return render_template("auth/login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        return redirect(url_for("admin_dashboard"))

    if current_user.role == "teacher":
        return redirect(url_for("teacher_dashboard"))

    if current_user.role == "student":
        return redirect(url_for("student_dashboard"))

    logout_user()
    flash("Invalid account role.", "danger")
    return redirect(url_for("login"))


# ---------------------------------------------------------
# ADMIN DASHBOARD
# ---------------------------------------------------------

@app.route("/admin")
@login_required
@role_required("admin")
def admin_dashboard():
    total_students = Student.query.count()
    total_teachers = User.query.filter_by(role="teacher").count()
    total_courses = Course.query.count()
    total_enrollments = Enrollment.query.count()

    recent_students = Student.query.order_by(Student.id.desc()).limit(5).all()
    recent_courses = Course.query.order_by(Course.id.desc()).limit(5).all()

    return render_template(
        "admin/dashboard.html",
        total_students=total_students,
        total_teachers=total_teachers,
        total_courses=total_courses,
        total_enrollments=total_enrollments,
        recent_students=recent_students,
        recent_courses=recent_courses,
    )


# ---------------------------------------------------------
# STUDENT MANAGEMENT
# ---------------------------------------------------------

@app.route("/admin/students")
@login_required
@role_required("admin")
def students():
    search = request.args.get("search", "").strip()
    department = request.args.get("department", "").strip()
    semester = request.args.get("semester", "").strip()

    query = Student.query.join(User, Student.user_id == User.id)

    if search:
        query = query.filter(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                Student.roll_number.ilike(f"%{search}%"),
                Student.department.ilike(f"%{search}%"),
            )
        )

    if department:
        query = query.filter(Student.department == department)

    if semester.isdigit():
        query = query.filter(Student.semester == int(semester))

    student_records = query.order_by(Student.id.desc()).all()

    departments = [
        row[0]
        for row in db.session.query(Student.department)
        .distinct()
        .order_by(Student.department)
        .all()
    ]

    return render_template(
        "admin/students.html",
        students=student_records,
        search=search,
        selected_department=department,
        selected_semester=semester,
        departments=departments,
    )


@app.route("/admin/add-student", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_student():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        roll_number = request.form.get("roll_number", "").strip().upper()
        department = request.form.get("department", "").strip()
        semester_value = request.form.get("semester", "").strip()

        if not all(
            [name, email, password, roll_number, department, semester_value]
        ):
            flash("All fields are required.", "danger")
            return render_template("add_student.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return render_template("add_student.html")

        try:
            semester = int(semester_value)
        except ValueError:
            flash("Semester must be valid.", "danger")
            return render_template("add_student.html")

        if semester not in range(1, 9):
            flash("Semester must be between 1 and 8.", "danger")
            return render_template("add_student.html")

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
            return render_template("add_student.html")

        if Student.query.filter_by(roll_number=roll_number).first():
            flash("This roll number is already registered.", "danger")
            return render_template("add_student.html")

        try:
            user = User(
                name=name,
                email=email,
                password=generate_password_hash(password),
                role="student",
            )

            db.session.add(user)
            db.session.flush()

            student = Student(
                roll_number=roll_number,
                department=department,
                semester=semester,
                user_id=user.id,
            )

            db.session.add(student)
            db.session.commit()

            flash(f"{name} was added successfully.", "success")
            return redirect(url_for("students"))

        except IntegrityError:
            db.session.rollback()
            flash("Email or roll number already exists.", "danger")

        except Exception:
            db.session.rollback()
            app.logger.exception("Failed to create student")
            flash("Student creation failed.", "danger")

    return render_template("add_student.html")


@app.route(
    "/admin/students/<int:student_id>/edit",
    methods=["GET", "POST"],
)
@login_required
@role_required("admin")
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    user = student.user

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        roll_number = request.form.get("roll_number", "").strip().upper()
        department = request.form.get("department", "").strip()
        semester_value = request.form.get("semester", "").strip()
        new_password = request.form.get("password", "")

        if not all(
            [name, email, roll_number, department, semester_value]
        ):
            flash("All required fields must be completed.", "danger")
            return render_template(
                "admin/edit_student.html",
                student=student,
            )

        duplicate_email = User.query.filter(
            User.email == email,
            User.id != user.id,
        ).first()

        if duplicate_email:
            flash("Another account already uses this email.", "danger")
            return render_template(
                "admin/edit_student.html",
                student=student,
            )

        duplicate_roll = Student.query.filter(
            Student.roll_number == roll_number,
            Student.id != student.id,
        ).first()

        if duplicate_roll:
            flash("Another student already uses this roll number.", "danger")
            return render_template(
                "admin/edit_student.html",
                student=student,
            )

        try:
            semester = int(semester_value)
        except ValueError:
            flash("Semester must be valid.", "danger")
            return render_template(
                "admin/edit_student.html",
                student=student,
            )

        if semester not in range(1, 9):
            flash("Semester must be between 1 and 8.", "danger")
            return render_template(
                "admin/edit_student.html",
                student=student,
            )

        if new_password and len(new_password) < 8:
            flash(
                "New password must contain at least 8 characters.",
                "danger",
            )
            return render_template(
                "admin/edit_student.html",
                student=student,
            )

        try:
            user.name = name
            user.email = email

            if new_password:
                user.password = generate_password_hash(new_password)

            student.roll_number = roll_number
            student.department = department
            student.semester = semester

            db.session.commit()

            flash(f"{name}'s profile was updated.", "success")
            return redirect(url_for("students"))

        except IntegrityError:
            db.session.rollback()
            flash("Email or roll number already exists.", "danger")

        except Exception:
            db.session.rollback()
            app.logger.exception("Failed to update student")
            flash("Student update failed.", "danger")

    return render_template(
        "admin/edit_student.html",
        student=student,
    )


@app.route(
    "/admin/students/<int:student_id>/delete",
    methods=["POST"],
)
@login_required
@role_required("admin")
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    user = student.user
    student_name = user.name

    try:
        db.session.delete(user)
        db.session.commit()
        flash(f"{student_name} was deleted.", "success")

    except Exception:
        db.session.rollback()
        app.logger.exception("Failed to delete student")
        flash(
            "Student could not be deleted. Remove related records first.",
            "danger",
        )

    return redirect(url_for("students"))


@app.route("/admin/students/export")
@login_required
@role_required("admin")
def export_students():
    student_records = Student.query.order_by(Student.id).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "Student ID",
            "Name",
            "Email",
            "Roll Number",
            "Department",
            "Semester",
        ]
    )

    for student in student_records:
        writer.writerow(
            [
                student.id,
                student.user.name,
                student.user.email,
                student.roll_number,
                student.department,
                student.semester,
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; filename=cloud_sms_students.csv"
            )
        },
    )


# ---------------------------------------------------------
# TEACHER MANAGEMENT
# ---------------------------------------------------------

@app.route("/admin/teachers")
@login_required
@role_required("admin")
def teachers():
    search = request.args.get("search", "").strip()

    query = User.query.filter_by(role="teacher")

    if search:
        query = query.filter(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
            )
        )

    teacher_records = query.order_by(User.id.desc()).all()

    return render_template(
        "admin/teachers.html",
        teachers=teacher_records,
        search=search,
    )


@app.route("/admin/add-teacher", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_teacher():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not all([name, email, password]):
            flash("All fields are required.", "danger")
            return render_template("admin/add_teacher.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return render_template("admin/add_teacher.html")

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
            return render_template("admin/add_teacher.html")

        try:
            teacher = User(
                name=name,
                email=email,
                password=generate_password_hash(password),
                role="teacher",
            )

            db.session.add(teacher)
            db.session.commit()

            flash(f"{name} was added successfully.", "success")
            return redirect(url_for("teachers"))

        except IntegrityError:
            db.session.rollback()
            flash("This email address is already registered.", "danger")

        except Exception:
            db.session.rollback()
            app.logger.exception("Failed to create teacher")
            flash("Teacher creation failed.", "danger")

    return render_template("admin/add_teacher.html")


@app.route(
    "/admin/teachers/<int:teacher_id>/edit",
    methods=["GET", "POST"],
)
@login_required
@role_required("admin")
def edit_teacher(teacher_id):
    teacher = User.query.filter_by(
        id=teacher_id,
        role="teacher",
    ).first_or_404()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("password", "")

        if not all([name, email]):
            flash("Name and email are required.", "danger")
            return render_template(
                "admin/edit_teacher.html",
                teacher=teacher,
            )

        duplicate_email = User.query.filter(
            User.email == email,
            User.id != teacher.id,
        ).first()

        if duplicate_email:
            flash("Another account already uses this email.", "danger")
            return render_template(
                "admin/edit_teacher.html",
                teacher=teacher,
            )

        if new_password and len(new_password) < 8:
            flash(
                "New password must contain at least 8 characters.",
                "danger",
            )
            return render_template(
                "admin/edit_teacher.html",
                teacher=teacher,
            )

        try:
            teacher.name = name
            teacher.email = email

            if new_password:
                teacher.password = generate_password_hash(new_password)

            db.session.commit()

            flash(f"{name}'s profile was updated.", "success")
            return redirect(url_for("teachers"))

        except IntegrityError:
            db.session.rollback()
            flash("This email address is already registered.", "danger")

        except Exception:
            db.session.rollback()
            app.logger.exception("Failed to update teacher")
            flash("Teacher update failed.", "danger")

    return render_template(
        "admin/edit_teacher.html",
        teacher=teacher,
    )


@app.route(
    "/admin/teachers/<int:teacher_id>/delete",
    methods=["POST"],
)
@login_required
@role_required("admin")
def delete_teacher(teacher_id):
    teacher = User.query.filter_by(
        id=teacher_id,
        role="teacher",
    ).first_or_404()

    teacher_name = teacher.name

    try:
        assigned_courses = Course.query.filter_by(
            teacher_id=teacher.id
        ).all()

        for course in assigned_courses:
            course.teacher_id = None

        db.session.delete(teacher)
        db.session.commit()

        flash(f"{teacher_name} was deleted.", "success")

    except Exception:
        db.session.rollback()
        app.logger.exception("Failed to delete teacher")
        flash("Teacher could not be deleted.", "danger")

    return redirect(url_for("teachers"))


@app.route("/admin/teachers/export")
@login_required
@role_required("admin")
def export_teachers():
    teacher_records = (
        User.query.filter_by(role="teacher")
        .order_by(User.id)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "Teacher ID",
            "Name",
            "Email",
            "Assigned Courses",
        ]
    )

    for teacher in teacher_records:
        writer.writerow(
            [
                teacher.id,
                teacher.name,
                teacher.email,
                len(teacher.assigned_courses),
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; filename=cloud_sms_teachers.csv"
            )
        },
    )


# ---------------------------------------------------------
# TEACHER AND STUDENT DASHBOARDS
# ---------------------------------------------------------

@app.route("/teacher")
@login_required
@role_required("teacher")
def teacher_dashboard():
    courses = Course.query.filter_by(
        teacher_id=current_user.id
    ).all()

    total_students = (
        db.session.query(Enrollment.student_id)
        .join(Course, Enrollment.course_id == Course.id)
        .filter(Course.teacher_id == current_user.id)
        .distinct()
        .count()
    )

    return render_template(
        "teacher/dashboard.html",
        courses=courses,
        total_students=total_students,
    )


@app.route("/student")
@login_required
@role_required("student")
def student_dashboard():
    student = Student.query.filter_by(
        user_id=current_user.id
    ).first()

    if not student:
        flash("Student profile is missing.", "danger")

        return render_template(
            "student/dashboard.html",
            student=None,
            enrollments=[],
        )

    enrollments = Enrollment.query.filter_by(
        student_id=student.id
    ).all()

    return render_template(
        "student/dashboard.html",
        student=student,
        enrollments=enrollments,
    )


def create_default_admin():
    admin = User.query.filter_by(
        email="admin@codsoft.com"
    ).first()

    if not admin:
        admin = User(
            name="System Administrator",
            email="admin@codsoft.com",
            password=generate_password_hash("Admin@123"),
            role="admin",
        )

        db.session.add(admin)
        db.session.commit()


with app.app_context():
    db.create_all()
    create_default_admin()


if __name__ == "__main__":
    app.run(debug=True, port=5003)

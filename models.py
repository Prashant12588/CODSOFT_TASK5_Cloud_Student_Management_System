from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    student_profile = db.relationship(
        "Student",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(50), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        unique=True,
        nullable=False,
    )


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(30), unique=True, nullable=False)
    course_name = db.Column(db.String(120), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    teacher = db.relationship(
        "User",
        foreign_keys=[teacher_id],
        backref="assigned_courses",
    )


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student.id"),
        nullable=False,
    )
    course_id = db.Column(
        db.Integer,
        db.ForeignKey("course.id"),
        nullable=False,
    )

    student = db.relationship("Student", backref="enrollments")
    course = db.relationship("Course", backref="enrollments")

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "course_id",
            name="unique_student_course",
        ),
    )


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student.id"),
        nullable=False,
    )
    course_id = db.Column(
        db.Integer,
        db.ForeignKey("course.id"),
        nullable=False,
    )
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)

    student = db.relationship("Student", backref="attendance_records")
    course = db.relationship("Course", backref="attendance_records")


class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student.id"),
        nullable=False,
    )
    course_id = db.Column(
        db.Integer,
        db.ForeignKey("course.id"),
        nullable=False,
    )
    marks = db.Column(db.Float, nullable=False)
    grade = db.Column(db.String(5), nullable=False)

    student = db.relationship("Student", backref="grades")
    course = db.relationship("Course", backref="grades")

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "course_id",
            name="unique_student_grade",
        ),
    )

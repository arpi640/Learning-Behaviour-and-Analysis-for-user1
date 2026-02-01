from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)  # admin, teacher, student
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    teacher_profile = db.relationship('Teacher', backref='user', uselist=False)
    student_profile = db.relationship('Student', backref='user', uselist=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(200))
    experience = db.Column(db.String(100))
    
    courses = db.relationship('Course', backref='teacher', lazy=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    grade_level = db.Column(db.String(50))
    
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    test_results = db.relationship('TestResult', backref='student', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    materials = db.relationship('CourseMaterial', backref='course', lazy=True)
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)
    tests = db.relationship('Test', backref='course', lazy=True)

class CourseMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    questions = db.relationship('Question', backref='material', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('course_material.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)  # basic, intermediate, excellent
    question_type = db.Column(db.String(50))

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    time_limit = db.Column(db.Integer)  # in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    test_questions = db.relationship('TestQuestion', backref='test', lazy=True)
    results = db.relationship('TestResult', backref='test', lazy=True)

class TestQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    
    question = db.relationship('Question', backref='test_questions')

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    answers_data = db.Column(db.Text)  # JSON string of student answers
    
    def set_answers(self, answers_dict):
        self.answers_data = json.dumps(answers_dict)
    
    def get_answers(self):
        return json.loads(self.answers_data) if self.answers_data else {}

class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey('student.id'),
        nullable=False
    )

    course_id = db.Column(
        db.Integer,
        db.ForeignKey('course.id'),
        nullable=False
    )

    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    certificate_url = db.Column(db.String(300))

    # ✅ ADD THESE RELATIONSHIPS
    student = db.relationship('Student', backref='certificates')
    course = db.relationship('Course', backref='certificates')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, nullable=False)
    sender_role = db.Column(db.String(20), nullable=False)  # 'teacher' or 'student'
    receiver_id = db.Column(db.Integer, nullable=False)
    receiver_role = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

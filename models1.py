# models.py - Update Question model for MCQs
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, teacher, student
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    teacher_profile = db.relationship('Teacher', backref='user', uselist=False, lazy=True)
    student_profile = db.relationship('Student', backref='user', uselist=False, lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    
    # Relationships
    courses = db.relationship('Course', backref='teacher', lazy=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    test_results = db.relationship('TestResult', backref='student', lazy=True)
    certificates = db.relationship('Certificate', backref='student', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    materials = db.relationship('CourseMaterial', backref='course', lazy=True)
    tests = db.relationship('Test', backref='course', lazy=True)
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)

class CourseMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='material', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('course_material.id'))
    question_text = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)  # Correct answer text
    difficulty = db.Column(db.String(50), nullable=False)  # basic, intermediate, excellent
    options = db.Column(db.Text)  # JSON string of options for MCQ
    correct_index = db.Column(db.Integer)  # Index of correct answer in options
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    test_questions = db.relationship('TestQuestion', backref='question', lazy=True)
    
    def get_options(self):
        """Return options as Python list"""
        if self.options:
            return json.loads(self.options)
        return []

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    time_limit = db.Column(db.Integer)  # in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    test_questions = db.relationship('TestQuestion', backref='test', lazy=True)
    results = db.relationship('TestResult', backref='test', lazy=True)

class TestQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)  # percentage
    total_questions = db.Column(db.Integer, nullable=False)
    answers = db.Column(db.Text)  # JSON string of answers
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_answers(self, answers_dict):
        self.answers = json.dumps(answers_dict)
    
    def get_answers(self):
        if self.answers:
            return json.loads(self.answers)
        return {}

class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    certificate_url = db.Column(db.String(500))
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
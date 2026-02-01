from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Teacher, Student, Course, CourseMaterial, Question, Test, Enrollment, TestResult, Certificate
from werkzeug.security import generate_password_hash, check_password_hash
import nltk
from nltk.tokenize import sent_tokenize
import random
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Teacher, Student, Course, CourseMaterial, Question, Test, TestQuestion, Enrollment, TestResult, Certificate
from werkzeug.security import generate_password_hash, check_password_hash
import nltk
from nltk.tokenize import sent_tokenize
import random
import json
from datetime import datetime
# Download NLTK data
from flask import Response
import re

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
   nltk.download('punkt')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# NLP Question Generator
class QuestionGenerator:
    @staticmethod
    def generate_questions(text, num_questions=3):
        sentences = sent_tokenize(text)
        questions = []
        
        for sentence in sentences[:num_questions]:
            words = sentence.split()
            
            if len(words) > 5:
                # -------- BASIC LEVEL (Fill in the blank) --------
                blank_word = random.choice(words[2:-2])
                basic_question = sentence.replace(blank_word, "______", 1)
                basic_answer = blank_word
                
                # -------- INTERMEDIATE LEVEL (Main idea) --------
                intermediate_question = f"What is the main idea of the following sentence?\n\"{sentence}\""
                intermediate_answer = (
                    "The sentence explains that " + " ".join(words[:6]).lower() + "..."
                )
                
                # -------- EXCELLENT LEVEL (Inference) --------
                excellent_question = f"What can be inferred from the following sentence?\n\"{sentence}\""
                excellent_answer = (
                    "It can be inferred that " + " ".join(words[:5]).lower() +
                    " plays an important role in the given context."
                )
                
                questions.extend([
                    {
                        'question': basic_question,
                        'answer': basic_answer,
                        'difficulty': 'basic'
                    },
                    {
                        'question': intermediate_question,
                        'answer': intermediate_answer,
                        'difficulty': 'intermediate'
                    },
                    {
                        'question': excellent_question,
                        'answer': excellent_answer,
                        'difficulty': 'excellent'
                    }
                ])
        
        return questions


question_generator = QuestionGenerator()

# Theme color
THEME_COLOR = "#9370DB"  # Light bluish purple

# Routes
@app.route('/')
def index():
    return render_template('auth/login.html', theme_color=THEME_COLOR)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html', theme_color=THEME_COLOR)

@app.route('/register/<role>', methods=['GET', 'POST'])
def register(role):
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register', role=role))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('register', role=role))
        
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        if role == 'teacher':
            teacher = Teacher(user_id=user.id, full_name=full_name)
            db.session.add(teacher)
        elif role == 'student':
            student = Student(user_id=user.id, full_name=full_name)
            db.session.add(student)
        
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html', role=role, theme_color=THEME_COLOR)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Admin Routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    stats = {
        'teachers': Teacher.query.count(),
        'students': Student.query.count(),
        'courses': Course.query.count(),
        'tests': Test.query.count()
    }
    
    return render_template('admin/dashboard.html', stats=stats, theme_color=THEME_COLOR)

@app.route('/admin/teachers')
@login_required
def manage_teachers():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    teachers = Teacher.query.all()
    return render_template('admin/teachers.html', teachers=teachers, theme_color=THEME_COLOR)

@app.route('/admin/students')
@login_required
def manage_students():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    students = Student.query.all()
    return render_template('admin/students.html', students=students, theme_color=THEME_COLOR)

@app.route('/admin/courses')
@login_required
def manage_courses():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    courses = Course.query.all()
    teachers = Teacher.query.all()  # Get all teachers for the dropdown
    return render_template('admin/courses.html', courses=courses, teachers=teachers, theme_color=THEME_COLOR)

# Teacher Routes
@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    courses = Course.query.filter_by(teacher_id=teacher.id).all()
    
    stats = {
        'courses': len(courses),
        'students': sum(len(course.enrollments) for course in courses),
        'materials': sum(len(course.materials) for course in courses)
    }
    
    return render_template('teacher/dashboard.html', stats=stats, courses=courses, theme_color=THEME_COLOR)

@app.route('/teacher/courses/<int:course_id>/materials', methods=['GET', 'POST'])
@login_required
def manage_materials(course_id):
    if current_user.role != 'teacher':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        material = CourseMaterial(course_id=course_id, title=title, content=content)
        db.session.add(material)
        db.session.commit()
        
        # Generate questions from content
        questions_data = question_generator.generate_questions(content)
        for q_data in questions_data:
            question = Question(
                material_id=material.id,
                question_text=q_data['question'],
                answer=q_data['answer'],
                difficulty=q_data['difficulty']
            )
            db.session.add(question)
        
        db.session.commit()
        flash('Material added and questions generated!', 'success')
    
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    return render_template('teacher/materials.html', course=course, materials=materials, theme_color=THEME_COLOR)

@app.route('/teacher/students')
@login_required
def enrolled_students():
    if current_user.role != 'teacher':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    courses = Course.query.filter_by(teacher_id=teacher.id).all()
    
    enrollments = []
    for course in courses:
        for enrollment in course.enrollments:
            # Get the latest test result for this student in this course
            latest_result = TestResult.query.filter_by(student_id=enrollment.student_id)\
                .join(Test)\
                .filter(Test.course_id == course.id)\
                .order_by(TestResult.completed_at.desc())\
                .first()
            
            enrollments.append({
                'course': course,
                'student': enrollment.student,
                'enrolled_at': enrollment.enrolled_at,
                'latest_result': latest_result
            })
    
    return render_template('teacher/students.html', enrollments=enrollments, theme_color=THEME_COLOR)
# Student Routes
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    enrollments = Enrollment.query.filter_by(student_id=student.id).all()
    
    return render_template('student/dashboard.html', enrollments=enrollments, theme_color=THEME_COLOR)

@app.route('/student/courses')
@login_required
def student_courses():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    courses = Course.query.all()
    student = Student.query.filter_by(user_id=current_user.id).first()
    enrolled_course_ids = [e.course_id for e in student.enrollments]
    
    return render_template('student/courses.html', courses=courses, enrolled_course_ids=enrolled_course_ids, theme_color=THEME_COLOR)

@app.route('/student/enroll/<int:course_id>')
@login_required
def enroll_course(course_id):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    # Check if already enrolled
    existing_enrollment = Enrollment.query.filter_by(student_id=student.id, course_id=course_id).first()
    if existing_enrollment:
        flash('Already enrolled in this course', 'info')
    else:
        enrollment = Enrollment(student_id=student.id, course_id=course_id)
        db.session.add(enrollment)
        db.session.commit()
        flash('Successfully enrolled in course!', 'success')
    
    return redirect(url_for('student_courses'))

@app.route('/student/course/<int:course_id>/materials')
@login_required
def view_course_materials(course_id):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    enrollment = Enrollment.query.filter_by(student_id=student.id, course_id=course_id).first()
    
    if not enrollment:
        flash('You are not enrolled in this course', 'error')
        return redirect(url_for('student_courses'))
    
    course = Course.query.get_or_404(course_id)
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    
    return render_template('student/materials.html', course=course, materials=materials, theme_color=THEME_COLOR)

# Test Routes
@app.route('/student/test/<int:test_id>', methods=['GET', 'POST'])
@login_required
def take_test(test_id):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    test = Test.query.get_or_404(test_id)
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    # Check if student is enrolled in the course
    enrollment = Enrollment.query.filter_by(student_id=student.id, course_id=test.course_id).first()
    if not enrollment:
        flash('You are not enrolled in this course', 'error')
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        answers = {}
        score = 0
        total_questions = len(test.test_questions)
        
        for tq in test.test_questions:
            answer = request.form.get(f'question_{tq.question_id}')
            answers[tq.question_id] = answer
            
            if answer and answer.strip().lower() == tq.question.answer.strip().lower():
                score += 1
        
        percentage = (score / total_questions) * 100 if total_questions > 0 else 0
        
        test_result = TestResult(
            student_id=student.id,
            test_id=test_id,
            score=percentage,
            total_questions=total_questions
        )
        test_result.set_answers(answers)
        db.session.add(test_result)
        db.session.commit()
        
        return redirect(url_for('test_result', result_id=test_result.id))
    
    return render_template('student/test.html', test=test, theme_color=THEME_COLOR)

@app.route('/student/result/<int:result_id>')
@login_required
def test_result(result_id):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    result = TestResult.query.get_or_404(result_id)
    
    # Analysis based on difficulty levels
    answers = result.get_answers()
    difficulty_analysis = {'basic': 0, 'intermediate': 0, 'excellent': 0}
    difficulty_correct = {'basic': 0, 'intermediate': 0, 'excellent': 0}
    
    for tq in result.test.test_questions:
        difficulty = tq.question.difficulty
        difficulty_analysis[difficulty] += 1
        if answers.get(tq.question_id, '').strip().lower() == tq.question.answer.strip().lower():
            difficulty_correct[difficulty] += 1
    
    analysis = {}
    for diff in ['basic', 'intermediate', 'excellent']:
        total = difficulty_analysis[diff]
        correct = difficulty_correct[diff]
        analysis[diff] = {
            'total': total,
            'correct': correct,
            'percentage': (correct / total * 100) if total > 0 else 0
        }
    
    return render_template('student/result.html', result=result, analysis=analysis, theme_color=THEME_COLOR)

# Add these routes to app.py

@app.route('/admin/create_course', methods=['POST'])
@login_required
def create_course():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    title = request.form.get('title')
    description = request.form.get('description')
    teacher_id = request.form.get('teacher_id')
    
    if not title or not teacher_id:
        flash('Title and teacher are required', 'error')
        return redirect(url_for('manage_courses'))
    
    course = Course(
        title=title,
        description=description,
        teacher_id=teacher_id
    )
    
    db.session.add(course)
    db.session.commit()
    flash('Course created successfully!', 'success')
    return redirect(url_for('manage_courses'))
@app.route('/teacher/create_test/<int:course_id>', methods=['GET', 'POST'])
@login_required
def create_test(course_id):
    if current_user.role != 'teacher':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    course = Course.query.get_or_404(course_id)
    
    # Calculate total questions for this course
    total_questions = 0
    for material in course.materials:
        total_questions += len(material.questions)
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        time_limit = request.form.get('time_limit')
        
        # Create the test
        test = Test(
            course_id=course_id,
            title=title,
            description=description,
            time_limit=time_limit
        )
        db.session.add(test)
        db.session.flush()  # This gets the test ID without committing
        
        # Add questions from course materials
        questions_added = 0
        for material in course.materials:
            for question in material.questions:
                test_question = TestQuestion(
                    test_id=test.id, 
                    question_id=question.id
                )
                db.session.add(test_question)
                questions_added += 1
        
        db.session.commit()
        flash(f'Test "{title}" created successfully with {questions_added} questions!', 'success')
        return redirect(url_for('manage_tests'))
    
    return render_template('teacher/create_test.html', 
                         course=course, 
                         total_questions=total_questions,
                         theme_color=THEME_COLOR)

@app.route('/teacher/tests')
@login_required
def manage_tests():
    if current_user.role != 'teacher':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    courses = Course.query.filter_by(teacher_id=teacher.id).all()
    
    tests = []
    for course in courses:
        tests.extend(course.tests)
    
    return render_template('teacher/tests.html', tests=tests, theme_color=THEME_COLOR)

@app.route('/admin/certificates')
@login_required
def manage_certificates():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    certificates = Certificate.query.all()
    students = Student.query.all()
    courses = Course.query.all()

    return render_template('admin/certificates.html', certificates=certificates, students=students,student=students,courses=courses,theme_color=THEME_COLOR)


@app.route('/teacher/student/<int:student_id>/progress')
@login_required
def view_student_progress(student_id):
    if current_user.role != 'teacher':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    student = Student.query.get_or_404(student_id)
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    # Get enrollments in teacher's courses
    enrollments = Enrollment.query.filter_by(student_id=student_id)\
        .join(Course)\
        .filter(Course.teacher_id == teacher.id)\
        .all()
    
    # Get test results for this student in teacher's courses
    test_results = TestResult.query.filter_by(student_id=student_id)\
        .join(Test)\
        .join(Course)\
        .filter(Course.teacher_id == teacher.id)\
        .all()
    
    # Calculate progress statistics
    progress_data = []
    for enrollment in enrollments:
        course = enrollment.course
        course_results = [tr for tr in test_results if tr.test.course_id == course.id]
        
        avg_score = sum(tr.score for tr in course_results) / len(course_results) if course_results else 0
        completed_materials = 0  # This would need tracking in a real system
        
        progress_data.append({
            'course': course,
            'enrollment': enrollment,
            'test_count': len(course_results),
            'average_score': avg_score,
            'completed_materials': completed_materials,
            'last_activity': course_results[-1].completed_at if course_results else enrollment.enrolled_at
        })
    
    return render_template('teacher/student_progress.html', 
                         student=student, 
                         progress_data=progress_data,
                         theme_color=THEME_COLOR)

@app.route('/teacher/student/<int:student_id>/send_message', methods=['GET', 'POST'])
@login_required
def send_message_to_student(student_id):
    if current_user.role != 'teacher':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    student = Student.query.get_or_404(student_id)
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        message_content = request.form.get('message')
        subject = request.form.get('subject')
        
        # In a real application, you would save this to a messages table
        # and implement email notification or in-app messaging
        
        flash(f'Message sent to {student.full_name}!', 'success')
        return redirect(url_for('enrolled_students'))
    
    return render_template('teacher/send_message.html', 
                         student=student, 
                         teacher=teacher,
                         theme_color=THEME_COLOR)

# Add these admin routes to app.py
@app.route('/admin/tests')
@login_required
def admin_manage_tests():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    tests = Test.query.all()
    
    # Pre-calculate statistics to avoid template errors
    test_data = []
    for test in tests:
        total_attempts = len(test.results)
        average_score = 0
        if total_attempts > 0:
            average_score = sum(result.score for result in test.results) / total_attempts
        
        test_data.append({
            'test': test,
            'total_attempts': total_attempts,
            'average_score': average_score,
            'total_questions': len(test.test_questions),
            'has_time_limit': test.time_limit is not None
        })
    
    # Calculate overall statistics
    total_test_attempts = sum(data['total_attempts'] for data in test_data)
    total_questions = sum(data['total_questions'] for data in test_data)
    
    return render_template('admin/tests.html', 
                         test_data=test_data,
                         total_test_attempts=total_test_attempts,
                         total_questions=total_questions,
                         theme_color=THEME_COLOR)
@app.route('/admin/test/<int:test_id>/delete')
@login_required
def admin_delete_test(test_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    test = Test.query.get_or_404(test_id)
    
    # Delete related test questions and results first
    TestQuestion.query.filter_by(test_id=test_id).delete()
    TestResult.query.filter_by(test_id=test_id).delete()
    
    db.session.delete(test)
    db.session.commit()
    flash('Test deleted successfully!', 'success')
    return redirect(url_for('admin_manage_tests'))

@app.route('/admin/certificates')
@login_required
def admin_manage_certificates():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    try:
        certificates = Certificate.query.all()
        students = Student.query.all()
        courses = Course.query.all()
        
        # Calculate basic statistics
        total_certificates = len(certificates)
        total_students = len(students)
        total_courses = len(courses)
        
        # Calculate issuance rate safely
        issuance_rate = 0
        if total_students > 0 and total_courses > 0:
            max_possible = total_students * total_courses
            if max_possible > 0:
                issuance_rate = (total_certificates / max_possible) * 100
        
        print(f"Students count: {len(students)}")  # Debug
        print(f"Courses count: {len(courses)}")    # Debug
        
        return render_template('admin/certificates.html', 
                             certificates=certificates, 
                             students=students,
                             courses=courses,
                             total_certificates=total_certificates,
                             eligible_students=total_students,
                             available_courses=total_courses,
                             issuance_rate=issuance_rate,
                             theme_color=THEME_COLOR)
                             
    except Exception as e:
        print(f"Error in admin_manage_certificates: {str(e)}")  # Debug
        flash(f'Error loading certificates: {str(e)}', 'error')
        return render_template('admin/certificates.html', 
                             certificates=[], 
                             students=[],
                             courses=[],
                             total_certificates=0,
                             eligible_students=0,
                             available_courses=0,
                             issuance_rate=0,
                             theme_color=THEME_COLOR)
@app.route('/admin/certificate/issue', methods=['POST'])
@login_required
def admin_issue_certificate():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    student_id = request.form.get('student_id')
    course_id = request.form.get('course_id')
    
    if not student_id or not course_id:
        flash('Student and course are required', 'error')
        return redirect(url_for('admin_manage_certificates'))
    
    # Check if certificate already exists
    existing_certificate = Certificate.query.filter_by(
        student_id=student_id, 
        course_id=course_id
    ).first()
    
    if existing_certificate:
        flash('Certificate already exists for this student and course', 'warning')
        return redirect(url_for('admin_manage_certificates'))
    
    # Create certificate
    certificate = Certificate(
        student_id=student_id,
        course_id=course_id,
        certificate_url=f"/certificates/{student_id}_{course_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    )
    
    db.session.add(certificate)
    db.session.commit()
    flash('Certificate issued successfully!', 'success')
    return redirect(url_for('admin_manage_certificates'))

@app.route('/admin/certificate/<int:certificate_id>/delete')
@login_required
def admin_delete_certificate(certificate_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    certificate = Certificate.query.get_or_404(certificate_id)
    db.session.delete(certificate)
    db.session.commit()
    flash('Certificate deleted successfully!', 'success')
    return redirect(url_for('admin_manage_certificates'))

# Student Message Routes
@app.route('/student/messages')
@login_required
def student_messages():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    # Get messages for this student
    messages = Message.query.filter_by(receiver_id=student.id, receiver_role='student')\
        .order_by(Message.sent_at.desc())\
        .all()
    
    # Mark unread messages count for the badge
    unread_count = Message.query.filter_by(
        receiver_id=student.id, 
        receiver_role='student', 
        read=False
    ).count()
    
    return render_template('student/messages.html', 
                         messages=messages, 
                         unread_count=unread_count,
                         theme_color=THEME_COLOR)

@app.route('/student/message/<int:message_id>')
@login_required
def view_student_message(message_id):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    message = Message.query.filter_by(id=message_id, receiver_id=student.id).first_or_404()
    
    # Mark as read
    if not message.read:
        message.read = True
        db.session.commit()
    
    return render_template('student/view_message.html', 
                         message=message,
                         theme_color=THEME_COLOR)

@app.route('/student/send_message', methods=['GET', 'POST'])
@login_required
def student_send_message():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    teachers = Teacher.query.all()
    
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        subject = request.form.get('subject')
        content = request.form.get('content')
        
        teacher = Teacher.query.get(teacher_id)
        if teacher:
            message = Message(
                sender_id=student.id,
                sender_role='student',
                sender_name=student.full_name,
                receiver_id=teacher.id,
                receiver_role='teacher',
                subject=subject,
                content=content
            )
            db.session.add(message)
            db.session.commit()
            flash('Message sent to teacher successfully!', 'success')
            return redirect(url_for('student_messages'))
        else:
            flash('Teacher not found', 'error')
    
    return render_template('student/send_message.html', 
                         student=student,
                         teachers=teachers,
                         theme_color=THEME_COLOR)

# Student Test Routes
@app.route('/student/tests')
@login_required
def student_tests():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    # Get courses the student is enrolled in
    enrolled_courses = [enrollment.course_id for enrollment in student.enrollments]
    
    # Get tests from enrolled courses
    tests = Test.query.filter(Test.course_id.in_(enrolled_courses)).all()
    
    # Get test results for progress tracking
    test_results = {result.test_id: result for result in student.test_results}
    
    return render_template('student/tests.html', 
                         tests=tests, 
                         test_results=test_results,
                         theme_color=THEME_COLOR)
@app.route('/student/course/<int:course_id>/materials/summary')
@login_required
def download_material_summary(course_id):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    student = Student.query.filter_by(user_id=current_user.id).first()
    enrollment = Enrollment.query.filter_by(student_id=student.id, course_id=course_id).first()

    if not enrollment:
        flash('You are not enrolled in this course', 'error')
        return redirect(url_for('student_courses'))

    course = Course.query.get_or_404(course_id)
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()

    summary_points = []

    for material in materials:
        # Split content into sentences
        sentences = re.split(r'[.\n]', material.content)

        # Pick important sentences (basic heuristic)
        important = [
            s.strip()
            for s in sentences
            if len(s.strip()) > 40 and any(
                k in s.lower()
                for k in ['important', 'key', 'definition', 'concept', 'main', 'use', 'advantage']
            )
        ]

        summary_points.extend(important[:5])  # limit per material

    if not summary_points:
        summary_points.append("No important summary points available.")

    summary_text = f"Course: {course.title}\n\nIMPORTANT POINTS:\n\n"
    for i, point in enumerate(summary_points, start=1):
        summary_text += f"{i}. {point}\n"

    return Response(
        summary_text,
        mimetype="text/plain",
        headers={
            "Content-Disposition": f"attachment;filename={course.title}_summary.txt"
        }
    )
@app.route('/student/test/<int:test_id>/start')
@login_required
def start_test(test_id):
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    test = Test.query.get_or_404(test_id)
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    # Check if student is enrolled in the course
    enrollment = Enrollment.query.filter_by(
        student_id=student.id, 
        course_id=test.course_id
    ).first()
    
    if not enrollment:
        flash('You are not enrolled in this course', 'error')
        return redirect(url_for('student_tests'))
    
    # Check if test has already been taken
    existing_result = TestResult.query.filter_by(
        student_id=student.id, 
        test_id=test_id
    ).first()
    
    if existing_result:
        flash('You have already taken this test', 'info')
        return redirect(url_for('test_result', result_id=existing_result.id))
    
    return render_template('student/take_test.html', 
                         test=test,
                         theme_color=THEME_COLOR)

# Update the existing take_test route to handle the test submission

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        if not User.query.filter_by(role='admin').first():
            admin = User(username='admin', email='admin@school.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True,port="5050")

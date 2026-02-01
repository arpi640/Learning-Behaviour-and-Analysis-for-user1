from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models1 import db, User, Teacher, Student, Course, CourseMaterial, Question, Test, Enrollment, TestResult, Certificate
from werkzeug.security import generate_password_hash, check_password_hash
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.tag import pos_tag
import random
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Teacher, Student, Course, CourseMaterial, Question, Test, TestQuestion, Enrollment, TestResult, Certificate
from werkzeug.security import generate_password_hash, check_password_hash
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.tag import pos_tag
import random
import json
from datetime import datetime

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
   nltk.download('punkt')
   nltk.download('averaged_perceptron_tagger')
   nltk.download('words')

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

# NLP Question Generator - UPDATED FOR MCQs
class QuestionGenerator:
    @staticmethod
    def extract_key_terms(text):
        """Extract important nouns and verbs from text"""
        sentences = sent_tokenize(text)
        key_terms = []
        
        for sentence in sentences:
            words = word_tokenize(sentence)
            tagged = pos_tag(words)
            
            # Extract nouns and verbs (NN*, VB*)
            for word, tag in tagged:
                if tag.startswith('NN') or tag.startswith('VB'):
                    if word.lower() not in ['is', 'are', 'was', 'were', 'be', 'been', 'being']:
                        key_terms.append(word)
        
        return list(set(key_terms))  # Remove duplicates
    
    @staticmethod
    def generate_distractors(correct_answer, all_terms, num_distractors=3):
        """Generate plausible distractors for MCQs"""
        distractors = []
        
        # Filter out the correct answer
        other_terms = [term for term in all_terms if term.lower() != correct_answer.lower()]
        
        # Try to get distractors from same sentence or similar terms
        if len(other_terms) >= num_distractors:
            distractors = random.sample(other_terms, num_distractors)
        else:
            # If not enough terms, generate some common alternatives
            common_distractors = {
                'computer': ['laptop', 'device', 'machine', 'system'],
                'program': ['application', 'software', 'code', 'script'],
                'data': ['information', 'facts', 'statistics', 'details'],
                'network': ['connection', 'web', 'system', 'grid'],
                'algorithm': ['procedure', 'method', 'process', 'technique'],
                'system': ['framework', 'structure', 'organization', 'setup'],
                'process': ['procedure', 'method', 'operation', 'technique'],
                'information': ['data', 'knowledge', 'facts', 'details'],
                'technology': ['innovation', 'tools', 'devices', 'equipment'],
                'software': ['program', 'application', 'tool', 'package'],
                'student': ['learner', 'pupil', 'scholar', 'trainee'],
                'teacher': ['instructor', 'educator', 'tutor', 'professor'],
                'course': ['class', 'subject', 'module', 'program'],
                'test': ['exam', 'assessment', 'quiz', 'evaluation']
            }
            
            # Check if we have common distractors for this term
            lower_answer = correct_answer.lower()
            for key, values in common_distractors.items():
                if key in lower_answer or any(key_word in lower_answer for key_word in key.split()):
                    distractors = values[:num_distractors]
                    break
            
            # If still no distractors, create some generic ones
            if not distractors:
                generic_distractors = ['option', 'choice', 'selection', 'alternative', 
                                     'possibility', 'variant', 'version', 'type']
                distractors = random.sample(generic_distractors, min(num_distractors, len(generic_distractors)))
        
        return distractors
    
    @staticmethod
    def generate_mcq_questions(text, num_questions=5):
        """Generate Multiple Choice Questions from text"""
        sentences = sent_tokenize(text)
        questions = []
        
        # Filter sentences that are long enough
        valid_sentences = [s for s in sentences if len(word_tokenize(s)) >= 6]
        
        for sentence in valid_sentences[:num_questions]:
            # Extract all key terms for potential answers
            all_terms = QuestionGenerator.extract_key_terms(sentence)
            
            if not all_terms or len(all_terms) < 4:
                continue
            
            # Select a key term as correct answer (prefer nouns)
            tagged = pos_tag(word_tokenize(sentence))
            nouns = [word for word, tag in tagged if tag.startswith('NN') and len(word) > 3]
            
            if nouns:
                correct_answer = random.choice(nouns)
            else:
                correct_answer = random.choice(all_terms)
            
            # Generate distractors
            distractors = QuestionGenerator.generate_distractors(correct_answer, all_terms)
            
            # If we don't have enough distractors, skip this sentence
            if len(distractors) < 3:
                continue
            
            # Create question by replacing the answer with a blank
            question_text = sentence.replace(correct_answer, "______")
            
            # Combine all options
            all_options = distractors + [correct_answer]
            random.shuffle(all_options)
            
            # Find the index of correct answer after shuffling
            correct_index = all_options.index(correct_answer)
            
            # Create question for basic level (fill in the blank)
            questions.append({
                'question': f"Fill in the blank: {question_text}",
                'options': all_options,
                'correct_index': correct_index,
                'correct_answer': correct_answer,
                'difficulty': 'basic',
                'original_sentence': sentence
            })
        
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
        
        flash('Course material added successfully! You can now generate questions for this material.', 'success')
        return redirect(url_for('manage_materials', course_id=course_id))
    
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    return render_template('teacher/materials.html', course=course, materials=materials, theme_color=THEME_COLOR)

# NEW ROUTE: Generate questions from material
@app.route('/teacher/material/<int:material_id>/generate-questions', methods=['GET', 'POST'])
@login_required
def generate_questions_from_material(material_id):
    if current_user.role != 'teacher':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    material = CourseMaterial.query.get_or_404(material_id)
    course = Course.query.get_or_404(material.course_id)
    
    # Verify that the teacher owns this course
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if course.teacher_id != teacher.id:
        flash('Access denied', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        # Save generated questions to database
        questions_data = json.loads(request.form.get('questions_data', '[]'))
        
        for q_data in questions_data:
            question = Question(
                material_id=material_id,
                question_text=q_data['question'],
                answer=q_data['correct_answer'],
                difficulty=q_data['difficulty'],
                options=json.dumps(q_data['options']),
                correct_index=q_data['correct_index']
            )
            db.session.add(question)
        
        db.session.commit()
        flash(f'{len(questions_data)} questions generated and saved successfully!', 'success')
        return redirect(url_for('view_material_questions', material_id=material_id))
    
    # GET request - show question generation interface
    existing_questions_count = Question.query.filter_by(material_id=material_id).count()
    
    return render_template('teacher/generate_questions.html', 
                         material=material, 
                         course=course,
                         existing_questions_count=existing_questions_count,
                         theme_color=THEME_COLOR)

# AJAX endpoint for generating questions
@app.route('/teacher/material/<int:material_id>/generate-questions-ajax', methods=['POST'])
@login_required
def generate_questions_ajax(material_id):
    if current_user.role != 'teacher':
        return jsonify({'error': 'Access denied'}), 403
    
    material = CourseMaterial.query.get_or_404(material_id)
    
    # Get parameters from request
    data = request.get_json()
    num_questions = data.get('num_questions', 5)
    
    # Generate questions
    questions = question_generator.generate_mcq_questions(material.content, num_questions)
    
    return jsonify({
        'success': True,
        'questions': questions,
        'material_title': material.title,
        'generated_count': len(questions)
    })

# NEW ROUTE: View and manage questions for a material
@app.route('/teacher/material/<int:material_id>/questions')
@login_required
def view_material_questions(material_id):
    if current_user.role != 'teacher':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    material = CourseMaterial.query.get_or_404(material_id)
    course = Course.query.get_or_404(material.course_id)
    questions = Question.query.filter_by(material_id=material_id).all()
    
    # Parse options for each question
    for question in questions:
        if question.options:
            question.options_list = json.loads(question.options)
    
    return render_template('teacher/material_questions.html', 
                         material=material,
                         course=course,
                         questions=questions,
                         theme_color=THEME_COLOR)

# NEW ROUTE: Edit a specific question
@app.route('/teacher/question/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    if current_user.role != 'teacher':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    question = Question.query.get_or_404(question_id)
    material = CourseMaterial.query.get_or_404(question.material_id)
    course = Course.query.get_or_404(material.course_id)
    
    # Verify teacher ownership
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if course.teacher_id != teacher.id:
        flash('Access denied', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        question.question_text = request.form.get('question_text')
        question.answer = request.form.get('answer')
        question.difficulty = request.form.get('difficulty')
        
        # Update options
        options_text = request.form.get('options')
        if options_text:
            options_list = [opt.strip() for opt in options_text.split(',')]
            question.options = json.dumps(options_list)
            
            # Update correct index if needed
            if question.answer in options_list:
                question.correct_index = options_list.index(question.answer)
        
        db.session.commit()
        flash('Question updated successfully!', 'success')
        return redirect(url_for('view_material_questions', material_id=material.id))
    
    # Parse options for display
    options_list = []
    if question.options:
        options_list = json.loads(question.options)
    
    return render_template('teacher/edit_question.html',
                         question=question,
                         material=material,
                         options_list=options_list,
                         theme_color=THEME_COLOR)

# NEW ROUTE: Delete a question
@app.route('/teacher/question/<int:question_id>/delete')
@login_required
def delete_question(question_id):
    if current_user.role != 'teacher':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    question = Question.query.get_or_404(question_id)
    material_id = question.material_id
    material = CourseMaterial.query.get_or_404(material_id)
    course = Course.query.get_or_404(material.course_id)
    
    # Verify teacher ownership
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if course.teacher_id != teacher.id:
        flash('Access denied', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully!', 'success')
    return redirect(url_for('view_material_questions', material_id=material_id))

# NEW ROUTE: Add a manual question
@app.route('/teacher/material/<int:material_id>/add-question', methods=['GET', 'POST'])
@login_required
def add_manual_question(material_id):
    if current_user.role != 'teacher':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    material = CourseMaterial.query.get_or_404(material_id)
    course = Course.query.get_or_404(material.course_id)
    
    # Verify teacher ownership
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if course.teacher_id != teacher.id:
        flash('Access denied', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        question_text = request.form.get('question_text')
        answer = request.form.get('answer')
        difficulty = request.form.get('difficulty')
        options_text = request.form.get('options')
        
        # Parse options
        options_list = [opt.strip() for opt in options_text.split(',')]
        options_json = json.dumps(options_list)
        
        # Determine correct index
        correct_index = options_list.index(answer) if answer in options_list else 0
        
        question = Question(
            material_id=material_id,
            question_text=question_text,
            answer=answer,
            difficulty=difficulty,
            options=options_json,
            correct_index=correct_index
        )
        
        db.session.add(question)
        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('view_material_questions', material_id=material_id))
    
    return render_template('teacher/add_manual_question.html',
                         material=material,
                         course=course,
                         theme_color=THEME_COLOR)

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

# Test Routes - UPDATED FOR MCQs
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
            
            # For MCQ, check if selected option index matches correct index
            if answer and answer.isdigit():
                selected_index = int(answer)
                if tq.question.options:
                    question_options = json.loads(tq.question.options)
                    correct_index = tq.question.correct_index
                    
                    if selected_index == correct_index:
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
    
    # For GET request, prepare questions with options
    test_questions_with_options = []
    for tq in test.test_questions:
        question_data = {
            'id': tq.question.id,
            'text': tq.question.question_text,
            'options': json.loads(tq.question.options) if tq.question.options else [],
            'difficulty': tq.question.difficulty
        }
        test_questions_with_options.append(question_data)
    
    return render_template('student/test.html', 
                         test=test, 
                         questions=test_questions_with_options, 
                         theme_color=THEME_COLOR)

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
        
        answer = answers.get(tq.question_id, '')
        if answer and answer.isdigit():
            selected_index = int(answer)
            if tq.question.options:
                question_options = json.loads(tq.question.options)
                correct_index = tq.question.correct_index
                
                if selected_index == correct_index:
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

# UPDATED TEST CREATION ROUTE
@app.route('/teacher/create_test/<int:course_id>', methods=['GET', 'POST'])
@login_required
def create_test(course_id):
    if current_user.role != 'teacher':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    course = Course.query.get_or_404(course_id)
    
    # Verify teacher ownership
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if course.teacher_id != teacher.id:
        flash('Access denied', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        time_limit = request.form.get('time_limit', type=int)
        
        # Get selected question IDs
        selected_questions = request.form.getlist('question_ids')
        
        if not selected_questions:
            flash('Please select at least one question for the test.', 'error')
            return redirect(url_for('create_test', course_id=course_id))
        
        # Create the test
        test = Test(
            course_id=course_id,
            title=title,
            description=description,
            time_limit=time_limit
        )
        db.session.add(test)
        db.session.flush()  # Get test ID
        
        # Add selected questions
        for question_id in selected_questions:
            test_question = TestQuestion(
                test_id=test.id, 
                question_id=question_id
            )
            db.session.add(test_question)
        
        db.session.commit()
        flash(f'Test "{title}" created successfully with {len(selected_questions)} questions!', 'success')
        return redirect(url_for('manage_tests'))
    
    # GET request - show all available questions from course materials
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    
    # Collect all questions from all materials
    all_questions = []
    for material in materials:
        questions = Question.query.filter_by(material_id=material.id).all()
        for q in questions:
            q.material_title = material.title
            if q.options:
                q.options_list = json.loads(q.options)
        all_questions.extend(questions)
    
    return render_template('teacher/create_test.html', 
                         course=course, 
                         questions=all_questions,
                         total_questions=len(all_questions),
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
    return render_template('admin/certificates.html', certificates=certificates, theme_color=THEME_COLOR)


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
    
    return redirect(url_for('take_test', test_id=test_id))

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
    app.run(debug=True, port="5050")
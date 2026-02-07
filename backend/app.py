from flask import Flask, request, jsonify, session, send_from_directory, make_response
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
import os
import uuid
import json
import threading
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from config import config
from dotenv import load_dotenv
load_dotenv()

# OpenAI imports
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI library not installed. Transcription and notes generation will not work.")

# PDF generation imports
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: ReportLab library not installed. PDF generation will not work.")

# Get environment
env = os.environ.get('FLASK_ENV', 'development')
app = Flask(__name__, static_folder='../static', template_folder='../theme')
app.config.from_object(config.get(env, config['default']))

# Initialize extensions
db = SQLAlchemy()

# Development fallback: if MySQL is configured but not reachable, use SQLite so the app can boot
if env == 'development':
    try:
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        if isinstance(db_uri, str) and db_uri.startswith('mysql'):
            test_engine = create_engine(db_uri, pool_pre_ping=True)
            with test_engine.connect():
                pass
    except SQLAlchemyError:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/VirtualClassroom.sqlite3'

db.init_app(app)

# CORS Configuration - Universal CORS for ALL routes including errors
# This ensures CORS headers are applied to EVERY response, even error responses

def add_cors_headers(response):
    """Helper function to add CORS headers to any response"""
    origin = request.headers.get('Origin')
    
    # Handle different origin scenarios
    if origin and origin != 'null':
        # Allow the specific origin that made the request
        # This handles both localhost:5000 and 127.0.0.1:5000
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    else:
        # For null origin (file:// protocol) or no origin, allow all
        response.headers['Access-Control-Allow-Origin'] = '*'
    
    # Add required CORS headers
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Methods'] = '*'
    response.headers['Access-Control-Expose-Headers'] = '*'
    response.headers['Access-Control-Max-Age'] = '3600'
    
    return response

@app.after_request
def apply_cors_to_all_responses(response):
    """
    Automatically apply CORS headers to ALL responses (including errors).
    This decorator runs after every request, ensuring CORS is applied to:
    - All /api/* routes (login, signup, teacher, student, admin)
    - All /uploads/* routes
    - All /static/* routes
    - Error responses (500, 404, etc.)
    - Any other route in the application
    """
    return add_cors_headers(response)

# Handle OPTIONS preflight requests for ALL routes
@app.before_request
def handle_cors_preflight():
    """
    Handle CORS preflight OPTIONS requests for all routes.
    This ensures preflight requests work for every API endpoint.
    """
    if request.method == "OPTIONS":
        response = make_response()
        return add_cors_headers(response)

# Error handlers to ensure CORS headers are added even on errors
@app.errorhandler(404)
def not_found(error):
    response = make_response(jsonify({'success': False, 'message': 'Resource not found'}), 404)
    return add_cors_headers(response)

@app.errorhandler(500)
def internal_error(error):
    response = make_response(jsonify({
        'success': False, 
        'message': 'Internal server error', 
        'error': str(error) if app.debug else 'An error occurred'
    }), 500)
    return add_cors_headers(response)

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions and ensure CORS headers are present"""
    response = make_response(jsonify({
        'success': False, 
        'message': 'An error occurred', 
        'error': str(e) if app.debug else 'Internal server error'
    }), 500)
    return add_cors_headers(response)

# Initialize Flask-CORS with comprehensive settings
# Note: When using credentials, we can't use wildcard origins in some browsers
# So we handle it dynamically in add_cors_headers
CORS(app, 
     resources={r"/*": {"origins": "*"}},
     supports_credentials=True,  # Changed to True to support session cookies
     allow_headers="*",
     methods="*",
     expose_headers="*")

# SocketIO CORS
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   cors_credentials=True,
                   async_mode='threading')

# Create upload directories
os.makedirs('uploads/audio', exist_ok=True)
os.makedirs('uploads/transcriptions', exist_ok=True)
os.makedirs('uploads/notes', exist_ok=True)
os.makedirs('../static/qr_codes', exist_ok=True)

# Initialize OpenAI client
openai_client = None
if OPENAI_AVAILABLE:
    try:
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if openai_api_key:
            openai_client = OpenAI(api_key=openai_api_key)
        else:
            OPENAI_AVAILABLE = False
            print("Warning: OPENAI_API_KEY not set. Transcription and notes generation will be disabled.")
    except Exception as e:
        OPENAI_AVAILABLE = False
        openai_client = None
        print(f"Warning: OpenAI client initialization failed ({e}). Transcription and notes generation will be disabled.")

# Database Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, teacher, student
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Active')
    
    # Relationships
    broadcasts = db.relationship('Broadcast', backref='teacher_user', lazy=True)
    attendances = db.relationship('Attendance', backref='student_user', lazy=True)
    recordings = db.relationship('Recording', backref='user', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'phone': self.phone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status': self.status
        }

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    broadcasts = db.relationship('Broadcast', backref='course', lazy=True)
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'teacher_id': self.teacher_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'course_id': self.course_id,
            'enrolled_at': self.enrolled_at.isoformat() if self.enrolled_at else None
        }

class Broadcast(db.Model):
    __tablename__ = 'broadcasts'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    lecture_topic = db.Column(db.String(200), nullable=False)
    course_title = db.Column(db.String(200), nullable=False)
    broadcast_url = db.Column(db.String(500), unique=True)
    status = db.Column(db.String(20), default='active')  # active, ended
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    audio_file_path = db.Column(db.String(500))
    
    # Relationships
    attendances = db.relationship('Attendance', backref='broadcast', lazy=True)
    recordings = db.relationship('Recording', backref='broadcast', lazy=True)
    transcriptions = db.relationship('Transcription', backref='broadcast', lazy=True)
    notes = db.relationship('Note', backref='broadcast', lazy=True)
    
    def to_dict(self):
        teacher = User.query.get(self.teacher_id)
        # Normalize audio_file_path to use forward slashes (for URLs)
        normalized_audio_path = self.audio_file_path.replace('\\', '/') if self.audio_file_path else None
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'teacher_username': teacher.username if teacher else None,
            'course_id': self.course_id,
            'lecture_topic': self.lecture_topic,
            'course_title': self.course_title,
            'broadcast_url': self.broadcast_url,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'audio_file_path': normalized_audio_path
        }

class Attendance(db.Model):
    __tablename__ = 'attendances'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    broadcast_id = db.Column(db.Integer, db.ForeignKey('broadcasts.id'), nullable=False)
    student_username = db.Column(db.String(80), nullable=False)
    attended_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_username': self.student_username,
            'broadcast_id': self.broadcast_id,
            'attended_at': self.attended_at.isoformat() if self.attended_at else None
        }

class Recording(db.Model):
    __tablename__ = 'recordings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    broadcast_id = db.Column(db.Integer, db.ForeignKey('broadcasts.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # in bytes
    duration = db.Column(db.Integer)  # in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        # Normalize file path to use forward slashes (for URLs)
        normalized_path = self.file_path.replace('\\', '/') if self.file_path else None
        return {
            'id': self.id,
            'user_id': self.user_id,
            'broadcast_id': self.broadcast_id,
            'title': self.title,
            'file_path': normalized_path,
            'file_size': self.file_size,
            'duration': self.duration,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Transcription(db.Model):
    __tablename__ = 'transcriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    broadcast_id = db.Column(db.Integer, db.ForeignKey('broadcasts.id'), nullable=True)
    recording_id = db.Column(db.Integer, db.ForeignKey('recordings.id'), nullable=True)
    text_content = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(500))
    word_count = db.Column(db.Integer)
    language = db.Column(db.String(50), default='English')
    status = db.Column(db.String(20), default='completed')  # completed, processing
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'broadcast_id': self.broadcast_id,
            'recording_id': self.recording_id,
            'text_content': self.text_content,
            'file_path': self.file_path,
            'word_count': self.word_count,
            'language': self.language,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    broadcast_id = db.Column(db.Integer, db.ForeignKey('broadcasts.id'), nullable=True)
    transcription_id = db.Column(db.Integer, db.ForeignKey('transcriptions.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(500))
    summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'broadcast_id': self.broadcast_id,
            'transcription_id': self.transcription_id,
            'title': self.title,
            'content': self.content,
            'file_path': self.file_path,
            'summary': self.summary,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    broadcast_id = db.Column(db.Integer, db.ForeignKey('broadcasts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'broadcast_id': self.broadcast_id,
            'user_id': self.user_id,
            'username': self.username,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Initialize database
with app.app_context():
    db.create_all()
    
    # Create default admin user if not exists
    admin = User.query.filter_by(email='admin@lectureflow.com').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@lectureflow.com',
            password_hash=generate_password_hash('lectureflow123'),
            role='admin',
            status='Active'
        )
        db.session.add(admin)
        db.session.commit()

# Authentication Routes
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password_hash, password):
        session.permanent = True  # Make session permanent
        session['user_id'] = user.id
        session['user_role'] = user.role
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'message': 'Login successful'
        }), 200
    
    return jsonify({
        'success': False,
        'message': 'Invalid credentials'
    }), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200

@app.route('/api/check-session', methods=['GET'])
def check_session():
    """Check if user session is valid"""
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    
    if user_id:
        user = User.query.get(user_id)
        if user:
            return jsonify({
                'success': True,
                'authenticated': True,
                'user': user.to_dict()
            }), 200
    
    return jsonify({
        'success': False,
        'authenticated': False,
        'message': 'No active session'
    }), 401

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')
    phone = data.get('phone')
    
    # Check if user exists
    if User.query.filter_by(email=email).first():
        return jsonify({
            'success': False,
            'message': 'Email already registered'
        }), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({
            'success': False,
            'message': 'Username already taken'
        }), 400
    
    # Create new user
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
        phone=phone,
        status='Active'
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'message': 'Registration successful'
    }), 201

# Admin Routes
@app.route('/api/admin/teachers', methods=['GET', 'POST'])
def manage_teachers():
    if request.method == 'GET':
        teachers = User.query.filter_by(role='teacher').all()
        return jsonify([teacher.to_dict() for teacher in teachers]), 200
    
    elif request.method == 'POST':
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password', 'default123')  # Default password
        phone = data.get('phone')
        
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already exists'}), 400
        
        teacher = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role='teacher',
            phone=phone,
            status='Active'
        )
        
        db.session.add(teacher)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'teacher': teacher.to_dict(),
            'message': 'Teacher registered successfully'
        }), 201

@app.route('/api/admin/teachers/<int:teacher_id>', methods=['PUT', 'DELETE'])
def teacher_detail(teacher_id):
    teacher = User.query.get_or_404(teacher_id)
    
    if request.method == 'PUT':
        data = request.json
        teacher.username = data.get('username', teacher.username)
        teacher.email = data.get('email', teacher.email)
        teacher.phone = data.get('phone', teacher.phone)
        teacher.status = data.get('status', teacher.status)
        
        if 'password' in data:
            teacher.password_hash = generate_password_hash(data['password'])
        
        db.session.commit()
        return jsonify({'success': True, 'teacher': teacher.to_dict()}), 200
    
    elif request.method == 'DELETE':
        db.session.delete(teacher)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Teacher deleted'}), 200

@app.route('/api/admin/students', methods=['GET', 'POST'])
def manage_students():
    if request.method == 'GET':
        students = User.query.filter_by(role='student').all()
        return jsonify([student.to_dict() for student in students]), 200
    
    elif request.method == 'POST':
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password', 'default123')
        phone = data.get('phone')
        
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already exists'}), 400
        
        student = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role='student',
            phone=phone,
            status='Active'
        )
        
        db.session.add(student)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'student': student.to_dict(),
            'message': 'Student registered successfully'
        }), 201

@app.route('/api/admin/students/<int:student_id>', methods=['PUT', 'DELETE'])
def student_detail(student_id):
    student = User.query.get_or_404(student_id)
    
    if request.method == 'PUT':
        data = request.json
        student.username = data.get('username', student.username)
        student.email = data.get('email', student.email)
        student.phone = data.get('phone', student.phone)
        student.status = data.get('status', student.status)
        
        if 'password' in data:
            student.password_hash = generate_password_hash(data['password'])
        
        db.session.commit()
        return jsonify({'success': True, 'student': student.to_dict()}), 200
    
    elif request.method == 'DELETE':
        db.session.delete(student)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Student deleted'}), 200

# Unified endpoints for all roles - Recordings, Transcriptions, Notes

def get_authenticated_user():
    """Helper function to get authenticated user from session or headers"""
    # Try to get user_id from session first
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    
    # Fallback: Try to get from request headers or query params (from localStorage)
    if not user_id:
        user_id = request.headers.get('X-User-Id') or request.args.get('user_id')
        user_role = request.headers.get('X-User-Role') or request.args.get('user_role')
        if user_id:
            try:
                user_id = int(user_id)
                # If we got user_id from header/query, verify the user exists
                user = User.query.get(user_id)
                if user:
                    # Set session for future requests
                    session['user_id'] = user_id
                    session['user_role'] = user.role
                    user_role = user.role
                else:
                    user_id = None
                    user_role = None
            except (ValueError, TypeError):
                user_id = None
                user_role = None
    
    return user_id, user_role

@app.route('/api/recordings', methods=['GET'])
def get_recordings_unified():
    """Get recordings - works for all roles (admin sees all, others see their own)"""
    user_id, user_role = get_authenticated_user()
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    # Admin can see all recordings
    if user_role == 'admin':
        recordings = Recording.query.order_by(Recording.created_at.desc()).all()
        # Include user information for each recording
        result = []
        for recording in recordings:
            user = User.query.get(recording.user_id)
            rec_dict = recording.to_dict()
            rec_dict['user'] = user.to_dict() if user else None
            result.append(rec_dict)
        return jsonify(result), 200
    else:
        # Teachers and students see only their own recordings
        recordings = Recording.query.filter_by(user_id=user_id).order_by(Recording.created_at.desc()).all()
        return jsonify([r.to_dict() for r in recordings]), 200

@app.route('/api/transcriptions', methods=['GET'])
def get_transcriptions_unified():
    """Get transcriptions - works for all roles (admin sees all, others see their own)"""
    user_id, user_role = get_authenticated_user()
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    # Admin can see all transcriptions
    if user_role == 'admin':
        transcriptions = Transcription.query.order_by(Transcription.created_at.desc()).all()
        # Include user and broadcast information
        result = []
        for transcription in transcriptions:
            user = User.query.get(transcription.user_id)
            broadcast = Broadcast.query.get(transcription.broadcast_id) if transcription.broadcast_id else None
            trans_dict = transcription.to_dict()
            trans_dict['user'] = user.to_dict() if user else None
            trans_dict['broadcast'] = broadcast.to_dict() if broadcast else None
            result.append(trans_dict)
        return jsonify(result), 200
    else:
        # Teachers and students see only their own transcriptions
        transcriptions = Transcription.query.filter_by(user_id=user_id).order_by(Transcription.created_at.desc()).all()
        return jsonify([t.to_dict() for t in transcriptions]), 200

@app.route('/api/notes', methods=['GET'])
def get_notes_unified():
    """Get notes - works for all roles (admin sees all, others see their own)"""
    user_id, user_role = get_authenticated_user()
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    # Admin can see all notes
    if user_role == 'admin':
        notes = Note.query.order_by(Note.created_at.desc()).all()
        # Include user, broadcast, and transcription information
        result = []
        for note in notes:
            user = User.query.get(note.user_id)
            broadcast = Broadcast.query.get(note.broadcast_id) if note.broadcast_id else None
            transcription = Transcription.query.get(note.transcription_id) if note.transcription_id else None
            note_dict = note.to_dict()
            note_dict['user'] = user.to_dict() if user else None
            note_dict['broadcast'] = broadcast.to_dict() if broadcast else None
            note_dict['transcription'] = transcription.to_dict() if transcription else None
            result.append(note_dict)
        return jsonify(result), 200
    else:
        # Teachers and students see only their own notes
        notes = Note.query.filter_by(user_id=user_id).order_by(Note.created_at.desc()).all()
        return jsonify([n.to_dict() for n in notes]), 200

# Admin - Get All Recordings (backward compatibility)
@app.route('/api/admin/recordings', methods=['GET'])
def get_all_recordings():
    """Get all recordings for admin"""
    return get_recordings_unified()

# Admin - Get All Transcriptions (backward compatibility)
@app.route('/api/admin/transcriptions', methods=['GET'])
def get_all_transcriptions():
    """Get all transcriptions for admin"""
    return get_transcriptions_unified()

# Admin - Get All Notes (new endpoint)
@app.route('/api/admin/notes', methods=['GET'])
def get_all_notes():
    """Get all notes for admin"""
    return get_notes_unified()

# Admin - Get All Broadcasts
@app.route('/api/admin/broadcasts', methods=['GET'])
def get_all_broadcasts():
    """Get all broadcasts for admin"""
    broadcasts = Broadcast.query.order_by(Broadcast.started_at.desc()).all()
    return jsonify([b.to_dict() for b in broadcasts]), 200

# Teacher Routes
@app.route('/api/teacher/broadcasts', methods=['GET', 'POST'])
def manage_broadcasts():
    try:
        if request.method == 'GET':
            # Get status filter from query params (default to 'active')
            status_filter = request.args.get('status', 'active')
            if status_filter == 'all':
                broadcasts = Broadcast.query.order_by(Broadcast.started_at.desc()).all()
            else:
                broadcasts = Broadcast.query.filter_by(status=status_filter).all()
            return jsonify([b.to_dict() for b in broadcasts]), 200
        
        elif request.method == 'POST':
            data = request.json
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Try to get teacher_id from session first
            teacher_id = session.get('user_id')
            
            # Fallback: If session doesn't work, try to get from request data or headers
            # This handles cases where cookies aren't being sent properly
            if not teacher_id:
                # Try to get from request data (less secure but works as fallback)
                teacher_id = data.get('teacher_id') or data.get('user_id')
                
                # If still no teacher_id, try to get user from email/username in request
                if not teacher_id:
                    user_email = data.get('email')
                    user_username = data.get('username')
                    if user_email:
                        user = User.query.filter_by(email=user_email).first()
                        if user and user.role == 'teacher':
                            teacher_id = user.id
                            # Set session for future requests
                            session['user_id'] = user.id
                            session['user_role'] = user.role
                    elif user_username:
                        user = User.query.filter_by(username=user_username).first()
                        if user and user.role == 'teacher':
                            teacher_id = user.id
                            session['user_id'] = user.id
                            session['user_role'] = user.role
            
            if not teacher_id:
                return jsonify({
                    'success': False, 
                    'message': 'Not authenticated. Please login first',
                    'hint': 'Make sure you are logged in and session cookies are enabled'
                }), 401
            
            # Verify the user is actually a teacher
            user = User.query.get(teacher_id)
            if not user or user.role != 'teacher':
                return jsonify({
                    'success': False, 
                    'message': 'Only teachers can start broadcasts'
                }), 403
            
            lecture_topic = data.get('lecture_topic')
            course_title = data.get('course_title')
            course_id = data.get('course_id')
            
            # Validate required fields
            if not lecture_topic or not course_title:
                return jsonify({'success': False, 'message': 'lecture_topic and course_title are required'}), 400
            
            # Generate unique broadcast URL
            broadcast_url = f"/broadcast/{uuid.uuid4().hex[:12]}"
            
            # Handle course_id: If not provided, we need to handle the database constraint
            # The database might have a NOT NULL constraint even though the model allows NULL
            # So we'll create a default course if course_id is not provided
            if not course_id:
                # Try to find or create a default course for this teacher
                default_course = Course.query.filter_by(
                    teacher_id=teacher_id,
                    name=course_title  # Use course_title as the course name
                ).first()
                
                if not default_course:
                    # Create a default course for this broadcast
                    default_course = Course(
                        name=course_title,
                        description=f"Default course for {lecture_topic}",
                        teacher_id=teacher_id
                    )
                    db.session.add(default_course)
                    db.session.flush()  # Flush to get the ID
                
                course_id = default_course.id
            
            broadcast = Broadcast(
                teacher_id=teacher_id,
                course_id=course_id,
                lecture_topic=lecture_topic,
                course_title=course_title,
                broadcast_url=broadcast_url,
                status='active'
            )
            
            db.session.add(broadcast)
            db.session.commit()
            
            # Emit to all clients that a new broadcast started
            # Note: socketio.emit() from Flask routes broadcasts to all clients by default
            socketio.emit('new_broadcast', broadcast.to_dict())
            
            return jsonify({
                'success': True,
                'broadcast': broadcast.to_dict(),
                'message': 'Broadcast started successfully'
            }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Error creating broadcast',
            'error': str(e)
        }), 500

@app.route('/api/teacher/broadcasts/<int:broadcast_id>/end', methods=['POST'])
def end_broadcast(broadcast_id):
    broadcast = Broadcast.query.get_or_404(broadcast_id)
    broadcast.status = 'ended'
    broadcast.ended_at = datetime.utcnow()
    
    # Save audio file path if provided
    data = request.json or {}
    if 'audio_file_path' in data and data['audio_file_path']:
        broadcast.audio_file_path = data['audio_file_path']
    else:
        # Try to find the most recent recording for this broadcast
        recording = Recording.query.filter_by(broadcast_id=broadcast_id).order_by(Recording.created_at.desc()).first()
        if not recording:
            # Try to find by teacher_id and recent timestamp
            recording = Recording.query.filter_by(
                user_id=broadcast.teacher_id
            ).order_by(Recording.created_at.desc()).first()
        
        if recording and recording.file_path:
            broadcast.audio_file_path = recording.file_path
    
    db.session.commit()
    
    # Automatically trigger transcription if audio file exists
    if broadcast.audio_file_path:
        # Verify file exists
        audio_path = broadcast.audio_file_path
        if not os.path.exists(audio_path):
            # Try alternative path
            audio_path = os.path.join('uploads', 'audio', os.path.basename(broadcast.audio_file_path))
        
        if os.path.exists(audio_path):
            # Run transcription in background thread with application context
            def transcribe_with_context():
                with app.app_context():
                    transcribe_broadcast_audio(broadcast_id)
            thread = threading.Thread(target=transcribe_with_context)
            thread.daemon = True
            thread.start()
        else:
            print(f"Warning: Audio file not found for broadcast {broadcast_id}: {broadcast.audio_file_path}")
    
    # Emit broadcast ended event
    # Note: socketio.emit() from Flask routes broadcasts to all clients by default
    socketio.emit('broadcast_ended', {'broadcast_id': broadcast_id})
    
    return jsonify({'success': True, 'message': 'Broadcast ended'}), 200

@app.route('/api/teacher/recordings', methods=['GET'])
def get_recordings():
    """Get recordings for teacher (backward compatibility - uses unified endpoint)"""
    return get_recordings_unified()

@app.route('/api/teacher/attendance/<int:broadcast_id>', methods=['GET'])
def get_attendance(broadcast_id):
    attendances = Attendance.query.filter_by(broadcast_id=broadcast_id).all()
    return jsonify([a.to_dict() for a in attendances]), 200

# Student Routes
@app.route('/api/student/broadcasts', methods=['GET'])
def get_active_broadcasts():
    """Get active broadcasts for students"""
    broadcasts = Broadcast.query.filter_by(status='active').all()
    return jsonify([b.to_dict() for b in broadcasts]), 200

@app.route('/api/student/broadcasts/all', methods=['GET'])
def get_all_student_broadcasts():
    """Get all broadcasts (active and ended) for students"""
    broadcasts = Broadcast.query.order_by(Broadcast.started_at.desc()).all()
    return jsonify([b.to_dict() for b in broadcasts]), 200

@app.route('/api/student/broadcasts/<int:broadcast_id>/join', methods=['POST'])
def join_broadcast(broadcast_id):
    data = request.json
    student_username = data.get('username')
    student_id = session.get('user_id')
    
    # Check if already attended
    existing = Attendance.query.filter_by(
        broadcast_id=broadcast_id,
        student_id=student_id
    ).first()
    
    if not existing:
        attendance = Attendance(
            student_id=student_id,
            broadcast_id=broadcast_id,
            student_username=student_username
        )
        db.session.add(attendance)
        db.session.commit()
        
        # Emit attendance update
        socketio.emit('attendance_update', {
            'broadcast_id': broadcast_id,
            'student_username': student_username
        }, room=f'broadcast_{broadcast_id}')
    
    return jsonify({'success': True, 'message': 'Joined broadcast'}), 200

@app.route('/api/student/recordings', methods=['GET'])
def get_student_recordings():
    """Get recordings for student (backward compatibility - uses unified endpoint)"""
    return get_recordings_unified()

@app.route('/api/student/transcriptions', methods=['GET'])
def get_student_transcriptions():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    transcriptions = Transcription.query.filter_by(user_id=user_id).all()
    return jsonify([t.to_dict() for t in transcriptions]), 200

@app.route('/api/student/notes', methods=['GET'])
def get_student_notes():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    notes = Note.query.filter_by(user_id=user_id).all()
    return jsonify([n.to_dict() for n in notes]), 200

# Teacher-specific endpoints for transcriptions and notes (backward compatibility)
@app.route('/api/teacher/transcriptions', methods=['GET'])
def get_teacher_transcriptions():
    """Get all transcriptions for the logged-in teacher (uses unified endpoint)"""
    return get_transcriptions_unified()

@app.route('/api/teacher/notes', methods=['GET'])
def get_teacher_notes():
    """Get all notes for the logged-in teacher (uses unified endpoint)"""
    return get_notes_unified()

@app.route('/api/instructors', methods=['GET'])
def get_instructors():
    teachers = User.query.filter_by(role='teacher', status='Active').all()
    return jsonify([{'id': t.id, 'username': t.username, 'email': t.email} for t in teachers]), 200

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join_broadcast')
def handle_join_broadcast(data):
    broadcast_id = data.get('broadcast_id')
    room = f'broadcast_{broadcast_id}'
    join_room(room)
    emit('joined_broadcast', {'broadcast_id': broadcast_id, 'room': room})

@socketio.on('leave_broadcast')
def handle_leave_broadcast(data):
    broadcast_id = data.get('broadcast_id')
    room = f'broadcast_{broadcast_id}'
    leave_room(room)
    emit('left_broadcast', {'broadcast_id': broadcast_id})

@socketio.on('chat_message')
def handle_chat_message(data):
    broadcast_id = data.get('broadcast_id')
    user_id = session.get('user_id')
    username = data.get('username')
    message = data.get('message')
    
    if user_id and broadcast_id:
        # Save message to database
        chat_msg = ChatMessage(
            broadcast_id=broadcast_id,
            user_id=user_id,
            username=username,
            message=message
        )
        db.session.add(chat_msg)
        db.session.commit()
        
        # Broadcast to all in the room
        emit('new_message', {
            'id': chat_msg.id,
            'broadcast_id': broadcast_id,  # Include broadcast_id so clients can filter
            'username': username,
            'message': message,
            'created_at': chat_msg.created_at.isoformat()
        }, room=f'broadcast_{broadcast_id}')

@socketio.on('get_chat_history')
def handle_get_chat_history(data):
    broadcast_id = data.get('broadcast_id')
    messages = ChatMessage.query.filter_by(broadcast_id=broadcast_id).order_by(ChatMessage.created_at).limit(50).all()
    emit('chat_history', [m.to_dict() for m in messages])

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    """Handle real-time audio streaming chunks from teacher (PCM format)"""
    broadcast_id = data.get('broadcast_id')
    audio_data = data.get('audio_data')
    format_type = data.get('format', 'pcm')  # PCM format
    sample_rate = data.get('sample_rate', 44100)
    channels = data.get('channels', 1)
    
    if broadcast_id and audio_data:
        # Broadcast audio chunk to all students in the broadcast room
        emit('audio_chunk', {
            'broadcast_id': broadcast_id,
            'audio_data': audio_data,
            'format': format_type,
            'sample_rate': sample_rate,
            'channels': channels,
            'timestamp': data.get('timestamp', datetime.utcnow().isoformat())
        }, room=f'broadcast_{broadcast_id}')

# Helper Functions for Transcription and Notes Generation
def transcribe_broadcast_audio(broadcast_id):
    """Transcribe audio file for a broadcast using OpenAI"""
    try:
        broadcast = Broadcast.query.get(broadcast_id)
        if not broadcast:
            print(f"Broadcast {broadcast_id} not found")
            return
        
        # Try to get audio file path
        audio_path = None
        if broadcast.audio_file_path:
            # Try the stored path first
            if os.path.exists(broadcast.audio_file_path):
                audio_path = broadcast.audio_file_path
            else:
                # Try with uploads/audio prefix
                audio_path = os.path.join('uploads', 'audio', os.path.basename(broadcast.audio_file_path))
                if not os.path.exists(audio_path):
                    audio_path = None
        
        # If still no path, try to find from recordings
        if not audio_path:
            recording = Recording.query.filter_by(broadcast_id=broadcast_id).order_by(Recording.created_at.desc()).first()
            if recording and recording.file_path:
                if os.path.exists(recording.file_path):
                    audio_path = recording.file_path
                else:
                    # Try with uploads/audio prefix
                    audio_path = os.path.join('uploads', 'audio', os.path.basename(recording.file_path))
                    if not os.path.exists(audio_path):
                        audio_path = None
        
        if not audio_path or not os.path.exists(audio_path):
            print(f"Audio file not found for broadcast {broadcast_id}")
            return
        
        if not openai_client:
            print("OpenAI client not available")
            return
        
        # Check if transcription already exists
        existing_transcription = Transcription.query.filter_by(
            broadcast_id=broadcast_id,
            user_id=broadcast.teacher_id
        ).first()
        
        if existing_transcription:
            print(f"Transcription already exists for broadcast {broadcast_id}")
            return
        
        # Create transcription record with processing status
        transcription = Transcription(
            user_id=broadcast.teacher_id,
            broadcast_id=broadcast_id,
            text_content="",
            status='processing',
            language='English'
        )
        db.session.add(transcription)
        db.session.commit()
        transcription_id = transcription.id  # Save ID before committing
        
        # Transcribe using OpenAI
        print(f"Starting transcription for broadcast {broadcast_id}, audio file: {audio_path}")
        with open(audio_path, 'rb') as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        print(f"Transcription completed for broadcast {broadcast_id}, length: {len(transcript)} characters")
        
        # Update transcription - use a fresh query to avoid session issues
        transcription = Transcription.query.get(transcription_id)
        if transcription:
            transcription.text_content = transcript
            transcription.word_count = len(transcript.split())
            transcription.status = 'completed'
            
            # Save transcription to file
            transcription_filename = f"transcription_{broadcast_id}_{uuid.uuid4().hex[:8]}.txt"
            transcription_path = os.path.join('uploads', 'transcriptions', transcription_filename)
            os.makedirs(os.path.dirname(transcription_path), exist_ok=True)
            with open(transcription_path, 'w', encoding='utf-8') as f:
                f.write(transcript)
            transcription.file_path = transcription_path.replace('\\', '/')
            
            db.session.commit()
            
            # Automatically generate notes after transcription (with app context)
            def generate_notes_with_context():
                with app.app_context():
                    generate_broadcast_notes(broadcast_id, transcription_id)
            notes_thread = threading.Thread(target=generate_notes_with_context)
            notes_thread.daemon = True
            notes_thread.start()
            
            # Emit status update
            socketio.emit('transcription_completed', {
                'broadcast_id': broadcast_id,
                'transcription_id': transcription_id
            })
        
    except Exception as e:
        print(f"Error transcribing audio: {str(e)}")
        import traceback
        traceback.print_exc()
        # Update transcription status to failed - use fresh query
        try:
            if 'transcription_id' in locals():
                transcription = Transcription.query.get(transcription_id)
                if transcription:
                    transcription.status = 'failed'
                    db.session.commit()
        except Exception as update_error:
            print(f"Error updating transcription status: {str(update_error)}")

def generate_broadcast_notes(broadcast_id, transcription_id):
    """Generate notes from transcription using OpenAI"""
    try:
        # Use fresh queries to avoid session issues
        transcription = Transcription.query.get(transcription_id)
        if not transcription or not transcription.text_content:
            print(f"Transcription {transcription_id} not found or has no content")
            return
        
        broadcast = Broadcast.query.get(broadcast_id)
        if not broadcast:
            print(f"Broadcast {broadcast_id} not found")
            return
        
        if not openai_client:
            print("OpenAI client not available")
            return
        
        # Check if notes already exist
        existing_note = Note.query.filter_by(
            broadcast_id=broadcast_id,
            transcription_id=transcription_id
        ).first()
        
        if existing_note:
            print(f"Notes already exist for broadcast {broadcast_id}")
            return
        
        # Create note record
        note = Note(
            user_id=broadcast.teacher_id,
            broadcast_id=broadcast_id,
            transcription_id=transcription_id,
            title=f"Notes: {broadcast.lecture_topic}",
            content="",
            summary=""
        )
        db.session.add(note)
        db.session.commit()
        note_id = note.id  # Save ID before continuing
        
        # Generate notes using OpenAI
        print(f"Starting notes generation for broadcast {broadcast_id}")
        prompt = f"""Please create comprehensive study notes from the following lecture transcription. 
        Organize the notes with:
        1. A brief summary at the top
        2. Key concepts and main points
        3. Important details and examples
        4. Any formulas, definitions, or important facts
        
        Transcription:
        {transcription.text_content}
        
        Format the notes in a clear, structured way that would be helpful for studying."""
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates comprehensive study notes from lecture transcriptions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        print(f"Notes generation completed for broadcast {broadcast_id}")
        
        notes_content = response.choices[0].message.content
        
        # Extract summary (first paragraph or first few sentences)
        summary = notes_content.split('\n\n')[0] if '\n\n' in notes_content else notes_content[:200]
        
        # Update note - use fresh query
        note = Note.query.get(note_id)
        if note:
            note.content = notes_content
            note.summary = summary
            
            # Save notes to file
            notes_filename = f"notes_{broadcast_id}_{uuid.uuid4().hex[:8]}.txt"
            notes_path = os.path.join('uploads', 'notes', notes_filename)
            os.makedirs(os.path.dirname(notes_path), exist_ok=True)
            with open(notes_path, 'w', encoding='utf-8') as f:
                f.write(notes_content)
            note.file_path = notes_path.replace('\\', '/')
            
            db.session.commit()
            
            # Emit status update
            socketio.emit('notes_completed', {
                'broadcast_id': broadcast_id,
                'note_id': note_id
            })
        
    except Exception as e:
        print(f"Error generating notes: {str(e)}")
        import traceback
        traceback.print_exc()
        try:
            if 'note_id' in locals():
                note = Note.query.get(note_id)
                if note:
                    db.session.delete(note)
                    db.session.commit()
        except Exception as cleanup_error:
            print(f"Error cleaning up note: {str(cleanup_error)}")

# Broadcast Status and Processing Routes
@app.route('/api/broadcasts/<int:broadcast_id>/status', methods=['GET'])
def get_broadcast_status(broadcast_id):
    """Get transcription and notes status for a broadcast"""
    try:
        broadcast = Broadcast.query.get(broadcast_id)
        if not broadcast:
            return jsonify({
                'success': False,
                'message': 'Broadcast not found'
            }), 404
        
        # Get transcription status
        transcription = Transcription.query.filter_by(broadcast_id=broadcast_id).first()
        transcription_status = {
            'exists': transcription is not None,
            'status': transcription.status if transcription else 'not_started',
            'id': transcription.id if transcription else None
        }
        
        # Get notes status
        note = Note.query.filter_by(broadcast_id=broadcast_id).first()
        notes_status = {
            'exists': note is not None,
            'status': note.status if note and hasattr(note, 'status') else ('completed' if note else 'not_started'),
            'id': note.id if note else None
        }
        
        # Check if audio file exists (for transcription to start)
        has_audio = bool(broadcast.audio_file_path)
        if not has_audio:
            # Try to find from recordings
            recording = Recording.query.filter_by(broadcast_id=broadcast_id).order_by(Recording.created_at.desc()).first()
            has_audio = bool(recording and recording.file_path)
        
        return jsonify({
            'success': True,
            'broadcast_id': broadcast_id,
            'has_audio': has_audio,
            'transcription': transcription_status,
            'notes': notes_status
        }), 200
    except Exception as e:
        print(f"Error getting broadcast status: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/broadcasts/<int:broadcast_id>/transcribe', methods=['POST'])
def trigger_transcription(broadcast_id):
    """Manually trigger transcription for a broadcast"""
    broadcast = Broadcast.query.get_or_404(broadcast_id)
    
    if not broadcast.audio_file_path:
        return jsonify({
            'success': False,
            'message': 'No audio file found for this broadcast'
        }), 400
    
    # Check if transcription already exists
    existing = Transcription.query.filter_by(broadcast_id=broadcast_id).first()
    if existing and existing.status == 'completed':
        return jsonify({
            'success': False,
            'message': 'Transcription already completed'
        }), 400
    
    # Start transcription in background with application context
    def transcribe_with_context():
        with app.app_context():
            transcribe_broadcast_audio(broadcast_id)
    thread = threading.Thread(target=transcribe_with_context)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Transcription started'
    }), 200

@app.route('/api/broadcasts/<int:broadcast_id>/generate-notes', methods=['POST'])
def trigger_notes_generation(broadcast_id):
    """Manually trigger notes generation for a broadcast"""
    broadcast = Broadcast.query.get_or_404(broadcast_id)
    
    # Get transcription
    transcription = Transcription.query.filter_by(broadcast_id=broadcast_id).first()
    if not transcription:
        return jsonify({
            'success': False,
            'message': 'No transcription found. Please transcribe the audio first.'
        }), 400
    
    if transcription.status != 'completed':
        return jsonify({
            'success': False,
            'message': 'Transcription is still processing'
        }), 400
    
    # Check if notes already exist
    existing = Note.query.filter_by(broadcast_id=broadcast_id).first()
    if existing:
        return jsonify({
            'success': False,
            'message': 'Notes already generated'
        }), 400
    
    # Start notes generation in background with application context
    def generate_notes_with_context():
        with app.app_context():
            generate_broadcast_notes(broadcast_id, transcription.id)
    thread = threading.Thread(target=generate_notes_with_context)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Notes generation started'
    }), 200

@app.route('/api/broadcasts/<int:broadcast_id>/transcript', methods=['GET'])
def get_transcript(broadcast_id):
    """Get transcript for a broadcast"""
    transcription = Transcription.query.filter_by(broadcast_id=broadcast_id).first()
    
    if not transcription:
        return jsonify({
            'success': False,
            'message': 'Transcription not found'
        }), 404
    
    return jsonify({
        'success': True,
        'transcription': transcription.to_dict()
    }), 200

@app.route('/api/broadcasts/<int:broadcast_id>/transcript/download', methods=['GET'])
def download_transcript(broadcast_id):
    """Download transcript as text file"""
    transcription = Transcription.query.filter_by(broadcast_id=broadcast_id).first()
    
    if not transcription:
        return jsonify({
            'success': False,
            'message': 'Transcription not found'
        }), 404
    
    if transcription.file_path and os.path.exists(transcription.file_path):
        return send_from_directory(
            os.path.dirname(transcription.file_path),
            os.path.basename(transcription.file_path),
            as_attachment=True,
            download_name=f"transcript_{broadcast_id}.txt"
        )
    else:
        # Create temporary file if file_path doesn't exist
        response = make_response(transcription.text_content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = f'attachment; filename=transcript_{broadcast_id}.txt'
        return response

@app.route('/api/broadcasts/<int:broadcast_id>/notes', methods=['GET'])
def get_notes(broadcast_id):
    """Get notes for a broadcast"""
    note = Note.query.filter_by(broadcast_id=broadcast_id).first()
    
    if not note:
        return jsonify({
            'success': False,
            'message': 'Notes not found'
        }), 404
    
    return jsonify({
        'success': True,
        'note': note.to_dict()
    }), 200

@app.route('/api/broadcasts/<int:broadcast_id>/notes/download', methods=['GET'])
def download_notes_pdf(broadcast_id):
    """Download notes as PDF"""
    note = Note.query.filter_by(broadcast_id=broadcast_id).first()
    
    if not note:
        return jsonify({
            'success': False,
            'message': 'Notes not found'
        }), 404
    
    if not REPORTLAB_AVAILABLE:
        # Fallback: return as text file
        response = make_response(note.content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = f'attachment; filename=notes_{broadcast_id}.txt'
        return response
    
    try:
        # Create PDF in memory
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor='#000000',
            spaceAfter=30
        )
        story.append(Paragraph(note.title, title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Summary
        if note.summary:
            story.append(Paragraph("<b>Summary:</b>", styles['Heading2']))
            story.append(Paragraph(note.summary, styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Content - split by newlines and create paragraphs
        content_lines = note.content.split('\n')
        for line in content_lines:
            line = line.strip()
            if line:
                # Check if it's a heading (starts with # or is all caps)
                if line.startswith('#') or (line.isupper() and len(line) > 3):
                    story.append(Spacer(1, 0.1*inch))
                    story.append(Paragraph(line.replace('#', '').strip(), styles['Heading2']))
                else:
                    story.append(Paragraph(line, styles['Normal']))
            else:
                story.append(Spacer(1, 0.1*inch))
        
        doc.build(story)
        buffer.seek(0)
        
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=notes_{broadcast_id}.pdf'
        return response
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        # Fallback to text
        response = make_response(note.content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = f'attachment; filename=notes_{broadcast_id}.txt'
        return response

# File Upload Routes
@app.route('/api/upload/audio', methods=['POST'])
def upload_audio():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    # Use os.path.join for actual file system path (handles Windows/Unix differences)
    file_system_path = os.path.join('uploads', 'audio', unique_filename)
    file.save(file_system_path)
    
    # Normalize path for database storage (always use forward slashes for URLs)
    file_path = file_system_path.replace('\\', '/')
    
    # Try to get user_id from session, if not available try from request data
    user_id = session.get('user_id')
    if not user_id:
        # Try to get from request data (for cases where session cookies aren't working)
        data = request.form.to_dict()
        if 'user_id' in data:
            try:
                user_id = int(data['user_id'])
            except (ValueError, TypeError):
                pass
    
    # If still no user_id, try to get from broadcast_id if provided
    broadcast_id = request.form.get('broadcast_id')
    if not user_id and broadcast_id:
        try:
            broadcast = Broadcast.query.get(int(broadcast_id))
            if broadcast:
                user_id = broadcast.teacher_id
        except (ValueError, TypeError):
            pass
    
    title = request.form.get('title', filename)
    broadcast_id = request.form.get('broadcast_id')
    
    recording = Recording(
        user_id=user_id,
        broadcast_id=int(broadcast_id) if broadcast_id else None,
        title=title,
        file_path=file_path,
        file_size=os.path.getsize(file_system_path)
    )
    
    db.session.add(recording)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'recording': recording.to_dict(),
        'message': 'Audio uploaded successfully'
    }), 201

@app.route('/api/recordings/<int:recording_id>', methods=['DELETE'])
def delete_recording(recording_id):
    recording = Recording.query.get_or_404(recording_id)
    
    # Check ownership
    if recording.user_id != session.get('user_id'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Delete file
    if os.path.exists(recording.file_path):
        os.remove(recording.file_path)
    
    db.session.delete(recording)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Recording deleted'}), 200

# Transcription Routes
@app.route('/api/transcriptions', methods=['POST'])
def create_transcription():
    data = request.json
    user_id = session.get('user_id')
    text_content = data.get('text_content')
    broadcast_id = data.get('broadcast_id')
    recording_id = data.get('recording_id')
    
    # For now, save static data (AI transcription will be added later)
    transcription = Transcription(
        user_id=user_id,
        broadcast_id=broadcast_id,
        recording_id=recording_id,
        text_content=text_content,
        word_count=len(text_content.split()) if text_content else 0,
        status='completed'
    )
    
    db.session.add(transcription)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'transcription': transcription.to_dict(),
        'message': 'Transcription saved'
    }), 201

# Notes Routes
@app.route('/api/notes', methods=['POST'])
def create_note():
    data = request.json
    user_id = session.get('user_id')
    title = data.get('title')
    content = data.get('content')
    broadcast_id = data.get('broadcast_id')
    transcription_id = data.get('transcription_id')
    summary = data.get('summary')  # AI-generated summary (placeholder)
    
    note = Note(
        user_id=user_id,
        broadcast_id=broadcast_id,
        transcription_id=transcription_id,
        title=title,
        content=content,
        summary=summary
    )
    
    db.session.add(note)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'note': note.to_dict(),
        'message': 'Note created successfully'
    }), 201

@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    
    if note.user_id != session.get('user_id'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    db.session.delete(note)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Note deleted'}), 200

# Serve static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('../static', filename)

# Serve uploaded files (audio, transcriptions, notes)
@app.route('/uploads/<path:filepath>')
def serve_upload(filepath):
    """Serve uploaded files (audio, transcriptions, notes)"""
    try:
        # Security: Only allow files from uploads directory
        if '..' in filepath or filepath.startswith('/'):
            return jsonify({'error': 'Invalid file path'}), 400
        
        upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
        full_path = os.path.join(upload_dir, filepath)
        
        # Ensure file is within uploads directory
        if not os.path.abspath(full_path).startswith(os.path.abspath(upload_dir)):
            return jsonify({'error': 'Invalid file path'}), 400
        
        if not os.path.exists(full_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_from_directory(upload_dir, filepath)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Serve HTML files (to avoid CORS issues with file:// protocol)
@app.route('/')
def index():
    return send_from_directory('../theme', 'login .html')

@app.route('/<path:filename>')
def serve_html(filename):
    if filename.endswith('.html'):
        return send_from_directory('../theme', filename)
    return send_from_directory('../theme', filename)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)


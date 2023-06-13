#!/usr/bin/env python3

from flask import request, make_response, session
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from config import app, db, api
from datetime import datetime, timedelta
from models import Student, Teacher, Lesson, Enrollment, Feedback, Payment

class Signup(Resource):
    def post(self):
        user_input = request.get_json()
        required_fields = ['username', 'email', 'first_name', 'last_name', 'password']
        fields = {field: user_input.get(field) for field in required_fields}

        if any(value is None for value in fields.values()):
            return {'error': 'username, email, first name, last name, and password cannot be empty'}, 400

        role = user_input.get('role')
        bio = user_input.get('bio')

        if not role:
            return {'error': "user's role, teacher or student, must be specified"}, 422

        if role == 'teacher' and bio is None:
            return {'error': 'bio is required for a teacher'}, 400

        try:
            fields.pop('password')
            if role == 'teacher':
                user = Teacher(**fields, bio=bio)

            elif role == 'student':
                user = Student(**fields)

            user.password_hash = user_input.get('password')
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            session['role'] = role
            return user.to_dict(), 201

        except IntegrityError:
            return {'error': 'invalid input: username and email needs to be unique'}, 422

class CheckSession(Resource):
    def get(self):
        if session.get('user_id'):
            if session['role'] == 'student':
                 user = Student.query.filter_by(id=session['user_id']).first()
            else:
                user = Teacher.query.filter_by(id=session['user_id']).first()
            return user.to_dict(), 200
        return {'error': '401 Unauthorized'}, 401

class Login(Resource):
    def post(self):
        user_input = request.get_json()
        username = user_input.get('username')
        password = user_input.get('password')
        role = user_input.get('role')

        if not role:
            return {'error': "user's role, teacher or student, must be specified"}, 422

        if role == "teacher":
            user = Teacher.query.filter_by(username=username).first()
        elif role == "student":
            user = Student.query.filter_by(username=username).first()
        if user:
            if user.authenticate(password):
                session['user_id'] = user.id
                session['role'] = role
                return user.to_dict(), 200
            else:
                return {'error': 'Incorrect password'}, 401
        else:
            return {'error': 'User not found'}, 404

class Logout(Resource):
    def delete(self):
        if session.get('user_id'):
            session['user_id'] = None
            session['role'] = None
            return {}, 204
        return {'error': '401 Unauthorized'}, 401

class Teachers(Resource):
    def get(self):
        teachers = Teacher.query.all()
        #MAYBE ADD RULES TO SERIALIZE TO DELETE PRIVATE INFO
        teachers_serialized = [teacher.to_dict() for teacher in teachers]
        return teachers_serialized, 200

class TeacherById(Resource):
    def get(self, id):
        #SIGNED IN TEACHER CAN ONLY GET THEIR OWN INFO
        if session.get('user_id') and session['role'] == 'teacher' and session['user_id'] == id:
            teacher = Teacher.query.filter_by(id=session['user_id']).first()
            return teacher.to_dict(), 200
        return {'error': '401 Unauthorized'}, 401

    #TEACHER EDITING PROFILE
    def patch(self, id):
        if session.get('user_id') and session['role'] == 'teacher' and session['user_id'] == id:
            teacher = Teacher.query.filter_by(id=id).first()
            if teacher:
                for attr in request.get_json():
                    #DOUBLE CHECK DATETIME
                    setattr(teacher, attr, request.json[attr])
                return teacher.to_dict(), 200
            return {'error': 'Teacher not found'}, 404
        return {'error': '401 Unauthorized'}, 401

class StudentById(Resource):
    def get(self, id):
        if session.get('user_id') and (session['role'] == 'teacher' or (session['role'] == 'student' and session['user_id'] == id)):
            student = Student.query.filter_by(id=id).first()
            return student.to_dict(), 200
        else:
            return {'error': '401 Unauthorized'}, 401

    def patch(self, id):
        if session.get('user_id') and session['role'] == 'student' and session['user_id'] == id:
            student = Student.query.filter_by(id=id).first()
            if student:
                disallowed_field = ['lesson_credit']
                data = request.get_json()
                for attr, value in data.items():
                    if attr not in disallowed_field:
                        setattr(student, attr, value)
                    else:
                        return {'error': 'Write access forbidden'}, 403
                return student.to_dict(), 200
            return {'error': 'Student not found'}, 404
        return {'error': '401 Unauthorized'}, 401

class Lessons(Resource):
    def get(self):
        if session.get('user_id'):
            lessons = Lesson.query.all()
            lessons_serialized = [lesson.to_dict() for lesson in lessons]
            return lessons_serialized, 200
        return {'error': '401 Unauthorized'}, 401

    def post(self):
        if session.get('user_id') and session['role'] == 'teacher':
            lesson_data = request.get_json()
            teacher_id = session['user_id']

            required_fields = ['title',
                               'description',
                               'level', 'start',
                               'end', 'capacity',
                               'price']

            fields = {field: lesson_data.get(field) for field in required_fields}

            if any(value is None for value in fields.values()):
                return {'error': 'title, description, level, start time, end time, capacity, and price cannot be empty'}, 400

            #NEED TO VERIFY THE TYPE OF INPUT DATETIME FROM FRONTEND
            start_time = datetime.strptime(lesson_data.get('start'), '%Y-%m-%d %H:%M:%S')
            end_time = datetime.strptime(lesson_data.get('end'), '%Y-%m-%d %H:%M:%S')
            blackout_period_start = start_time - timedelta(hours=3)
            blackout_period_end = start_time + timedelta(hours=3)
            lessons = Lesson.query.filter(
                Lesson.start.between(blackout_period_start, blackout_period_end),
                Lesson.teacher_id == teacher_id
                ).all()

            if lessons:
                return {'error': 'You already have a scheduled lesson within a three-hour window before or after this lesson'}, 409

            try:
                fields['start']=start_time
                fields['end']=end_time

                lesson = Lesson(**fields,
                                teacher_id=teacher_id)
                db.session.add(lesson)
                db.session.commit()
                return lesson.to_dict(), 201
            except IntegrityError:
                return {'error': 'invalid input'}, 422
        return {'error': '401 Unauthorized'}, 401

class LessonById(Resource):
    def get(self, id):
        if session.get('user_id'):
            lesson = Lesson.query.filter_by(id=id).first()
            if lesson:
                return lesson.to_dict(), 200
            return {'error': 'Lesson not found'}, 404
        return {'error': '401 Unauthorized'}, 401

    #TEACHER EDIT A LESSON
    def patch(self, id):
        if session.get('user_id') and session['role'] == 'teacher':
            lesson = Lesson.query.filter_by(id=id, teacher_id=session['user_id']).first()
            if lesson:
                data = request.get_json()
                try:
                    for attr, value in data.items():
                        setattr(lesson, attr, value)
                    return lesson.to_dict(), 200
                except IntegrityError:
                    return {'error': 'invalid input'}, 422
            return {'error': 'Lesson not found'}, 404
        return {'error': '401 Unauthorized'}, 401

    #TEACHER DELETE A LESSON
    def delete(self, id):
        if session.get('user_id') and session['role'] == 'teacher':
            lesson = Lesson.query.filter_by(id=id, teacher_id=session['user_id']).first()
            if lesson:
                try:
                    db.session.delete(lesson)
                    db.session.commit()
                    return {}, 204
                except:
                    return {'error': 'Failed to delete the lesson'}, 500
            return {'error': 'Lesson not found'}, 404
        return {'error': '401 Unauthorized'}, 401

class LessonsByStudentId(Resource):
    def get(self, student_id):
        if session.get('user_id'):
            if session['role'] == 'student':
                pass
            elif session['role'] == 'teacher':
                pass
                lessons = Lesson.query.join(Enrollment).filter()

        return {'error': '401 Unauthorized'}, 401

class LessonsByTeacherId(Resource):
    pass

class EnrollmentsByLessonId(Resource):
    #TEACHER GET ENROLLMENT OF THEIR OWN LESSON
    def get(self, lesson_id):
        if session.get('user_id') and session['role'] == 'teacher':
            lesson = Lesson.query.filter_by(
                teacher_id=session['user_id'],
                id=lesson_id
            ).first()

            if lesson:
                enrollments = lesson.enrollments
                enroll_serialized = [enroll.to_dict() for enroll in enrollments]
                return enroll_serialized, 200
            return {'error': 'Lesson not found'}, 404
        return {'error': '401 Unauthorized'}, 401
     #STUDENT ENROLL IN A LESSON
    def post(self, lesson_id):
        if session.get('user_id') and session['role'] == 'student':
            lesson = Lesson.query.filter_by(
                id=lesson_id
            ).first()
            if lesson:
                new_enrollment = Enrollment(
                    #POTENTIALLY CAN ADD DISCOUNT HERE
                    cost=lesson.price,
                    status=True,
                    student_id=session['user_id'],
                    lesson_id=lesson_id
                )
                try:
                    db.session.add(new_enrollment)
                    db.session.commit()
                    return new_enrollment.to_dict(), 201
                except IntegrityError:
                    return {'error': 'invalid input'}, 422
            return {'error': 'Lesson not found'}, 404
        return {'error': '401 Unauthorized'}, 401

class IndividualEnrollmentByLessonId(Resource):
    def get(self, lesson_id, enrollment_id):
        pass
    def patch(self, lesson_id, enrollment_id):
        pass
    def delete(self, lesson_id, enrollment_id):
        if not session.get('user_id'):
            return {'error': '401 Unauthorized'}, 401

        lesson = Lesson.query.filter_by(id=lesson_id).first()
        if not lesson:
            return {'error': 'Lesson not found'}, 404

        enrollment = next((enrollment for enrollment in lesson.enrollments if enrollment.id == enrollment_id), None)
        if not enrollment:
            return {'error': 'Enrollment not found'}, 404

        user_id = session['user_id']
        role = session['role']

        if role == 'student':
            if enrollment.student_id != user_id:
                return {'error': '401 Unauthorized'}, 401
        elif role == 'teacher':
            if lesson.teacher_id != user_id:
                return {'error': '401 Unauthorized'}, 401

        try:
            #IS IT OKAY TO NOT ACTUALLY DELETE THE RECORD HERE
            enrollment.status = False
            db.session.commit()
        except IntegrityError:
            return {'error': 'Invalid input'}, 422

        return enrollment.to_dict(), 204


api.add_resource(Signup, '/signup', endpoint='signup')
api.add_resource(CheckSession, '/check_session', endpoint='check_session')
api.add_resource(Login, '/login', endpoint='login')
api.add_resource(Logout, '/logout', endpoint='logout')
api.add_resource(Teachers,'/teachers', endpoint='teachers')
api.add_resource(TeacherById, '/teachers/<int:id>', endpoint='teacher_by_id')
api.add_resource(StudentById, '/students/<int:id>', endpoint='student_byid')
api.add_resource(Lessons, '/lessons', endpoint='lessons')
api.add_resource(LessonById, '/lessons/<int:id>', endpoint='lesson_by_id')
api.add_resource(LessonsByStudentId, '/students/<int:student_id>/lessons', endpoint="lesson_by_student_id")
api.add_resource(LessonsByTeacherId, '/teachers/<int:teacher_id>/lessons', endpoint="lesson_by_teacher_id")
api.add_resource(EnrollmentsByLessonId, '/lessons/<int:lesson_id>/enrollments', endpoint='enrollments_by_lesson_id')
api.add_resource(IndividualEnrollmentByLessonId, '/lessons/<int:lesson_id>/enrollments/<int:enrollment_id>', endpoint='individual_enrollment_by_lesson_id')




if __name__ == '__main__':
    app.run(port=5555, debug=True)

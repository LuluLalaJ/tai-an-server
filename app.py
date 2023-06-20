#!/usr/bin/env python3

from flask import request, make_response, session, redirect
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from config import app, db, api, stripe
from datetime import datetime, timedelta, timezone
from models import Student, Teacher, Lesson, Enrollment, Feedback, Payment

YOUR_DOMAIN = 'http://localhost:4000'

class Signup(Resource):
    def post(self):
        user_input = request.get_json()
        required_fields = ['username', 'email', 'first_name', 'last_name', 'password']
        fields = {field: user_input.get(field) for field in required_fields}

        if any(value is None for value in fields.values()):
            return {'error': 'username, email, first name, last name, and password cannot be empty'}, 400

        role = user_input.get('role')

        if not role:
            return {'error': "user's role, teacher or student, must be specified"}, 422

        try:
            fields.pop('password')
            if role == 'teacher':
                user = Teacher(**fields)

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
                try:
                    db.session.add(teacher)
                    db.session.commit()
                except IntegrityError:
                    return {'error': 'invalid input'}, 422
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
                    return {'error': 'Write access forbidden'}, 403
                try:
                    db.session.add(student)
                    db.session.commit()
                except IntegrityError:
                    return {'error': 'invalid input'}, 422
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
            start_time = datetime.fromisoformat(lesson_data.get('start'))
            end_time = datetime.fromisoformat(lesson_data.get('end'))
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
                        if attr in ["start", "end"]:
                            value = datetime.fromisoformat(value)
                        setattr(lesson, attr, value)
                    db.session.add(lesson)
                    db.session.commit()
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
        if not session.get('user_id'):
            return {'error': '401 Unauthorized'}, 401

        user_id = session['user_id']
        role = session['role']

        if role == "student" and user_id != student_id:
            return {'error': '401 Unauthorized'}, 401

        lessons_query = Lesson.query.join(Enrollment).filter(Enrollment.student_id == student_id)

        if role == "teacher":
            lessons_query = lessons_query.filter(Lesson.teacher_id == user_id)

        lessons = lessons_query.all()

        if not lessons:
            return {'error': 'Lesson not found'}, 404

        lessons_serialized = [l.to_dict() for l in lessons]
        return lessons_serialized, 200

class LessonsByTeacherId(Resource):
    def get(self, teacher_id):
        if not session.get('user_id') or session['role'] != "teacher" or session['user_id'] != teacher_id:
            return {'error': '401 Unauthorized'}, 401
        lessons = Lesson.query.filter_by(teacher_id=teacher_id).all()
        if not lessons:
            return {'error': 'Lesson not found'}, 404

        lessons_serialized = [l.to_dict() for l in lessons]
        return lessons_serialized, 200

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
     #NEED TO MAKE SURE STUDENT IS NOT ALREADY IN THE CLASS
    def post(self, lesson_id):
        if session.get('user_id') and session['role'] == 'student':
            lesson = Lesson.query.filter_by(
                id=lesson_id
            ).first()
            student = Student.query.filter_by(
                id=session['user_id']
            ).first()
            if lesson:
                if student.lesson_credit < lesson.price:
                    return  {'error': 'Insufficient credit'}, 400

                status = "waitlisted" if lesson.is_full else "registered"
                new_enrollment = Enrollment(
                    # POTENTIALLY CAN ADD DISCOUNT HERE
                    cost=lesson.price,
                    status=status,
                    student_id=session['user_id'],
                    lesson_id=lesson_id
                )
                lesson.update_is_full()
                student.lesson_credit = student.lesson_credit - lesson.price
                try:
                    db.session.add(new_enrollment)
                    db.session.add(student)
                    db.session.commit()
                    return new_enrollment.to_dict(), 201
                except IntegrityError:
                    return {'error': 'invalid input'}, 422
            return {'error': 'Lesson not found'}, 404
        return {'error': '401 Unauthorized'}, 401

class IndividualEnrollmentByLessonId(Resource):
    def get(self, lesson_id, enrollment_id):
        pass

        # DOUBLE CHECK PATCH REQUEST
    def patch(self, lesson_id, enrollment_id):
        role = session['role']
        if not session.get('user_id') or (role == 'student'):
            return {'error': '401 Unauthorized'}, 401

        lesson = Lesson.query.filter_by(id=lesson_id).first()
        if not lesson:
            return {'error': 'Lesson not found'}, 404

        enrollment = next((enrollment for enrollment in lesson.enrollments if enrollment.id == enrollment_id), None)
        if not enrollment:
            return {'error': 'Enrollment not found'}, 404

        user_id = session['user_id']
        if lesson.teacher_id != user_id:
            return {'error': '401 Unauthorized'}, 401
        data = request.get_json()
        try:
            allowed_fields = ['cost', 'status', 'comment']
            for attr, value in data.items():
                if attr in allowed_fields:
                    if attr == 'status' and value not in ['registered', 'waitlisted']:
                        return {'error': 'Invalid input'}, 422
                    if attr == 'status' and value == 'registered' and lesson.is_full:
                        value = "waitlisted"
                    setattr(enrollment, attr, value)
            lesson.update_is_full()  # Check and update is_full attribute
            db.session.commit()
            return enrollment.to_dict(), 200
        except IntegrityError:
            return {'error': 'Invalid input'}, 422

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
            try:
                student = enrollment.student
                student.lesson_credit += lesson.price
                db.session.delete(enrollment)  # Delete the enrollment
                lesson.update_is_full()
                db.session.commit()
                return {'message': 'Enrollment deleted'}, 200

            except IntegrityError:
                return {'error': 'Invalid input'}, 422

        elif role == 'teacher':
            if lesson.teacher_id != user_id:
                return {'error': '401 Unauthorized'}, 401
            try:
                student = enrollment.student
                student.lesson_credit += lesson.price
                db.session.delete(enrollment)  # Delete the enrollment
                lesson.update_is_full()  # Check and update is_full attribute
                db.session.commit()
                return {'message': 'Enrollment deleted'}, 200
            except IntegrityError:
                return {'error': 'Invalid input'}, 422

class PaymentsByStudentId(Resource):
    def get(self, student_id):
        if not (session.get['user_id'] or session['role'] == 'student'):
            return {'error': '401 Unauthorized'}, 401

        payments = Payment.query.filter_by(student_id=student_id)
        if not payments:
            return {'eror': 'Payment not found'}, 404

        payments_serialized = [p.to_dict() for p in payments]
        return payments_serialized, 200

class FeedbacksByStudentId(Resource):
    pass

class FeedbacksByLessonId(Resource):
    pass

class FeedbackByStudentAndLessonId(Resource):
    def get(self, student_id, lesson_id):
        if not session.get('user_id'):
            return {'error': '401 Unauthorized'}, 401

        if session['role'] == 'student':
            if session['user_id'] != student_id:
                return {'error': '401 Unauthorized'}, 401
            feedback = Feedback.query.filter_by(student_id=student_id, lesson_id=lesson_id).first()

        if session['role'] == 'teacher':
            lesson = Lesson.query.filter_by(id=lesson_id).first()
            if session['user_id'] != lesson.teacher_id:
                return {'error': '401 Unauthorized'}, 401
            feedback = Feedback.query.filter_by(student_id=student_id, lesson_id=lesson_id).first()

        if feedback:
            return feedback.to_dict(), 200
        else:
            return {'error': 'Feedback not found'}, 404

class FeedbackById(Resource):

    def patch(self, id):
        if not session.get('user_id') or session['role'] == 'student':
            return {'error': '401 Unauthorized'}, 401

        feedback = Feedback.query.filter_by(id=id).first()

        if not feedback:
            return {'error': 'Feedback not found'}, 404

        if session['role'] == 'teacher' and session['user_id'] != feedback.lesson.teacher_id:
                return {'error': '401 Unauthorized'}, 401

        try:
            data = request.get_json()
            for attr, value in data.items():
                if attr != 'message':
                    return {'error': 'Invalid input'}, 422
                setattr(feedback, attr, value)

            db.session.commit()
            return feedback.to_dict(), 200
        except IntegrityError:
            return {'error': 'Invalid input'}, 422

class StudentsByTeacherId(Resource):
    def get(self, teacher_id):
        if not session.get('user_id') or session['role'] != "teacher" or session['user_id'] != teacher_id:
            return {'error': '401 Unauthorized'}, 401
        teacher = Teacher.query.filter_by(id=teacher_id).first()
        if not teacher:
            return {'error': 'teacher not found'}, 404


        # lessons = teacher.lessons
        # students = []
        # for lesson in lessons:
        #     students.extend(lesson.enrollments)

        students = Student.query.join(Enrollment).filter(Enrollment.lesson.has(teacher_id=teacher_id)).all()
        # students = Student.query.join(Student.enrollments).join(Enrollment.lesson).join(Lesson.teacher).filter(Teacher.id == teacher_id).all()

        students_serialized = [s.to_dict() for s in students]

        return students_serialized, 200

class Checkout(Resource):
    def post(self):
        try:
            checkout_session = stripe.checkout.Session.create(
                line_items=[
                    {
                        # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                        'price': 'price_1NL9syFn2n3otckJKJQgP5Nt',
                        'quantity': 1,
                    },
                    {
                        'price': 'price_1NL9scFn2n3otckJ9prL76e4',
                        'quantity': 1,
                    },
                    {
                        'price': 'price_1NL9rpFn2n3otckJfO3TD2NA',
                        'quantity': 1,
                    }
                ],
                mode='payment',
                # success_url=YOUR_DOMAIN + '?success=true',
                # cancel_url=YOUR_DOMAIN + '?canceled=true',
                success_url=YOUR_DOMAIN + '/',
                cancel_url=YOUR_DOMAIN + '/teachers',
            )
        except Exception as e:
            return str(e)

        return redirect(checkout_session.url, code=303)


api.add_resource(Signup, '/signup', endpoint='signup')
api.add_resource(CheckSession, '/check_session', endpoint='check_session')
api.add_resource(Login, '/login', endpoint='login')
api.add_resource(Logout, '/logout', endpoint='logout')
api.add_resource(Teachers,'/teachers', endpoint='teachers')
api.add_resource(TeacherById, '/teachers/<int:id>', endpoint='teacher_by_id')
api.add_resource(StudentsByTeacherId, '/teachers/<int:teacher_id>/students', endpoint='students_by_teacher_id')
api.add_resource(StudentById, '/students/<int:id>', endpoint='student_by_id')
api.add_resource(Lessons, '/lessons', endpoint='lessons')
api.add_resource(LessonById, '/lessons/<int:id>', endpoint='lesson_by_id')
api.add_resource(LessonsByStudentId, '/students/<int:student_id>/lessons', endpoint="lesson_by_student_id")
api.add_resource(LessonsByTeacherId, '/teachers/<int:teacher_id>/lessons', endpoint="lesson_by_teacher_id")
api.add_resource(EnrollmentsByLessonId, '/lessons/<int:lesson_id>/enrollments', endpoint='enrollments_by_lesson_id')
api.add_resource(IndividualEnrollmentByLessonId, '/lessons/<int:lesson_id>/enrollments/<int:enrollment_id>', endpoint='individual_enrollment_by_lesson_id')
api.add_resource(PaymentsByStudentId,'/students/<int:student_id>/payments', endpoint='payments_by_student_id')
api.add_resource(FeedbacksByStudentId, '/students/<int:student_id>/feedbacks', endpoint='feedbacks_by_student_id')
api.add_resource(FeedbacksByLessonId, '/lessons/<int:lesson_id>/feedbacks', endpoint='feedbacks_by_lesson_id')
api.add_resource(FeedbackByStudentAndLessonId, '/students/<int:student_id>/lessons/<int:lesson_id>/feedback', endpoint='feedback_by_student_and_lesson_id')
api.add_resource(FeedbackById, '/feedbacks/<int:id>', endpoint='feedback_by_id')
api.add_resource(Checkout, '/checkout', endpoint="checkout")


if __name__ == '__main__':
    app.run(port=5555, debug=True)

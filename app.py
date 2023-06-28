#!/usr/bin/env python3
from flask import request, make_response, session, redirect, jsonify
import json
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from config import app, db, api
from datetime import datetime, timedelta, timezone
from models import Student, Teacher, Lesson, Enrollment, Feedback, Payment, LessonCreditHistory
import stripe
import os
from dotenv import load_dotenv, find_dotenv
from decimal import Decimal

load_dotenv(find_dotenv())
credit_price = os.getenv('PRICE')
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
stripe.api_version = "2022-11-15"


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
        teachers_serialized = [teacher.to_dict() for teacher in teachers]
        return teachers_serialized, 200

class TeacherById(Resource):
    def get(self, id):
        if session.get('user_id') and session['role'] == 'teacher' and session['user_id'] == id:
            teacher = Teacher.query.filter_by(id=session['user_id']).first()
            return teacher.to_dict(), 200
        return {'error': '401 Unauthorized'}, 401

    def patch(self, id):
        if session.get('user_id') and session['role'] == 'teacher' and session['user_id'] == id:
            teacher = Teacher.query.filter_by(id=id).first()
            if teacher:
                for attr in request.get_json():
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
                    if attr in disallowed_field:
                        return {'error': 'Write access forbidden'}, 403
                    setattr(student, attr, value)
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

    def post(self, lesson_id):
        if not session.get('user_id') or session['role'] != 'student':
            return {'error': '401 Unauthorized'}, 401

        lesson = Lesson.query.filter_by(
            id=lesson_id
        ).first()

        if not lesson:
            return {'error': 'Lesson not found'}, 404

        student_id = session['user_id']
        enrollments = lesson.enrollments
        already_enrolled = any(enrollment.student_id == student_id for enrollment in enrollments)
        if already_enrolled:
            return {'error': 'Already enrolled'}, 400

        student = Student.query.filter_by(
            id=student_id
        ).first()
        if not student:
            return {'error': 'Student not found'}, 404

        if student.lesson_credit < lesson.price:
            return  {'error': 'Insufficient credit'}, 400


        if lesson.is_full:
            status = "waitlisted"
        else:
            status = "registered"
            old_credit = student.lesson_credit
            student.lesson_credit -= lesson.price
            new_credit = student.lesson_credit
            new_lesson_credit_history = LessonCreditHistory(
                old_credit=old_credit,
                new_credit=new_credit,
                student_id=student.id,
                memo="credit deduction after lesson registration"
            )
            db.session.add(new_lesson_credit_history)


        new_enrollment = Enrollment(
            cost=lesson.price,
            status=status,
            student_id=student_id,
            lesson_id=lesson_id
        )
        lesson.update_is_full()

        try:
            db.session.add(new_enrollment)
            db.session.add(student)
            db.session.commit()
            return new_enrollment.to_dict(), 201
        except IntegrityError:
            return {'error': 'invalid input'}, 422

class IndividualEnrollmentByLessonId(Resource):
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

        student_id = enrollment.student_id
        student = Student.query.filter_by(id=student_id).first()
        if not student:
            return {'error': 'Student not found'}, 404

        try:
            allowed_fields = ['cost', 'status', 'comment']
            for attr, value in data.items():
                if attr in allowed_fields:
                    if attr == 'status' and value not in ['registered', 'waitlisted']:
                        return {'error': 'Invalid input'}, 422
                    if attr == 'status' and value == 'registered' and lesson.is_full:
                        value = "waitlisted"
                    if attr == 'status' and not lesson.is_full:
                        if value == 'registered':
                            old_credit = student.lesson_credit
                            if old_credit < enrollment.cost:
                                return  {'error': 'Insufficient credit'}, 400
                            else:
                                student.lesson_credit -= enrollment.cost
                                new_credit = student.lesson_credit
                                new_lesson_credit_history = LessonCreditHistory(
                                    old_credit=old_credit,
                                    new_credit=new_credit,
                                    student_id=student.id,
                                    memo="credit deduction after being added to registered list"
                                )
                                db.session.add(new_lesson_credit_history)

                        if value == 'waitlisted':
                            old_credit = student.lesson_credit
                            student.lesson_credit += enrollment.cost
                            new_credit = student.lesson_credit
                            new_lesson_credit_history = LessonCreditHistory(
                                old_credit=old_credit,
                                new_credit=new_credit,
                                student_id=student.id,
                                memo="credit refund after being removed to waitlist"
                            )
                            db.session.add(new_lesson_credit_history)
                    setattr(enrollment, attr, value)
            lesson.update_is_full()
            db.session.add(student)
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
                if enrollment.status == "registered":
                    old_credit = student.lesson_credit
                    student.lesson_credit += lesson.price
                    new_credit = student.lesson_credit
                    new_lesson_credit_history = LessonCreditHistory(
                        old_credit=old_credit,
                        new_credit=new_credit,
                        student_id=student.id,
                        memo="credit refund after lesson cancellation"
                    )
                    db.session.add(new_lesson_credit_history)
                db.session.delete(enrollment)
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
                if enrollment.status == "registered":
                    old_credit = student.lesson_credit
                    student.lesson_credit += lesson.price
                    new_credit = student.lesson_credit
                    new_lesson_credit_history = LessonCreditHistory(
                        old_credit=old_credit,
                        new_credit=new_credit,
                        student_id=student.id,
                        memo="credit refund after lesson cancellation"
                    )
                    db.session.add(new_lesson_credit_history)
                db.session.delete(enrollment)
                lesson.update_is_full()
                db.session.commit()
                return {'message': 'Enrollment deleted'}, 200
            except IntegrityError:
                return {'error': 'Invalid input'}, 422

class PaymentsByStudentId(Resource):
    def get(self, student_id):
        if not (session.get('user_id') or  session['role'] == 'student'):
            return {'error': '401 Unauthorized'}, 401

        payments = Payment.query.filter_by(student_id=student_id).all()
        if not payments:
            return {'eror': 'Payment not found'}, 404

        payments_serialized = [p.to_dict() for p in payments]
        return payments_serialized, 200

class LessonCreditHistoryByStudentId(Resource):
    def get(self, student_id):
        if not (session.get('user_id') or  session['role'] == 'student'):
            return {'error': '401 Unauthorized'}, 401

        records = LessonCreditHistory.query.filter_by(student_id=student_id).all()
        if not records:
            return {'eror': 'History records not found'}, 404

        records_serialized = [c.to_dict() for c in records]
        return records_serialized, 200

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

        students = Student.query.join(Enrollment).filter(Enrollment.lesson.has(teacher_id=teacher_id)).all()
        students_serialized = [s.to_dict() for s in students]

        return students_serialized, 200

@app.route('/config', methods=['GET'])
def get_publishable_key():
    return jsonify({
      'publicKey': os.getenv('STRIPE_PUBLISHABLE_KEY'),
    })

@app.route('/checkout-session', methods=['GET'])
def get_checkout_session():
    id = request.args.get('sessionId')
    checkout_session = stripe.checkout.Session.retrieve(id)
    return jsonify(checkout_session)

# stripe listen --forward-to localhost:5555/webhook
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    data = request.get_json()
    quantity = data.get('quantity')
    price = data.get('price')
    metadata=data.get('metadata')
    domain_url = os.getenv('DOMAIN')

    try:
        checkout_session = stripe.checkout.Session.create(
            success_url=domain_url + '/completion?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=domain_url + '/canceled',
            mode='payment',
            metadata=metadata,
            line_items=[{
                'price': price,
                'quantity': quantity,
            }],
        )
        return jsonify({"url": checkout_session.url}), 200

    except Exception as e:
        return jsonify(error=str(e)), 403



@app.route('/webhook', methods=['POST'])
def webhook():
    event = None
    payload = request.data
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        event = json.loads(payload)
    except:
        print('⚠️  Webhook error while parsing basic request.' + str(e))
        return jsonify(success=False)
    if endpoint_secret:
        sig_header = request.headers.get('stripe-signature')
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except stripe.error.SignatureVerificationError as e:
            print('⚠️  Webhook signature verification failed.' + str(e))
            return jsonify(success=False)

    if event and event['type'] == 'checkout.session.completed':

        checkout_session = event['data']['object']
        paid = checkout_session["payment_status"] == "paid"
        if paid:
            amount = checkout_session['amount_total']
            id = checkout_session['metadata']['id']
            new_payment = Payment(
                lesson_credit=amount/100,
                student_id=id,
            )
            student = Student.query.filter_by(id=id).first()
            old_credit = student.lesson_credit
            student.lesson_credit += Decimal(str(amount/100))
            new_credit = student.lesson_credit

            new_lesson_credit_history = LessonCreditHistory(
                old_credit=old_credit,
                new_credit=new_credit,
                student_id=id,
                memo="purchase credit"
            )
            db.session.add(new_lesson_credit_history)
            db.session.add(new_payment)
            db.session.commit()
    elif event['type'] == 'payment_method.attached':
        payment_method = event['data']['object']
    else:
        print('Unhandled event type {}'.format(event['type']))

    return jsonify(success=True)


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
api.add_resource(LessonCreditHistoryByStudentId,'/students/<int:student_id>/lessoncredithistory', endpoint='lessoncredithistory_by_student_id')
api.add_resource(FeedbackByStudentAndLessonId, '/students/<int:student_id>/lessons/<int:lesson_id>/feedback', endpoint='feedback_by_student_and_lesson_id')
api.add_resource(FeedbackById, '/feedbacks/<int:id>', endpoint='feedback_by_id')


if __name__ == '__main__':
    app.run(port=5555, debug=True)

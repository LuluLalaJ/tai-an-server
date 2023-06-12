#!/usr/bin/env python3

from flask import request, make_response, session
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from config import app, db, api
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
            return {}, 204
        return {'error': '401 Unauthorized'}, 401



api.add_resource(Signup, '/signup', endpoint='signup')
api.add_resource(CheckSession, '/check_session', endpoint='check_session')
api.add_resource(Login, '/login', endpoint='login')
api.add_resource(Logout, '/logout', endpoint='logout')

if __name__ == '__main__':
    app.run(port=5555, debug=True)

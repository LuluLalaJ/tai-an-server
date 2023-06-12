#!/usr/bin/env python3

from flask import request, make_response, session
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from config import app, db, api
from models import db


if __name__ == '__main__':
    app.run(port=5555, debug=True)

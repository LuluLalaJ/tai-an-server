from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm import validates
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_serializer import SerializerMixin
from config import db, bcrypt

class Student(db.Model, SerializerMixin):
    __tablename__ = "students"

    serialize_rules = ("-enrollments.lesson", "-feedbacks")

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    _password_hash = db.Column(db.String)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    avatar = db.Column(db.String)
    lesson_credit = db.Column(db.Numeric(8, 2), default=0)
    phone = db.Column(db.String)
    address_line1 = db.Column(db.String)
    address_line2 = db.Column(db.String)
    city = db.Column(db.String)
    state = db.Column(db.String)
    country = db.Column(db.String)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

    enrollments = db.relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    feedbacks = db.relationship("Feedback", back_populates="student", cascade="all, delete-orphan")
    lessons = association_proxy('enrollments', 'lesson')

    @hybrid_property
    def password_hash(self):
        raise AttributeError("Password hashes can't be viewed")

    @password_hash.setter
    def password_hash(self, password):
        password_hash = bcrypt.generate_password_hash(password.encode('utf-8') )
        self._password_hash = password_hash.decode('utf-8')

    def authenticate(self, password):
        return bcrypt.check_password_hash(
            self._password_hash, password.encode('utf-8')
        )
    def __repr__(self):
        return f'<Student: {self.id} {self.first_name} {self.last_name}>'


class Teacher(db.Model, SerializerMixin):
    __tablename__ = "teachers"

    serialize_rules = ("-lessons.students",)

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    _password_hash = db.Column(db.String)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    avatar = db.Column(db.String)
    teaching_since = db.Column(db.DateTime)
    bio = db.Column(db.String, nullable=False)
    phone = db.Column(db.String)
    address_line1 = db.Column(db.String)
    address_line2 = db.Column(db.String)
    city = db.Column(db.String)
    state = db.Column(db.String)
    country = db.Column(db.String)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

    lessons = db.relationship("Lesson", back_populates="teacher", cascade="all, delete-orphan")

    @hybrid_property
    def password_hash(self):
        raise AttributeError("Password hashes can't be viewed")

    @password_hash.setter
    def password_hash(self, password):
        password_hash = bcrypt.generate_password_hash(password.encode('utf-8'))
        self._password_hash = password_hash.decode('utf-8')

    def authenticate(self, password):
        return bcrypt.check_password_hash(self._password_hash, password.encode('utf-8'))

    def __repr__(self):
        return f'<Teacher: {self.id} {self.first_name} {self.last_name}>'

class Lesson(db.Model, SerializerMixin):
    __tablename__ = "lessons"

    serialize_rules = ("-enrollments.student", "-feedbacks")

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    level = db.Column(db.Integer, nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(8, 2), default=0)

    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'))
    teacher = db.relationship("Teacher", back_populates="lessons")

    enrollments = db.relationship("Enrollment", back_populates="lesson", cascade="all, delete-orphan")
    feedbacks = db.relationship("Feedback", back_populates="lesson", cascade="all, delete-orphan")

    @validates('level')
    def check_level(self, key, level):
        if 1 <= level <= 5:
            return level
        raise ValueError('lesson level must be between 1 and 5')

    @validates('capacity')
    def check_capacity(self, key, capacity):
        if 1 <= capacity <= 5:
            return capacity
        raise ValueError('lesson capacity must be between 1 and 5')

    @validates('price')
    def check_price(self, key, price):
        if price >= 0:
            return price
        raise ValueError('lesson price must be positive')

    @validates('end')
    def validate_end(self, key, end):
        if end > self.start:
            return end
        raise ValueError("lesson end datetime must be later than start datetime")

    def __repr__(self):
        return f'<Lesson: {self.id} {self.title}>'

class Enrollment(db.Model, SerializerMixin):
    __tablename__ = "enrollments"

    serialize_rules = ("-student", "-lesson")

    id = db.Column(db.Integer, primary_key=True)
    cost = db.Column(db.Numeric(8, 2), default=0)
    status = db.Column(db.Boolean)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))

    student = db.relationship("Student", back_populates="enrollments")
    lesson = db.relationship("Lesson", back_populates="enrollments")

    @validates('cost')
    def check_cost(self, key, cost):
        if cost >= 0:
            return cost
        raise ValueError('lesson cost must be positive')

    def __repr__(self):
        return f'<Enrollment: {self.id} {self.lesson.title}>'

class Feedback(db.Model, SerializerMixin):
    __tablename__ = "feedbacks"

    serialize_rules = ("-student", "-lesson")

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String, default="No feedback provided yet!")

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))

    student = db.relationship("Student", back_populates="feedbacks")
    lesson = db.relationship("Lesson", back_populates="feedbacks")

    def __repr__(self):
        return f'<Feedback: {self.id} for {self.student}>'

class Payment(db.Model, SerializerMixin):
    __tablename__ = "payments"

    serialize_rules = ("-student",)

    id = db.Column(db.Integer, primary_key=True)
    lesson_credit = db.Column(db.Numeric(8, 2), default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))

    student = db.relationship("Student")

    @validates('lesson_credit')
    def check_credit(self, key, credit):
        if credit >= 0:
            return credit
        raise ValueError('lesson credit must be positive')

    def __repr__(self):
        return f'<Payment: {self.id} for ${self.lesson_credit}>'

from datetime import datetime, timedelta
import random
from faker import Faker
from app import app
from config import db
from models import Student, Teacher, Lesson, Enrollment, Feedback, Payment
from assets.avatars import student_avatars, teacher_avatars
fake = Faker()


# Clear data from students table
def clear_students():
    Student.query.delete()
    db.session.commit()

# Clear data from teachers table
def clear_teachers():
    Teacher.query.delete()
    db.session.commit()

# Clear data from lessons table
def clear_lessons():
    Lesson.query.delete()
    db.session.commit()

# Clear data from enrollments table
def clear_enrollments():
    Enrollment.query.delete()
    db.session.commit()

# Clear data from feedbacks table
def clear_feedbacks():
    Feedback.query.delete()
    db.session.commit()

# Clear data from payments table
def clear_payments():
    Payment.query.delete()
    db.session.commit()

# Seed fake data for students
def seed_students(num_students):
    for i in range(num_students):
        username = fake.unique.user_name()
        email = fake.unique.email()
        password = username + "hello"
        student = Student(
            username=username,
            email=email,
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            avatar=student_avatars[i],
            lesson_credit=random.randint(0, 300),
            phone="123-456-7890",
            address_line1=fake.street_address(),
            address_line2=fake.secondary_address(),
            city=fake.city(),
            state=fake.state(),
            country=fake.country(),
        )
        student.password_hash=password
        db.session.add(student)

    db.session.commit()

# Seed fake data for teachers
def seed_teachers(num_teachers):
    for i in range(num_teachers):
        username = fake.unique.first_name()
        email = fake.unique.email()
        password = username + "hello"
        teacher = Teacher(
            username=username,
            email=email,
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            avatar=teacher_avatars[i],
            teaching_since=fake.date_this_century(),
            bio=fake.text(),
            phone="123-456-7890",
            address_line1=fake.street_address(),
            address_line2=fake.secondary_address(),
            city=fake.city(),
            state=fake.state(),
            country=fake.country(),
        )
        teacher.password_hash=password
        db.session.add(teacher)

    db.session.commit()

# Seed fake data for lessons
def seed_lessons(num_lessons, num_teachers):
    for _ in range(num_lessons):
        title = fake.catch_phrase()
        description = fake.text()
        level = fake.random_int(min=1, max=5)

        # Generate start and end datetime
        start = fake.date_time_between(start_date="-1M", end_date="+1M")
        hour = random.randint(9, 17)
        start = start.replace(hour=hour, minute=0, second=0)
        duration = timedelta(hours=fake.random_int(min=1, max=3))
        end = start + duration

        teacher_id = fake.random_int(min=1, max=num_teachers)
        teacher = Teacher.query.filter_by(id=teacher_id).first()

        lesson = Lesson(
            title=title,
            description=description,
            level=level,
            start=start,
            end=end,
            capacity=fake.random_int(min=1, max=5),
            price=random.randint(30, 50),
            teacher=teacher
        )
        db.session.add(lesson)

    db.session.commit()


# Seed fake data for enrollments
# NEED TO MAKE SURE STUDENTS WHO HAVE ALREADY REGISTER/ENROLL SHOULD NOT REGISTE/ENROLL THE SAME CLASS AGAIN
def seed_enrollments(num_enrollments, num_students, num_lessons):
    students = Student.query.limit(num_students).all()
    lessons = Lesson.query.limit(num_lessons).all()


    for _ in range(num_enrollments):
        student = fake.random_element(students)
        lesson = fake.random_element(lessons)

        if lesson.is_full:
            status = 'waitlisted'
        else:
            status = 'registered'

        enrollment = Enrollment(
            cost=lesson.price,
            status=status,
            student=student,
            lesson=lesson
        )

        db.session.add(enrollment)
        lesson.update_is_full()

    db.session.commit()

# Seed fake data for feedbacks
def seed_feedbacks(num_feedbacks, num_students, num_lessons):
    students = Student.query.limit(num_students).all()
    lessons = Lesson.query.limit(num_lessons).all()

    for _ in range(num_feedbacks):
        student = fake.random_element(students)
        lesson = fake.random_element(lessons)
        feedback = Feedback(
            message=fake.text(),
            student=student,
            lesson=lesson
        )
        db.session.add(feedback)

    db.session.commit()

# Seed fake data for payments
# def seed_payments(num_payments, num_students):
#     students = Student.query.limit(num_students).all()
#     amount = [50, 100, 150, 200, 250, 300]

#     for _ in range(num_payments):
#         student = fake.random_element(students)
#         payment = Payment(
#             lesson_credit=random.choice(amount),
#             student=student
#         )
#         db.session.add(payment)

#     db.session.commit()

# Set the number of fake records you want to seed for each model
NUM_STUDENTS = 10
NUM_TEACHERS = 6
NUM_LESSONS = 30
NUM_ENROLLMENTS = 30
NUM_FEEDBACKS = 30
NUM_PAYMENTS = 10


if __name__ == '__main__':

    with app.app_context():
        # Seed fake data for each model
        clear_students()
        clear_teachers()
        clear_lessons()
        clear_enrollments()
        clear_feedbacks()
        clear_payments()
        seed_students(NUM_STUDENTS)
        seed_teachers(NUM_TEACHERS)
        seed_lessons(NUM_LESSONS, NUM_TEACHERS)
        seed_enrollments(NUM_ENROLLMENTS, NUM_STUDENTS, NUM_LESSONS)
        seed_feedbacks(NUM_FEEDBACKS, NUM_STUDENTS, NUM_LESSONS)
        # seed_payments(NUM_PAYMENTS, NUM_STUDENTS)

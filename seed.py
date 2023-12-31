from datetime import datetime, timedelta
import random
from faker import Faker
from app import app
from config import db
from models import Student, Teacher, Lesson, Enrollment, Feedback, Payment, LessonCreditHistory
from assets.avatars import student_avatars, teacher_avatars
from assets.bio import bio_samples
from assets.feedback import comments
from assets.titles import lesson_titles
from assets.lesson_content import lesson_content
fake = Faker()

def clear_students():
    Student.query.delete()
    db.session.commit()

def clear_teachers():
    Teacher.query.delete()
    db.session.commit()

def clear_lessons():
    Lesson.query.delete()
    db.session.commit()

def clear_enrollments():
    Enrollment.query.delete()
    db.session.commit()

def clear_feedbacks():
    Feedback.query.delete()
    db.session.commit()

def clear_payments():
    Payment.query.delete()
    db.session.commit()

def clear_credit_history():
    LessonCreditHistory.query.delete()
    db.session.commit()

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

def seed_teachers(num_teachers):
    for i in range(num_teachers):
        username = fake.unique.user_name()
        email = fake.unique.email()
        password = username + "hello"
        teacher = Teacher(
            username=username,
            email=email,
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            avatar=teacher_avatars[i],
            teaching_since=fake.date_this_century(),
            bio=bio_samples[i],
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

def seed_lessons(num_lessons, num_teachers):
    for i in range(num_lessons):
        title = lesson_titles[(i%30)]
        description = lesson_content[(i%30)]
        level = fake.random_int(min=1, max=5)

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

def seed_enrollments(num_enrollments, num_students, num_lessons):
    students = Student.query.limit(num_students).all()
    lessons = Lesson.query.limit(num_lessons).all()

    current_date = datetime.now()

    for i in range(num_enrollments):
        student = fake.random_element(students)
        lesson = fake.random_element(lessons)
        current_date = datetime.now()
        day_after_tomorrow = current_date + timedelta(days=2)

        if Enrollment.query.filter_by(student=student, lesson=lesson).first():
            continue

        if lesson.is_full:
            enrollment = Enrollment(
                cost=lesson.price,
                status='waitlisted',
                student=student,
                lesson=lesson,
            )


        else:
            if lesson.start > day_after_tomorrow:
                comment = "No feedback provided yet!"
            else:
                comment = comments[(i%60)]

            enrollment = Enrollment(
                cost=lesson.price,
                status='registered',
                student=student,
                lesson=lesson,
                comment=comment
            )

        db.session.add(enrollment)
        lesson.update_is_full()

    db.session.commit()

NUM_STUDENTS = 10
NUM_TEACHERS = 9
NUM_LESSONS = 45
NUM_ENROLLMENTS = 150
NUM_FEEDBACKS = 30

if __name__ == '__main__':

    with app.app_context():
        clear_students()
        clear_teachers()
        clear_lessons()
        clear_enrollments()
        clear_feedbacks()
        clear_payments()
        clear_credit_history()
        seed_students(NUM_STUDENTS)
        seed_teachers(NUM_TEACHERS)
        seed_lessons(NUM_LESSONS, NUM_TEACHERS)
        seed_enrollments(NUM_ENROLLMENTS, NUM_STUDENTS, NUM_LESSONS)

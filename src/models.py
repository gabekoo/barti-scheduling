from src.extensions import db
from flask import jsonify
from datetime import timedelta

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)

    def __init__(self, name):
        self.name = name

    def list_appointments(self, start_time, end_time):
        return Appointment.query.filter(
            Appointment.doctor_id == self.id,
            Appointment.start_time <= end_time, 
            Appointment.end_time >= start_time).all()

class WorkingHours(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)
    start_hour = db.Column(db.Integer, nullable=False)
    end_hour = db.Column(db.Integer, nullable=False)

    def __init__(self, doctor, day_of_week, start_hour, end_hour):
        self.doctor_id = doctor.id
        self.day_of_week = day_of_week
        self.start_hour = start_hour
        self.end_hour = end_hour

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    patient_name = db.Column(db.String, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

    def __init__(self, doctor, patient_name, start_time, length_minutes):
        self.doctor_id = doctor.id
        self.patient_name = patient_name
        self.start_time = start_time
        self.length_minutes = length_minutes
        self.end_time = start_time + timedelta(minutes=length_minutes)

    def update_start_time(self, start_time):
        self.start_time = start_time
        self.end_time = start_time + timedelta(minutes=self.length_minutes)

    @staticmethod
    def list_appointments(doctor_id, start_time, end_time):
        return Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.start_time <= end_time, 
            Appointment.end_time >= start_time)

    def has_conflicts(self):
        doctor = Doctor.query.filter_by(id=self.doctor_id).first()
        return any(doctor.list_appointments(self.start_time, self.end_time))

    def within_working_hours(self):
        day_of_week = self.start_time.isoweekday()
        doctor_working_hours = WorkingHours.query.filter(WorkingHours.doctor_id == self.doctor_id, WorkingHours.day_of_week == day_of_week)
        if not any(doctor_working_hours):
            return False
        doctor_working_hours = doctor_working_hours.first()
        return doctor_working_hours.start_hour <= self.start_time.hour and doctor_working_hours.end_hour >= self.end_time.hour

    def pretty_print(self):
        return {
            'id': self.id, 
            'doctor': Doctor.query.filter_by(id=self.doctor_id).first().name,
            'patient': self.patient_name,
            'startTime': self.start_time.isoformat(), 
            'endTime': self.end_time.isoformat()
        }

    def json(self):
        return jsonify(self.pretty_print())


class DummyModel(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    value = db.Column(db.String, nullable=False)

    def json(self) -> str:
        """
        :return: Serializes this object to JSON
        """
        return jsonify({'id': self.id, 'value': self.value})

from flask import Blueprint, jsonify, request
from http import HTTPStatus
from src.extensions import db
from src.models import DummyModel, Appointment, Doctor, WorkingHours
from webargs import fields
from webargs.flaskparser import use_args
from datetime import datetime, timedelta

home = Blueprint('/', __name__)


# Helpful documentation:
# https://webargs.readthedocs.io/en/latest/framework_support.html
# https://flask.palletsprojects.com/en/2.0.x/quickstart/#variable-rules


@home.route('/')
def index():
    return {'data': 'OK'}

@home.route('/test')
def test():
    foo = Doctor.query.all()
    return jsonify([f.name for f in foo])

@home.route('/create_appointment', methods=['POST'])
@use_args({'doctorName': fields.String(),
           'patientName': fields.String(),
           'startTime': fields.String(),
           'lengthMinutes': fields.Integer()})
def create_appointment(args):
    try:
        doctor_name = args.get('doctorName')
        patient_name = args.get('patientName')
        start_time = args.get('startTime')
        length_minutes = args.get('lengthMinutes')
        doctor = Doctor.query.filter_by(name=doctor_name).first()
        if not (doctor_name and patient_name and start_time and length_minutes and doctor):
            return jsonify('Missing paramters. doctorName, patientName, startTime, and lengthMinutes are required.'), HTTPStatus.BAD_REQUEST
        start_time = datetime.fromisoformat(start_time)
        new_appointment = Appointment(doctor, patient_name, start_time, length_minutes)
        if not new_appointment.has_conflicts() and new_appointment.is_within_working_hours():
            db.session.add(new_appointment)
            db.session.commit()
            return new_appointment.json()
        return jsonify('There are conflicts with the given appointment time for the doctor you requested.'), HTTPStatus.BAD_REQUEST
    except Exception:
        return jsonify('An error ocurred while creating the appointment.'), HTTPStatus.INTERNAL_SERVER_ERROR


@home.route('/doctor/<doctor_name>/appointments', methods=['GET'])
def get_appointments(doctor_name):
    try:
        start_time = request.args.get('startTime')
        end_time = request.args.get('endTime')
        if not (start_time and end_time and doctor_name):
            return jsonify('Missing paramters. doctorName, startTime, and endTime are required.'), HTTPStatus.BAD_REQUEST
        start_time = datetime.fromisoformat(start_time)
        end_time = datetime.fromisoformat(end_time)
        doctor = Doctor.query.filter_by(name=doctor_name).first()
        return jsonify([a.pretty_print() for a in doctor.list_appointments(start_time, end_time)])
    except Exception:
        return jsonify('An error ocurred while fetching appointments.'), HTTPStatus.INTERNAL_SERVER_ERROR

@home.route('/create_earliest_appointment', methods=['POST'])
@use_args({'doctorName': fields.String(),
           'patientName': fields.String(),
           'lengthMinutes': fields.Integer()})
def create_earliest_appointment(args):
    try:
        doctor_name = args.get('doctorName')
        patient_name = args.get('patientName')
        length_minutes = args.get('lengthMinutes')
        doctor = Doctor.query.filter_by(name=doctor_name).first()
        if not (doctor_name and patient_name and length_minutes and doctor):
            return jsonify('Missing paramters. doctorName, patientName, and lengthMinutes are required'), HTTPStatus.BAD_REQUEST
        working_hours = WorkingHours.query.filter_by(doctor_id=doctor.id).all()
        day_working_hours_map = {wh.day_of_week: wh for wh in working_hours}
        # Start by trying to make an appointment immediately
        new_start_time = datetime.today()
        new_appointment = Appointment(doctor, patient_name, new_start_time, length_minutes)
        # Find all future existing appointments, plus ones that might be happening right now
        existing_appointments = Appointment.query.filter(
            Appointment.doctor_id == doctor.id, 
            (Appointment.start_time > new_start_time) | 
            ((Appointment.start_time < new_start_time) & (Appointment.end_time > new_start_time))).all()
        existing_appointments.sort(key=lambda x: x.start_time)
        ensure_appointment_is_within_working_hours(new_appointment, day_working_hours_map)
        # Check the appointment we want to make against each scheduled appointment in order until we find an open time slot
        for app in existing_appointments:
            # If the appointment we want to make conflicts with the next existing appointment
            if new_appointment.start_time <= app.end_time and new_appointment.end_time >= app.start_time:
                # Update the appointment to start as soon as the conflicting appointment ends
                new_appointment.update_start_time(app.end_time)
                # If our new appointment is not within working hours, bump it to the next day
                ensure_appointment_is_within_working_hours(new_appointment, day_working_hours_map)
            else:
                break
        db.session.add(new_appointment)
        db.session.commit()
        return new_appointment.json()
    except Exception:
        return jsonify('An error ocurred while creating the appointment.'), HTTPStatus.INTERNAL_SERVER_ERROR

def ensure_appointment_is_within_working_hours(appointment, day_working_hours_map):
    appointment_day_of_week = appointment.start_time.isoweekday()
    # If the appointment is not on a day when the doctor is working, or outside of 
    # the working hours for that day
    if appointment.end_time.isoweekday() not in day_working_hours_map.keys() or \
            appointment.end_time.hour >= day_working_hours_map[appointment_day_of_week].end_hour or \
            appointment.end_time.hour < day_working_hours_map[appointment_day_of_week].start_hour:
                # Move the appointment to the next day that the doctor is working
                new_start_time = appointment.start_time + timedelta(days=1)
                while new_start_time.isoweekday() not in day_working_hours_map.keys():
                    new_start_time += timedelta(days=1)
                # Set the hour of the appointment to the first hour that the doctor is working that day
                new_start_time = new_start_time.replace(hour=day_working_hours_map[new_start_time.isoweekday()].start_hour, minute=0)
                appointment.update_start_time(new_start_time)

@home.route('/dummy_model/<id_>', methods=['GET'])
def dummy_model(id_):
    record = DummyModel.query.filter_by(id=id_).first()
    if record is not None:
        return record.json()
    else:
        return jsonify(None), HTTPStatus.NOT_FOUND


@home.route('/dummy_model', methods=['POST'])
@use_args({'value': fields.String()})
def dummy_model_create(args):
    new_record = DummyModel(value=args.get('value'))
    db.session.add(new_record)
    db.session.commit()
    return new_record.json()

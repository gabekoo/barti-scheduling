from http import HTTPStatus
from datetime import datetime
from unittest import mock

class FakeDateTime(datetime):
    "A fake replacement for datetime that can be mocked for testing."
    def __new__(cls, *args, **kwargs):
        return datetime.__new__(datetime, *args, **kwargs)

def test_create_new_appointment(client):
    response = client.post('/create_appointment', json={
        "doctorName": "Strange", 
        "patientName": "Peter", 
        "startTime": "2023-06-20 09:00:00", 
        "lengthMinutes": 60}
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json == {"doctor":"Strange", "endTime":"2023-06-20T10:00:00", "id":1, "patient":"Peter", "startTime":"2023-06-20T09:00:00"}

def test_do_not_create_conflicting_appointment(client):
    client.post('/create_appointment', json={
        "doctorName": "Strange", 
        "patientName": "Peter", 
        "startTime": "2023-06-20 09:00:00", 
        "lengthMinutes": 60}
    )
    response = client.post('/create_appointment', json={
        "doctorName": "Strange", 
        "patientName": "Peter", 
        "startTime": "2023-06-20 09:30:00", 
        "lengthMinutes": 60}
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json == 'There are conflicts with the given appointment time for the doctor you requested.'

def test_do_not_create_appointment_outside_working_hours(client):
    response = client.post('/create_appointment', json={
        "doctorName": "Strange", 
        "patientName": "Peter", 
        "startTime": "2023-06-20 20:00:00", 
        "lengthMinutes": 60}
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json == 'There are conflicts with the given appointment time for the doctor you requested.'

def test_do_not_create_appointment_with_missing_parameters(client):
    response = client.post('/create_appointment', json={
        "doctorName": "Strange", 
        "patientName": "Peter", 
        "lengthMinutes": 60}
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json == 'Missing paramters. doctorName, patientName, startTime, and lengthMinutes are required.'

def test_get_appointments(client):
    client.post('/create_appointment', json={
        "doctorName": "Strange", 
        "patientName": "Peter", 
        "startTime": "2023-06-20 09:00:00", 
        "lengthMinutes": 60}
    )
    response = client.get('/doctor/Strange/appointments?startTime=2023-06-20T09:00:00&endTime=2023-06-20T12:00:00')
    assert response.status_code == HTTPStatus.OK
    assert response.json == [{"doctor":"Strange", "endTime":"2023-06-20T10:00:00", "id":1, "patient":"Peter", "startTime":"2023-06-20T09:00:00"}]

def test_do_not_get_appointments_with_missing_parameters(client):
    response = client.get('/doctor/Strange/appointments?startTime=2023-06-20T09:00:00')
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json == 'Missing paramters. doctorName, startTime, and endTime are required.'

@mock.patch('src.endpoints.datetime', FakeDateTime)
def test_create_earliest_appointment_now(client):
    FakeDateTime.today = classmethod(lambda cls: datetime(2023, 6, 20, 9, 0, 0))
    response = client.post('/create_earliest_appointment', json={
        "doctorName": "Strange", 
        "patientName": "Peter", 
        "lengthMinutes": 60}
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json == {"doctor":"Strange", "endTime":"2023-06-20T10:00:00", "id":1, "patient":"Peter", "startTime":"2023-06-20T09:00:00"}

@mock.patch('src.endpoints.datetime', FakeDateTime)
def test_create_earliest_appointment_move_to_working_hours(client):
    FakeDateTime.today = classmethod(lambda cls: datetime(2023, 6, 18, 9, 0, 0))
    response = client.post('/create_earliest_appointment', json={
        "doctorName": "Strange", 
        "patientName": "Peter", 
        "lengthMinutes": 60}
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json == {"doctor":"Strange", "endTime":"2023-06-19T10:00:00", "id":1, "patient":"Peter", "startTime":"2023-06-19T09:00:00"}

@mock.patch('src.endpoints.datetime', FakeDateTime)
def test_create_earliest_appointment_after_existing_appointment(client):
    client.post('/create_appointment', json={
        "doctorName": "Strange", 
        "patientName": "Peter", 
        "startTime": "2023-06-20 09:30:00", 
        "lengthMinutes": 60}
    )
    FakeDateTime.today = classmethod(lambda cls: datetime(2023, 6, 20, 10, 0, 0))
    response = client.post('/create_earliest_appointment', json={
        "doctorName": "Strange", 
        "patientName": "Peter", 
        "lengthMinutes": 60}
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json == {"doctor":"Strange", "endTime":"2023-06-20T11:30:00", "id":2, "patient":"Peter", "startTime":"2023-06-20T10:30:00"}

def test_home_api(client):
    response = client.get('/')
    assert response.status_code == HTTPStatus.OK
    # Response is binary string data because data is the raw data of the output.
    # The switch from ' to " is due to json serialization
    assert response.data == b'{"data":"OK"}\n'
    # json allows us to get back a deserialized data structure without us needing to manually do it
    assert response.json == {'data': 'OK'}

def test_dummy_model_api(client):
    response = client.post('/dummy_model', json={
        'value': 'foobar'
    })
    assert response.status_code == HTTPStatus.OK
    obj = response.json
    new_id = obj.get('id')
    response = client.get(f'/dummy_model/{new_id}')
    assert response.status_code == HTTPStatus.OK
    assert response.json.get('value') == 'foobar'

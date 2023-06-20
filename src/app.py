from flask import Flask
from src.extensions import db
from src.endpoints import home
from src.models import Doctor, WorkingHours


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    db.init_app(app)
    # We are doing a create all here to set up all the tables. Because we are using an in memory sqllite db, each
    # restart wipes the db clean, but does have the advantage of not having to worry about schema migrations.
    with app.app_context():
        db.create_all()
        doctor_strange = Doctor('Strange')
        db.session.add(doctor_strange)
        doctor_who = Doctor('Who')
        db.session.add(doctor_who)
        db.session.commit()
        for i in range(1, 6):
            db.session.add(WorkingHours(doctor_strange, i, 9, 17))
            db.session.add(WorkingHours(doctor_who, i, 8, 16))
        db.session.commit()
    app.register_blueprint(home)
    return app

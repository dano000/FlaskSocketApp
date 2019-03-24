# Demo Flask Web Socket App
# Imports #
################################################################################
import hashlib
import pickle
from datetime import datetime
from os import environ

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy

from constants import COUNTRIES_OF_ORIGIN, REQUIRED_ASSISTANCE_TYPES, LANGUAGES

# App Setup #
################################################################################
app = Flask(__name__)
app.config['SECRET_KEY'] = environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('SQLITE_DB')
APP_VERSION = 0.1
socket = SocketIO(app)
db = SQLAlchemy(app)

clf = pickle.load(open('clf.p', 'rb'))


# DB Setup #
################################################################################
class Crisis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    code = db.Column(db.String(3), nullable=False)


class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    date_of_birth = db.Column(db.DateTime, nullable=False)
    country_of_origin = db.Column(db.String(3), nullable=False)
    crisis_id = db.Column(db.Integer, db.ForeignKey('crisis.id'),
                          nullable=False)
    crisis = db.relationship('Crisis', backref=db.backref('cases', lazy=True))
    food = db.Column(db.Boolean)
    housing = db.Column(db.Boolean)
    equipment = db.Column(db.Boolean)
    water = db.Column(db.Boolean)
    sanitation = db.Column(db.Boolean)
    building = db.Column(db.Boolean)
    amount = db.Column(db.Numeric(precision=10, scale=2))
    hashsum = db.Column(db.String(32), nullable=False)


# Rendering Main Page #
################################################################################
@app.route("/")
def home():
    return render_template(
        'main.html',
        async_mode=socket.async_mode,
        countries_of_origin=COUNTRIES_OF_ORIGIN,
        countries_of_crisis=[(crisis.id, crisis.title) for crisis in Crisis.query.all()],
        assistant_types=REQUIRED_ASSISTANCE_TYPES,
        languages=LANGUAGES,
    )


def generate_hashsum(data):
    # Generate hashsum for each individual case
    data_string = data['FN'] + data['LN'] + data['DOB'] + data['COO']
    hashsum = hashlib.md5(data_string.encode()).hexdigest()
    return hashsum


def verify_data(data):
    # Verify that the data/case is not already in the database
    hashsum = generate_hashsum(data)
    case = Case.query.filter_by(hashsum=hashsum).first()
    return case


def commit_data(data):
    # Commit dictionary data to database.

    first_name = data['FN']
    last_name = data['LN']
    country_of_origin = data['COO']
    current_crisis_country = data['CCC']
    date_of_birth = datetime.strptime(data['DOB'], '%Y-%m-%d')
    requested_assistance_type = data['RAT'].split(',')
    amount = data['AMO']

    food = True if 'FO' in requested_assistance_type else False
    housing = True if 'TH' in requested_assistance_type else False
    equipment = True if 'CE' in requested_assistance_type else False
    water = True if 'WA' in requested_assistance_type else False
    sanitation = True if 'SA' in requested_assistance_type else False
    building = True if 'RE' in requested_assistance_type else False

    crisis = Crisis.query.get(current_crisis_country)

    hashsum = generate_hashsum(data)

    case = Case(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
        country_of_origin=country_of_origin,
        crisis=crisis,
        food=food,
        housing=housing,
        equipment=equipment,
        water=water,
        sanitation=sanitation,
        building=building,
        amount=amount,
        hashsum=hashsum
    )

    db.session.add(case)
    db.session.commit()

    return case


# Respond to message #
################################################################################
@socket.on('event')
def process_event(data):
    # Process a socket 'event'
    print(data)

    # Verify that this is a real claim.
    case_check = verify_data(data)

    if case_check is None:
        # Check if it is an outlier or if legitimate.
        outlier_prediction = clf.predict(
            [[float(data['AMO']), int(len(data['RAT'].split(',')))]])

        if outlier_prediction == [-1]:
            new_case = 'P'
            print('Case outlier. Not Accepted.')
            case_hashsum = '-' * 32
        else:
            case = commit_data(data)
            print("Case saved.")
            print("Case hashsum: " + case.hashsum)
            case_hashsum = case.hashsum
            new_case = 'T'
    else:
        # Case already exists, so reject.
        print("Case already exists.")
        print("Case hashsum: " + case_check.hashsum)
        case_hashsum = case_check.hashsum
        new_case = 'F'

    # Emit the type of case and it's hashsum (if it exists).
    emit('verification', {'data': case_hashsum, 'new': new_case})
    print(case_hashsum)


# Run App #
################################################################################
if __name__ == '__main__':
    socket.run(app)

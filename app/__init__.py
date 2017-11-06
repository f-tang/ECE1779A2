from flask import Flask, render_template, redirect, url_for, flash, session, g
from functools import wraps
import pymysql.cursors
from app.config import db_config
import boto3
import time
from botocore.client import Config


webapp = Flask(__name__)
webapp.secret_key='\x80\xa9s*\x12\xc7x\xa9d\x1f(\x03\xbeHJ:\x9f\xf0!\xb1a\xaa\x0f\xee'


# access database
def connect_to_database():
    return pymysql.connect(host=db_config['host'],
                                user=db_config['user'],
                                password=db_config['password'],
                                db=db_config['database'])

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._databse = connect_to_database()
    return db

# database exception teardown
@webapp.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# login-required wrapper
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("You need to login first")
            return redirect(url_for('login_form'))

    return wrap

# access aws s3 bucket
BUCKET_NAME = 'ece1779-ft'
def get_s3bucket():
    aws_session = boto3.Session(profile_name="s3")
    s3 = aws_session.resource('s3')

    return s3.Bucket(BUCKET_NAME)

def get_s3client():
    aws_session = boto3.Session(profile_name="s3")
    s3 = aws_session.client('s3')

    return s3

def get_milliseconds():
    millis = int(round(time.time() * 1000000))
    return millis


from app import main
from app import gallery
from app import login_signup
from app import image_upload
from app import test

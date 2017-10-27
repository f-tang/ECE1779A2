from flask import render_template, redirect, url_for, request, g, session, flash
from app import webapp, login_required, get_db, teardown_db, get_s3client
from pymysql import escape_string
import boto3

import gc
import os, shutil


# get the absolute path of the file
APP_ROOT = os.path.dirname(os.path.abspath(__file__)) + "/static"

BUCKET_NAME = 'ece1779-ft'


# page for the thumbnail gallery
@webapp.route("/gallery")
@login_required
def gallery():
    error = ""
    try:
        # access database
        cnx = get_db()
        cursor = cnx.cursor()

        url = "https://s3.amazonaws.com/ece1779-ft/images/" + session['username']

        # fetch names of the images owned by user
        cursor.execute("SELECT userID FROM users WHERE username = (%s)",
                       (escape_string(session['username'])))
        uID = cursor.fetchone()[0]
        cursor.execute("SELECT pName FROM images WHERE users_userID = (%s)",
                       (int(uID)))
        imagenames = cursor.fetchall()

        # store image paths and pass to frontend
        images = []
        for imagename in imagenames:
            image = url + '/' + imagename[0]
            images.append(image)

        #cleanup
        cursor.close()
        cnx.close()

        return render_template("thumbnail-gallery.html", title="Gallery", images=images)

    except Exception as e:
        teardown_db(e)
        return str(e)


# page for showing full images
@webapp.route("/gallery/<username>/<path:image>")
@login_required
def full_image(username, image):
    try:
        # verify the identity of the user
        pathname = str(image).split('/')
        if not username == pathname[-2] or not username == session['username']:
            flash("access denied")
            return redirect(url_for('gallery'))

        # initialize the image list
        images = []
        images.append(str(image))

        # access to database
        cnx = get_db()
        cursor = cnx.cursor()

        # fetch names of the transformed images
        cursor.execute("SELECT tpName FROM images, trimages WHERE pName=(%s) AND pID=images_pID",
                       (escape_string(pathname[-1])))
        imagenames = cursor.fetchall()

        url = "https://s3.amazonaws.com/ece1779-ft/images/" + session['username']
        # store image paths and pass to frontend
        for imagename in imagenames:
            image = url + '/' + imagename[0]
            images.append(image)

        # cleanup
        cursor.close()
        cnx.close()
        return render_template("full-image.html", username=username, images=images)

    except Exception as e:
        APP_RELATED = 'tmp/' + session['username']
        if os.path.isdir(os.path.join(APP_ROOT, APP_RELATED)):
            shutil.rmtree(os.path.join(APP_ROOT, APP_RELATED))
        teardown_db(e)
        return str(e)

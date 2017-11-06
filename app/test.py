from flask import render_template, redirect, url_for, request, g, flash, session
from app import webapp, get_db, teardown_db, get_s3bucket, get_milliseconds
from pymysql import escape_string
from passlib.hash import sha256_crypt
from wand.image import Image

import gc
import os, shutil

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# path of s3 images folder
IMAGES_PATH = "images/"


def image_transfer(imagefile, method):
    try:
        if int(method) == 0:
            imagefile.flip()
        if int(method) == 1:
            imagefile.evaluate(operator='rightshift', value=1, channel='blue')
            imagefile.evaluate(operator='leftshift', value=1, channel='red')
        if int(method) == 2:
            imagefile.type = 'grayscale'
        return imagefile
    except Exception as e:
        return str(e)


# page for marking test
@webapp.route("/test/FileUpload", methods=['GET', 'POST'])
def test_fileupload():
    error = ""

    if request.method == 'POST':
        username = request.form["userID"]
        password = request.form["password"]

        APP_RELATED = 'static/tmp/' + escape_string(username)
        tmp_target = os.path.join(APP_ROOT, APP_RELATED)
        target = IMAGES_PATH + username

        try:
            cnx = get_db()
            cursor = cnx.cursor()
            s3 = get_s3bucket()

            # verify the username and password
            cursor.execute("SELECT password FROM users WHERE username = (%s)",
                           (escape_string(username)))
            x = cursor.fetchone()
            if x is None:
                error = "Invalid credentials, try again."
                cursor.close()
                cnx.close()
                return render_template("test-form.html", error=error)

            data = x[0]
            if not sha256_crypt.verify(password, data):
                error = "Invalid credentials, try again."
                cursor.close()
                cnx.close()
                return render_template("test-form.html", error=error)

            # check if 'uploadedfile' is in the request
            if 'uploadedfile' not in request.files:
                error = "file does not exist"
                cursor.close()
                cnx.close()
                return render_template("test-form.html", error=error)

            file = request.files['uploadedfile']

            # double check if the file exists
            if file is None or file.filename == '':
                error = "file does not exist"
                cursor.close()
                cnx.close()
                return render_template("test-form.html", error=error)

            # determine the file path for upload
            cursor.execute("SELECT userID FROM users WHERE username = (%s)",
                           (escape_string(username)))
            uID = cursor.fetchone()[0]

            if not os.path.isdir(os.path.join(APP_ROOT, 'static/tmp/')):
                os.mkdir(os.path.join(APP_ROOT, 'static/tmp/'))

            if not os.path.isdir(tmp_target):
                os.mkdir(tmp_target)

            # give a pID for the new image
            cursor.execute("SELECT max(pID) FROM images")
            x = cursor.fetchone()
            if x[0] == None:
                pID = 1
            else:
                pID = x[0] + 1

            # save file
            filename = str(file.filename).split('.')[-1]
            filename = escape_string(str(pID) + '_' + str(get_milliseconds()) + '.' + filename)
            destination = "/".join([target, filename])
            tmp_dest = "/".join([tmp_target, filename])
            file.save(tmp_dest)
            file.seek(0)
            s3.put_object(Key=destination, Body=file, ACL='public-read')

            # insert image info into database
            cursor.execute("INSERT INTO images (pID, pName, users_userID) VALUES (%s, %s, %s)",
                           (int(pID), filename, int(uID)))

            # apply image transformations
            for i in range(3):
                cursor.execute("SELECT max(tpID) FROM trimages")
                x = cursor.fetchone()
                if x[0] == None:
                    tpID = 1
                else:
                    tpID = x[0] + 1

                tfilename = escape_string("tr" + str(i) + "_" + filename)
                img = Image(filename=tmp_dest)
                with img.clone() as tfile:
                    image_transfer(tfile, i)
                    # save the image file
                    tmp_tdest = "/".join([tmp_target, tfilename])
                    tfile.save(filename=tmp_tdest)
                    tdestination = "/".join([target, tfilename])
                    s3.put_object(Key=tdestination, Body=open(tmp_tdest, 'rb'), ACL='public-read')

                    cursor.execute("INSERT INTO trimages (tpID, tpName, images_pID) VALUES (%s, %s, %s)",
                                   (int(tpID), tfilename, int(pID)))

            shutil.rmtree(tmp_target)
            cnx.commit()
            cursor.close()
            cnx.close()

            gc.collect()

            flash("upload successful")
            return redirect(url_for("test_fileupload"))

        except Exception as e:
            if os.path.isdir(tmp_target):
                shutil.rmtree(tmp_target)
            teardown_db(e)
        return str(e)

    return render_template("test-form.html")

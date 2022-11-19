# from crypt import methods
from distutils.log import debug
from email import message
from gzip import BadGzipFile
from itertools import dropwhile
# from signal import alarm
from sqlite3 import connect
import cvlib as cv
from cvlib.object_detection import draw_bbox
import cv2 
import time
import numpy as np

from werkzeug.utils import secure_filename
from playsound import playsound

import os
from dotenv import load_dotenv, find_dotenv

# from .utils import download_file

from flask import Flask, request, render_template, redirect, url_for, make_response

from cloudant.client import Cloudant

load_dotenv(find_dotenv())

client = Cloudant.iam(os.getenv("IBM_CLOUDANT_KEY"), os.getenv("IBM_CLOUDANT_USER"), connect=True)

my_database = client.create_database("my_database")

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/index.html")
def home():
    return render_template("index.html")

@app.route("/prediction")
def prediction():
    if request.cookies.get("isLoggedIn") == "True":
        return render_template("prediction.html")
    else:
        return render_template("login.html", message="You must be logged in first!")

@app.route("/dashboard")
def dashboard():
    if request.cookies.get("isLoggedIn") == "True":
        return render_template("dashboard.html")
    else:
        return render_template("login.html", message="You must be logged in first!")
        

@app.route('/upload', methods = ['POST'])
def upload_file():
    if request.cookies.get("isLoggedIn") == "True":
        if request.method == 'POST':
            f = request.files['video']
            f.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads', secure_filename(f.filename)))
            return render_template("prediction.html", message="File upload success, Processing stream...", bad=False)
    else:
        return render_template("login.html", message="You must be logged in first!")

@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/afterreg", methods=["POST"])
def afterreg():
    x = [x for x in request.form.values()]
    print(x)
    data = {
        "_id": x[1],
        "name": x[0],
        "psw": x[2]
    }
    print(data)

    query = {"_id": {"$eq": data["_id"]}}

    docs = my_database.get_query_result(query)
    print(docs)

    print(len(docs.all()))

    if(len(docs.all()) == 0):
        url = my_database.create_document(data)
        return render_template("register.html", message="Registration Successfull, Please login using your credentials", bad=False)
    else:
        return render_template("register.html", message="You are already a member, please login using your credentials", bad=True)


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/afterlogin", methods=["POST"])
def afterlogin():
   
    user = request.form["_id"]
    passw = request.form["psw"]
    print(user, passw)

    query = {"_id": {"$eq": user}}

    docs = my_database.get_query_result(query)
    print(docs)

    print(len(docs.all()))

    if(len(docs.all()) == 0):
        resp = make_response(render_template("login.html", message="The email is not found!"))  
        return resp
    else:
        if((user == docs[0][0]["_id"]) and passw == docs[0][0]["psw"]):
            resp = make_response(redirect(url_for("dashboard")))
            resp.set_cookie('isLoggedIn',"True")  
            return resp
        else:
            print("Invalid User")
    

@app.route("/logout")
def logout():
    if request.cookies.get("isLoggedIn") == "True":
        resp = make_response(render_template("login.html", message="You have logged out successfully!"))
        resp.set_cookie('isLoggedIn', '', expires=0)
        return resp
    else:
        return render_template("login.html", message="You must be logged in first!")

@app.route("/result", methods=["GET", "POST"])
def res():

    if request.cookies.get("isLoggedIn") == "True":

        webcam = cv2.VideoCapture("static/drowning.mp4")

        if not webcam.isOpened():
            print("Could not open webcam")
            exit()

        t0 = time.time()
        centre0 = np.zeros(2)
        isDrowning = False

        while webcam.isOpened():

            status, frame = webcam.read()
            bbox, label, conf = cv.detect_common_objects(frame)

            if(len(bbox) > 0):
                bbox0 = bbox[0]
                centre = [0,0]
                
                centre = [(bbox0[0]+bbox0[2])/2, (bbox0[1]+bbox0[3])/2]

                hmov = abs(centre[0]-centre0[0])
                vmov = abs(centre[1]-centre0[1])

                x = time.time()

                threshold = 10

                if((hmov > threshold) or (vmov > threshold)):
                    print(x-t0, "s")
                    t0 = time.time()
                    isDrowning = False
                
                else:

                    print(x-t0, "s")
                    if((time.time() - t0) > 10):
                        isDrowning = True

                print("bbox: ", bbox, "Centre: ", centre, "Centre0: ", centre0)
                print("Is he drowning: ", isDrowning)

                centre0 = centre

            
                out = draw_bbox(frame, bbox, label, conf)

                cv2.imshow("Real-time object detection: ", out)
                
                if(isDrowning == True):
                    playsound("http://localhost:5000/static/sound3.mp3")

                    webcam.release()
                    cv2.destroyAllWindows()

                    return render_template("prediction.html", message="Emergency!!! The Person is Drowning", bad=True)

                if(cv2.waitKey(1) & 0xFF ==  ord("q")):
                    break

        webcam.release()
        cv2.destroyAllWindows()

        return render_template("prediction.html")
    else:
        return render_template("login.html", message="You must be logged in first!")

@app.route("/result-upload", methods=["GET", "POST"])
def resUpload():
    
    if request.cookies.get("isLoggedIn") == "True":

        # print(request.files["video"])

        # file = request.files['video']
        # file.save(secure_filename(file.filename))


        #webcam = cv2.VideoCapture("static/uploads/"+ file.filename +".mp4")
        webcam = cv2.VideoCapture("static/uploads/drowning.mp4")

        if not webcam.isOpened():
            print("Could not open webcam")
            exit()

        t0 = time.time()
        centre0 = np.zeros(2)
        isDrowning = False

        while webcam.isOpened():

            status, frame = webcam.read()
            bbox, label, conf = cv.detect_common_objects(frame)

            if(len(bbox) > 0):
                bbox0 = bbox[0]
                centre = [0,0]
                
                centre = [(bbox0[0]+bbox0[2])/2, (bbox0[1]+bbox0[3])/2]

                hmov = abs(centre[0]-centre0[0])
                vmov = abs(centre[1]-centre0[1])

                x = time.time()

                threshold = 10

                if((hmov > threshold) or (vmov > threshold)):
                    print(x-t0, "s")
                    t0 = time.time()
                    isDrowning = False
                
                else:

                    print(x-t0, "s")
                    if((time.time() - t0) > 10):
                        isDrowning = True

                print("bbox: ", bbox, "Centre: ", centre, "Centre0: ", centre0)
                print("Is he drowning: ", isDrowning)

                centre0 = centre

            
                out = draw_bbox(frame, bbox, label, conf)

                cv2.imshow("Real-time object detection: ", out)
                
                if(isDrowning == True):
            
                    webcam.release()
                    cv2.destroyAllWindows()

                    playsound("http://localhost:5000/static/sound3.mp3")

                    return render_template("prediction.html", message="Emergency!!! The Person is Drowning")

                if(cv2.waitKey(1) & 0xFF ==  ord("q")):
                    break

        webcam.release()
        cv2.destroyAllWindows()

        return render_template("prediction.html")
    else:
        return render_template("login.html", message="You must be logged in first!")


if __name__ == '__main__':
    app.run(debug=True, static_url_path="static", static_folder='static', template_folder="templates")






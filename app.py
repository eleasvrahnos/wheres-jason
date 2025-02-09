# WHERESJAOSN.HEROKUAPP.COM - Where's Jaosn?
# Created by Eleas Vrahnos
# app.py - Runs the backend of the website using Flask


# --------------------------------IMPORTS-------------------------------------


# Imports for basic Flask application, including website sessions per user, rendering templates of websites, and link redirections
from flask import Flask, render_template, request, session, redirect
# Import for operating on the random image, including opening, pastes, and resizing
from PIL import Image
# Import for converting image data to a byte stream
from io import BytesIO
# Import for a random integer generator
import random
# Import for keeping track of time
import time
# Import for sending data to client in a JSON format
import json
# Import for rounding data
import math
# Import for encrypting image data with AES encryption
from Cryptodome.Cipher import AES
# Import for padding image data with null bytes for decoding
from Cryptodome.Util.Padding import pad
# Import for randomizing key for decrypting image data
from Cryptodome.Random import get_random_bytes
# Import for setting up the leaderboard database, using SQLAlchemy
from flask_sqlalchemy import SQLAlchemy


# --------------------------------INITIALIZATIONS-------------------------------------


# Initializes application
app = Flask(__name__)
app.secret_key = "JAOSNJAOSNJJJJJJJJJJJJJJJJJJJ"


# Initializes leaderboard database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///leaderboards.db'
db = SQLAlchemy(app)
class Leaderboards(db.Model):
    # Sets three columns: ID (orders by insertion time), username, and score
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    score = db.Column(db.Integer, nullable=False)


# --------------------------------FUNCTIONS-------------------------------------


# Clears the total play session in preparation for a new game, but keeps the volume level settings
def save_volume_clear():
    if "bg_vol" in session:
        temp_1 = session["bg_vol"]
        temp_2 = session["sfx_vol"]
        session.clear()
        session["bg_vol"] = temp_1
        session["sfx_vol"] = temp_2


# Updates life count in the case that a life is lost
def update_lives_count():
    if "lives_left" not in session:
        session["lives_left"] = 2
    else:
        session["lives_left"] -= 1


# --------------------------------HIDDEN ROUTES-------------------------------------


# Hidden route for getting image to use
@app.route("/get-image", methods=["GET"])
def get_image():
    # Randomly picks a picture to use out of the possible images on the GitHub repository
    num_pics_available = 171 # Number of pictures on GitHub repository
    pic_to_use = random.randint(1, num_pics_available)
    # Opens both background image and standard Jaosn image
    background_image = Image.open('static/projectWJ/' + str(pic_to_use) + '.jpg')
    jaosn_image = Image.open('static/jaosnTransparentBG.png')
    # Randomly gives Jaosn a size to scale down to, based on background image height
    bg_width, bg_height = background_image.size
    max_jaosn_height = bg_height // 13 # 13 is random
    min_jaosn_height = bg_height // 23 # 23 is random
    height_to_use = random.randint(min_jaosn_height, max_jaosn_height)
    # Scales Jaosn down to generated size
    jaosn_image.thumbnail((height_to_use, height_to_use))
    # Randomly places Jaosn somewhere within the background image
    new_jaosn_width, new_jaosn_height = jaosn_image.size
    session["jaosn_next_width"] = new_jaosn_width
    session["jaosn_next_height"] = new_jaosn_height
    x_coord = random.randint(10, bg_width - new_jaosn_width - 10)
    y_coord = random.randint(10, bg_height - new_jaosn_height - 10)
    session["jaosn_next_position_x"] = x_coord
    session["jaosn_next_position_y"] = y_coord
    background_image.paste(jaosn_image, (x_coord, y_coord), jaosn_image)
    # Encrypts image through byte stream and AES (mode CBC)
    img_io = BytesIO()
    background_image.save(img_io, "JPEG")
    img_data = img_io.getvalue()
    key = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC)
    # Saves image iv
    iv = cipher.iv.hex()
    session["iv"] = str(iv)
    # Saves image key
    key = key.hex()
    session["key"] = str(key)
    # Returns the encrypted version of the image (ct = ciphertext)
    ct_bytes = cipher.encrypt(pad(img_data, AES.block_size))
    ct = ct_bytes.hex()
    return ct


# Hidden route for getting image's key and iv
@app.route("/get-key-iv", methods=["GET"])
def get_key_iv():
    # When getting key iv, the 'next image' specs are updated to be the 'current image' specs
    session["jaosn_current_width"] = session["jaosn_next_width"]
    session["jaosn_current_height"] = session["jaosn_next_height"]
    session["jaosn_current_position_x"] = session["jaosn_next_position_x"]
    session["jaosn_current_position_y"] = session["jaosn_next_position_y"]
    # Starts the backend timer
    session["start_time"] = time.time()
    # Sends the key and iv data
    key_iv_data = { "key": session["key"], "iv": session["iv"] }
    return key_iv_data


# Hidden route for checking the state of an image click/timeout and returning updated game state data
# TIMEOUT - always leads to losing life
# CLICK - correct click leads to points given, incorrect click leads to losing life
@app.route("/check", methods=["POST"])
def check():
    # Goes here when a timeout happens
    if request.form.get("type") == "TIMEOUT":
        update_lives_count()
        timeout_data = { "state": "incorrect", "lives": str(session["lives_left"]), "left": session["jaosn_current_position_x"], "top": session["jaosn_current_position_y"], "width": session["jaosn_current_width"], "height": session["jaosn_current_height"] }
        return timeout_data
    # Goes here if a click is registered
    elif request.form.get("type") == "CLICK":
        # Tries in case that data sent to backend is not a float - otherwise it doesn't register so nothing happens
        click_data = {}
        try:
            x = float(request.form.get('x'))
            y = float(request.form.get('y'))
            # Goes through if the click is determined to be on Jaosn
            if ((x > session["jaosn_current_position_x"]) and (x < (session["jaosn_current_position_x"] + session["jaosn_current_width"]))) and ((y > session["jaosn_current_position_y"]) and (y < (session["jaosn_current_position_y"] + session["jaosn_current_height"]))):
                # Stops backend timer
                session["end_time"] = time.time()
                # Calculates points based on backend time recorded
                time_left = 60 - (session["end_time"] - session["start_time"])
                time_left_adjusted = 60 - math.floor(session["end_time"] - session["start_time"] )
                points = round((time_left * 1000) / 60)
                # Updates total points on backend
                if "total_points" not in session:
                    session["total_points"] = points
                else:
                    session["total_points"] = session["total_points"] + points
                # Initializes click_data in the case that the click is confirmed to be correct
                click_data = { "state": "correct", "points": str(points), "total": session["total_points"], "time": time_left_adjusted, "left": session["jaosn_current_position_x"], "top": session["jaosn_current_position_y"], "width": session["jaosn_current_width"], "height": session["jaosn_current_height"] }
            else:
                update_lives_count()
                # Initializes click_data in the case that the click is confirmed to be incorrect
                click_data = { "state": "incorrect", "lives": str(session["lives_left"]), "left": session["jaosn_current_position_x"], "top": session["jaosn_current_position_y"], "width": session["jaosn_current_width"], "height": session["jaosn_current_height"]}
        finally:
            # Returns click_data to client
            return click_data


# Hidden route for updating the leaderboard page based on the leaderboard page number
@app.route("/statsupdate", methods=["POST"])
def statsupdate():
    # Orders leaderboard by descending score
    leaderboards = Leaderboards.query.order_by(Leaderboards.score.desc())
    # Initializes name, score, and page data to send
    name_data = []
    score_data = []
    page_data = {}
    # Tries in case that data sent to backend is not an int - otherwise it doesn't register so nothing happens
    try:
        current_page = int(request.form.get("current_page"))
        # Calculates the start and end bound of the ranks of the given page
        start_bound = ((current_page - 1) * 10) + 1
        end_bound = start_bound + 10
        # Below is the case when the whole page doesn't have any values, so set everything to "---"
        if leaderboards.count() < start_bound:
            for i in range(10):
                name_data.append("---")
                score_data.append("---")
        # Below is the case when part of page doesn't have any values, so set those null values to "---"
        elif leaderboards.count() < (end_bound - 1):
            true_end_bound = 11 - (end_bound - leaderboards.count())
            for user in leaderboards[(start_bound - 1):(start_bound + true_end_bound)]:
                name_data.append(user.username)
                score_data.append(user.score)
            for i in range(10 - true_end_bound):
                name_data.append("---")
                score_data.append("---")
        # Below is the case when all the values are not null
        else:
            for user in leaderboards[(start_bound - 1):(end_bound - 1)]:
                name_data.append(user.username)
                score_data.append(user.score)
        page_data = { "nameData": name_data, "scoreData": score_data }
    # Finally returns the page data
    finally:
        return page_data


# Hidden route for getting the total points earned in the game so far
@app.route("/get-total-points", methods=["GET"])
def get_total_points():
    # If total points hasn't been registered in session, that means no points have been earned
    if "total_points" not in session:
        return "0"
    # Otherwise, return the total points earned
    return str(session["total_points"])


# Hidden route for getting the current settings of the Background and SFX volume levels
@app.route("/get-volume-states", methods=["POST", "GET"])
def getvolumestats():
    # If the method is POST, volume data is being saved to the session
    if request.method == "POST":
        # Tries in case that data sent to backend is not a float - otherwise it doesn't register so nothing happens
        try:
            bg_vol = float(request.form.get("current_bg_volume"))
            sfx_vol = float(request.form.get("current_sfx_volume"))
            session["bg_vol"] = bg_vol
            session["sfx_vol"] = sfx_vol
        # Finally, returns a random positive string to confirm that the changes went through.
        finally:
            return "Volume settings saved successfully.";
    # If the method is GET, the saved volume data is trying to be accessed
    elif request.method == "GET":
        # If there are no volume settings saved, the default is at half-volume
        if "bg_vol" not in session:
            session["bg_vol"] = 0.5
            session["sfx_vol"] = 0.5
        # The pre-saved volume settings are returned
        volume_data = { "bgVol": str(session["bg_vol"]), "sfxVol": str(session["sfx_vol"]) }
        return volume_data


# --------------------------------WEBSITE ROUTES-------------------------------------


# Website route for Home page
@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html")


# Website route for Play page
@app.route("/play")
def play():
    # Clears session for new game
    save_volume_clear()
    return render_template("play.html", title="Play")


# Website route for How to Play page
@app.route("/how-to-play")
def howtoplay():
    return render_template("how-to-play.html", title="How to Play")


# Website route for Leaderboards page
@app.route("/leaderboards", methods=["POST", "GET"])
def leaderboards():
    # If the method is POST, a new entry is being added
    if request.method == "POST":
        # Tries to add an entry with username "user" and score "game_score"
        try:
            user = request.form['username']
            game_score = int(get_total_points())
            new_user_entry = Leaderboards(username=user, score=game_score)
            db.session.add(new_user_entry)
            db.session.commit()
            return redirect('/leaderboards')
        # If for some reason there was an error adding to the leaderboard, an error is thrown and investigation is required
        except:
            return "There was an error adding to the leaderboard."
        # Redirects to the actual leaderboard (with method "GET")
        return redirect("/leaderboards")
    # If the method is GET, the leaderboards are being accessed from the menu, or it was just updated from a new entry
    elif request.method == "GET":
        # Orders leaderboard by descending score
        leaderboards = Leaderboards.query.order_by(Leaderboards.score.desc())
        # Sets blankRange to the initial amount of blank spaces on the page 1 leaderboard when it is first loaded
        if (leaderboards.count() >= 10):
            blank_range = 0
        else:
            blank_range = 10 - leaderboards.count()
        save_volume_clear()
        return render_template("leaderboards.html", startLeaderboards=leaderboards[0:10], title="Leaderboards", blankRange=range(blank_range))


# --------------------------------APP STARTER-------------------------------------


# Runs application if from local computer
if __name__ == '__main__':
  app.run(debug=True)

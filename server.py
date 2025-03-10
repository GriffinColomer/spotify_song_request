from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import config
import time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///queued_songs_test.db'
db = SQLAlchemy(app)

# Configure Spotify API credentials
scope = "user-modify-playback-state,user-read-playback-state"
spOAuth = SpotifyOAuth(client_id=config.client_id, client_secret=config.client_secret, redirect_uri='http://google.com/',open_browser=False, scope=scope)
sp = spotipy.Spotify(auth_manager=spOAuth)
past_track_uri = ""
print(" * User logged in: " + sp.current_user()['display_name'])

class playedSongs(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uri = db.Column(db.String(64))

def checkSong():
    try:
        with app.app_context():
            global past_track_uri
            current_track = sp.current_playback()
            current_track_uri = current_track['item']['uri']
            if current_track_uri != past_track_uri:
                past_track_uri = current_track_uri
                song = playedSongs(uri=current_track_uri)
                db.session.add(song)
                db.session.commit()
                print("song: " + current_track['item']['name'] + " added to database")
    except:
        print("no song playing")  
        
        
def startScheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=checkSong, trigger="interval", seconds = 30)
    scheduler.start()

@app.route('/song_queue/search')
def home():
    song_name = request.args.get('name')
    if song_name:
        tracks = sp.search(song_name, limit=20, type= 'track')
        tracks = tracks['tracks']['items']
        return render_template('results.html', tracks= tracks)
        
    return render_template('search.html')

@app.route('/song_queue/api/queue', methods=['POST'])
def addToQueue():
    try:
        uri = request.get_data(as_text=True)
        sp.add_to_queue(uri=uri)
        return jsonify({"message":"recieved"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/song_queue/queue')
def queue():
    queue = sp.queue()
    currently_playing = queue['currently_playing']
    queue = queue['queue']
    return render_template('queue.html', currently_playing = currently_playing, queue = queue)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    startScheduler()
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000)
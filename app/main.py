# Standard packages
import json
import os
from os.path import join, dirname
from urllib.parse import urlencode
import logging

# External libraries
from flask import Flask, render_template, session, redirect, request, make_response, url_for
import spotipy.util as util
import spotipy
import requests
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

# This loads values from .env file into environment
load_dotenv('.env')

app = Flask(__name__)
app.secret_key = os.environ['FLASK_SECRET']  # random secret key for app

cid = os.environ['CLIENT_ID']
secret = os.environ['CLIENT_SECRET']

logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', level='DEBUG')


## --- also ensure http://127.0.0.1:5000/callback is there in your app's redirect uris


# Home page
@app.route('/')
def home():
    return render_template('index.html')


client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
API_BASE = 'https://accounts.spotify.com'

SCOPE = 'user-library-read,user-read-recently-played,user-top-read'
SHOW_DIALOG = False


def get_callback_url():
    return url_for('auth_callback', _external=True)


@app.route('/callback')
def auth_callback():
    session.clear()
    code = request.args.get('code')
    auth_token_url = f'{API_BASE}/api/token'
    res = requests.post(auth_token_url, data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': get_callback_url(),
        'client_id': cid,
        'client_secret': secret,
        }).json()
    session['spotify_token'] = res['access_token']
    return redirect('recents')


SONG_LIMIT = 10

@app.route('/recents')
def recents():
    try:
        count = 0
        # danceability energy mood speechiness Acousticness tempo key popularity
        stats = [0, 0, 0, 0, 0, 0, 0, 0]
        key = ['danceability', 'energy', 'valence', 'speechiness', 'acousticness', 'tempo', 'key', 'popularity']
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager, auth=session['spotify_token'])

        results = sp.current_user_recently_played(limit=SONG_LIMIT)

        logging.info(json.dumps(results['items'][0], indent=2))

        tracks = []
        for item in results['items']:
            # song name, artist, image url, track uri
            tracks.append({
                'name': item['track']['name'],
                'artists': ', '.join(artist['name'] for artist in item['track']['artists']),
                'image_url': item['track']['album']['images'][2]['url'],
                'uri': item['track']['uri'],
            })

            audio_features = sp.audio_features(tracks=item['track']['id'])[0]
            for i in range(len(stats)-1):
                stats[i] += audio_features[key[i]]
            stats[-1] += item['track']['popularity']
            count += 1

        if count >= 1:
            for i in range(len(stats)):
                stats[i] = (stats[i]/count)*100
        stats[-1] /= 100
        stats[-2] /= 100
        stats[-3] /= 100
        return render_template('recents.html', tracks=tracks, name=sp.current_user()['display_name'], stats=stats)

    except Exception as e:
        logging.exception('Not authorized')
        params = {
            'client_id': cid,
            'response_type': 'code',
            'redirect_uri': get_callback_url(),
            'scope': SCOPE,
            'show_dialog': SHOW_DIALOG,
        }
        query_string = urlencode(params)
        auth_url = f'{API_BASE}/authorize?{query_string}'
        return redirect(auth_url)


# Used to supply assets to page
@app.route('/<path:path>')
def static_file(path):
    return app.send_static_file(path)

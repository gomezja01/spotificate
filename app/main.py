from flask import Flask, render_template, session, redirect, request, make_response
import spotipy.util as util
import spotipy, requests, os
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__)
app.secret_key = os.environ.get('SECKEY', 'insert random string') # random secret key

## ------ To run locally set localrun to True and use your client id and secret ----------------
localrun = False
cid = os.environ.get('CLID', 'insert ') # spotify client id
secret = os.environ.get('SECR', 'insert') # spotify client secret

## --- also ensure http://127.0.0.1:5000/callback is there in your app's redirect uris

# Redirect http to https
@app.before_request
def before_request():
    if not localrun :
        if not request.is_secure and app.env != "development" :
            url = request.url.replace("http://", "https://", 1)
            code = 301
            return redirect(url, code=code)
    else :
        pass

# Home page
@app.route('/')
def home():
    return render_template('index.html')

# Used to supply assets to page
@app.route('/<path:path>')
def static_file(path):
    return app.send_static_file(path)


client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
API_BASE = 'https://accounts.spotify.com'

if localrun :
    REDIRECT_URI = "http://127.0.0.1:5000/callback" # ensure this redirect uri is added in your app dashboard
else :
    REDIRECT_URI = "https://spotificate.herokuapp.com/callback" # Must be present in the app dashboard redirect uris

SCOPE = 'user-library-read,user-read-recently-played,user-top-read'
SHOW_DIALOG = False

@app.route("/callback")
def api_callback():
    session.clear()
    code = request.args.get('code')
    #print(code)
    auth_token_url = f"{API_BASE}/api/token"
    res = requests.post(auth_token_url, data={
        "grant_type":"authorization_code",
        "code":code,
        "redirect_uri":REDIRECT_URI,
        "client_id":cid,
        "client_secret":secret
        })
    res_body = res.json()
    #print(res.json())
    session["toke"] = res_body.get("access_token")
    return redirect("recents")

@app.route("/recents")
def go():
    try :
        count = 0
        stats = [0,0,0,0,0,0,0,0] # danceability energy mood speechiness Acousticness tempo key popularity
        key = ['danceability','energy','valence','speechiness','acousticness','tempo','key','popularity']
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager,auth=session['toke'])
        response = []
        results = sp.current_user_recently_played(limit=50)
        for item in (results['items']):
            # song name , artist , image url , track uri
            response.append((item['track']['name'],item['track']['artists'][0]['name'],item['track']['album']['images'][2]['url'],item['track']['uri']))
            audio_features = sp.audio_features(tracks=item['track']['id'])[0]
            for i in range(len(stats)-1):
                stats[i] += audio_features[key[i]]
            stats[-1] += item['track']['popularity']
            count+=1
        for i in range(len(stats)):
            stats[i] = (stats[i]/count)*100
        stats[-1] /= 100
        stats[-2] /= 100
        stats[-3] /= 100
        return render_template("recents.html", data=response,len=len(response),name=sp.current_user()['display_name'],stats=stats)
    except Exception as e:
        print('-----------error : ',e)
        auth_url = f'{API_BASE}/authorize?client_id={cid}&response_type=code&redirect_uri={REDIRECT_URI}&scope={SCOPE}&show_dialog={SHOW_DIALOG}'
        return redirect(auth_url)

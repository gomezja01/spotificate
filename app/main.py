from flask import Flask, render_template, session, redirect, request, make_response
import spotipy.util as util
import spotipy, requests, os
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__)
app.secret_key = os.environ.get('SECKEY', 'insert random string') # random secret key

## ------ To run locally set localrun to True and use your client id and secret ----------------
localrun = False
cid = os.environ.get('CLID', 'insert client id') # spotify client id
secret = os.environ.get('SECR', 'insert client secret') # spotify client secret

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

    return redirect("spotificate")


@app.route("/spotificate")
def go():
    try :
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager,auth=session['toke'])
        response = []
        print('------------',sp.current_user())
        x=0
        for i in range(5) :
            flag=0
            results = sp.current_user_top_tracks(offset=x,limit=20,time_range='long_term')

            for item in (results['items']):
                track = item['name']
                response.append(('-', '-', " – ", track))
            x+=20
        return render_template("page1.html", data=response,len=len(response),name=sp.current_user()['display_name'])
    except :
        auth_url = f'{API_BASE}/authorize?client_id={cid}&response_type=code&redirect_uri={REDIRECT_URI}&scope={SCOPE}&show_dialog={SHOW_DIALOG}'
        return redirect(auth_url)

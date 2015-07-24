from flask import Flask, request, render_template
from api_calls import userExists
from format import createItemSet
from datetime import datetime
app = Flask(__name__, static_url_path="")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/results', methods=['POST'])
def results():
    """
    The route that shows the results of the user's search.
    :return: A render_template object for Flask to render.
    """
    start_time = datetime.utcnow()
    id = userExists(request.form['username'], start_time)
    if (isinstance( id, int)):
        return error_render(id, request.form['username'])
    else:
        call = createItemSet(id, start_time)
        if not hasattr(call, 'status_code'):
            item_set = call[0]
            match_count = call[1]
            return render_template("results.html", username=request.form['username'], items=item_set, matches=match_count)
        else:
            return error_render(call.status_code)

def error_render(status_code, param=""):
    """
    If there's an error, use this to choose what message to display.
    :param status_code: The status code associated with the error (HTTP 404, HTTP 429, etc.)
    :param param: Paramters that might be needed to correctly display an error message.
    :return: A render_template object for Flask to render.
    """
    errorMsg = ""
    if status_code == 400: #Bad request -- something is wrong with my code, show an error, DO NOT keep making calls
        errorMsg = "Either something is wrong with the way I made this website, or you didn't enter a summoner name."
    elif status_code == 401: #Unauthorized -- my api key isn't valid, show a page for this
        errorMsg = "Something is wrong with my access to Riot's database."
    elif status_code == 404:
        errorMsg = u"No user with the name {0} found.".format(param)
    elif status_code == 429:
        errorMsg = "For some reason, I am running very slow today (I should go buy boots!) Please try again later."
    else:
        errorMsg = "I'm not quite sure what went wrong!"

    return render_template("failure.html", error_code=status_code, error=errorMsg)

if __name__ == '__main__':
    app.run()

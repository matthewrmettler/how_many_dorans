from flask import Flask, request, render_template
from api_calls import user_exists
from format import createItemSet
app = Flask(__name__, static_url_path="")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/results', methods=['POST'])
def results():
    id = user_exists(request.form['username'])
    if not hasattr(id, 'status_code'):
        call = createItemSet(id)
        if not hasattr(call, 'status_code'):
            item_set = call[0]
            match_count = call[1]
            return render_template("results.html", username=request.form['username'], items=item_set, matches=match_count)
        else:
            return error_render(id.status_code, request.form['username'])
    else:
        return error_render(id.status_code, request.form['username'])

def error_render(status_code, param):
    if status_code == 400: #Bad request -- something is wrong with my code, show an error, DO NOT keep making calls
        errorMsg = "(400) Something is wrong with the way I made this website."
    if status_code == 401: #Unauthorized -- my api key isn't valid, show a page for this
        errorMsg = "(401) Something is wrong with my access to Riot's database."
    if status_code == 404:
        errorMsg = "(404) No user with the name {0} found.".format(param)
    else:
        errorMsg = "({0}) I'm not quite sure what went wrong!".format(status_code)

    return render_template("failure.html", error_code=status_code, error=errorMsg)

if __name__ == '__main__':
    app.run()

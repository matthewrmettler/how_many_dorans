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
    if id:
        call = createItemSet(id)
        print("createItemSet finished")
        item_set = call[0]
        match_count = call[1]
        print(match_count)
        return render_template("results.html", username=request.form['username'], items=item_set, matches=match_count)
    else:
        return render_template("failure.html", username=request.form['username'])


if __name__ == '__main__':
    app.run()

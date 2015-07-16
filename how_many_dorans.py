from flask import Flask, request, render_template
from api_calls import user_exists
from render import createItemSet
app = Flask(__name__, static_url_path="")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/results', methods=['POST'])
def results():
    #error = None
    id = user_exists(request.form['username'])
    if id:
        item_set = createItemSet(id)
        return render_template("results.html", username=request.form['username'], items=item_set)
    else:
        return render_template("failure.html", username=request.form['username'])


if __name__ == '__main__':
    app.run()

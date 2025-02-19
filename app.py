from flask import Flask, render_template, request
import main  # 导入 main.py 中的函数

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    bad_list = None

    if request.method == "POST":
        csrf_token = request.form["csrf_token"]
        cookie = request.form["cookie"]
        apikey = request.form["apikey"]
        oid = request.form["oid"]

        # 调用 main.py 中的函数
        data_list = main.parse_comments(oid, csrf_token, cookie)

        if data_list:
            # 调用 main.py 中的函数判断恶意评论
            bad_list = main.filter_non_positive_comments(data_list, apikey)

    return render_template("index.html", bad_list=bad_list)


if __name__ == "__main__":
    app.run(debug=True)

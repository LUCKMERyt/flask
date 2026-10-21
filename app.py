from flask import Flask, request, render_template
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://myuser:1234@127.0.0.1:3306/myapp"
)

db = SQLAlchemy(app)


from sqlalchemy import text
with app.app_context():
    try:
        db.session.execute(text("SELECT 1"))
        print(f"\033[1;3;4;92m Подключение к базе успешно выполнено \033[0m")
    except Exception as e:
        print(f"\033[1;3;4;91m Ошибка подключения: {e}\033[0m")





@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # проверка логина и пароля
        return 'Вы вошли в систему!'
    else:

        return render_template('login.html')

@app.route('/user/<username>-<int:user_id>')
def user_profile(username, user_id):
    return (
        f"<h1>Это профиль пользователя {username}.</h1>"
        f'<h2 style="color: red;">С ID {user_id}. Привет!</h2>'
    )

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/neo')
def neo():
    return render_template('neo.html')

@app.route('/comm')
def comm():
    return render_template('comm.html')



if __name__ == '__main__':
    app.run(debug=True)

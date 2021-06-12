from flask import  redirect, session, render_template, url_for, g, request
from flask_restful import Resource
from flask_mail import Message
from os import getcwd, path, environ
import hashlib
import logging
from mooncaker.forms import AdminForm, ConsoleForm
from mooncaker import app, mail, api_key_queue

# set REST API
# @deprecated
# class ApiKeyUpdate(Resource):
#     def put(self):
#         global API_KEY
#         with api_lock:
#             API_KEY = request.form['data']
#             logging.info("Received a new API key")
#             api_condition.notify()
        
#         return {"result": "ok"}


# api.add_resource(ApiKeyUpdate, '/set_api_key') #deprecated
# api.add_resource(DownloadLog, '/get_log') #deprecated

@app.before_request
def before_request():
    g.user = None
    if 'user' in session:
        g.user = session['user']

@app.route('/')
def hello_world():
    return redirect("https://mooncaker.theboringbakery.com", code=302)

@app.route('/send_suggestion/', methods=['POST'])
def send_suggestion():
    text = "Either this is a test or something went wrong with the parsing of the suggestion, see server log for further information"
    text = str(request.form)
    msg = Message(subject="A suggestion was submitted for Mooncaker!",
                  body=text,
                  sender=environ['mail-user'],
                  recipients=environ['mail-recipients'].split(" "))
    mail.send(msg)
    return {"result": "ok"}


@app.route("/admin/", methods=['GET', 'POST'])
def admin():
    form = AdminForm()
    if form.validate_on_submit():
        session.pop('user', None)
        if form.username.data == app.config['ADMIN_USER']:
            unhashed_password = form.password.data
            hashed_password = hashlib.pbkdf2_hmac('sha256', unhashed_password.encode('utf-8'), app.config['SALT'], 100000)
            if hashed_password == app.config['ADMIN_PASS']:
                session['user'] = form.username.data
                return redirect(url_for('console'))
            else:
                form.password.errors.append("Wrong password")
        else:
            form.username.errors.append("Wrong username")

    return render_template("admin.html", form=form)

def parse_command(command, args):
    if command == "set-api-key":
        api_key_queue.put(args[0])
        logging.info("mooncaker: Received a new API key")
        return 'New API key set correctly'
    elif command == "get-log":
        with open(path.join(getcwd(), app.config['LOG_FILENAME'])) as logfile:
            return "<br>".join(logfile.readlines())
    elif command == "help":
        return "Currently available commands are: <br> set-api-key [key] <br> get-log <br>"
    return 'Something when wrong parsing your command. Please report to the admins'

@app.route('/console/', methods=['GET', 'POST'])
def console():
    if g.user is not None:
        form = ConsoleForm()
        string_back = parse_command("help", [])
        if form.validate_on_submit():
            string_back = 'Something when wrong parsing your command. Please report to the admins' #string to send back
            command = str(form.command.data).split()[0].lower()
            args = str(form.command.data).split()[1:] #remove first command
            string_back = parse_command(command, args)
            string_back += "<br>"
        return render_template('console.html', form=form, response=string_back)
    return redirect(url_for('admin'))

from functools import partial
import hashlib
from logging import WARNING, INFO, DEBUG
from flask import redirect, session, render_template, url_for, g, request, send_file
from flask_restful import Resource
from flask_mail import Message
from flask_app.forms import AdminForm, ConsoleForm
from flask_app import app, mail, api_key_queue
from mooncaker.external_tools.logger import log as log_raw
from mooncaker.external_tools.logger import get_log
from mooncaker.external_tools.db_interactor import Database

log = partial(log_raw, "mooncaker")

# set REST API
# @deprecated
# class ApiKeyUpdate(Resource):
#     def put(self):
#         global API_KEY
#         with api_lock:
#             API_KEY = request.form['data']
#             logging.getLogger(LOGGER_NAME).info("Received a new API key")
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
    log(INFO, "A suggestion was submitted")
    if 'HTTP_ORIGIN' not in request.environ or request.environ['HTTP_ORIGIN'] != 'https://mooncaker.theboringbakery.com':
        log(WARNING, "A suggestion from a non-approved domain was made")
        return "<h1>We are sorry but we cannot validate the origin of this request, please visit theboringbakery.com for the correct interaction.</h1>"

    text = str(request.form)
    msg = Message(subject="Mooncaker: suggestion made",
                  body=text,
                  sender=app.config['MAIL_USERNAME'],
                  recipients=app.config['MAIL_RECIPIENTS'])
    mail.send(msg)
    # send automatic response
    msg = Message(subject="Mooncaker: thanks for your suggestion!",
                  body=f"Dear {request.form['username']},\n"
                  + f"we've received your suggestion about {request.form['reason']}.\n"
                  + "We really value your feedback and we'll do our best to "
                  + "follow all of your suggestions in the shortest amount of time possible."
                  + "Kind regards,\n The Mooncaker developers team",
                  sender=app.config['MAIL_USERNAME'],
                  recipients=request.form['email'])
    mail.send(msg)
    log(INFO, "The suggestion was successfully sent")
    return redirect("https://mooncaker.theboringbakery.com/#/response_suggestion", code=301)


@app.route("/admin/", methods=['GET', 'POST'])
def admin():
    form = AdminForm()
    if form.validate_on_submit():
        session.pop('user', None)
        if form.username.data == app.config['ADMIN_USER']:
            unhashed_password = form.password.data
            hashed_password = hashlib.pbkdf2_hmac('sha256',
                                                  unhashed_password.encode('utf-8'),
                                                  app.config['SALT'], 100000)
            if hashed_password == app.config['ADMIN_PASS']:
                session['user'] = form.username.data
                return redirect(url_for('console'))
            else:
                form.password.errors.append("Wrong password")
        else:
            form.username.errors.append("Wrong username")

    return render_template("admin.html", form=form)


def parse_command(command, args):
    # todo: implement database queries
    if command == "set-api-key":
        api_key_queue.put(args[0])
        log(INFO, "Received a new API key")
        return 'New API key set correctly'
    elif command == "get-log":
        return "<br>".join(get_log())
    elif command == "get-data":
        return f'You can download the file <a href="{url_for("download_data")}" target="_blank" rel="noopener noreferrer">here</a>'
    elif command == "help":
        return "Currently available commands are: <br> set-api-key [key] <br> get-log <br> get-data <br>"
    return 'Something when wrong parsing your command. Please report to the admins'


@app.route("/data")
def download_data():
    if g.user is not None:
        matches_filename = Database(app.config['DB_URL']).create_matches_csv()
        return send_file(matches_filename, as_attachment=True)
    return redirect(url_for('admin'))


@app.route('/console/', methods=['GET', 'POST'])
def console():
    if g.user is not None:
        form = ConsoleForm()
        string_back = parse_command("help", [])
        if form.validate_on_submit():
            string_back = 'Something when wrong parsing your command. Please report to the admins' # string to send back
            command = str(form.command.data).split()[0].lower()
            args = str(form.command.data).split()[1:]  # remove first command
            string_back = parse_command(command, args)
            string_back += "<br>"
        return render_template('console.html', form=form, response=string_back)
    return redirect(url_for('admin'))

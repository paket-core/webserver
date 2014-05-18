#!./py2/bin/python

import db

from flask import(
        Flask,
        render_template,
        request,
        g,
        session,
        flash,
        redirect,
        url_for,
        abort,
        current_app
)
app = Flask(__name__)
app.config.update(
    SECRET_KEY = 'botavibi',
    DEBUG = True
)

# Openid handling, directly lifted from the flask-openid repo.
# TODO move this shit to another file.
from flask.ext.openid import OpenID
from openid.extensions import pape
oid = OpenID(app, safe_roots=[], extension_responses=[pape.Response])

@app.before_request
def before_request():
    g.user = None
    if 'openid' in session:
        g.user = db.User.query.filter_by(openid=session['openid']).first()

@app.after_request
def after_request(response):
    db.session.remove()
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    """Does the login via OpenID.  Has to call into `oid.try_login`
    to start the OpenID machinery.
    """
    # if we are already logged in, go back to were we came from
    if g.user is not None:
        return redirect(oid.get_next_url())
    if request.method == 'POST':
        openid = request.form.get('openid')
        if openid:
            pape_req = pape.Request([])
            return oid.try_login(openid, ask_for=['email', 'nickname'],
                                         ask_for_optional=['fullname'],
                                         extensions=[pape_req])
    return render_template('login.html', next=oid.get_next_url(),
                           error=oid.fetch_error())

@oid.after_login
def create_or_login(resp):
    """This is called when login with OpenID succeeded and it's not
    necessary to figure out if this is the users's first login or not.
    This function has to redirect otherwise the user will be presented
    with a terrible URL which we certainly don't want.
    """
    session['openid'] = resp.identity_url
    if 'pape' in resp.extensions:
        pape_resp = resp.extensions['pape']
        session['auth_time'] = pape_resp.auth_time
    user = db.User.query.filter_by(openid=resp.identity_url).first()
    if user is not None:
        flash(u'Successfully signed in')
        g.user = user
        return redirect(oid.get_next_url())
    return redirect(url_for('create_profile', next=oid.get_next_url(),
                            name=resp.fullname or resp.nickname,
                            email=resp.email))

@app.route('/create-profile', methods=['GET', 'POST'])
def create_profile():
    """If this is the user's first login, the create_or_login function
    will redirect here so that the user can set up his profile.
    """
    if g.user is not None or 'openid' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        if not name:
            flash(u'Error: you have to provide a name')
        elif '@' not in email:
            flash(u'Error: you have to enter a valid email address')
        else:
            flash(u'Profile successfully created')
            db.session.add(db.User(name, email, session['openid']))
            db.session.commit()
            return redirect(oid.get_next_url())
    return render_template('create_profile.html', next_url=oid.get_next_url())

@app.route('/profile', methods=['GET', 'POST'])
def edit_profile():
    """Updates a profile"""
    if g.user is None:
        abort(401)
    form = dict(name=g.user.name, email=g.user.email)
    if request.method == 'POST':
        if 'delete' in request.form:
            db.session.delete(g.user)
            db.session.commit()
            session['openid'] = None
            flash(u'Profile deleted')
            return redirect(url_for('index'))
        form['name'] = request.form['name']
        form['email'] = request.form['email']
        if not form['name']:
            flash(u'Error: you have to provide a name')
        elif '@' not in form['email']:
            flash(u'Error: you have to enter a valid email address')
        else:
            flash(u'Profile successfully created')
            g.user.name = form['name']
            g.user.email = form['email']
            db.session.commit()
            return redirect(url_for('edit_profile'))
    return render_template('edit_profile.html', form=form)

@app.route('/logout')
def logout():
    session.pop('openid', None)
    flash(u'You have been signed out')
    return redirect(oid.get_next_url())

# JSONp handler decorator
from functools import wraps
from json import dumps
def support_jsonp(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            content = str(callback) + '(' + dumps(f(*args, **kwargs)) + ')'
            return current_app.response_class(content, mimetype='application/json')
        else:
            return f(*args, **kwargs)
    return decorated_function

# JSONp methods

# Get specific delivery.
@app.route('/delivery.jsonp', methods=['GET', 'POST'])
@support_jsonp
def getdelivery():
    return db.deliveries[request.args.get('id')].data()

# Get deliveries for pickup in a radius around a center.
@app.route('/deliveriesinrange.jsonp', methods=['GET', 'POST'])
@support_jsonp
def getdeliveries_sourceinrange():
    print(float(request.args.get('lat')), float(request.args.get('lng')), float(request.args.get('radius')))
    return [
        key for key, delivery in db.deliveries.items()
        if delivery.source.distance([
            float(request.args.get('lat')),
            float(request.args.get('lng'))
        ]) < float(request.args.get('radius'))
    ]

if __name__ == '__main__':
    app.run(host='0.0.0.0')

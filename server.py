#!./py2/bin/python

import db

from sqlalchemy import exc

from werkzeug.utils import secure_filename

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

@app.route('/')
def index():
    return render_template('index.html')

# Openid handling, directly lifted from the flask-openid repo #
# TODO move this shit to another file (currently indented for foldout).
if True:
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
            return render_template('index.html')
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
        return render_template('index.html')

# Package sender.
@app.route('/send', methods=['GET', 'POST'])
def sendpackage():
    if g.user is None: abort(401)

    # If the form was not filled, show it.
    if not (
        'from' in request.args and
        'to' in request.args and
        len(request.args.get('from')) > 0 and
        len(request.args.get('to')) > 0
    ): return render_template('send.html')

    # Always save valid locations in the DB.
    try: from_ = db.Location(address=request.args.get('from'))
    except ValueError: flash('Could not resolve from address')
    else: db.session.add(from_)
    try: to_ = db.Location(address=request.args.get('to'))
    except ValueError: flash('Could not resolve to address')
    else: db.session.add(to_)
    db.session.commit()
    try: from_, to_
    except UnboundLocalError: return render_template('send.html')

    try: reward = int(request.args.get('reward'))
    except ValueError: reward = 0
    # Make sure the sender has enough money.
    if reward > g.user.balance:
        flash('Ha ha! You are too poor to send this.')
        return render_template('send.html')
    try: penalty = int(request.args.get('penalty'))
    except ValueError: penalty = 0

    # TODO: Create parcels more carefully.
    parcel = db.Parcel()
    db.session.add(parcel)
    db.session.commit()

    delivery = db.Delivery(g.user, parcel, from_, to_, reward, penalty)
    g.user.balance -= reward
    db.session.add(delivery)
    db.session.add(g.user)
    db.session.commit()
    flash(
        "sending parcel from %s to %s" % (
            request.args.get('from'),
            request.args.get('to')
        )
    )
    return render_template('send.html', delivery=delivery)

# Package id.
@app.route('/id', methods=['GET', 'POST'])
def packageid():
    return render_template('id.html')

# Package grabber.
@app.route('/take', methods=['GET', 'POST'])
def takepackage():
    if g.user is None: abort(401)

    try:
        delivery = delivery=db.Delivery.query.filter_by(id=request.args.get('id')).one()
    except exc.SQLAlchemyError:
        flash('no such delivery')
        return render_template('index.html')

    if delivery.status != db.Delivery.STATUSES['CREATED']:
        flash('delivery no longer available')
        return render_template('index.html')

    # This is a user's second request of this page, after confirmation.
    if 'ok' in request.args:
        if delivery.penalty > g.user.balance:
            flash('Ha ha! You are too poor to take this, consider joining the klan.')
            return render_template('index.html')
        g.user.balance -= delivery.penalty
        delivery.take(g.user)

        db.session.add(g.user)
        db.session.add(delivery)
        db.session.commit()

        flash('Delivery taken, you best be on your way.')
        return redirect(url_for('deliveries'))

    # This is the user's first request of this page, ask for confirmation.
    return render_template('take.html', delivery=delivery)

# Package depositer.
from os import remove
@app.route('/give', methods=['GET', 'POST'])
def givepackage():
    if g.user is None: abort(401)

    try:
        delivery = delivery=db.Delivery.query.filter_by(id=request.args.get('id')).one()
    except exc.SQLAlchemyError:
        flash('no such delivery')
        return render_template('index.html')

    if(
        delivery.status != db.Delivery.STATUSES['TAKEN'] or
        delivery.courier != g.user
    ):
        flash('This delivery is not yours to deliver')
        return render_template('index.html')

    # This is a user's second request of this page, after confirmation.
    if 'ok' in request.form:
        proof = request.files['proof']
        if proof:
            filename = secure_filename(proof.filename)
            proof.save(filename)
            with open(filename, 'rb', buffering=0) as proof:
                delivery.receive(proof.read())
                g.user.balance += delivery.penalty + delivery.reward

                db.session.add(g.user)
                db.session.add(delivery)
                db.session.commit()

                flash('Delivery received, you are now rich.')

            remove(filename)
            return redirect(url_for('deliveries'))
        else: flash('Please attach proof of delivery.')

    # This is the user's first request of this page, ask for confirmation.
    return render_template('give.html', delivery=delivery)

# Package shower.
@app.route('/deliveries')
def deliveries():
    if g.user is None: abort(401)
    taken = db.Delivery.query.filter_by(
        courierid=g.user.id,
        status=db.Delivery.STATUSES['TAKEN']
    ).all()
    fromme = db.Delivery.query.filter_by(senderid=g.user.id)
    waiting = fromme.filter_by(status=db.Delivery.STATUSES['CREATED']).all()
    enroute = fromme.filter_by(status=db.Delivery.STATUSES['TAKEN']).all()
    delivered = fromme.filter_by(status=db.Delivery.STATUSES['RECEIVED']).all()
    return render_template(
        'deliveries.html',
        taken=taken,
        waiting=waiting,
        enroute=enroute,
        delivered=delivered
    )

# JSONp handler decorator.
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
            return dumps(f(*args, **kwargs))
    return decorated_function

# AJAX methods #

# Get specific delivery.
@app.route('/getdelivery', methods=['GET', 'POST'])
@support_jsonp
def getdelivery():
    return db.Delivery.query.filter_by(id=request.args.get('id')).one().data()

# Get deliveries with point of interest for pickup in a radius around a center.
@app.route('/deliveriesinrange', methods=['GET', 'POST'])
@support_jsonp
def getdeliveriesinrange():
    lat = float(request.args.get('lat'))
    lng = float(request.args.get('lng'))
    radius = float(request.args.get('radius'))
    if u'to' == request.args.get('pointofinterest'):
        pointofinterest = lambda d: d.to_
    else:
        pointofinterest = lambda d: d.from_

    return {
        delivery.id: delivery.data() for delivery in db.Delivery.query.all()
        if pointofinterest(delivery).distance([lat, lng]) < float(radius)
    }

@app.route('/deliveriescountinrange.jsonp', methods=['GET', 'POST'])
@support_jsonp
def getdeliveriescount_sourceinrange():
    print(float(request.args.get('lat')), float(request.args.get('lng')), float(request.args.get('radius')))
    return len(getdeliveriesarrayinrange(request.args.get('lat'), request.args.get('lng'), request.args.get('radius')))

@app.route('/deliveriesinrange.jsonp', methods=['GET', 'POST'])
@support_jsonp
def getdeliveries_sourceinrange():
    print(float(request.args.get('lat')), float(request.args.get('lng')), float(request.args.get('radius')))
    return getdeliveriesarrayinrange(request.args.get('lat'), request.args.get('lng'), request.args.get('radius'))


@app.route('/verify', methods=['GET', 'POST'])
@support_jsonp
def verifyuser():
    return db.User.query.filter_by(email=request.args.get('email')).first()

if __name__=='__main__':
    app.run(host='0.0.0.0')

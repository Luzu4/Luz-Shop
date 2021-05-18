from flask import Flask, render_template, redirect, url_for, request, jsonify, abort, flash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
from flask_ckeditor import CKEditor
from flask_login import login_user, LoginManager, current_user, logout_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
import stripe

app = Flask(__name__)
app.secret_key = 'Yo'
Bootstrap(app)
ckeditor = CKEditor(app)
login_manager = LoginManager()
login_manager.init_app(app)
app.config[
    'STRIPE_PUBLIC_KEY'] = 'YOUR_PUBLIC_KEY'
app.config[
    'STRIPE_SECRET_KEY'] = 'YOU_SECRET_KEY'
stripe.api_key = app.config['STRIPE_SECRET_KEY']
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///LuzShop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Create Database for Users and Cart


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    products_in_cart = relationship('Cart', back_populates="parent")


class Cart(db.Model):
    __tablename__ = 'cart'
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    price_id = db.Column(db.String)
    quantity = db.Column(db.Integer)
    parent = relationship('User', back_populates="products_in_cart")


db.create_all()


# Prepare forms for wtf quickform
class Register(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')


class Login(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = Register()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Mail Already Exist!')
            return render_template('register.html', form=form)
        else:
            new_user = User(
                name=form.name.data,
                email=form.email.data,
                password=generate_password_hash(form.password.data,
                                                method='pbkdf2:sha256',
                                                salt_length=8)
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('home'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['POST', 'GET'])
def login():
    form = Login()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if user is None:
            flash('Incorrect username or password.')
        else:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('home'))
            else:
                flash('Incorrect username or password.')
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

# Payment process with Stripe
@app.route('/stripe_pay')
def stripe_pay():
    line_items = []
    for article in Cart.query.filter_by(buyer_id=current_user.id):
        line_items.append({'price': article.price_id, 'quantity': article.quantity})
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=url_for('cancel', _external=True),
    )
    return {'checkout_session_id': session['id'],
            'checkout_public_key': app.config['STRIPE_PUBLIC_KEY']}

# Every time when user is adding smth to cart we want to save in in his own cart.
@app.route('/add_to_cart/<int:quantity>/<string:price_id>')
def add_to_cart(quantity, price_id):
    new_product_in_cart = Cart(
        price_id=price_id,
        quantity=quantity,
        parent=current_user)
    db.session.add(new_product_in_cart)
    db.session.commit()
    return {}

# If payment will success, we are clearing his cart.
@app.route('/success')
def success():
    items_to_delete = Cart.query.filter_by(buyer_id=current_user.id).all()
    for items in items_to_delete:
        db.session.delete(items)
        db.session.commit()
    current_user_id = current_user.get_id()
    all_users = db.session.query(User).all()
    product_list = stripe.Product.list()
    price_list = stripe.Price.list()
    cart_products = Cart.query.filter_by(buyer_id=current_user_id)
    return render_template('success.html', product_list=product_list, price_list=price_list,
                           cart_products=cart_products, user_id=current_user_id,
                           logged_in=current_user.is_authenticated, users=all_users)

# If payment is unsuccessful, an error message will appear and the shopping cart will remain unchanged
@app.route('/cancel')
def cancel():
    current_user_id = current_user.get_id()
    all_users = db.session.query(User).all()
    product_list = stripe.Product.list()
    price_list = stripe.Price.list()
    cart_products = Cart.query.filter_by(buyer_id=current_user_id)
    return render_template('cancel.html', product_list=product_list, price_list=price_list,
                           cart_products=cart_products, user_id=current_user_id,
                           logged_in=current_user.is_authenticated, users=all_users)


@app.route('/', methods=['POST', 'GET'])
def home():
    current_user_id = current_user.get_id()
    all_users = db.session.query(User).all()
    product_list = stripe.Product.list()
    price_list = stripe.Price.list()
    cart_products = Cart.query.filter_by(buyer_id=current_user_id)
    return render_template('home.html', product_list=product_list, price_list=price_list,
                           cart_products=cart_products, user_id=current_user_id,
                           logged_in=current_user.is_authenticated, users=all_users)


@app.route('/product/<string:product_id>')
def product(product_id):
    cart_products = Cart.query.filter_by(buyer_id=current_user.id)
    product_list = stripe.Product.list()
    price_list = stripe.Price.list()
    current_user_id = current_user.get_id()
    all_users = db.session.query(User).all()
    return render_template('product.html', product_list=product_list, price_list=price_list,
                           product_id=product_id, cart_products=cart_products,
                           user_id=current_user_id, logged_in=current_user.is_authenticated, users=all_users)


@app.route('/delete_from_cart/<string:id>')
def delete_from_cart(id):
    item_to_delete = Cart.query.get(id)
    db.session.delete(item_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/stripe_webhook', methods=['POST'])
def stripe_webhook():
    print('WEBHOOK CALLED')
    if request.content_length > 1024 * 1024:
        print('REQUEST TOO BIG')
        abort(400)
    payload = request.get_data()
    sig_header = request.environ.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = 'whsec_T25E1AFwvnu2fWsTvUQL0O3iV4mrKMFj'
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        print('INVALID PAYLOAD')
        return {}, 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print('INVALID SIGNATURE')
        return {}, 400

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        print(session)
        line_items = stripe.checkout.Session.list_line_items(session['id'], limit=1)
        print(line_items['data'][0]['description'])
    return {}


if __name__ == '__main__':
    app.run(debug=True)

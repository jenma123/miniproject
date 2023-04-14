import csv
from datetime import datetime
import random

import random
from flask import Flask, render_template, redirect, url_for,session
from flask_sqlalchemy import SQLAlchemy
from flask_user.forms import RegisterForm
from wtforms.validators import NumberRange,Regexp
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_uploads import UploadSet, configure_uploads, IMAGES
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, PasswordField,HiddenField,SelectField
from flask_wtf.file import FileField, FileAllowed
from flask_user import UserManager, UserMixin, SQLAlchemyAdapter, login_required,roles_required,current_user
from flask_mail import  Mail 
from flask_msearch import Search


app = Flask(__name__)


photos = UploadSet('photos', IMAGES)

app.config['UPLOADED_PHOTOS_DEST'] = 'images'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///greenthumb.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'mysecret'
app.config['CSRF_ENABLED'] = True 
app.config['USER_AFTER_LOGOUT_ENDPOINT'] = 'index'
app.config['USER_AFTER_LOGIN_ENDPOINT'] = 'profile'
app.config['USER_AFTER_REGISTER_ENDPOINT'] = 'user.login'
app.config['USER_AFTER_CONFIRM_ENDPOINT'] = 'user.login'
app.config['USER_AFTER_CHANGE_PASSWORD_ENDPOINT'] = 'user.logout'
app.config['USER_AFTER_CHANGE_USERNAME_ENDPOINT'] = 'user.login'
app.config['USER_ENABLE_EMAIL'] = True 
app.config['USER_APP_NAME'] = 'Green Thumb !'
app.config.from_pyfile('config.cfg')

db = SQLAlchemy(app)
search = Search()
search.init_app(app)
mail = Mail(app)
class User(db.Model, UserMixin):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')
    
    active = db.Column(db.Boolean(), nullable=False, server_default='1')
    email = db.Column(db.String(255), nullable=False, unique=True)
    
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary='user_roles')
class Role(db.Model):
        __tablename__ = 'roles'
        id = db.Column(db.Integer(), primary_key=True)
        name = db.Column(db.String(50), unique=True)
class UserRoles(db.Model):
        __tablename__ = 'user_roles'
        id = db.Column(db.Integer(), primary_key=True)
        user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
        role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))

db.create_all()
db_adapter = SQLAlchemyAdapter(db, User)
user_manager = UserManager(db_adapter, app)
if not User.query.filter(User.email == 'admin@example.com').first():
        user = User(
            username='admin',
            email='admin@example.com',
            confirmed_at=datetime.now(),
            password=user_manager.hash_password('admin'),
        )
    
        user.roles.append(Role(name='Admin'))
        db.session.add(user)
        db.session.commit()

configure_uploads(app, photos)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    price = db.Column(db.Integer)
    stock = db.Column(db.Integer)
    description = db.Column(db.String(500))
    image = db.Column(db.String(100))
    
    orders = db.relationship('Order_Item', backref='product', lazy=True)
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(5))
    first_name = db.Column(db.String(20))
    last_name = db.Column(db.String(20))
    phone_number = db.Column(db.Integer)
    email = db.Column(db.String(50))
    address = db.Column(db.String(100))
    city = db.Column(db.String(100))
    state = db.Column(db.String(20))
    country = db.Column(db.String(20))
    status = db.Column(db.String(10))
    payment_type = db.Column(db.String(10))
    items = db.relationship('Order_Item', backref='order', lazy=True)
    def order_total(self):
        return db.session.query(db.func.sum(Order_Item.quantity * Product.price)).join(Product).filter(Order_Item.order_id == self.id).scalar() + 100
    def quantity_total(self):
        return db.session.query(db.func.sum(Order_Item.quantity)).filter(Order_Item.order_id == self.id).scalar()

class Order_Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
class Checkout(FlaskForm):
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    phone_number = StringField('Number')
    email = StringField('Email')
    address = StringField('Address')
    city = StringField('City')
    state = SelectField('State', choices=[('KL', 'Kerala')])
    district = SelectField('District', choices=[('Ktym', 'Kottayam'), ('Idk', 'Idukki'), ('Ptm', 'Pathanamthitta')])
    pincode = StringField('Pincode')
    payment_type = SelectField('Payment Type', choices=[('COD', 'Cash On Delivery'), ('UPI', 'UPI')])
 
class AddProduct(FlaskForm):
    name = StringField('Name',validators=[Regexp('[a-zA-Z ]',message="Only alphabets ae allowed")])
    price = IntegerField('Price',validators=[NumberRange(min=1)])
    stock = IntegerField('Price',validators=[NumberRange(min=0)])
    description = TextAreaField('Description',validators=[Regexp('[a-zA-Z ]',message="Only alphabets ae allowed")])
    image = FileField('Image', validators=[FileAllowed(IMAGES, message= 'Only images are accepted.')])
class AddToCart(FlaskForm):
    quantity = IntegerField('Quantity')
    id = HiddenField('ID')
class AddUser(FlaskForm):
    username = StringField('Username')
    email = StringField('Email')
    password = StringField('Price')
class UpdateUser(FlaskForm):
    username = StringField('Username')
    email = StringField('Email')
    password = StringField('Price')

def handle_cart():
    products = []
    grand_total = 0
    index = 0
    quantity_total = 0

    for item in session['cart']:
        product = Product.query.filter_by(id=item['id']).first()

        quantity = int(item['quantity'])
        total = quantity * product.price
        grand_total += total
        quantity_total += quantity
        products.append({'id' : product.id, 'name' : product.name, 'price' :  product.price,'stock':product.stock ,'image' : product.image, 'quantity' : quantity, 'total': total, 'index': index})
        index += 1
    
    grand_total_plus_shipping = grand_total + 100
    return products, grand_total, grand_total_plus_shipping,quantity_total


    
@app.route('/')
def index():
    products = Product.query.all()

    return render_template('index.html', products=products)
@app.route('/compare')
def compare():
    with open ('indoorplants.csv',encoding="utf8") as csv_file:
     csv_reader=csv.DictReader(csv_file,delimiter=',')
     line_count=0
     product=[]
     rating=[]
   
     price=[]
     url=[]
     our=[]

     for row in csv_reader:
                product.append(row['product'])
                rating.append(row['rating'])
             
                price.append(row['price'])
                url.append(row['product url'])

    
   
                
    n=160
    for i in range(n):
        our.append(random.randint(100,500))

    csv_file.close() 
    

    return render_template('compare.html',product=product,rating=rating,price=price,url=url,our=our)




@app.route('/product/<id>')
@login_required
def product(id):

    product = Product.query.filter_by(id=id).first()
    form = AddToCart()
    return render_template('view-product.html', product=product,form = form)
@app.route('/profile')
@login_required
def profile():
     products = Product.query.all()
     return render_template('profile.html',products = products)
@app.route('/quick-add/<id>')
def quick_add(id):
    if 'cart' not in session:
        session['cart'] = []

    session['cart'].append({'id' : id, 'quantity' : 1})
    session.modified = True

    return redirect(url_for('cart'))
@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    if 'cart' not in session:
        session['cart'] = []
    form = AddToCart()
    if form.validate_on_submit():
        session['cart'].append({'id' : form.id.data, 'quantity' : form.quantity.data})
        session.modified = True
        session.permanent=True

    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    if 'cart' not in session:
        return  redirect(url_for('index'))
    products, grand_total, grand_total_plus_shipping, quantity_total = handle_cart()

    return render_template('cart.html', products=products, grand_total=grand_total, grand_total_plus_shipping=grand_total_plus_shipping,quantity_total=quantity_total)
@app.route('/remove-from-cart/<index>')
def remove_from_cart(index):
    del session['cart'][int(index)]
    session.modified = True
    return redirect(url_for('cart'))
@app.route('/edit-cart',methods=['POST'])
def edit_cart():
    if 'cart' not in session:
        session['cart'] = []

    form = AddToCart()

    if form.validate_on_submit():

        session['cart'].append({'id' : form.id.data, 'quantity' : form.quantity.data})
        session.modified = True

    return redirect(url_for('cart'))
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    form = Checkout()
    products, grand_total, grand_total_plus_shipping, quantity_total  = handle_cart()

    if form.validate_on_submit():
        order = Order()
        form.populate_obj(order)
        order.reference = ''.join([random.choice('ABCDE') for _ in range(5)])
        order.status = 'PENDING'
        for product in products:
            order_item = Order_Item(quantity=product['quantity'], product_id=product['id'])
            order.items.append(order_item)
            product = Product.query.filter_by(id=product['id']).update({'stock' : Product.stock - product['quantity']})

        db.session.add(order)
        db.session.commit()

        session['cart'] = []
        session.modified = True
        
        return redirect(url_for('index'))

    return render_template('checkout.html', form=form, grand_total=grand_total, grand_total_plus_shipping=grand_total_plus_shipping, quantity_total=quantity_total)

  
@app.route('/admin')
@login_required
@roles_required('Admin')
def admin():
    products = Product.query.all()
    orders = Order.query.all()
    users = User.query.all()
    products_in_stock = Product.query.filter(Product.stock > 0).count()
    total_users = Product.query.filter(Product.stock > 0).count()

    return render_template('admin/index.html', admin=True, products=products,users=users,total_users=total_users, products_in_stock=products_in_stock,orders=orders)

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required

def add():
    form = AddProduct()

    if form.validate_on_submit():
        image_url = photos.url(photos.save(form.image.data))

        new_product = Product(name=form.name.data, price=form.price.data, stock=form.stock.data, description=form.description.data, image=image_url)

        db.session.add(new_product)
        db.session.commit()

        return redirect(url_for('admin'))

    return render_template('admin/add-product.html', admin=True, form=form)
@app.route('/admin/add-user', methods=['GET', 'POST'])
@login_required
def adduser():
    form = AddUser()

    if form.validate_on_submit():
        

        new_user = User(username=form.username.data, email=form.email.data, password=user_manager.hash_password( form.password.data),active =1,confirmed_at=datetime.now())

        db.session.add(new_user)
        db.session.commit()
        

        return redirect(url_for('admin'))

    return render_template('admin/add-user.html', admin=True, form=form)
@app.route('/admin/update', methods=['GET', 'POST'])
@login_required
def update(id):
    form = AddProduct()
    product = Product.query.filter_by(id=id).first()
    if product:
            db.session.delete(product)
            db.session.commit()
    new_product = Product(name=form.name.data, price=form.price.data, stock=form.stock.data, description=form.description.data, image=image_url)


    return render_template('update-product.html', product=product)


@app.route('/admin/order/<order_id>')
def order(order_id):
    order = Order.query.filter_by(id=int(order_id)).first()

    return render_template('admin/view-order.html', order=order, admin=True)
if __name__ == '__main__':
    app.run()
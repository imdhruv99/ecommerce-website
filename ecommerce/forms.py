import hashlib

import smtplib

from email.mime.multipart import MIMEMultipart

from email.mime.text import MIMEText

from flask import session

from flask import url_for, flash, redirect

from flask_wtf import FlaskForm

from wtforms import StringField, SubmitField, TextAreaField, IntegerField, RadioField, FloatField, SelectField

from flask_wtf.file import FileField, FileAllowed

from wtforms.validators import DataRequired, Length, Email

from ecommerce import mysql

from ecommerce.models import *


def getAllProducts():

    itemData = Product.query.join(ProductCategory, Product.productid == ProductCategory.productid) \
        .add_columns(Product.productid, Product.product_name, Product.discounted_price, Product.description,
                     Product.image, Product.quantity) \
        .join(Category, Category.categoryid == ProductCategory.categoryid) \
        .order_by(Category.categoryid.desc()) \
        .all()

    return itemData


def getCategoryDetails():

    itemData = Category.query.join(ProductCategory, Category.categoryid == ProductCategory.categoryid) \
        .join(Product, Product.productid == ProductCategory.productid) \
        .order_by(Category.categoryid.desc()) \
        .distinct(Category.categoryid) \
        .all()

    return itemData


def massageItemData(data):

    ans = []

    i = 0

    while i < len(data):

        curr = []

        for j in range(6):

            if i >= len(data):

                break

            curr.append(data[i])

            i += 1

        ans.append(curr)

    return ans


def is_valid(email, password):

    cur = mysql.connection.cursor()

    cur.execute("SELECT email, password FROM user")

    userData = cur.fetchall()

    cur.close()

    for row in userData:

        if row['email'] == email and row['password'] == hashlib.md5(password.encode()).hexdigest():

            return True

    return False


def getLoginUserDetails():

    productCountCartForGivenUser = 0

    if 'email' not in session:

        loggedIn = False

        firstName = ''

    else:

        loggedIn = True

        userid, firstName = User.query.with_entities(User.userid, User.fname).filter(
            User.email == session['email']).first()

        productCountinCart = []

        for cart in Cart.query.filter(Cart.userid == userid).all():

            productCountinCart.append(cart.productid)

            productCountCartForGivenUser = len(productCountinCart)

    return loggedIn, firstName, productCountCartForGivenUser


def getProductDetails(productId):

    productDetailsById = Product.query.filter(Product.productid == productId).first()

    return productDetailsById


def extractAndPersistUserDataFromForm(request):

    password = request.form['password']

    email = request.form['email']

    firstName = request.form['firstName']

    lastName = request.form['lastName']

    address1 = request.form['address1']

    address2 = request.form['address2']

    zipcode = request.form['zipcode']

    city = request.form['city']

    state = request.form['state']

    country = request.form['country']

    phone = request.form['phone']

    user = User(fname=firstName, lname=lastName, password=hashlib.md5(password.encode()).hexdigest(),
                address1=address1, address2=address2, city=city, state=state, country=country, zipcode=zipcode,
                email=email, phone=phone)

    db.session.add(user)

    db.session.flush()

    db.session.commit()

    return 'Registered Successfully'


def isUserLoggedIn():

    if 'email' not in session:

        return False

    else:

        return True


def isUserAdmin():

    if isUserLoggedIn():

        userId = User.query.with_entities(User.userid).filter(User.email == session['email']).first()

        currentUser = User.query.get_or_404(userId)

        return currentUser.isadmin


def extractAndPersistKartDetailsUsingSubquery(productId):

    userId = User.query.with_entities(User.userid).filter(User.email == session['email']).first()

    userId = userId[0]

    subQuery = Cart.query.filter(Cart.userid == userId).filter(Cart.productid == productId).subquery()

    qry = db.session.query(Cart.quantity).select_entity_from(subQuery).all()

    if len(qry) == 0:

        cart = Cart(userid=userId, productid=productId, quantity=1)

    else:

        cart = Cart(userid=userId, productid=productId, quantity=qry[0][0] + 1)

    db.session.merge(cart)

    db.session.flush()

    db.session.commit()


class addCategoryForm(FlaskForm):

    category_name = StringField('Category Name', validators=[DataRequired()])

    submit = SubmitField('Save')


class addProductForm(FlaskForm):

    category = SelectField('Category:', coerce=int, id='select_category')

    sku = IntegerField('Product SKU:', validators=[DataRequired()])

    productName = StringField('Product Name:', validators=[DataRequired()])

    productDescription = TextAreaField('Product Description:', validators=[DataRequired()])

    productPrice = FloatField('Product Price:', validators=[DataRequired()])

    productQuantity = IntegerField('Product Quantity:', validators=[DataRequired()])

    image = FileField('Product Image', validators=[FileAllowed(['jpg', 'png'])])

    submit = SubmitField('Save')


def getusercartdetails():

    userId = User.query.with_entities(User.userid).filter(User.email == session['email']).first()

    productsinCart = Product.query.join(Cart, Product.productid == Cart.productid) \
        .add_columns(Product.productid, Product.product_name, Product.discounted_price, Cart.quantity, Product.image) \
        .add_columns(Product.discounted_price * Cart.quantity) \
        .filter(Cart.userid == userId)

    totalSum = 0

    for row in productsinCart:
        totalSum += row[6]

    tax = ("%.2f" % (.06 * float(totalSum)))

    totalSum = float("%.2f" % (1.06 * float(totalSum)))

    return productsinCart, totalSum, tax

# Removes products from cart when user clicks remove

def removeProductFromCart(productId):

    userId = User.query.with_entities(User.userid).filter(User.email == session['email']).first()

    userId = userId[0]

    kwargs = {'userid': userId, 'productid': productId}

    cart = Cart.query.filter_by(**kwargs).first()

    if productId is not None:

        db.session.delete(cart)

        db.session.commit()

        flash("Product has been removed from cart !!")

    else:

        flash("failed to remove Product cart please try again !!")

    return redirect(url_for('cart'))


# flask form for checkout details

class checkoutForm(FlaskForm):

    fullname = StringField('Full Name',
                           validators=[DataRequired(), Length(min=2, max=20)])

    email = StringField('Email',
                        validators=[DataRequired(), Email()])

    address = TextAreaField('address',
                            validators=[DataRequired()])

    city = StringField('city',
                       validators=[DataRequired(), Length(min=2, max=20)])

    state = StringField('state',
                        validators=[DataRequired(), Length(min=2, max=20)])

    zip = StringField('zip',
                      validators=[DataRequired(), Length(min=2, max=6)])

    cctype = RadioField('cardtype')

    cardname = StringField('cardnumber',
                           validators=[DataRequired(), Length(min=12, max=12)])

    ccnumber = StringField('Credit card number',
                           validators=[DataRequired()])

    expmonth = StringField('Exp Month',
                           validators=[DataRequired(), Length(min=12, max=12)])

    expyear = StringField('Expiry Year',
                          validators=[DataRequired(), Length(min=4, max=4)])

    cvv = StringField('CVV',
                      validators=[DataRequired(), Length(min=3, max=4)])

    submit = SubmitField('MAKE PAYMENT')


# Gets form data for the sales transaction

def extractOrderdetails(request, totalsum):

    fullname = request.form['FullName']

    email = request.form['email']

    address = request.form['address']

    phone = request.form['phone']

    city = request.form['city']

    state = request.form['state']

    zipcode = request.form['zipcode']

    cctype = request.form['cardtype']

    ccnumber = request.form['cardnumber']

    cardname = request.form['cardname']

    expmonth = request.form['expmonth']

    expyear = request.form['expyear']

    provider = request.form['provider']

    cvv = request.form['cvv']

    orderdate = datetime.utcnow()

    userId = User.query.with_entities(User.userid).filter(User.email == session['email']).first()

    userId = userId[0]

    order = Order(order_date=orderdate, total_price=totalsum, userid=userId)

    db.session.add(order)

    db.session.flush()

    db.session.commit()

    orderid = Order.query.with_entities(Order.orderid).filter(Order.userid == userId).order_by(
        Order.orderid.desc()).first()

    # add details to ordered;
    #  products table

    addOrderedproducts(userId, orderid)

    # add transaction details to the table

    updateSalestransaction(totalsum, ccnumber, orderid, cctype)

    # remove ordered products from cart after transaction is successful

    removeordprodfromcart(userId)

    # sendtextconfirmation(phone,fullname,orderid)

    return (email, fullname, orderid, address, fullname, phone, provider)


# adds data to orderdproduct table

def addOrderedproducts(userId, orderid):

    cart = Cart.query.with_entities(Cart.productid, Cart.quantity).filter(Cart.userid == userId)

    for item in cart:

        orderedproduct = OrderedProduct(orderid=orderid, productid=item.productid, quantity=item.quantity)

        db.session.add(orderedproduct)

        db.session.flush()

        db.session.commit()


# removes all sold products from cart for the user

def removeordprodfromcart(userId):

    userid = userId

    db.session.query(Cart).filter(Cart.userid == userid).delete()

    db.session.commit()


# adds sales transaction

def updateSalestransaction(totalsum, ccnumber, orderid, cctype):

    salesTransaction = SaleTransaction(orderid=orderid, transaction_date=datetime.utcnow(), amount=totalsum,
                                       cc_number=ccnumber, cc_type=cctype, response="success")

    db.session.add(salesTransaction)

    db.session.flush()

    db.session.commit()


# sends email for order confirmation

def sendEmailconfirmation(email, username, ordernumber, phonenumber, provider):

    msg = MIMEMultipart()

    sitemail = "ecommerce@engineer.com"

    msg['Subject'] = "Your Order has been placed for " + username

    msg['From'] = sitemail

    msg['To'] = email

    text = "Hello!\nThank you for shopping with us.Your order No is:" +str(ordernumber[0])

    html = """\
        <html>
          <head></head>
          <body>
            <p><br>
               Please stay tuned for more fabulous offers and gadgets.You can visit your account for more details on this order.<br> 
               <br>Please write to us at <u>stargadgets@engineer.com</u> for any assistance.</br>
               <br></br>
               <br></br>
               Thank you!
               <br></br>
               StarGadgets Team          
            </p>
          </body>
        </html>
        """

    msg1 = MIMEText(text, 'plain')

    msg2 = MIMEText(html, 'html')

    msg.attach(msg1)

    msg.attach(msg2)

    server = smtplib.SMTP(host='smtp.mail.com', port=587)

    server.connect('smtp.mail.com', 587)

    # Extended Simple Mail Transfer Protocol (ESMTP) command sent by an email server to identify itself
    # when connecting to another email.

    server.ehlo()

    # upgrade insecure connection to secure

    server.starttls()

    server.ehlo()

    server.login("admin@admin.com", "admin@123")

    server.ehlo()

    server.sendmail(sitemail, email, msg.as_string())

    # hack to send text confirmation using emailsms gateway

    if (provider == "Tmobile"):

        phonenumber = phonenumber + "@tmomail.net"

    if (provider == "ATT"):

        phonenumber = phonenumber + "@txt.att.net"

    server.sendmail(sitemail, phonenumber, msg.as_string())

    server.quit()

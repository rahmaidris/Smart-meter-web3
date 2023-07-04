#!/usr/bin/python
# -*- coding: utf-8 -*-

#import flask dependencies for web GUI
from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from passlib.hash import sha256_crypt
from flask_mysqldb import MySQL
from functools import wraps
from hashlib import sha256
#import other functions and classes
from sqlhelpers import *
from forms import *

#other dependencies
import time

#initialize the app
app = Flask(__name__)

#configure mysql
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123'
app.config['MYSQL_DB'] = 'crypto'
app.config['MYSQL_UNIX_SOCKET'] = '/var/run/mysqld/mysqld.sock'  
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#initialize mysql
mysql = MySQL(app)

#wrap to define if the user is currently logged in from session
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("Unauthorized, please login.", "danger")
            return redirect(url_for('login'))
    return wrap

#log in the user by updating session
def log_in_user(username):
    users = Table("users", "name", "username", "email", "password")
    user = users.getone("username", username)

    session['logged_in'] = True
    session['username'] = username
    session['name'] = user.get('name')
    session['email'] = user.get('email')

#Registration page
@app.route("/register", methods = ['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    users = Table("users","address","name", "email", "username", "password")

    #if form is submitted
    if request.method == 'POST' and form.validate():
        #collect form data
        username = form.username.data
        email = form.email.data
        name = form.name.data

        #make sure user does not already exist
        if isnewuser(username):
            #add the user to mysql and log them in
            address= sha256((username+form.password.data).encode("utf-8")).hexdigest()[:20]
            password = sha256_crypt.encrypt(form.password.data)
            users.insert(address,name,email,username,password)
            log_in_user(username)
            return redirect(url_for('dashboard'))
        else:
            flash('User already exists', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html', form=form)

#Login page
@app.route("/login", methods = ['GET', 'POST'])
def login():
    #if form is submitted
    if request.method == 'POST':
        #collect form data
        username = request.form['username']
        candidate = request.form['password']

        #access users table to get the user's actual password
        users = Table("users", "name", "username", "email", "password")
        user = users.getone("username", username)
        accPass = user.get('password')

        #if the password cannot be found, the user does not exist
        if accPass is None:
            flash("Username is not found", 'danger')
            return redirect(url_for('login'))
        else:
            #verify that the password entered matches the actual password
            if sha256_crypt.verify(candidate, accPass):
                #log in the user and redirect to Dashboard page
                log_in_user(username)
                flash('You are now logged in.', 'success')
                return redirect(url_for('dashboard'))
            else:
                #if the passwords do not match
                flash("Invalid password", 'danger')
                return redirect(url_for('login'))

    return render_template('login.html')

#Transaction page
@app.route("/Profil", methods = ['GET', 'POST'])
@is_logged_in
def profil():
    form = ProfilForm(request.form)
    balance = get_consommation(session.get('username'))

    #if form is submitted
    if request.method == 'POST':
        try:
            #attempt to execute the transaction
            update_profil(session.get('username'), form.start.data, form.end.data)
            flash(" profile updated successfully !", "success")
        except Exception as e:
            flash(str(e), 'danger')

        return redirect(url_for('dashboard'))

    return render_template('Profil.html', balance=balance, form=form, page='Profil')

#Buy page
@app.route("/Transact", methods = ['GET', 'POST'])
@is_logged_in
def transact():
    form = TransactForm(request.form)
    users = Table("users","address","name", "email", "username", "password")
    username=session.get('username')
    user = users.getone("username", username)
        
    address =user.get('address') 
    balance = get_consommation(username)

    if request.method == 'POST':
        #attempt to transact amount
        try:
            send_amount(username, address, form.amount.data)
            flash("Transaction Successful!", "success")
        except Exception as e:
            flash(str(e), 'danger')

        return redirect(url_for('dashboard'))

    return render_template('Transact.html', balance=balance, form=form, page='Transact')


#logout the user. Ends current session
@app.route("/logout")
@is_logged_in
def logout():
    session.clear()
    flash("Logout success", "success")
    return redirect(url_for('login'))


#Dashboard page
@app.route("/dashboard")
@is_logged_in
def dashboard():
    balance = get_consommation(session.get('username'))
    blockchain,timelist = get_blockchain()[0].chain,get_blockchain()[1]

    ct = time.strftime("%I:%M %p")
    return render_template('dashboard.html', balance=balance, session=session, ct=ct, blockchain=blockchain,timelist=timelist,zip=zip, page='dashboard')

#Index page
@app.route("/")
@app.route("/index")
def index():
    return render_template('index.html')

#Run app
if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug = True)

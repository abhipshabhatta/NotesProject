from flask import Flask, render_template, request, jsonify, session, redirect, url_for, g, make_response
import sqlite3
import random
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'azerty'  

# SQLite - User Authentication

#create database

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('users.db')
        create_table(db)  # Create the table if it doesn't exist
    return db

def create_table(db):
    cursor = db.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users(
                    id INTEGER  PRIMARY KEY,
                    user_key TEXT,
                    username TEXT,
                    password TEXT NOT NULL,
                    email TEXT)''')
    db.commit()

def check_user_key(user_key):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''SELECT id , username FROM users WHERE user_key = ?''', (user_key,))
    user = cursor.fetchone()
    if user:
        return user
    else:
        return None
    
#close connection

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/users')
def view_users():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM users''')
    users = cursor.fetchall()

    result = "List of users : \n \n"
    for user in users:
        result += f'ID : {user[0]}, username : {user[1]}, password : {user[2]}, email : {user[3]} \n\n'

    return result

# MongoDB - Notes

client = MongoClient("mongodb://localhost:27017")
db = client['notes_db']
collection = db['notes']

#Notes routes

@app.route('/add_note', methods=['GET','POST'])
def add_note():
    user = check_user_key(request.cookies.get('user_key'))
    if user is None:
        return redirect('/login')
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        note = {
            'title' : title,
            'content': content,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'user_id': user[0]
        }
        result = collection.insert_one(note)
        return redirect(f'/notes/{result.inserted_id}')
    return render_template('add_note.html')


#display all notes

@app.route('/notes', methods=['GET'])
def get_notes():
    user = check_user_key(request.cookies.get('user_key'))
    if user is None:
        return redirect('/login')
    notes = list(collection.find())
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''SELECT id , username FROM users''')
    users = cursor.fetchall()
    return render_template('notes_list.html', notes=notes, users=dict(users),user=user)
    

#edit Note

@app.route('/edit_note/<note_id>', methods=['GET','POST'])
def edit_note(note_id):
    user = check_user_key(request.cookies.get('user_key'))
    if user is None:
        return redirect('/login')
    note = collection.find_one({'_id': ObjectId(note_id)})

    if note is None or note['user_id'] != user[0] :
        return redirect('/notes')
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        edited_note = {
        'title': title,
        'content': content,
        'updated_at': datetime.utcnow()
    }   
        result = collection.update_one({'_id': ObjectId(note_id)}, {'$set': edited_note})
        return redirect(f'/notes/{note_id}')
    return render_template('edit_note.html', note=note)
    
#display a note

@app.route('/notes/<note_id>', methods=['GET'])
def get_note(note_id):
    user = check_user_key(request.cookies.get('user_key'))
    if user is None:
        return redirect('/login')
    note = collection.find_one({'_id': ObjectId(note_id)})
    if note is None or note['user_id'] != user[0] :
        return redirect('/notes')
    return render_template('note.html',note=note,user=user)


#Delete Note    

@app.route('/delete_note/<note_id>', methods=['GET'])
def delete_note(note_id):
    user = check_user_key(request.cookies.get('user_key'))
    if user is None:
        return redirect('/login')
    note = collection.find_one({'_id': ObjectId(note_id)})
    if note  and note['user_id'] == user[0] :
        collection.delete_one({'_id': ObjectId(note_id)})
    return redirect('/notes')  
  
#Home route

@app.route('/')
def home():
    user = check_user_key(request.cookies.get('user_key'))
    if user:
        return render_template('home.html',user=user[1])
    else:
        return render_template('home.html')
    
#Login routes

@app.route('/login', methods=['GET', 'POST'])
def login():
    user = check_user_key(request.cookies.get('user_key'))
    if user:
        return redirect('/notes')
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''SELECT * FROM users WHERE username = ? AND password = ?''', (username, password))
        user = cursor.fetchone()
        if user:
            session['user'] = username
            response =  make_response(redirect('/notes'))
            response.set_cookie('user_key', user[1])
            return response
        else:
            return 'Invalid username or password. <a href="/signup">Sign up</a>'
    
    return render_template('login.html')
    

#Signup route

@app.route('/signup', methods=['GET', 'POST'])
def sign_up():
    user = check_user_key(request.cookies.get('user_key'))
    if user:
        return redirect('/notes')
    if request.method == 'POST':
        email  = request.form['email']
        username = request.form['username']
        password = request.form['password']
        user_key = ''
        for i in range(6):
            user_key.join(random.choice('abcdefghijklmnopqrstuvwxyz') ) 
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''INSERT INTO users (user_key, email , username ,  password) VALUES (?,?,?,?)''', (user_key,email,username, password))
        db.commit()
        response =  make_response(redirect('/login'))
        return response
        
    else:
        return render_template('signup.html')


if __name__ == '__main__':
    app.run(debug=True)
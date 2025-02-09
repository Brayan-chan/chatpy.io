from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from pymongo.mongo_client import MongoClient
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from pytz import timezone

load_dotenv('.env')
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('chat'))
    return render_template('index.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json
    sender = data.get('sender')
    receiver = data.get('receiver')
    message_type = data.get('type')
    message_content = data.get('message')
    if sender and receiver and message_content:
        timestamp = datetime.utcnow().replace(tzinfo=timezone('UTC')).isoformat()
        message_id = str(MiBaseDatos.mensajes.count_documents({}) + 1).zfill(4)
        try:
            MiBaseDatos.mensajes.insert_one({
                "_id": message_id,
                "sender": sender,
                "receiver": receiver,
                "type": message_type,
                "message": message_content,
                "sent_at": timestamp,
                "read_by": []
            })
            return jsonify({"status": "success"}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error", "message": "Invalid data"}), 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = MiBaseDatos.usuarios.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['_id']
            return redirect(url_for('chat'))
        return "Nombre de usuario o contraseña incorrectos"
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Encriptar la contraseña con la librería check_password_hash
        hashed_password = generate_password_hash(password)
        # zfill(4) para que el id sea de 4 dígitos
        user_id = str(MiBaseDatos.usuarios.count_documents({}) + 1).zfill(4)
        user = {
            "_id": user_id,
            "username": username,
            "password": hashed_password,
            "profile_pic": "default.png",
            "created_at": datetime.utcnow()
        }
        MiBaseDatos.usuarios.insert_one(user)
        session['user_id'] = user_id
        return redirect(url_for('chat'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/chat')
def chat():
    # Si no hay un usuario logueado, redirigir al index
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('chat.html')

@app.route('/get_messages', methods=['GET'])
def get_messages():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    user_id = session['user_id']
    messages = list(MiBaseDatos.mensajes.find({"$or": [{"sender": user_id}, {"receiver": user_id}]}))
    for message in messages:
        message['_id'] = str(message['_id'])
        utc_time = datetime.fromisoformat(message['sent_at'])
        local_time = utc_time.astimezone(timezone('America/Mexico_City'))
        message['sent_at'] = local_time.strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({"status": "success", "messages": messages}), 200

uri = os.getenv('MONGO_URI')

client = MongoClient(uri)

try:
    client.admin.command('ping')
    print("Pinged your deployment. You Sucessfully Connected to MongoDB!")
except Exception as e:
    print(e)

MiBaseDatos = client['chat']

# Crear la colección 'usuarios' si no existe
if 'usuarios' not in MiBaseDatos.list_collection_names():
    MiBaseDatos.create_collection('usuarios')

# Crear la colección 'mensajes' si no existe
if 'mensajes' not in MiBaseDatos.list_collection_names():
    MiBaseDatos.create_collection('mensajes')

print(MiBaseDatos)

collection = MiBaseDatos['chat']

print(MiBaseDatos.list_collection_names())

# Comentar la inserción manual de documentos
# MiBaseDatos.notes.insert_one({"Nombre":"Mi nota desde colab", "Contenido": "Esta es mi primera nota desde vsc"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=True)
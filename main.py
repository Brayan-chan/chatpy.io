from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room
from pymongo.mongo_client import MongoClient
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from pytz import timezone

load_dotenv('.env')
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
socketio = SocketIO(app)

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
        hashed_password = generate_password_hash(password)
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
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user = MiBaseDatos.usuarios.find_one({"_id": session['user_id']})
    return render_template('chat.html', user=user)

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

@app.route('/get_messages_with/<contact_id>', methods=['GET'])
def get_messages_with(contact_id):
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    user_id = session['user_id']
    messages = list(MiBaseDatos.mensajes.find({
        "$or": [
            {"sender": user_id, "receiver": contact_id},
            {"sender": contact_id, "receiver": user_id}
        ]
    }))
    for message in messages:
        message['_id'] = str(message['_id'])
        utc_time = datetime.fromisoformat(message['sent_at'])
        local_time = utc_time.astimezone(timezone('America/Mexico_City'))
        message['sent_at'] = local_time.strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({"status": "success", "messages": messages}), 200

@app.route('/get_group_messages/<group_id>', methods=['GET'])
def get_group_messages(group_id):
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    messages = list(MiBaseDatos.mensajes.find({"receiver": group_id, "type": "group"}))
    for message in messages:
        message['_id'] = str(message['_id'])
        utc_time = datetime.fromisoformat(message['sent_at'])
        local_time = utc_time.astimezone(timezone('America/Mexico_City'))
        message['sent_at'] = local_time.strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({"status": "success", "messages": messages}), 200

@app.route('/add_contact', methods=['POST'])
def add_contact():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json
    user_id = session['user_id']
    contact_username = data.get('contact_username')
    contact = MiBaseDatos.usuarios.find_one({"username": contact_username})
    if contact:
        contact_id = contact['_id']
        try:
            MiBaseDatos.contactos.update_one(
                {"_id": user_id},
                {"$addToSet": {"contacts": contact_id}},
                upsert=True
            )
            return jsonify({"status": "success"}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404

@app.route('/get_user/<username>', methods=['GET'])
def get_user(username):
    user = MiBaseDatos.usuarios.find_one({"username": username})
    if user:
        user['_id'] = str(user['_id'])
        return jsonify({"status": "success", "user": user}), 200
    return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404

@app.route('/get_contacts', methods=['GET'])
def get_contacts():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    user_id = session['user_id']
    user_contacts = MiBaseDatos.contactos.find_one({"_id": user_id})
    if user_contacts:
        contacts = []
        for contact_id in user_contacts['contacts']:
            contact = MiBaseDatos.usuarios.find_one({"_id": contact_id})
            if contact:
                contact['_id'] = str(contact['_id'])
                contacts.append(contact)
        return jsonify({"status": "success", "contacts": contacts}), 200
    return jsonify({"status": "success", "contacts": []}), 200

@app.route('/get_groups', methods=['GET'])
def get_groups():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    user_id = session['user_id']
    groups = list(MiBaseDatos.grupos.find({"members": user_id}))
    for group in groups:
        group['_id'] = str(group['_id'])
    return jsonify({"status": "success", "groups": groups}), 200

@app.route('/create_group', methods=['POST'])
def create_group():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json
    group_name = data.get('group_name')
    members = data.get('members', [])
    admins = data.get('admins', [])
    if not group_name:
        return jsonify({"status": "error", "message": "Se requiere el nombre del grupo"}), 400

    creator = session['user_id']
    if creator not in members:
        members.append(creator)
    if creator not in admins:
        admins.append(creator)
    for admin in admins:
        if admin not in members:
            members.append(admin)
            
    timestamp = datetime.utcnow().replace(tzinfo=timezone('UTC')).isoformat()
    group_id = str(MiBaseDatos.grupos.count_documents({}) + 1).zfill(4)
    group = {
        "_id": group_id,
        "group_name": group_name,
        "members": members,
        "admins": admins,
        "created_by": creator,
        "created_at": timestamp
    }
    try:
        MiBaseDatos.grupos.insert_one(group)
        # Notificar a cada miembro conectado para que el grupo aparezca en su lista
        for member in members:
            socketio.emit('new_group', group, room=member)
        return jsonify({"status": "success", "group": group}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/update_avatar', methods=['POST'])
def update_avatar():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json
    avatar_url = data.get('avatar_url')
    if avatar_url:
        try:
            result = MiBaseDatos.usuarios.update_one(
                {"_id": session['user_id']},
                {"$set": {"profile_pic": avatar_url}}
            )
            if result.modified_count == 1:
                return jsonify({"status": "success"}), 200
            else:
                return jsonify({"status": "error", "message": "No se pudo actualizar el avatar"}), 500
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error", "message": "Invalid data"}), 400

@socketio.on('connect')
def handle_connect():
    if 'user_id' in session:
        user_id = session['user_id']
        join_room(user_id)
        # Unirse a las rooms de cada grupo en que es miembro
        groups = list(MiBaseDatos.grupos.find({"members": user_id}))
        for group in groups:
            join_room(group['_id'])
        # Emitir la lista de grupos al usuario conectado
        groups_data = [{"_id": str(group['_id']), "group_name": group['group_name']} for group in groups]
        socketio.emit('group_list', {"groups": groups_data}, room=user_id)
        print(f"User {user_id} connected and joined personal and group rooms")

@socketio.on('disconnect')
def handle_disconnect():
    if 'user_id' in session:
        user_id = session['user_id']
        leave_room(user_id)
        print(f"User {user_id} disconnected and left room {user_id}")

@socketio.on('send_message')
def handle_send_message(data):
    sender = data.get('sender')
    receiver = data.get('receiver')
    message_type = data.get('type')
    message_content = data.get('message')
    if sender and receiver and message_content:
        timestamp = datetime.utcnow().replace(tzinfo=timezone('UTC')).isoformat()
        message_id = str(MiBaseDatos.mensajes.count_documents({}) + 1).zfill(4)
        try:
            message = {
                "_id": message_id,
                "sender": sender,
                "receiver": receiver,
                "type": message_type,
                "message": message_content,
                "sent_at": timestamp,
                "read_by": []
            }
            MiBaseDatos.mensajes.insert_one(message)
        except Exception as e:
            print(f"Error sending message: {e}")

def watch_messages():
    with MiBaseDatos.mensajes.watch() as stream:
        for change in stream:
            if change['operationType'] == 'insert':
                message = change['fullDocument']
                if message.get('type') == 'group':
                    socketio.emit('new_message', message, room=message['receiver'])
                else:
                    sender = message['sender']
                    receiver = message['receiver']
                    socketio.emit('new_message', message, room=receiver)
                    socketio.emit('new_message', message, room=sender)

uri = os.getenv('MONGO_URI')
client = MongoClient(uri)

try:
    client.admin.command('ping')
    print("Pinged your deployment. You Sucessfully Connected to MongoDB!")
except Exception as e:
    print(e)

MiBaseDatos = client['chat']

if 'usuarios' not in MiBaseDatos.list_collection_names():
    MiBaseDatos.create_collection('usuarios')

if 'mensajes' not in MiBaseDatos.list_collection_names():
    MiBaseDatos.create_collection('mensajes')

if 'contactos' not in MiBaseDatos.list_collection_names():
    MiBaseDatos.create_collection('contactos')

if 'grupos' not in MiBaseDatos.list_collection_names():
    MiBaseDatos.create_collection('grupos')

print(MiBaseDatos)
print(MiBaseDatos.list_collection_names())

if __name__ == '__main__':
    from threading import Thread
    port = int(os.environ.get('PORT', 3000))
    watcher_thread = Thread(target=watch_messages)
    watcher_thread.start()
    socketio.run(app, host='0.0.0.0', port=port, debug=True)

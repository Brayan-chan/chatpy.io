from flask import Flask, request, render_template, jsonify, redirect, url_for, session, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room
from pymongo.mongo_client import MongoClient
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from pytz import timezone
from bson import ObjectId

load_dotenv('.env')
app = Flask(__name__, static_folder='static')
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
socketio = SocketIO(app)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename, mimetype='application/javascript')

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
        message_id = str(ObjectId())
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
        user_id = str(ObjectId())  # Generar un ObjectId único
        user = {
            "_id": user_id,
            "username": username,
            "password": hashed_password,
            "profile_pic": "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y",
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

@app.route('/videochat')
def videochat():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user = MiBaseDatos.usuarios.find_one({"_id": session['user_id']})
    contact = request.args.get('contact')
    if contact:
        contact_user = MiBaseDatos.usuarios.find_one({"_id": contact})
        return render_template('videochat.html', user=user, contact_user=contact_user)
    return render_template('videochat.html', user=user)

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
        # Obtener el nombre del usuario en lugar de mostrar el ID
        sender = MiBaseDatos.usuarios.find_one({"_id": message['sender']})
        message['sender'] = sender['username']
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
            {"sender": contact_id, "receiver": user_id},
            # Agregar condición para mensajes de IA dirigidos a este chat
            {"sender": "ai_assistant", "receiver": contact_id}
        ]
    }))
    for message in messages:
        message['_id'] = str(message['_id'])
        utc_time = datetime.fromisoformat(message['sent_at'])
        local_time = utc_time.astimezone(timezone('America/Mexico_City'))
        
        # Manejar mensajes de IA de forma especial
        if message['sender'] == "ai_assistant":
            message['sender'] = "Asistente IA"
            message['sender_id'] = "ai_assistant"
            message['sender_avatar'] = "https://storage.googleapis.com/gweb-uniblog-publish-prod/images/IO24_WhatsInAName_Hero_1.width-1200.format-webp.webp"
        else:
            # Para mensajes normales, buscar el usuario en la base de datos
            sender = MiBaseDatos.usuarios.find_one({"_id": message['sender']})
            message['sender'] = sender['username']
            message['sender_id'] = str(sender['_id'])
            message['sender_avatar'] = sender.get('profile_pic', 'https://via.placeholder.com/150')
        
        message['sent_at'] = local_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Agregar flag para mensajes de IA
        message['is_ai'] = message.get('is_ai', False) or message['sender_id'] == "ai_assistant"
    
    contact = MiBaseDatos.usuarios.find_one({"_id": contact_id})
    contact['_id'] = str(contact['_id'])
    contact['profile_pic'] = contact.get('profile_pic', 'https://via.placeholder.com/150')
    return jsonify({"status": "success", "messages": messages, "contact": contact}), 200

@app.route('/get_group_messages/<group_id>', methods=['GET'])
def get_group_messages(group_id):
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    user_id = session['user_id']
    messages = list(MiBaseDatos.mensajes.find({"receiver": group_id, "type": "group"}))
    for message in messages:
        message['_id'] = str(message['_id'])
        utc_time = datetime.fromisoformat(message['sent_at'])
        local_time = utc_time.astimezone(timezone('America/Mexico_City'))
        sender = MiBaseDatos.usuarios.find_one({"_id": message['sender']})
        message['sender'] = sender['username']
        message['sender_id'] = str(sender['_id'])
        message['sender_avatar'] = sender.get('profile_pic', 'https://via.placeholder.com/150')
        message['sent_at'] = local_time.strftime('%Y-%m-%d %H:%M:%S')
    group = MiBaseDatos.grupos.find_one({"_id": group_id})
    group['_id'] = str(group['_id'])
    group['profile_pic'] = 'https://via.placeholder.com/150?text=Grupo'
    return jsonify({"status": "success", "messages": messages, "group": group}), 200

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
        group['profile_pic'] = group.get('profile_pic', 'https://via.placeholder.com/150?text=Grupo')
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
    group_id = str(ObjectId()) # Generar un ObjectId único
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

@app.route('/update_group_avatar', methods=['POST'])
def update_group_avatar():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json
    group_id = data.get('group_id')
    avatar_url = data.get('avatar_url')
    if group_id and avatar_url:
        try:
            result = MiBaseDatos.grupos.update_one(
                {"_id": group_id},
                {"$set": {"profile_pic": avatar_url}}
            )
            if result.modified_count == 1:
                return jsonify({"status": "success"}), 200
            else:
                return jsonify({"status": "error", "message": "No se pudo actualizar el avatar del grupo"}), 500
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error", "message": "Invalid data"}), 400

@app.route('/start_videochat', methods=['POST'])
def start_videochat():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json
    receiver_id = data.get('receiver_id')
    if not receiver_id:
        return jsonify({"status": "error", "message": "Invalid data"}), 400
    room_id = str(ObjectId())
    try:
        MiBaseDatos.salas.insert_one({
            "_id": room_id,
            "caller": session['user_id'],
            "receiver": receiver_id,
            "status": "pending"
        })
        socketio.emit('videochat_request', {"room_id": room_id, "caller": session['user_id']}, room=receiver_id)
        return jsonify({"status": "success", "room_id": room_id}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/accept_videochat', methods=['POST'])
def accept_videochat():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json
    room_id = data.get('room_id')
    if not room_id:
        return jsonify({"status": "error", "message": "Invalid data"}), 400
    try:
        # Corregido: No usar ObjectId ya que room_id ya es un string
        result = MiBaseDatos.salas.update_one(
            {"_id": room_id, "receiver": session['user_id']},
            {"$set": {"status": "received"}}
        )
        if result.modified_count == 1:
            room = MiBaseDatos.salas.find_one({"_id": room_id})
            socketio.emit('videochat_accepted', {"room_id": room_id}, room=room['caller'])
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "error", "message": "No se pudo aceptar la videollamada"}), 500
    except Exception as e:
        print(f"Error en accept_videochat: {e}")  # Log para depuración
        return jsonify({"status": "error", "message": str(e)}), 500

# Nueva ruta para obtener información de la sala
@app.route('/get_room_info/<room_id>', methods=['GET'])
def get_room_info(room_id):
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    try:
        room = MiBaseDatos.salas.find_one({"_id": room_id})
        
        if room:
            return jsonify({
                "status": "success", 
                "caller": room['caller'], 
                "receiver": room['receiver'],
                "room_status": room['status']
            }), 200
        else:
            return jsonify({"status": "error", "message": "Sala no encontrada"}), 404
    except Exception as e:
        print(f"Error en get_room_info: {e}")  # Log para depuración
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_latest_messages', methods=['GET'])
def get_latest_messages():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    user_id = session['user_id']
    contact_id = request.args.get('contact_id')
    if not contact_id:
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    messages = list(MiBaseDatos.mensajes.find({
        "$or": [
            {"sender": user_id, "receiver": contact_id},
            {"sender": contact_id, "receiver": user_id}
        ]
    }).sort("sent_at", -1).limit(10))  # Obtener los últimos 10 mensajes

    for message in messages:
        message['_id'] = str(message['_id'])
        utc_time = datetime.fromisoformat(message['sent_at'])
        local_time = utc_time.astimezone(timezone('America/Mexico_City'))
        sender = MiBaseDatos.usuarios.find_one({"_id": message['sender']})
        message['sender'] = sender['username']
        message['sent_at'] = local_time.strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({"status": "success", "messages": messages}), 200

@app.route('/get_api_key', methods=['GET'])
def get_api_key():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    api_key = os.getenv('API_KEY')
    if api_key:
        return jsonify({"status": "success", "api_key": api_key}), 200
    return jsonify({"status": "error", "message": "API key not found"}), 500

@app.route('/send_ai_message', methods=['POST'])
def send_ai_message():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    data = request.json
    receiver = data.get('receiver')
    message_type = data.get('type')
    message_content = data.get('message')
    
    if receiver and message_content:
        timestamp = datetime.utcnow().replace(tzinfo=timezone('UTC')).isoformat()
        message_id = str(ObjectId())
        
        # Crear un remitente especial para la IA
        ai_sender = {
            "_id": "ai_assistant",
            "username": "Asistente IA",
            "profile_pic": "https://storage.googleapis.com/gweb-uniblog-publish-prod/images/IO24_WhatsInAName_Hero_1.width-1200.format-webp.webp"
        }
        
        try:
            # Insertar el mensaje en la base de datos
            MiBaseDatos.mensajes.insert_one({
                "_id": message_id,
                "sender": "ai_assistant",  # ID especial para la IA
                "receiver": receiver,
                "type": message_type,
                "message": message_content,
                "sent_at": timestamp,
                "read_by": [],
                "is_ai": True  # Marcar como mensaje de IA
            })
            
            # Emitir el mensaje a través de Socket.IO
            message = {
                "_id": message_id,
                "sender": "ai_assistant",
                "sender_id": "ai_assistant",
                "receiver": receiver,
                "type": message_type,
                "message": message_content,
                "sent_at": timestamp,
                "is_ai": True,
                "sender_avatar": "https://storage.googleapis.com/gweb-uniblog-publish-prod/images/IO24_WhatsInAName_Hero_1.width-1200.format-webp.webp"
            }
            
            # Emitir solo al receptor
            socketio.emit('new_message', message, room=receiver)
            
            return jsonify({"status": "success"}), 200
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
        message_id = str(ObjectId()) # Generar un ObjectId único
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
                    
@app.route('/register_peer_id/<room_id>/<peer_id>', methods=['POST'])
def register_peer_id(room_id, peer_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"status": "error", "message": "No hay sesión activa"})
        
        # Obtener la sala
        room = MiBaseDatos.salas.find_one({"_id": room_id})
        if not room:
            return jsonify({"status": "error", "message": "Sala no encontrada"})
        
        # Verificar que el usuario pertenezca a la sala
        if user_id != room['caller'] and user_id != room['receiver']:
            return jsonify({"status": "error", "message": "No tienes permiso para acceder a esta sala"})
        
        # Determinar si es caller o receiver
        field_to_update = "caller_peer_id" if user_id == room['caller'] else "receiver_peer_id"
        
        # Actualizar el ID de peer en la sala
        MiBaseDatos.salas.update_one(
            {"_id": room_id},
            {"$set": {field_to_update: peer_id}}
        )
        
        return jsonify({"status": "success", "message": "ID de peer registrado correctamente"})
    except Exception as e:
        print(f"Error al registrar peer ID: {e}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_peer_id/<room_id>', methods=['GET'])
def get_peer_id(room_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"status": "error", "message": "No hay sesión activa"})
        
        # Obtener la sala
        room = MiBaseDatos.salas.find_one({"_id": room_id})
        if not room:
            return jsonify({"status": "error", "message": "Sala no encontrada"})
        
        # Verificar que el usuario pertenezca a la sala
        if user_id != room['caller'] and user_id != room['receiver']:
            return jsonify({"status": "error", "message": "No tienes permiso para acceder a esta sala"})
        
        # Determinar el ID del peer del otro usuario
        other_peer_id = room.get('receiver_peer_id') if user_id == room['caller'] else room.get('caller_peer_id')
        
        if not other_peer_id:
            return jsonify({"status": "waiting", "message": "El otro usuario aún no se ha conectado"})
        
        return jsonify({"status": "success", "peer_id": other_peer_id})
    except Exception as e:
        print(f"Error al obtener peer ID: {e}")
        return jsonify({"status": "error", "message": str(e)})

def watch_videochat_requests():
    with MiBaseDatos.salas.watch() as stream:
        for change in stream:
            try:
                if change['operationType'] == 'update' and change['updateDescription']['updatedFields'].get('status') == 'received':
                    # Obtener el documento completo después de la actualización
                    room_id = change['documentKey']['_id']
                    room = MiBaseDatos.salas.find_one({"_id": room_id})
                    
                    if room:
                        socketio.emit('videochat_start', {"room_id": room['_id']}, room=room['caller'])
                        socketio.emit('videochat_start', {"room_id": room['_id']}, room=room['receiver'])
                        print(f"Videochat iniciado entre {room['caller']} y {room['receiver']}")
            except Exception as e:
                print(f"Error en watch_videochat_requests: {e}")

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

if 'salas' not in MiBaseDatos.list_collection_names():
    MiBaseDatos.create_collection('salas')

print(MiBaseDatos)
print(MiBaseDatos.list_collection_names())

if __name__ == '__main__':
    from threading import Thread
    port = int(os.environ.get('PORT', 8080))
    watcher_thread = Thread(target=watch_messages)
    watcher_thread.start()
    videochat_watcher_thread = Thread(target=watch_videochat_requests)
    videochat_watcher_thread.start()
    socketio.run(app, host='0.0.0.0', port=port)
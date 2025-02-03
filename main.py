from pymongo.mongo_client import MongoClient
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
import os
from flask_socketio import SocketIO, emit, join_room, leave_room

load_dotenv('.env')
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # Clave secreta para Socket.IO
socketio = SocketIO(app)  # Inicializa Socket.IO

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    nombre = data.get('nombre')
    contenido = data.get('contenido')
    sala = data.get('sala') # Obtener la sala del mensaje
    if nombre and contenido and sala:
        MiBaseDatos.chats.insert_one({"Nombre": nombre, "Contenido": contenido, "Sala": sala}) #Guardar sala
        # Emitir el mensaje a la sala correspondiente
        socketio.emit('message', {'nombre': nombre, 'contenido': contenido, 'sala': sala}, to=sala) # Emitir a la sala
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error", "message": "Invalid data"}), 400

uri = os.getenv('MONGO_URI')

client = MongoClient(uri)

try:
    client.admin.command('ping')
    print("Pinged your deployment. You Sucessfully Connected to MongoDB!")
except Exception as e:
    print(e)

MiBaseDatos = client['chat']

print(MiBaseDatos.list_collection_names())


# Eventos de Socket.IO
@socketio.on('connect')
def handle_connect():
    print('Cliente conectado')

@socketio.on('disconnect')
def handle_disconnect():
    print('Cliente desconectado')

@socketio.on('join_room')
def handle_join_room(data):
    sala = data['sala']
    join_room(sala)
    emit('joined_room', {'sala': sala})  # Confirmación de unión a la sala
    print(f"Usuario se unió a la sala: {sala}")


@socketio.on('leave_room')
def handle_leave_room(data):
  sala = data['sala']
  leave_room(sala)
  emit('left_room', {'sala': sala})
  print(f"Usuario abandonó la sala: {sala}")


@socketio.on('send_message')  # Escucha el evento 'send_message' desde el cliente
def handle_send_message(data):
    nombre = data['nombre']
    contenido = data['contenido']
    sala = data['sala']
    MiBaseDatos.chats.insert_one({"Nombre": nombre, "Contenido": contenido, "Sala": sala})
    socketio.emit('message', {'nombre': nombre, 'contenido': contenido, 'sala': sala}, to=sala)  # Emitir a la sala


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)  # Usar socketio.run

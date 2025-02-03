from pymongo.mongo_client import MongoClient
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
import os  # Importar el módulo os

load_dotenv('.env')
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    nombre = data.get('nombre')
    contenido = data.get('contenido')
    if nombre and contenido:
        MiBaseDatos.chats.insert_one({"Nombre": nombre, "Contenido": contenido})
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error", "message": "Invalid data"}), 400

uri = os.getenv('MONGO_URI')

client = MongoClient(uri)

try:
  client.admin.command('ping')
  print("Pinged your deployment. You Sucessfully Connected to MongoDB!")
except Exception as e:
  print(e)

collection = client['chat']['collection']

MiBaseDatos = client['chat']

print(MiBaseDatos)

collection = MiBaseDatos['chat']

print(MiBaseDatos.list_collection_names())

# Comentar la inserción manual de documentos
# MiBaseDatos.notes.insert_one({"Nombre":"Mi nota desde colab", "Contenido": "Esta es mi primera nota desde vsc"})

if __name__ == '__main__':
  
  #Para ejecutar el servidor en local
  #Descomentar esta línea si se ejecuta en local
    app.run(debug=True)
  
  #Para ejecutar el servidor en Render
  #Comentar estas líneas si se ejecuta en local
    #port = int(os.environ.get('PORT', 5000))
    #app.run(host='0.0.0.0', port=port, debug=True)
from pymongo.mongo_client import MongoClient
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
import os  # Importar el módulo os

load_dotenv('.env')
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

uri = os.getenv('MONGO_URI')

client = MongoClient(uri)

try:
  client.admin.command('ping')
  print("Pinged your deployment. You Sucessfully Connected to MongoDB!")
except Exception as e:
  print(e)

collection = client['test']['collection']

MiBaseDatos = client['test']

print(MiBaseDatos)

collection = MiBaseDatos['test']

print(MiBaseDatos.list_collection_names())

MiBaseDatos.notes.insert_one({"Nombre":"Mi nota desde colab", "Contenido": "Esta es mi primera nota desde vsc"})

if __name__ == '__main__':
    app.run(debug=True)
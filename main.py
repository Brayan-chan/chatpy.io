from pymongo.mongo_client import MongoClient
from flask import Flask, request, render_template, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

uri = "mongodb+srv://al071392:7UpmTr9MbmnHxQLn@cluster0.vkdby.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

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
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import glob
import requests
import re
from collections import defaultdict

# 1. Cria o app PRIMEIRO
app = Flask(__name__)
CORS(app)

# 2. Depois define as rotas
@app.route('/gastos/<id_deputado>')
def buscar_gastos(id_deputado):
    # ... (seu código de gastos) ...
    pass

@app.route('/votacoes/<id_deputado>')
def buscar_votacoes(id_deputado):
    # ... (seu código de votações) ...
    pass

@app.route('/proposicao/<id_proposicao>')
def detalhes_proposicao(id_proposicao):
    # ... (seu código de proposições) ...
    pass

# 3. Finaliza o arquivo
if __name__ == '__main__':
    app.run(debug=True)

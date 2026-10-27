from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
import os
import time
import requests
import pandas as pd

app = Flask(__name__)
CORS(app)

votacoes_bp = Blueprint('votacoes', __name__)
BASE_URL = "https://dadosabertos.camara.leg.br/arquivos"
CACHE_DIR = "/tmp/cache_votacoes"
TTL_SEGUNDOS = 24 * 60 * 60

os.makedirs(CACHE_DIR, exist_ok=True)

def _arquivo_local(nome: str) -> str:
    return os.path.join(CACHE_DIR, nome)

def _precisa_baixar(caminho: str) -> bool:
    if not os.path.exists(caminho):
        return True
    idade = time.time() - os.path.getmtime(caminho)
    return idade > TTL_SEGUNDOS

def _baixar_csv(ano: int, nome: str) -> str:
    caminho = _arquivo_local(nome)
    if _precisa_baixar(caminho):
        if "votacoesVotos" in nome:
            url = f"https://dadosabertos.camara.leg.br/arquivos/votacoesVotos/csv/{nome}"
        else:
            url = f"{BASE_URL}/votacoes/csv/{nome}"
            
        print(f"[votacoes] Baixando {url} ...")
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        with open(caminho, "wb") as f:
            f.write(r.content)
    return caminho

def _carregar_dataframes(ano: int):
    arq_vot = _baixar_csv(ano, f"votacoes-{ano}.csv")
    arq_votos = _baixar_csv(ano, f"votacoesVotos-{ano}.csv")
    votacoes = pd.read_csv(arq_vot, sep=";", encoding="utf-8-sig", dtype=str)
    votos = pd.read_csv(arq_votos, sep=";", encoding="utf-8-sig", dtype=str)
    return votacoes, votos

def gerar_votacoes_deputado(id_deputado: str, ano: int = 2024):
    votacoes, votos = _carregar_dataframes(ano)
    votos_dep = votos[votos["deputado_id"] == str(id_deputado)]
    mapa_votos = dict(zip(votos_dep["idVotacao"], votos_dep["voto"]))

    resultado = []
    for _, v in votacoes.iterrows():
        id_vot = v["id"]
        voto = mapa_votos.get(id_vot, "Não registrado individualmente")
        observacao = ""
        if voto == "Não registrado individualmente":
            observacao = ("Votação simbólica ou sem registro individual. "
                          "A Câmara não registrou o voto nominal deste deputado.")

        resultado.append({
            "id": id_vot,
            "data": v.get("data", ""),
            "dataHora": v.get("dataHoraRegistro", ""),
            "descricao": v.get("descricao", ""),
            "orgao": v.get("siglaOrgao", ""),
            "aprovacao": v.get("aprovacao", ""),
            "voto": voto,
            "observacao": observacao,
        })

    resultado.sort(key=lambda x: x["dataHora"], reverse=True)
    return resultado

@votacoes_bp.route("/votacoes/<id_deputado>", methods=["GET"])
def votacoes_deputado(id_deputado):
    try:
        ano = int(request.args.get("ano", 2024))
    except Exception:
        ano = 2024
    try:
        lista = gerar_votacoes_deputado(id_deputado, ano=ano)
        return jsonify({"votacoes": lista, "ano": ano, "total": len(lista)})
    except Exception as e:
        return jsonify({"erro": str(e), "votacoes": []}), 500

@votacoes_bp.route("/votacoes/teste/<id_deputado>", methods=["GET"])
def votacoes_teste(id_deputado):
    try:
        lista = gerar_votacoes_deputado(id_deputado, ano=2024)
        return jsonify({
            "status": "ok",
            "total_votacoes": len(lista),
            "primeiras_3": lista[:3],
        })
    except Exception as e:
        return jsonify({"status": "erro", "detalhe": str(e)}), 500

app.register_blueprint(votacoes_bp)

@app.route("/")
def home():
    return "Backend do Voto Aberto está rodando!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

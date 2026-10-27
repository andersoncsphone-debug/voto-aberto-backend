import os
import json
import time
import requests
import pandas as pd
from flask import Blueprint, jsonify

votacoes_bp = Blueprint('votacoes', __name__)

# Configurações
BASE_URL = "https://dadosabertos.camara.leg.br/arquivos"
CACHE_DIR = "/tmp/cache_votacoes"   # Render free tier: /tmp é gravável
TTL_SEGUNDOS = 24 * 60 * 60         # 24h

os.makedirs(CACHE_DIR, exist_ok=True)


def _arquivo_local(nome: str) -> str:
    return os.path.join(CACHE_DIR, nome)


def _precisa_baixar(caminho: str) -> bool:
    if not os.path.exists(caminho):
        return True
    idade = time.time() - os.path.getmtime(caminho)
    return idade > TTL_SEGUNDOS


def _baixar_csv(ano: int, nome: str) -> str:
    """Baixa o CSV da Câmara se não existir ou se o cache expirou."""
    caminho = _arquivo_local(nome)
    if _precisa_baixar(caminho):
        url = f"{BASE_URL}/votacoes/csv/{nome}"
        print(f"[votacoes] Baixando {url} ...")
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        with open(caminho, "wb") as f:
            f.write(r.content)
        print(f"[votacoes] Salvo em {caminho} ({len(r.content)} bytes)")
    return caminho


def _carregar_dataframes(ano: int):
    """Carrega (ou baixa) os dois CSVs e devolve DataFrames."""
    arq_vot = _baixar_csv(ano, f"votacoes-{ano}.csv")
    arq_votos = _baixar_csv(ano, f"votacoesVotos-{ano}.csv")

    # utf-8-sig remove o BOM inicial
    votacoes = pd.read_csv(arq_vot, sep=";", encoding="utf-8-sig", dtype=str)
    votos = pd.read_csv(arq_votos, sep=";", encoding="utf-8-sig", dtype=str)
    return votacoes, votos


def gerar_votacoes_deputado(id_deputado: str, ano: int = 2024):
    """Cruza os dois arquivos e devolve a lista de votações do deputado."""
    votacoes, votos = _carregar_dataframes(ano)

    # Filtra os votos do deputado
    votos_dep = votos[votos["deputado_id"] == str(id_deputado)]

    # Mapa {idVotacao: voto}
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

    # Ordena do mais recente para o mais antigo
    resultado.sort(key=lambda x: x["dataHora"], reverse=True)
    return resultado


@votacoes_bp.route("/votacoes/<id_deputado>", methods=["GET"])
def votacoes_deputado(id_deputado):
    try:
        ano = int(request.args.get("ano", 2024)) if 'request' in globals() else 2024
    except Exception:
        ano = 2024
    try:
        lista = gerar_votacoes_deputado(id_deputado, ano=ano)
        return jsonify({"votacoes": lista, "ano": ano, "total": len(lista)})
    except Exception as e:
        return jsonify({"erro": str(e), "votacoes": []}), 500

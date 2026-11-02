from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import glob
from collections import defaultdict

app = Flask(__name__)
CORS(app)
BASE = os.path.join("dados", "camara_federal")

def ler_partes(tipo, id_deputado):
    """Lê todas as partes de um tipo e junta numa lista."""
    pasta = os.path.join(BASE, tipo, str(id_deputado))
    if not os.path.exists(pasta): return []
    
    dados = []
    for arq in sorted(glob.glob(os.path.join(pasta, "parte_*.json"))):
        with open(arq, "r", encoding="utf-8") as f:
            dados.extend(json.load(f).get("dados", []))
    return dados

# ==========================================
# ROTA UNIFICADA (O app vai usar esta)
# ==========================================
@app.route('/ficha/<id_deputado>')
def buscar_ficha(id_deputado):
    ficha = {
        "id": id_deputado,
        "cotas": ler_partes("cotas", id_deputado),
        "votacoes": ler_partes("votacoes", id_deputado),
        "proposicoes": ler_partes("proposicoes", id_deputado)
    }
    
    if not ficha["cotas"] and not ficha["votacoes"] and not ficha["proposicoes"]:
        return jsonify({"erro": "Nenhum dado encontrado."}), 404
    return jsonify(ficha)

# ==========================================
# ROTA DE GASTOS (Mantida para compatibilidade)
# ==========================================
@app.route('/gastos/<id_deputado>')
def buscar_gastos(id_deputado):
    despesas = ler_partes("cotas", id_deputado)
    if not despesas: return jsonify({"erro": "Nenhum gasto."}), 404

    ano_inicio = request.args.get('ano_inicio')
    ano_fim = request.args.get('ano_fim')
    resumo_mensal = defaultdict(float)
    anos_historicos = set()
    filtradas = []

    for g in despesas:
        ano = int(g.get("ano", 0))
        anos_historicos.add(ano)
        if ano_inicio and ano_fim:
            if ano < int(ano_inicio) or ano > int(ano_fim): continue
        mes = int(g.get("mes", 0))
        valor = float(g.get("valorLiquido", 0))
        filtradas.append({
            "mes": mes, "ano": ano, "valor": valor,
            "fornecedor": g.get("fornecedor", "Desconhecido"),
            "url_pdf": g.get("urlDocumento", ""),
        })
        resumo_mensal[f"{mes}/{ano}"] += valor

    if not filtradas: return jsonify({"erro": "Nenhuma despesa no período."}), 404
    total = sum(d['valor'] for d in filtradas)
    media = total / len(resumo_mensal) if resumo_mensal else 0

    return jsonify({
        "id": id_deputado, "total_gasto": total, "media_mensal": media,
        "despesas": filtradas, "resumo_mensal": dict(resumo_mensal),
        "anos_historicos": sorted(anos_historicos),
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from collections import defaultdict

app = Flask(__name__)
CORS(app)

BASE = os.path.join("dados", "camara_federal")


# ==========================================
# ROTA 1: GASTOS (Cotas)
# ==========================================
@app.route('/gastos/<id_deputado>')
def buscar_gastos(id_deputado):
    caminho = os.path.join(BASE, "cotas", f"{id_deputado}.json")
    if not os.path.exists(caminho):
        return jsonify({"erro": f"Nenhum gasto encontrado para {id_deputado}."}), 404

    ano_inicio = request.args.get('ano_inicio')
    ano_fim = request.args.get('ano_fim')

    todas_as_despesas = []
    resumo_mensal = defaultdict(float)
    anos_historicos = set()

    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
            for g in dados.get("dados", []):
                ano = int(g.get("ano", 0))
                anos_historicos.add(ano)

                if ano_inicio and ano_fim:
                    if ano < int(ano_inicio) or ano > int(ano_fim):
                        continue

                mes = int(g.get("mes", 0))
                valor = float(g.get("valorLiquido", 0))
                todas_as_despesas.append({
                    "mes": mes,
                    "ano": ano,
                    "valor": valor,
                    "fornecedor": g.get("fornecedor", "Desconhecido"),
                    "url_pdf": g.get("urlDocumento", ""),
                })
                resumo_mensal[f"{mes}/{ano}"] += valor
    except Exception as e:
        print(f"Erro ao ler {caminho}: {e}")
        return jsonify({"erro": "Erro interno ao processar dados."}), 500

    if not todas_as_despesas:
        return jsonify({"erro": "Nenhuma despesa encontrada para este período."}), 404

    total = sum(d["valor"] for d in todas_as_despesas)
    media = total / len(resumo_mensal) if resumo_mensal else 0

    return jsonify({
        "id": id_deputado,
        "total_gasto": total,
        "media_mensal": media,
        "despesas": todas_as_despesas,
        "resumo_mensal": dict(resumo_mensal),
        "anos_historicos": sorted(anos_historicos),
    })


# ==========================================
# ROTA 2: VOTAÇÕES
# ==========================================
@app.route('/votacoes/<id_deputado>')
def buscar_votacoes(id_deputado):
    caminho = os.path.join(BASE, "votacoes", f"{id_deputado}.json")
    if not os.path.exists(caminho):
        return jsonify({"erro": f"Nenhuma votação encontrada para {id_deputado}."}), 404

    ano_inicio = request.args.get('ano_inicio')
    ano_fim = request.args.get('ano_fim')

    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
            votacoes = dados.get("dados", [])
            if ano_inicio and ano_fim:
                votacoes = [
                    v for v in votacoes
                    if int(ano_inicio) <= int(v.get("ano", 0)) <= int(ano_fim)
                ]
            return jsonify({
                "id": id_deputado,
                "total_votacoes": len(votacoes),
                "votacoes": votacoes,
            })
    except Exception as e:
        print(f"Erro ao ler {caminho}: {e}")
        return jsonify({"erro": "Erro interno ao processar dados."}), 500


# ==========================================
# ROTA 3: PROPOSIÇÕES
# ==========================================
@app.route('/proposicoes/<id_deputado>')
def buscar_proposicoes(id_deputado):
    caminho = os.path.join(BASE, "proposicoes", f"{id_deputado}.json")
    if not os.path.exists(caminho):
        return jsonify({"erro": f"Nenhuma proposição encontrada para {id_deputado}."}), 404

    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
            props = dados.get("dados", [])
            return jsonify({
                "id": id_deputado,
                "total_proposicoes": len(props),
                "proposicoes": props,
            })
    except Exception as e:
        print(f"Erro ao ler {caminho}: {e}")
        return jsonify({"erro": "Erro interno ao processar dados."}), 500


# ==========================================
# ROTA ADMIN: forçar atualização (D025)
# ==========================================
@app.route('/admin/atualizar')
def admin_atualizar():
    from atualizador import main as rodar_atualizador
    try:
        rodar_atualizador()
        return jsonify({"status": "ok", "mensagem": "Atualização concluída."})
    except Exception as e:
        return jsonify({"status": "erro", "erro": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

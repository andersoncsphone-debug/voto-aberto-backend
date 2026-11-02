from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import glob
from collections import defaultdict
import math

app = Flask(__name__)
# Isso permite que o Flutter acesse a API de qualquer lugar
CORS(app)

BASE = os.path.join("dados", "camara_federal")

def limpar_nan(obj):
    """Remove NaN e Infinity (que quebram o JSON) e transforma em None."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: limpar_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [limpar_nan(v) for v in obj]
    # Se o dado vier como string "NaN", transforma em None
    if isinstance(obj, str) and obj.strip().upper() == "NAN":
        return None
    return obj

def ler_partes(tipo, id_deputado):
    """Lê todas as partes de um tipo, junta numa lista e limpa os NaNs."""
    pasta = os.path.join(BASE, tipo, str(id_deputado))
    if not os.path.exists(pasta): 
        return []
    
    dados = []
    # Lê todos os arquivos parte_*.json na pasta
    for arq in sorted(glob.glob(os.path.join(pasta, "parte_*.json"))):
        try:
            with open(arq, "r", encoding="utf-8") as f:
                conteudo = json.load(f)
                # Pega a lista dentro da chave "dados"
                if isinstance(conteudo, dict) and "dados" in conteudo:
                    dados.extend(conteudo["dados"])
                elif isinstance(conteudo, list):
                    dados.extend(conteudo)
        except Exception as e:
            print(f"Erro ao ler {arq}: {e}")
            
    # Limpa a lista de dados para garantir que não há NaN
    return limpar_nan(dados)

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
        
    # jsonify com allow_nan=False garante que se sobrar algum NaN, ele dá erro em vez de quebrar o app do cliente
    return app.response_class(
        response=json.dumps(ficha, ensure_ascii=False, allow_nan=False),
        status=200,
        mimetype='application/json'
    )

# ==========================================
# ROTA DE GASTOS (Mantida para compatibilidade)
# ==========================================
@app.route('/gastos/<id_deputado>')
def buscar_gastos(id_deputado):
    despesas = ler_partes("cotas", id_deputado)
    if not despesas: 
        return jsonify({"erro": "Nenhum gasto."}), 404

    ano_inicio = request.args.get('ano_inicio')
    ano_fim = request.args.get('ano_fim')
    resumo_mensal = defaultdict(float)
    anos_historicos = set()
    filtradas = []

    for g in despesas:
        try:
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
        except ValueError:
            continue # Pula se tiver algum valor corrompido

    if not filtradas: 
        return jsonify({"erro": "Nenhuma despesa no período."}), 404
        
    total = sum(d['valor'] for d in filtradas)
    media = total / len(resumo_mensal) if resumo_mensal else 0

    return jsonify({
        "id": id_deputado, "total_gasto": total, "media_mensal": media,
        "despesas": filtradas, "resumo_mensal": dict(resumo_mensal),
        "anos_historicos": sorted(anos_historicos),
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
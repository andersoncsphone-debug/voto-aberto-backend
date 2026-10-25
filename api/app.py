from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import glob
from collections import defaultdict

app = Flask(__name__)
CORS(app)

@app.route('/gastos/<id_deputado>')
def buscar_gastos(id_deputado):
    ano_inicio = request.args.get('ano_inicio')
    ano_fim = request.args.get('ano_fim')
    
    padrao_busca = os.path.join('dados', 'por_politico', f'politico_{id_deputado}*.json')
    arquivos = glob.glob(padrao_busca)

    if not arquivos:
        return jsonify({"erro": "Nenhum gasto encontrado."}), 404

    todas_as_despesas = []
    resumo_mensal = defaultdict(float)
    anos_historicos = set() # Guarda todos os anos que ele teve gastos

    for arquivo in arquivos:
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                for g in dados.get('dados', []):
                    ano = int(g.get('ano'))
                    anos_historicos.add(ano) # Adiciona o ano ao histórico geral
                    
                    # Se um filtro de mandato foi enviado, só processa se estiver dentro dele
                    if ano_inicio and ano_fim:
                        if ano < int(ano_inicio) or ano > int(ano_fim):
                            continue
                    
                    mes = int(g.get('mes'))
                    valor = float(g.get('valorLiquido', 0))
                    todas_as_despesas.append({
                        "mes": mes,
                        "ano": ano,
                        "valor": valor,
                        "fornecedor": g.get('fornecedor', 'Desconhecido'),
                        "url_pdf": g.get('urlDocumento', '')
                    })
                    resumo_mensal[f"{mes}/{ano}"] += valor
        except Exception as e:
            print(f"Erro ao ler {arquivo}: {e}")

    if not todas_as_despesas:
        return jsonify({"erro": "Nenhuma despesa encontrada para este período."}), 404

    total = sum(d['valor'] for d in todas_as_despesas)
    media = total / len(resumo_mensal) if resumo_mensal else 0

    return jsonify({
        "id": id_deputado,
        "total_gasto": total,
        "media_mensal": media,
        "despesas": todas_as_despesas,
        "resumo_mensal": resumo_mensal,
        "anos_historicos": sorted(list(anos_historicos)) # Envia todos os anos para os botões
    })

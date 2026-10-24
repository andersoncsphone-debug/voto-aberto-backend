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
    ano_filtro = request.args.get('ano')
    mes_filtro = request.args.get('mes')
    
    padrao_busca = os.path.join('dados', 'por_politico', f'politico_{id_deputado}*.json')
    arquivos = glob.glob(padrao_busca)

    if not arquivos:
        return jsonify({"erro": "Nenhum gasto encontrado."}), 404

    todas_as_despesas = []
    resumo_mensal = defaultdict(float) # Guarda o total por "mes/ano"
    anos_com_gasto = set()

    for arquivo in arquivos:
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                for g in dados.get('dados', []):
                    ano = str(g.get('ano'))
                    mes = str(g.get('mes'))
                    
                    if ano_filtro and ano != str(ano_filtro):
                        continue
                    if mes_filtro and mes != str(mes_filtro):
                        continue
                    
                    valor = float(g.get('valorLiquido', 0))
                    todas_as_despesas.append({
                        "mes": int(mes),
                        "ano": int(ano),
                        "valor": valor,
                        "fornecedor": g.get('fornecedor', 'Desconhecido'),
                        "url_pdf": g.get('urlDocumento', '')
                    })
                    
                    # Agrupa o total por mês
                    chave_mes = f"{mes}/{ano}"
                    resumo_mensal[chave_mes] += valor
                    anos_com_gasto.add(int(ano))
        except Exception as e:
            print(f"Erro ao ler {arquivo}: {e}")

    if not todas_as_despesas:
        return jsonify({"erro": "Nenhuma despesa encontrada."}), 404

    total = sum(d['valor'] for d in todas_as_despesas)
    
    # Calcula a média real (Total dividido pelos meses que tiveram gasto)
    meses_unicos = len(resumo_mensal)
    media_real = total / meses_unicos if meses_unicos > 0 else 0

    return jsonify({
        "id": id_deputado,
        "total_gasto": total,
        "media_mensal": media_real,
        "despesas": todas_as_despesas,
        "resumo_mensal": resumo_mensal,
        "anos_disponiveis": sorted(list(anos_com_gasto))
    })

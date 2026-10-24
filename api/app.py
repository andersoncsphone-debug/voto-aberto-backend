from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import glob

app = Flask(__name__)
CORS(app)

# Função para carregar as médias (roda uma vez quando a API inicia)
def carregar_medias():
    caminho = os.path.join('dados', 'medias_gerais.json')
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar medias_gerais.json: {e}")
        return {}

MEDIAS = carregar_medias()

@app.route('/gastos/<id_deputado>')
def buscar_gastos(id_deputado):
    ano_filtro = request.args.get('ano') # Ex: ?ano=2024
    mes_filtro = request.args.get('mes') # Ex: ?mes=5
    
    padrao_busca = os.path.join('dados', 'por_politico', f'politico_{id_deputado}*.json')
    arquivos = glob.glob(padrao_busca)

    if not arquivos:
        return jsonify({"erro": "Nenhum gasto encontrado."}), 404

    todas_as_despesas = []
    anos_com_gasto = set()

    for arquivo in arquivos:
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                for g in dados.get('dados', []):
                    # Aplica os filtros de ano e mês (se enviados)
                    if ano_filtro and str(g.get('ano')) != str(ano_filtro):
                        continue
                    if mes_filtro and str(g.get('mes')) != str(mes_filtro):
                        continue
                    
                    todas_as_despesas.append({
                        "mes": g.get('mes'),
                        "ano": g.get('ano'),
                        "valor": float(g.get('valorLiquido', 0)),
                        "fornecedor": g.get('fornecedor', 'Desconhecido'),
                        "url_pdf": g.get('urlDocumento', '')
                    })
                    anos_com_gasto.add(g.get('ano'))
        except Exception as e:
            print(f"Erro ao ler {arquivo}: {e}")
            continue

    if not todas_as_despesas:
        return jsonify({"erro": "Nenhuma despesa encontrada para este filtro."}), 404

    total = sum(d['valor'] for d in todas_as_despesas)
    
    # Busca a média geral do mês específico (se o filtro foi aplicado)
    media_geral_mes = 0.0
    if ano_filtro and mes_filtro:
        try:
            media_geral_mes = MEDIAS.get(str(ano_filtro), {}).get(str(mes_filtro), {}).get('media_geral', 0.0)
        except:
            pass

    return jsonify({
        "id": id_deputado,
        "total_gasto": total,
        "despesas": todas_as_despesas,
        "anos_disponiveis": sorted(list(anos_com_gasto)),
        "media_geral_mes": media_geral_mes # Média real daquele mês
    })

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import glob
from collections import defaultdict

app = Flask(__name__)
CORS(app)

# ==========================================
# ROTA 1: GASTOS (Mantida exatamente como estava)
# ==========================================
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
    anos_historicos = set()

    for arquivo in arquivos:
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                for g in dados.get('dados', []):
                    ano = int(g.get('ano'))
                    anos_historicos.add(ano)
                    
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
        "anos_historicos": sorted(list(anos_historicos))
    })


# ==========================================
# ROTA 2: VOTAÇÕES (Nova rota para os arquivos gerados)
# ==========================================
@app.route('/votacoes/<id_deputado>')
def buscar_votacoes(id_deputado):
    # Verifica se o arquivo específico daquele deputado existe
    caminho_arquivo = os.path.join('dados', 'votacoes_por_politico', f'votacoes_{id_deputado}.json')
    
    if not os.path.exists(caminho_arquivo):
        return jsonify({"erro": f"Nenhuma votação encontrada para o deputado {id_deputado}."}), 404

    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            
            # Opcional: Filtro por ano, caso o app queira buscar um mandato específico
            ano_inicio = request.args.get('ano_inicio')
            ano_fim = request.args.get('ano_fim')
            
            votacoes_filtradas = []
            for v in dados.get('dados', []):
                ano_votacao = int(v.get('ano', 0))
                
                if ano_inicio and ano_fim:
                    if ano_votacao < int(ano_inicio) or ano_votacao > int(ano_fim):
                        continue
                
                votacoes_filtradas.append(v)

            return jsonify({
                "id": id_deputado,
                "total_votacoes": len(votacoes_filtradas),
                "votacoes": votacoes_filtradas
            })
            
    except Exception as e:
        print(f"Erro ao ler votações do deputado {id_deputado}: {e}")
        return jsonify({"erro": "Erro interno ao processar os dados."}), 500


if __name__ == '__main__':
    # O host 0.0.0.0 permite que o app Flutter acesse a API se estiverem na mesma rede local
    app.run(host='0.0.0.0', port=5000, debug=True)
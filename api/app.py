from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import glob
import requests
import re
from collections import defaultdict

# ==========================================
# 1. INICIALIZAÇÃO DO APP (PRECISA SER O PRIMEIRO)
# ==========================================
app = Flask(__name__)
CORS(app)

# ==========================================
# 2. ROTA DE GASTOS (CEAP)
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
# 3. ROTA DE VOTAÇÕES
# ==========================================
@app.route('/votacoes/<id_deputado>')
def buscar_votacoes(id_deputado):
    try:
        url_votacoes = 'https://dadosabertos.camara.leg.br/api/v2/votacoes?ordem=DESC&ordenarPor=dataHoraRegistro&itens=10'
        resp = requests.get(url_votacoes).json()
        lista_votacoes = resp.get('dados', [])

        votos_do_deputado = []

        for votacao in lista_votacoes:
            id_votacao = votacao['id']
            descricao = votacao.get('descricao', 'Descrição não disponível')

            url_votos = f'https://dadosabertos.camara.leg.br/api/v2/votacoes/{id_votacao}/votos'
            resp_votos = requests.get(url_votos).json()
            votos = resp_votos.get('dados', [])

            voto_encontrado = next((v for v in votos if str(v['deputado_']['id']) == id_deputado), None)

            if voto_encontrado:
                id_proposicao = votacao.get('idProposicaoObjeto')
                
                if not id_proposicao:
                    url_detalhes = f'https://dadosabertos.camara.leg.br/api/v2/votacoes/{id_votacao}'
                    resp_detalhes = requests.get(url_detalhes).json()
                    dados_detalhes = resp_detalhes.get('dados', {})
                    
                    objetos = dados_detalhes.get('objetosPossiveis', [])
                    if objetos:
                        id_proposicao = objetos[0].get('id')

                match = re.search(r'(Projeto de Lei(?: Complementar)?)\s*n[º°]?\s*(\d+).*?de\s*(\d{4})', descricao, re.IGNORECASE)
                projeto_simplificado = descricao
                link_projeto = None
                
                if match:
                    tipo_texto = match.group(1)
                    numero = match.group(2)
                    ano = match.group(3)
                    projeto_simplificado = f'{tipo_texto} {numero}/{ano}'

                if id_proposicao:
                    link_projeto = f'https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id_proposicao}'

                votos_do_deputado.append({
                    'id': id_votacao,
                    'descricao_original': descricao,
                    'projeto_simplificado': projeto_simplificado,
                    'link_projeto': link_projeto,
                    'data': votacao.get('dataHoraRegistro', '').split('T')[0],
                    'voto': voto_encontrado.get('voto', 'Não registrado')
                })

        return jsonify({'votacoes': votos_do_deputado})

    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ==========================================
# 4. ROTA DE DETALHES DA PROPOSIÇÃO
# ==========================================
@app.route('/proposicao/<id_proposicao>')
def detalhes_proposicao(id_proposicao):
    try:
        url_prop = f'https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id_proposicao}'
        resp_prop = requests.get(url_prop).json()
        dados_prop = resp_prop.get('dados', {})

        return jsonify({
            'id': id_proposicao,
            'ementa': dados_prop.get('ementa', 'Ementa não disponível'),
            'link_oficial': f'https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id_proposicao}'
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ==========================================
# 5. EXECUÇÃO (FINAL DO ARQUIVO)
# ==========================================
if __name__ == '__main__':
    app.run(debug=True)

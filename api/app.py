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

            # Busca o voto do deputado
            url_votos = f'https://dadosabertos.camara.leg.br/api/v2/votacoes/{id_votacao}/votos'
            resp_votos = requests.get(url_votos).json()
            votos = resp_votos.get('dados', [])

            voto_encontrado = next((v for v in votos if str(v['deputado_']['id']) == id_deputado), None)

            if voto_encontrado:
                # Tenta pegar o ID da proposição diretamente
                id_proposicao = votacao.get('idProposicaoObjeto')
                
                # SE FOR NULO, busca os detalhes da votação para encontrar a proposição
                if not id_proposicao:
                    url_detalhes = f'https://dadosabertos.camara.leg.br/api/v2/votacoes/{id_votacao}'
                    resp_detalhes = requests.get(url_detalhes).json()
                    dados_detalhes = resp_detalhes.get('dados', {})
                    
                    # Pega a primeira proposição da lista de objetosPossiveis
                    objetos = dados_detalhes.get('objetosPossiveis', [])
                    if objetos:
                        id_proposicao = objetos[0].get('id')

                # Tenta simplificar a descrição
                match = re.search(r'(Projeto de Lei(?: Complementar)?)\s*n[º°]?\s*(\d+).*?de\s*(\d{4})', descricao, re.IGNORECASE)
                projeto_simplificado = descricao
                link_projeto = None
                
                if match:
                    tipo_texto = match.group(1)
                    numero = match.group(2)
                    ano = match.group(3)
                    projeto_simplificado = f'{tipo_texto} {numero}/{ano}'

                # Só monta o link se tivermos um ID de proposição válido
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

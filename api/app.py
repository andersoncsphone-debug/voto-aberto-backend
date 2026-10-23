from flask import Flask, jsonify
import json
import urllib.request

app = Flask(__name__)

# URL do arquivo JSON da Câmara (vamos usar o de 2024 que é menor)
URL_ARQUIVO = "http://www.camara.leg.br/cotas/Ano-2024.json"

@app.route('/gastos/<id_deputado>')
def buscar_gastos(id_deputado):
    try:
        # 1. Baixa o arquivo da Câmara
        resposta = urllib.request.urlopen(URL_ARQUIVO)
        dados = json.loads(resposta.read().decode('utf-8'))
        
        # 2. Filtra os gastos do deputado
        gastos = [d for d in dados.get('dados', []) if str(d.get('idDeputado')) == id_deputado]
        
        if not gastos:
            return jsonify({"erro": "Nenhum gasto encontrado para este deputado."}), 404

        # 3. Calcula os totais
        total = sum(float(d.get('valorLiquido', 0)) for d in gastos)
        meses = len(set(d.get('mes') for d in gastos))
        media = total / meses if meses > 0 else 0
        ultimo_mes = f"Mês {gastos[-1]['mes']}/{gastos[-1]['ano']}"

        # 4. Retorna um JSON pequeno e limpo
        return jsonify({
            "id": id_deputado,
            "total_gasto": total,
            "media_mensal": media,
            "ultimo_mes": ultimo_mes,
            "total_despesas": len(gastos)
        })

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

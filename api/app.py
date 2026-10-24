from flask import Flask, jsonify
import json
import os
import glob

app = Flask(__name__)

@app.route('/gastos/<id_deputado>')
def buscar_gastos(id_deputado):
    # Procura qualquer arquivo que comece com 'politico_ID' (seja único ou dividido)
    padrao_busca = os.path.join('dados', 'por_politico', f'politico_{id_deputado}*.json')
    arquivos = glob.glob(padrao_busca)

    if not arquivos:
        return jsonify({"erro": "Nenhum gasto encontrado para este deputado."}), 404

    total_gasto = 0.0
    meses_com_gasto = set()
    ultimo_mes = ""
    total_despesas = 0

    for arquivo in arquivos:
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                gastos = dados.get('dados', [])
                
                for g in gastos:
                    total_gasto += float(g.get('valorLiquido', 0))
                    meses_com_gasto.add(g.get('mes'))
                    ultimo_mes = f"Mês {g.get('mes')}/{g.get('ano')}"
                    total_despesas += 1
        except Exception as e:
            print(f"Erro ao ler {arquivo}: {e}")
            continue

    if total_gasto == 0:
        return jsonify({"erro": "Nenhum valor de gasto encontrado."}), 404

    media = total_gasto / len(meses_com_gasto) if meses_com_gasto else 0

    return jsonify({
        "id": id_deputado,
        "total_gasto": total_gasto,
        "media_mensal": media,
        "ultimo_mes": ultimo_mes,
        "total_despesas": total_despesas
    })

if __name__ == '__main__':
    app.run(debug=True)

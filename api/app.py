from flask import Flask, jsonify
import json
import glob
import os

app = Flask(__name__)

@app.route('/gastos/<id_deputado>')
def buscar_gastos(id_deputado):
    total_gasto = 0.0
    meses_com_gasto = set()
    ultimo_mes = ""

    # O caminho relativo a partir da pasta 'api' (raiz do Render)
    # Ele vai procurar qualquer arquivo .json dentro de 'dados/despesas/'
    padrao_busca = os.path.join('dados', 'despesas', '*.json')
    arquivos = glob.glob(padrao_busca)

    if not arquivos:
        return jsonify({"erro": "Nenhum arquivo de despesa encontrado no servidor."}), 500

    for arquivo in arquivos:
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                # Filtra pelo ID do deputado
                gastos = [d for d in dados.get('dados', []) if str(d.get('idDeputado')) == id_deputado]
                
                for g in gastos:
                    total_gasto += float(g.get('valorLiquido', 0))
                    meses_com_gasto.add(g.get('mes'))
                    ultimo_mes = f"Mês {g.get('mes')}/{g.get('ano')}"
        except Exception as e:
            print(f"Erro ao ler {arquivo}: {e}")
            continue

    if total_gasto == 0:
        return jsonify({"erro": "Nenhum gasto encontrado para este deputado."}), 404

    media = total_gasto / len(meses_com_gasto) if meses_com_gasto else 0

    return jsonify({
        "id": id_deputado,
        "total_gasto": total_gasto,
        "media_mensal": media,
        "ultimo_mes": ultimo_mes,
        "total_despesas": len(meses_com_gasto)
    })

if __name__ == '__main__':
    app.run(debug=True)

import os
import io
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

DIR_ATUAL = os.path.dirname(os.path.abspath(__file__))
DIR_RAIZ = os.path.dirname(DIR_ATUAL)
BASE_DIR = os.path.join(DIR_RAIZ, "api", "dados", "camara_federal")
DIR_PROPOSICOES = os.path.join(BASE_DIR, "proposicoes")
DIR_CACHE = os.path.join(BASE_DIR, "_cache")
LIMITE_BYTES = 20 * 1024 * 1024

URL_PROPOSICOES = "https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-{ano}.csv"
URL_PROP_AUTORES = "https://dadosabertos.camara.leg.br/arquivos/proposicoesAutores/csv/proposicoesAutores-{ano}.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (VotoAberto/1.0)"}

def ja_baixou_hoje(ano):
    marker = os.path.join(DIR_CACHE, f"proposicoes_{ano}.done")
    if not os.path.exists(marker): return False
    return datetime.now() - datetime.fromtimestamp(os.path.getmtime(marker)) < timedelta(hours=24)

def marcar_baixado(ano):
    marker = os.path.join(DIR_CACHE, f"proposicoes_{ano}.done")
    with open(marker, "w") as f: f.write(datetime.now().isoformat())

def carregar_dados_existentes(pasta_deputado):
    existentes = []
    if os.path.exists(pasta_deputado):
        for arq in sorted(os.listdir(pasta_deputado)):
            if arq.startswith("parte_") and arq.endswith(".json"):
                with open(os.path.join(pasta_deputado, arq), "r", encoding="utf-8") as f:
                    try: existentes.extend(json.load(f).get("dados", []))
                    except: pass
    return existentes

def salvar_em_partes(id_deputado, todas_props):
    pasta_deputado = os.path.join(DIR_PROPOSICOES, str(id_deputado))
    os.makedirs(pasta_deputado, exist_ok=True)
    for f in os.listdir(pasta_deputado):
        if f.startswith("parte_"): os.remove(os.path.join(pasta_deputado, f))
    parte, tamanho, num = [], 0, 1
    for p in todas_props:
        t = len(json.dumps(p, ensure_ascii=False).encode('utf-8'))
        if tamanho + t > LIMITE_BYTES and parte:
            with open(os.path.join(pasta_deputado, f"parte_{num:03d}.json"), "w", encoding="utf-8") as f:
                json.dump({"dados": parte}, f, ensure_ascii=False)
            num += 1; parte = []; tamanho = 0
        parte.append(p); tamanho += t
    if parte:
        with open(os.path.join(pasta_deputado, f"parte_{num:03d}.json"), "w", encoding="utf-8") as f:
            json.dump({"dados": parte}, f, ensure_ascii=False)

def atualizar_proposicoes(ano):
    os.makedirs(DIR_PROPOSICOES, exist_ok=True); os.makedirs(DIR_CACHE, exist_ok=True)
    if ja_baixou_hoje(ano):
        print(f"  ⏭️  Proposições {ano} já baixadas hoje. Pulando..."); return

    print(f"  ⬇️  Baixando: {URL_PROPOSICOES.format(ano=ano)}")
    print(f"  ⬇️  Baixando: {URL_PROP_AUTORES.format(ano=ano)}")
    try:
        r_prop = requests.get(URL_PROPOSICOES.format(ano=ano), headers=HEADERS, timeout=300)
        r_aut = requests.get(URL_PROP_AUTORES.format(ano=ano), headers=HEADERS, timeout=300)
        r_prop.raise_for_status(); r_aut.raise_for_status()
        df_prop = pd.read_csv(io.StringIO(r_prop.content.decode("utf-8-sig")), sep=";", dtype=str)
        df_aut = pd.read_csv(io.StringIO(r_aut.content.decode("utf-8-sig")), sep=";", dtype=str)
    except Exception as e:
        print(f"  ❌ Erro: {e}"); return

    df_prop['id'] = df_prop['id'].astype(str).str.replace('"', '').str.strip()
    df_aut['idProposicao'] = df_aut['idProposicao'].astype(str).str.replace('"', '').str.strip()
    df_aut['idDeputadoAutor'] = df_aut['idDeputadoAutor'].astype(str).str.replace('"', '').str.strip()
    df_aut = df_aut[df_aut['idDeputadoAutor'].notna() & (df_aut['idDeputadoAutor'] != 'nan')]

    proposicoes_dict = {}
    for _, row in df_prop.iterrows():
        proposicoes_dict[row['id']] = {
            "idProposicao": row.get("id"), "siglaTipo": row.get("siglaTipo"),
            "numero": row.get("numero"), "ano": ano, "ementa": row.get("ementa"),
            "situacao": row.get("descricaoSituacao") or row.get("ultimoStatus_descricaoSituacao"),
            "dataApresentacao": row.get("dataApresentacao"), "urlInteiroTeor": row.get("urlInteiroTeor"),
        }

    por_deputado = defaultdict(list)
    for _, row in df_aut.iterrows():
        id_prop = row['idProposicao']; id_dep = row['idDeputadoAutor']
        if id_prop in proposicoes_dict: por_deputado[id_dep].append(proposicoes_dict[id_prop])

    for id_dep, props in por_deputado.items():
        pasta_dep = os.path.join(DIR_PROPOSICOES, str(id_dep))
        existentes = carregar_dados_existentes(pasta_dep)
        existentes = [p for p in existentes if str(p.get("ano")) != str(ano)]
        salvar_em_partes(id_dep, existentes + props)

    marcar_baixado(ano)
    print(f"  ✅ Proposições {ano}: {len(por_deputado)} deputados.")

if __name__ == "__main__":
    print("\n=== COLETOR DE PROPOSIÇÕES ===")
    try:
        ano_input = input("Digite o ano (ex: 2026) ou ENTER para o atual: ").strip()
        ano = int(ano_input) if ano_input else datetime.now().year
        atualizar_proposicoes(ano)
    except ValueError: print("  ❌ Ano inválido.")
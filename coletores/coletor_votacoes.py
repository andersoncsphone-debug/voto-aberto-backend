import os
import io
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

# --- CAMINHOS INTELIGENTES ---
DIR_ATUAL = os.path.dirname(os.path.abspath(__file__))
DIR_RAIZ = os.path.dirname(DIR_ATUAL)
BASE_DIR = os.path.join(DIR_RAIZ, "api", "dados", "camara_federal")
DIR_PROPOSICOES = os.path.join(BASE_DIR, "proposicoes")
DIR_CACHE = os.path.join(BASE_DIR, "_cache")

URL_PROPOSICOES = "https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-{ano}.csv"
URL_PROP_AUTORES = "https://dadosabertos.camara.leg.br/arquivos/proposicoesAutores/csv/proposicoesAutores-{ano}.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (VotoAberto/1.0)"}

def ja_baixou_hoje(ano):
    marker = os.path.join(DIR_CACHE, f"proposicoes_{ano}.done")
    if not os.path.exists(marker): return False
    mod_time = datetime.fromtimestamp(os.path.getmtime(marker))
    return datetime.now() - mod_time < timedelta(hours=24)

def marcar_baixado(ano):
    marker = os.path.join(DIR_CACHE, f"proposicoes_{ano}.done")
    with open(marker, "w") as f: f.write(datetime.now().isoformat())

def atualizar_proposicoes(ano):
    os.makedirs(DIR_PROPOSICOES, exist_ok=True)
    os.makedirs(DIR_CACHE, exist_ok=True)

    if ja_baixou_hoje(ano):
        print(f"  ⏭️  Proposições {ano} já baixadas hoje. Pulando...")
        return

    print(f"  ⬇️  Baixando: {URL_PROPOSICOES.format(ano=ano)}")
    print(f"  ⬇️  Baixando: {URL_PROP_AUTORES.format(ano=ano)}")

    try:
        r_prop = requests.get(URL_PROPOSICOES.format(ano=ano), headers=HEADERS, timeout=300)
        r_aut = requests.get(URL_PROP_AUTORES.format(ano=ano), headers=HEADERS, timeout=300)
        r_prop.raise_for_status()
        r_aut.raise_for_status()
        
        # CORREÇÃO DO ERRO DE TOKENIZING
        df_prop = pd.read_csv(io.StringIO(r_prop.content.decode("utf-8-sig")), sep=";", dtype=str)
        df_aut = pd.read_csv(io.StringIO(r_aut.content.decode("utf-8-sig")), sep=";", dtype=str)
    except Exception as e:
        print(f"  ❌ Erro ao baixar/ler CSVs {ano}: {e}")
        return

    # Limpa aspas e espaços
    df_prop['id'] = df_prop['id'].astype(str).str.replace('"', '').str.strip()
    df_aut['idProposicao'] = df_aut['idProposicao'].astype(str).str.replace('"', '').str.strip()
    df_aut['idDeputadoAutor'] = df_aut['idDeputadoAutor'].astype(str).str.replace('"', '').str.strip()

    # Remove nulos do deputado
    df_aut = df_aut[df_aut['idDeputadoAutor'].notna() & (df_aut['idDeputadoAutor'] != 'nan')]

    proposicoes_dict = {}
    for _, row in df_prop.iterrows():
        proposicoes_dict[row['id']] = {
            "idProposicao": row.get("id"),
            "siglaTipo": row.get("siglaTipo"),
            "numero": row.get("numero"),
            "ano": ano,
            "ementa": row.get("ementa"),
            "situacao": row.get("descricaoSituacao") or row.get("ultimoStatus_descricaoSituacao"),
            "dataApresentacao": row.get("dataApresentacao"),
            "urlInteiroTeor": row.get("urlInteiroTeor"),
        }

    por_deputado = defaultdict(list)
    for _, row in df_aut.iterrows():
        id_prop = row['idProposicao']
        id_dep = row['idDeputadoAutor']
        if id_prop in proposicoes_dict:
            por_deputado[id_dep].append(proposicoes_dict[id_prop])

    print(f"  [debug] Cruzamento encontrou {len(por_deputado)} deputados.")

    for id_dep, props in por_deputado.items():
        caminho = os.path.join(DIR_PROPOSICOES, f"{id_dep}.json")
        existente = []
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                try: existente = json.load(f).get("dados", [])
                except: pass
        
        existente = [p for p in existente if str(p.get("ano")) != str(ano)]
        
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump({"dados": existente + props}, f, ensure_ascii=False)

    marcar_baixado(ano)
    print(f"  ✅ Proposições {ano}: {len(por_deputado)} deputados processados.")

if __name__ == "__main__":
    print("\n=== COLETOR DE PROPOSIÇÕES ===")
    try:
        ano_input = input("Digite o ano (ex: 2026) ou ENTER para o ano atual: ").strip()
        ano = int(ano_input) if ano_input else datetime.now().year
        atualizar_proposicoes(ano)
    except ValueError:
        print("  ❌ Ano inválido.")
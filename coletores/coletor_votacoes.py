import os
import io
import json
import requests
import pandas as pd
from datetime import datetime, timedelta

DIR_ATUAL = os.path.dirname(os.path.abspath(__file__))
DIR_RAIZ = os.path.dirname(DIR_ATUAL)
BASE_DIR = os.path.join(DIR_RAIZ, "api", "dados", "camara_federal")
DIR_VOTACOES = os.path.join(BASE_DIR, "votacoes")
DIR_CACHE = os.path.join(BASE_DIR, "_cache")
LIMITE_BYTES = 20 * 1024 * 1024

URL_VOTACOES = "https://dadosabertos.camara.leg.br/arquivos/votacoes/csv/votacoes-{ano}.csv"
URL_VOTOS = "https://dadosabertos.camara.leg.br/arquivos/votacoesVotos/csv/votacoesVotos-{ano}.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (VotoAberto/1.0)"}

def ja_baixou_hoje(ano):
    marker = os.path.join(DIR_CACHE, f"votacoes_{ano}.done")
    if not os.path.exists(marker): return False
    return datetime.now() - datetime.fromtimestamp(os.path.getmtime(marker)) < timedelta(hours=24)

def marcar_baixado(ano):
    marker = os.path.join(DIR_CACHE, f"votacoes_{ano}.done")
    with open(marker, "w") as f: f.write(datetime.now().isoformat())

def normalizar_voto(v):
    if not v or (isinstance(v, float) and pd.isna(v)): return "Não registrado individualmente"
    v = str(v).strip().lower()
    mapa = {"sim": "Sim", "não": "Não", "nao": "Não", "abstenção": "Abstenção", "abstencao": "Abstenção", "obstrução": "Obstrução", "obstrucao": "Obstrução", "art. 17": "Obstrução"}
    return mapa.get(v, str(v).capitalize())

def carregar_dados_existentes(pasta_deputado):
    existentes = []
    if os.path.exists(pasta_deputado):
        for arq in sorted(os.listdir(pasta_deputado)):
            if arq.startswith("parte_") and arq.endswith(".json"):
                with open(os.path.join(pasta_deputado, arq), "r", encoding="utf-8") as f:
                    try: existentes.extend(json.load(f).get("dados", []))
                    except: pass
    return existentes

def salvar_em_partes(id_deputado, todos_votos):
    pasta_deputado = os.path.join(DIR_VOTACOES, str(id_deputado))
    os.makedirs(pasta_deputado, exist_ok=True)
    for f in os.listdir(pasta_deputado):
        if f.startswith("parte_"): os.remove(os.path.join(pasta_deputado, f))
    parte, tamanho, num = [], 0, 1
    for v in todos_votos:
        t = len(json.dumps(v, ensure_ascii=False).encode('utf-8'))
        if tamanho + t > LIMITE_BYTES and parte:
            with open(os.path.join(pasta_deputado, f"parte_{num:03d}.json"), "w", encoding="utf-8") as f:
                json.dump({"dados": parte}, f, ensure_ascii=False)
            num += 1; parte = []; tamanho = 0
        parte.append(v); tamanho += t
    if parte:
        with open(os.path.join(pasta_deputado, f"parte_{num:03d}.json"), "w", encoding="utf-8") as f:
            json.dump({"dados": parte}, f, ensure_ascii=False)

def atualizar_votacoes(ano):
    os.makedirs(DIR_VOTACOES, exist_ok=True); os.makedirs(DIR_CACHE, exist_ok=True)
    if ja_baixou_hoje(ano):
        print(f"  ⏭️  Votações {ano} já baixadas hoje. Pulando..."); return

    print(f"  ⬇️  Baixando: {URL_VOTACOES.format(ano=ano)}")
    print(f"  ⬇️  Baixando: {URL_VOTOS.format(ano=ano)}")
    try:
        r_vot = requests.get(URL_VOTACOES.format(ano=ano), headers=HEADERS, timeout=300)
        r_votos = requests.get(URL_VOTOS.format(ano=ano), headers=HEADERS, timeout=300)
        r_vot.raise_for_status(); r_votos.raise_for_status()
        df_votacoes = pd.read_csv(io.StringIO(r_vot.content.decode("utf-8-sig")), sep=";", dtype=str)
        df_votos = pd.read_csv(io.StringIO(r_votos.content.decode("utf-8-sig")), sep=";", dtype=str)
    except Exception as e:
        print(f"  ❌ Erro: {e}"); return

    col_id = next((c for c in ["idVotacao", "id", "id_votacao"] if c in df_votacoes.columns), None)
    if not col_id: print("  ❌ ID não encontrado."); return
    df_votacoes = df_votacoes.rename(columns={col_id: "idVotacao"})
    df_votos = df_votos.rename(columns={col_id: "idVotacao"})
    df_votacoes["idVotacao"] = df_votacoes["idVotacao"].str.replace('"', '')
    df_votos["idVotacao"] = df_votos["idVotacao"].str.replace('"', '')
    df_completo = pd.merge(df_votos, df_votacoes, on="idVotacao", how="left")
    col_dep = next((c for c in ["deputado_id", "idDeputado", "deputadoID"] if c in df_completo.columns), None)
    if not col_dep: print("  ❌ Deputado não encontrado."); return
    df_completo[col_dep] = df_completo[col_dep].str.replace('"', '')

    for dep_id, grupo in df_completo.groupby(col_dep):
        pasta_dep = os.path.join(DIR_VOTACOES, str(dep_id))
        existentes = carregar_dados_existentes(pasta_dep)
        existentes = [d for d in existentes if str(d.get("ano")) != str(ano)]
        novos = grupo.to_dict("records")
        for d in novos:
            d["ano"] = ano
            if "voto" in d: d["voto"] = normalizar_voto(d["voto"])
        salvar_em_partes(dep_id, existentes + novos)

    marcar_baixado(ano)
    print(f"  ✅ Votações {ano}: {df_completo[col_dep].nunique()} deputados.")

if __name__ == "__main__":
    print("\n=== COLETOR DE VOTAÇÕES ===")
    try:
        ano_input = input("Digite o ano (ex: 2026) ou ENTER para o atual: ").strip()
        ano = int(ano_input) if ano_input else datetime.now().year
        atualizar_votacoes(ano)
    except ValueError: print("  ❌ Ano inválido.")
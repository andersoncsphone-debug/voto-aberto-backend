"""
atualizador.py — Voto Aberto (Backend Render)
Baixa dados da Câmara Federal e organiza em:
  dados/camara_federal/cotas/{id}.json
  dados/camara_federal/votacoes/{id}.json
  dados/camara_federal/proposicoes/{id}.json
"""

import os
import io
import json
import zipfile
import requests
import pandas as pd
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# ==========================================
# CONFIGURAÇÕES
# ==========================================
BASE_DIR = os.path.join("dados", "camara_federal")
DIR_COTAS = os.path.join(BASE_DIR, "cotas")
DIR_VOTACOES = os.path.join(BASE_DIR, "votacoes")
DIR_PROPOSICOES = os.path.join(BASE_DIR, "proposicoes")
DIR_CACHE = os.path.join(BASE_DIR, "_cache")

HEADERS = {"User-Agent": "Mozilla/5.0 (VotoAberto/1.0)"}

# URLs OFICIAIS
URL_COTAS = "http://www.camara.leg.br/cotas/Ano-{ano}.json.zip"
URL_VOTACOES = "https://dadosabertos.camara.leg.br/arquivos/votacoes/csv/votacoes-{ano}.csv"
URL_VOTOS = "https://dadosabertos.camara.leg.br/arquivos/votacoesVotos/csv/votacoesVotos-{ano}.csv"
URL_PROPOSICOES = "https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-{ano}.csv"
URL_PROP_AUTORES = "https://dadosabertos.camara.leg.br/arquivos/proposicoesAutores/csv/proposicoesAutores-{ano}.csv"

# ==========================================
# UTILITÁRIOS
# ==========================================
def garantir_pastas():
    for d in [DIR_COTAS, DIR_VOTACOES, DIR_PROPOSICOES, DIR_CACHE]:
        os.makedirs(d, exist_ok=True)

def ja_baixou_hoje(tipo, ano):
    marker = os.path.join(DIR_CACHE, f"{tipo}_{ano}.done")
    if not os.path.exists(marker):
        return False
    mod_time = datetime.fromtimestamp(os.path.getmtime(marker))
    return datetime.now() - mod_time < timedelta(hours=24)

def marcar_baixado(tipo, ano):
    marker = os.path.join(DIR_CACHE, f"{tipo}_{ano}.done")
    with open(marker, "w") as f:
        f.write(datetime.now().isoformat())

def baixar_bytes(url):
    print(f"  ⬇️  Baixando: {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=300)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print(f"  ❌ Falha: {e}")
        return None

def normalizar_voto(v):
    if not v or (isinstance(v, float) and pd.isna(v)):
        return "Não registrado individualmente"
    v = str(v).strip().lower()
    mapa = {
        "sim": "Sim", "não": "Não", "nao": "Não",
        "abstenção": "Abstenção", "abstencao": "Abstenção",
        "obstrução": "Obstrução", "obstrucao": "Obstrução",
        "art. 17": "Obstrução",
    }
    return mapa.get(v, str(v).capitalize())

# ==========================================
# 1. COTAS
# ==========================================
def atualizar_cotas(ano):
    if ja_baixou_hoje("cotas", ano):
        print(f"  ⏭️  Cotas {ano} já baixadas hoje.")
        return

    conteudo = baixar_bytes(URL_COTAS.format(ano=ano))
    if not conteudo:
        return

    por_deputado = defaultdict(list)
    try:
        with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
            for nome in z.namelist():
                if not nome.endswith(".json"):
                    continue
                with z.open(nome) as f:
                    dados = json.load(f)
                    for g in dados.get("dados", []):
                        id_dep = g.get("idDeputado")
                        if id_dep is not None:
                            por_deputado[str(id_dep)].append(g)
    except Exception as e:
        print(f"  ❌ Erro no ZIP {ano}: {e}")
        return

    for id_dep, gastos in por_deputado.items():
        caminho = os.path.join(DIR_COTAS, f"{id_dep}.json")
        existente = []
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                existente = json.load(f).get("dados", [])
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump({"dados": existente + gastos}, f, ensure_ascii=False)

    marcar_baixado("cotas", ano)
    print(f"  ✅ Cotas {ano}: {len(por_deputado)} deputados.")

# ==========================================
# 2. VOTAÇÕES
# ==========================================
def atualizar_votacoes(ano):
    if ja_baixou_hoje("votacoes", ano):
        print(f"  ⏭️  Votações {ano} já baixadas hoje.")
        return

    conteudo_vot = baixar_bytes(URL_VOTACOES.format(ano=ano))
    conteudo_votos = baixar_bytes(URL_VOTOS.format(ano=ano))
    if not conteudo_vot or not conteudo_votos:
        return

    try:
        df_votacoes = pd.read_csv(io.StringIO(conteudo_vot.decode("utf-8")), sep=";")
        df_votos = pd.read_csv(io.StringIO(conteudo_votos.decode("utf-8")), sep=";")
    except Exception as e:
        print(f"  ❌ Erro ao ler CSVs de votos {ano}: {e}")
        return

    col_id = next((c for c in ["idVotacao", "id", "id_votacao"] if c in df_votacoes.columns), None)
    if not col_id:
        print(f"  ❌ Coluna ID não encontrada.")
        return
    
    df_votacoes = df_votacoes.rename(columns={col_id: "idVotacao"})
    df_votos = df_votos.rename(columns={col_id: "idVotacao"})
    df_votacoes["idVotacao"] = df_votacoes["idVotacao"].astype(str)
    df_votos["idVotacao"] = df_votos["idVotacao"].astype(str)

    df_completo = pd.merge(df_votos, df_votacoes, on="idVotacao", how="left")
    col_dep = next((c for c in ["deputado_id", "idDeputado", "deputadoID"] if c in df_completo.columns), None)
    if not col_dep:
        print(f"  ❌ Coluna do deputado não encontrada.")
        return

    for dep_id, grupo in df_completo.groupby(col_dep):
        id_str = str(dep_id)
        caminho = os.path.join(DIR_VOTACOES, f"{id_str}.json")
        existente = []
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                try: existente = json.load(f).get("dados", [])
                except: pass
        
        existente = [d for d in existente if str(d.get("ano")) != str(ano)]
        novos = grupo.to_dict("records")
        for d in novos:
            d["ano"] = ano
            if "voto" in d: d["voto"] = normalizar_voto(d["voto"])
            
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump({"dados": existente + novos}, f, ensure_ascii=False)

    marcar_baixado("votacoes", ano)
    print(f"  ✅ Votações {ano}: {df_completo[col_dep].nunique()} deputados.")

# ==========================================
# 3. PROPOSIÇÕES (AGORA COM AUTORES!)
# ==========================================
def atualizar_proposicoes(ano):
    if ja_baixou_hoje("proposicoes", ano):
        print(f"  ⏭️  Proposições {ano} já baixadas hoje.")
        return

    # Baixa os dois arquivos: proposições e autores
    conteudo_prop = baixar_bytes(URL_PROPOSICOES.format(ano=ano))
    conteudo_aut = baixar_bytes(URL_PROP_AUTORES.format(ano=ano))
    
    if not conteudo_prop or not conteudo_aut:
        return

    try:
        df_prop = pd.read_csv(io.StringIO(conteudo_prop.decode("utf-8")), sep=";")
        df_aut = pd.read_csv(io.StringIO(conteudo_aut.decode("utf-8")), sep=";")
    except Exception as e:
        print(f"  ❌ Erro ao ler CSVs {ano}: {e}")
        return

    # O arquivo de autores tem 'idProposicao' e 'idDeputado' (ou similar)
    col_id_prop = next((c for c in ["id", "idProposicao"] if c in df_prop.columns), None)
    col_id_aut = next((c for c in ["idProposicao", "id"] if c in df_aut.columns), None)
    col_dep = next((c for c in ["idDeputado", "deputado_id"] if c in df_aut.columns), None)

    if not col_id_prop or not col_id_aut or not col_dep:
        print(f"  ❌ Colunas não encontradas. Autores: {df_aut.columns.tolist()}")
        return

    # Filtra autores que são deputados (ignora senadores, comissões, etc)
    df_aut = df_aut[df_aut[col_dep].notna()]
    df_aut[col_dep] = df_aut[col_dep].astype(float).astype(int).astype(str)

    # Merge: pega os dados da proposição para cada autor
    df_merge = pd.merge(df_aut, df_prop, left_on=col_id_aut, right_on=col_id_prop, how="inner")

    # Agrupa por deputado
    for dep_id, grupo in df_merge.groupby(col_dep):
        id_str = str(dep_id)
        caminho = os.path.join(DIR_PROPOSICOES, f"{id_str}.json")
        existente = []
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                try: existente = json.load(f).get("dados", [])
                except: pass

        existente = [p for p in existente if str(p.get("ano")) != str(ano)]
        
        novos = grupo.to_dict("records")
        props_limpas = []
        for row in novos:
            props_limpas.append({
                "idProposicao": row.get(col_id_prop),
                "siglaTipo": row.get("siglaTipo"),
                "numero": row.get("numero"),
                "ano": ano,
                "ementa": row.get("ementa"),
                "situacao": row.get("descricaoSituacao") or row.get("ultimoStatus_descricaoSituacao"),
                "dataApresentacao": row.get("dataApresentacao"),
                "urlInteiroTeor": row.get("urlInteiroTeor"),
            })

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump({"dados": existente + props_limpas}, f, ensure_ascii=False)

    marcar_baixado("proposicoes", ano)
    print(f"  ✅ Proposições {ano}: {df_merge[col_dep].nunique()} deputados.")

# ==========================================
# EXECUÇÃO
# ==========================================
def rodar_ano(ano):
    print(f"\n📅 Ano {ano}")
    atualizar_cotas(ano)
    atualizar_votacoes(ano)
    atualizar_proposicoes(ano)

def main():
    garantir_pastas()
    ano_atual = datetime.now().year
    ANO_INICIO = 2009

    print("=" * 70)
    print("ATUALIZADOR DE DADOS — Voto Aberto")
    print("=" * 70)
    print("\nEscolha uma opção digitando o número e apertando ENTER:")
    print("1 - Atualizar apenas o ANO ATUAL (rápido)")
    print(f"2 - Baixar TUDO ({ANO_INICIO} até {ano_atual}) — pode demorar horas")
    print("3 - Baixar um ANO ESPECÍFICO")
    
    opcao = input("\nOpção (1/2/3): ").strip()

    if opcao == "1":
        rodar_ano(ano_atual)
    elif opcao == "2":
        for a in range(ANO_INICIO, ano_atual + 1):
            rodar_ano(a)
    elif opcao == "3":
        try:
            ano_escolhido = int(input("Digite o ano (ex: 2022): "))
            rodar_ano(ano_escolhido)
        except ValueError:
            print("❌ Ano inválido.")
    else:
        print("❌ Opção inválida.")
    
    print("\n✅ Processo finalizado.")

if __name__ == "__main__":
    main()
    input("\nPressione ENTER para fechar...")



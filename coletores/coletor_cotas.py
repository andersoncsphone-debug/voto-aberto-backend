import os
import io
import json
import zipfile
import requests
from datetime import datetime, timedelta
from collections import defaultdict

# --- CAMINHOS INTELIGENTES ---
DIR_ATUAL = os.path.dirname(os.path.abspath(__file__))
DIR_RAIZ = os.path.dirname(DIR_ATUAL)
BASE_DIR = os.path.join(DIR_RAIZ, "api", "dados", "camara_federal")
DIR_COTAS = os.path.join(BASE_DIR, "cotas")
DIR_CACHE = os.path.join(BASE_DIR, "_cache")

URL_COTAS = "http://www.camara.leg.br/cotas/Ano-{ano}.json.zip"
HEADERS = {"User-Agent": "Mozilla/5.0 (VotoAberto/1.0)"}

def ja_baixou_hoje(ano):
    marker = os.path.join(DIR_CACHE, f"cotas_{ano}.done")
    if not os.path.exists(marker): return False
    mod_time = datetime.fromtimestamp(os.path.getmtime(marker))
    return datetime.now() - mod_time < timedelta(hours=24)

def marcar_baixado(ano):
    marker = os.path.join(DIR_CACHE, f"cotas_{ano}.done")
    with open(marker, "w") as f: f.write(datetime.now().isoformat())

def atualizar_cotas(ano):
    os.makedirs(DIR_COTAS, exist_ok=True)
    os.makedirs(DIR_CACHE, exist_ok=True)

    if ja_baixou_hoje(ano):
        print(f"  ⏭️  Cotas {ano} já baixadas hoje. Pulando...")
        return

    url = URL_COTAS.format(ano=ano)
    print(f"  ⬇️  Baixando: {url}")
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=300)
        r.raise_for_status()
    except Exception as e:
        print(f"  ❌ Falha ao baixar cotas {ano}: {e}")
        return

    por_deputado = defaultdict(list)
    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            for nome in z.namelist():
                if not nome.endswith(".json"): continue
                with z.open(nome) as f:
                    dados = json.load(f)
                    for g in dados.get("dados", []):
                        id_dep = g.get("idDeputado")
                        if id_dep is not None:
                            por_deputado[str(id_dep)].append(g)
    except Exception as e:
        print(f"  ❌ Erro ao processar ZIP {ano}: {e}")
        return

    for id_dep, gastos in por_deputado.items():
        caminho = os.path.join(DIR_COTAS, f"{id_dep}.json")
        existente = []
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                try: existente = json.load(f).get("dados", [])
                except: pass
        
        existente = [d for d in existente if str(d.get("ano")) != str(ano)]
        
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump({"dados": existente + gastos}, f, ensure_ascii=False)

    marcar_baixado(ano)
    print(f"  ✅ Cotas {ano}: {len(por_deputado)} deputados processados.")

if __name__ == "__main__":
    print("\n=== COLETOR DE COTAS (CEAP) ===")
    try:
        ano_input = input("Digite o ano (ex: 2026) ou ENTER para o ano atual: ").strip()
        ano = int(ano_input) if ano_input else datetime.now().year
        atualizar_cotas(ano)
    except ValueError:
        print("  ❌ Ano inválido.")
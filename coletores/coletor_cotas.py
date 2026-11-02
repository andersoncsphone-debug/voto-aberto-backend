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
LIMITE_BYTES = 20 * 1024 * 1024  # 20 MB

URL_COTAS = "http://www.camara.leg.br/cotas/Ano-{ano}.json.zip"
HEADERS = {"User-Agent": "Mozilla/5.0 (VotoAberto/1.0)"}

def ja_baixou_hoje(ano):
    marker = os.path.join(DIR_CACHE, f"cotas_{ano}.done")
    if not os.path.exists(marker): return False
    return datetime.now() - datetime.fromtimestamp(os.path.getmtime(marker)) < timedelta(hours=24)

def marcar_baixado(ano):
    marker = os.path.join(DIR_CACHE, f"cotas_{ano}.done")
    with open(marker, "w") as f: f.write(datetime.now().isoformat())

def carregar_dados_existentes(pasta_deputado):
    """Lê todas as partes existentes e junta numa lista só."""
    existentes = []
    if os.path.exists(pasta_deputado):
        for arq in sorted(os.listdir(pasta_deputado)):
            if arq.startswith("parte_") and arq.endswith(".json"):
                with open(os.path.join(pasta_deputado, arq), "r", encoding="utf-8") as f:
                    try: existentes.extend(json.load(f).get("dados", []))
                    except: pass
    return existentes

def salvar_em_partes(id_deputado, todos_gastos):
    """Divide a lista em partes de até 20MB e salva."""
    pasta_deputado = os.path.join(DIR_COTAS, str(id_deputado))
    os.makedirs(pasta_deputado, exist_ok=True)
    
    # Limpa partes antigas
    for f in os.listdir(pasta_deputado):
        if f.startswith("parte_"): os.remove(os.path.join(pasta_deputado, f))
    
    parte, tamanho, num = [], 0, 1
    for g in todos_gastos:
        t = len(json.dumps(g, ensure_ascii=False).encode('utf-8'))
        if tamanho + t > LIMITE_BYTES and parte:
            with open(os.path.join(pasta_deputado, f"parte_{num:03d}.json"), "w", encoding="utf-8") as f:
                json.dump({"dados": parte}, f, ensure_ascii=False)
            num += 1; parte = []; tamanho = 0
        parte.append(g); tamanho += t
    
    if parte:
        with open(os.path.join(pasta_deputado, f"parte_{num:03d}.json"), "w", encoding="utf-8") as f:
            json.dump({"dados": parte}, f, ensure_ascii=False)

def atualizar_cotas(ano):
    os.makedirs(DIR_COTAS, exist_ok=True); os.makedirs(DIR_CACHE, exist_ok=True)
    if ja_baixou_hoje(ano):
        print(f"  ⏭️  Cotas {ano} já baixadas hoje. Pulando..."); return

    url = URL_COTAS.format(ano=ano)
    print(f"  ⬇️  Baixando: {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=300); r.raise_for_status()
    except Exception as e:
        print(f"  ❌ Falha: {e}"); return

    por_deputado = defaultdict(list)
    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            for nome in z.namelist():
                if not nome.endswith(".json"): continue
                with z.open(nome) as f:
                    for g in json.load(f).get("dados", []):
                        if g.get("idDeputado"): por_deputado[str(g["idDeputado"])].append(g)
    except Exception as e:
        print(f"  ❌ Erro no ZIP: {e}"); return

    for id_dep, novos in por_deputado.items():
        pasta_dep = os.path.join(DIR_COTAS, str(id_dep))
        existentes = carregar_dados_existentes(pasta_dep)
        # Remove dados do mesmo ano para atualizar sem duplicar
        existentes = [d for d in existentes if str(d.get("ano")) != str(ano)]
        salvar_em_partes(id_dep, existentes + novos)

    marcar_baixado(ano)
    print(f"  ✅ Cotas {ano}: {len(por_deputado)} deputados.")

if __name__ == "__main__":
    print("\n=== COLETOR DE COTAS (CEAP) ===")
    try:
        ano_input = input("Digite o ano (ex: 2026) ou ENTER para o atual: ").strip()
        ano = int(ano_input) if ano_input else datetime.now().year
        atualizar_cotas(ano)
    except ValueError: print("  ❌ Ano inválido.")
import os
import json
import glob
from collections import defaultdict

# ==========================================
# CONFIGURAÇÃO DE CAMINHOS
# ==========================================
DIR_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PASTA_CAMARA = os.path.join(DIR_SCRIPT, '..', 'api', 'dados', 'camara_federal')

# Pastas antigas
PASTA_COTAS_ANTIGA = os.path.join(PASTA_CAMARA, 'cotas')
PASTA_VOTACOES_ANTIGA = os.path.join(PASTA_CAMARA, 'votacoes')
PASTA_PROPOSICOES_ANTIGA = os.path.join(PASTA_CAMARA, 'proposicoes')
PASTA_RESUMOS_ANTIGA = os.path.join(PASTA_CAMARA, 'votacoes_resumo')

# Pastas novas
PASTA_DEPUTADOS = os.path.join(PASTA_CAMARA, 'deputados')
PASTA_DEP_COTAS = os.path.join(PASTA_DEPUTADOS, 'cotas')
PASTA_DEP_VOTACOES = os.path.join(PASTA_DEPUTADOS, 'votacoes')
PASTA_DEP_PROPS = os.path.join(PASTA_DEPUTADOS, 'proposicoes')

PASTA_RESUMOS_NOVA = os.path.join(PASTA_CAMARA, 'votacoes_resumo')
PASTA_METADADOS_NOVA = os.path.join(PASTA_CAMARA, 'proposicoes_metadados')

# Cria as pastas novas
for p in [PASTA_DEP_COTAS, PASTA_DEP_VOTACOES, PASTA_DEP_PROPS, PASTA_RESUMOS_NOVA, PASTA_METADADOS_NOVA]:
    os.makedirs(p, exist_ok=True)

def migrar_cotas():
    print("\n=== 1. Migrando Cotas ===")
    arquivos = glob.glob(os.path.join(PASTA_COTAS_ANTIGA, 'politico_*.json'))
    print(f"Encontrados {len(arquivos)} arquivos de cotas.")

    for i, arquivo in enumerate(arquivos):
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            # Extrai o ID do nome do arquivo (politico_123.json)
            nome = os.path.basename(arquivo)
            id_dep = nome.replace('politico_', '').replace('.json', '')
            
            # Salva no novo local
            novo_caminho = os.path.join(PASTA_DEP_COTAS, f"cotas_{id_dep}.json")
            with open(novo_caminho, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            
            # Apaga o antigo
            os.remove(arquivo)
            
            if (i+1) % 100 == 0:
                print(f"  -> {i+1} arquivos migrados...")
        except Exception as e:
            print(f"Erro em {arquivo}: {e}")

    print("Cotas migradas.")

def migrar_votacoes():
    print("\n=== 2. Migrando Votações por Deputado ===")
    arquivos = glob.glob(os.path.join(PASTA_VOTACOES_ANTIGA, 'votacoes_*.json'))
    print(f"Encontrados {len(arquivos)} arquivos de votações.")

    for i, arquivo in enumerate(arquivos):
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            nome = os.path.basename(arquivo)
            id_dep = nome.replace('votacoes_', '').replace('.json', '')
            
            novo_caminho = os.path.join(PASTA_DEP_VOTACOES, f"votacoes_{id_dep}.json")
            with open(novo_caminho, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            
            os.remove(arquivo)
            
            if (i+1) % 100 == 0:
                print(f"  -> {i+1} arquivos migrados...")
        except Exception as e:
            print(f"Erro em {arquivo}: {e}")

    print("Votações migradas.")

def migrar_resumos():
    print("\n=== 3. Migrando Resumos de Votação (Agrupando por Ano) ===")
    arquivos = glob.glob(os.path.join(PASTA_RESUMOS_ANTIGA, 'resumo_votacao_*.json'))
    print(f"Encontrados {len(arquivos)} arquivos de resumos.")

    # Agrupa por ano
    resumos_por_ano = defaultdict(list)

    for i, arquivo in enumerate(arquivos):
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            ano = dados.get('data', '')[:4]  # Pega os 4 primeiros caracteres da data
            if not ano or not ano.isdigit():
                ano = '0000' # Fallback
            
            resumos_por_ano[ano].append(dados)
            os.remove(arquivo)
            
            if (i+1) % 10000 == 0:
                print(f"  -> {i+1} arquivos lidos...")
        except Exception as e:
            print(f"Erro em {arquivo}: {e}")

    # Salva os arquivos anuais
    print("Salvando arquivos anuais de resumos...")
    for ano, lista in resumos_por_ano.items():
        caminho = os.path.join(PASTA_RESUMOS_NOVA, f"resumos_votacoes_{ano}.json")
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump({"dados": lista}, f, ensure_ascii=False, indent=2)
        print(f"  -> {ano}: {len(lista)} resumos")

    print("Resumos migrados.")

def migrar_proposicoes():
    print("\n=== 4. Migrando Proposições ===")
    
    # 4.1 Metadados (Agrupando por Ano)
    print("Lendo metadados de proposições...")
    arquivos = glob.glob(os.path.join(PASTA_PROPOSICOES_ANTIGA, 'proposicao_*.json'))
    print(f"Encontrados {len(arquivos)} arquivos de metadados.")

    props_por_ano = defaultdict(list)

    for i, arquivo in enumerate(arquivos):
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            ano = str(dados.get('ano', '0000'))
            props_por_ano[ano].append(dados)
            os.remove(arquivo)
            
            if (i+1) % 50000 == 0:
                print(f"  -> {i+1} arquivos lidos...")
        except Exception as e:
            print(f"Erro em {arquivo}: {e}")

    print("Salvando arquivos anuais de metadados...")
    for ano, lista in props_por_ano.items():
        caminho = os.path.join(PASTA_METADADOS_NOVA, f"proposicoes_{ano}.json")
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump({"dados": lista}, f, ensure_ascii=False, indent=2)
        print(f"  -> {ano}: {len(lista)} proposições")

    # 4.2 Proposições por Deputado (Agrupando por Deputado)
    print("\nLendo proposições por deputado...")
    # Nota: A pasta proposicoes_por_deputado estava vazia no seu print, mas o código está pronto.
    pasta_antiga_props_dep = os.path.join(PASTA_CAMARA, 'proposicoes_por_deputado')
    if os.path.exists(pasta_antiga_props_dep):
        arquivos_dep = glob.glob(os.path.join(pasta_antiga_props_dep, 'proposicoes_*.json'))
        print(f"Encontrados {len(arquivos_dep)} arquivos de deputados.")
        
        for arquivo in arquivos_dep:
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                
                nome = os.path.basename(arquivo)
                id_dep = nome.replace('proposicoes_', '').replace('.json', '')
                
                novo_caminho = os.path.join(PASTA_DEP_PROPS, f"proposicoes_{id_dep}.json")
                with open(novo_caminho, 'w', encoding='utf-8') as f:
                    json.dump(dados, f, ensure_ascii=False, indent=2)
                
                os.remove(arquivo)
            except Exception as e:
                print(f"Erro em {arquivo}: {e}")
    else:
        print("Pasta 'proposicoes_por_deputado' não encontrada ou vazia. Pulando.")

    print("Proposições migradas.")

if __name__ == "__main__":
    print("=" * 60)
    print("MIGRADOR DE DADOS - VOTO ABERTO")
    print("Isso pode levar alguns minutos. Não feche o terminal.")
    print("=" * 60)

    migrar_cotas()
    migrar_votacoes()
    migrar_resumos()
    migrar_proposicoes()

    print("\n" + "=" * 60)
    print("MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("Verifique as novas pastas em api/dados/camara_federal/")
    print("=" * 60)
    input("\nPressione ENTER para fechar...")
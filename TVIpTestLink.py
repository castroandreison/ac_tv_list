import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import tkinter as tk
from tkinter import filedialog
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

THREADS = 80
TIMEOUT = 6


# --------------------------------
# Detectar resolução do canal
# --------------------------------
def detectar_resolucao(nome):

    nome = nome.upper()

    if "4K" in nome or "2160" in nome:
        return "4K"
    if "FHD" in nome or "1080" in nome:
        return "FHD"
    if "HD" in nome or "720" in nome:
        return "HD"

    return "SD"


# --------------------------------
# Extrair nome do canal
# --------------------------------
def extrair_nome(extinf):

    try:
        return extinf.split(",")[-1].strip()
    except:
        return extinf


# --------------------------------
# Extrair categoria
# --------------------------------
def extrair_categoria(extinf):

    match = re.search(r'group-title="([^"]+)"', extinf)

    if match:
        return match.group(1)

    return "OUTROS"


# --------------------------------
# Testar stream
# --------------------------------
def testar_stream(url):

    try:

        r = requests.head(url, timeout=TIMEOUT, allow_redirects=True)

        if r.status_code >= 400:
            return False

        # caso seja playlist HLS
        if ".m3u8" in url:

            r = requests.get(url, timeout=TIMEOUT)

            if "#EXTM3U" in r.text:
                return True

        r = requests.get(url, stream=True, timeout=TIMEOUT)

        if r.status_code == 200:

            for _ in r.iter_content(1024):
                return True

    except:
        pass

    return False


# --------------------------------
# Ler lista M3U / M3U8
# --------------------------------
def ler_lista(arquivo):

    canais = []

    with open(arquivo, "r", encoding="utf-8", errors="ignore") as f:
        linhas = f.readlines()

    for i in range(len(linhas)):

        if linhas[i].startswith("#EXTINF"):

            extinf = linhas[i].strip()
            url = linhas[i + 1].strip()

            nome = extrair_nome(extinf)
            categoria = extrair_categoria(extinf)
            resolucao = detectar_resolucao(nome)

            canais.append({
                "nome": nome,
                "categoria": categoria,
                "resolucao": resolucao,
                "extinf": extinf,
                "url": url
            })

    return canais


# --------------------------------
# Selecionar listas
# --------------------------------
def selecionar_listas():

    root = tk.Tk()
    root.withdraw()

    arquivos = filedialog.askopenfilenames(
        title="Selecionar listas IPTV",
        filetypes=[
            ("Listas IPTV", "*.m3u"),
            ("Listas IPTV UTF8", "*.m3u8"),
            ("Todos arquivos", "*.*")
        ]
    )

    return arquivos


# --------------------------------
# Programa principal
# --------------------------------
def main():

    arquivos = selecionar_listas()

    if not arquivos:
        print("Nenhuma lista selecionada")
        return

    todos_canais = []

    print("\nLendo listas...\n")

    for arquivo in arquivos:

        canais = ler_lista(arquivo)

        print(f"{arquivo} -> {len(canais)} canais")

        todos_canais.extend(canais)

    print("\nTotal de canais encontrados:", len(todos_canais))

    ativos = []
    nomes_vistos = set()

    print("\nTestando streams...\n")

    with ThreadPoolExecutor(max_workers=THREADS) as executor:

        futures = {
            executor.submit(testar_stream, canal["url"]): canal
            for canal in todos_canais
        }

        for future in as_completed(futures):

            canal = futures[future]

            try:

                if future.result():

                    nome = canal["nome"]

                    if nome not in nomes_vistos:

                        nomes_vistos.add(nome)

                        print("ATIVO:", nome)

                        ativos.append(canal)

                else:

                    print("INATIVO:", canal["nome"])

            except:

                print("ERRO:", canal["nome"])

    print("\nCanais ativos:", len(ativos))

    # ordenar por categoria e nome
    ativos.sort(key=lambda x: (x["categoria"], x["nome"]))

    print("\nGerando arquivo final...")

    with open("Listatestada.m3u", "w", encoding="utf-8") as f:

        f.write("#EXTM3U\n")

        for canal in ativos:

            f.write(canal["extinf"] + "\n")
            f.write(canal["url"] + "\n")

    print("\nArquivo gerado: Listatestada.m3u")


if __name__ == "__main__":
    main()
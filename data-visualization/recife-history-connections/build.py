#!/usr/bin/env python3
"""
build.py — gera os arquivos derivados que o site consome, a partir da base.

Fonte da verdade:  data/lista-geral-do-mapeamento.csv   (export do Google Sheets, 24 colunas)
Saídas geradas:    data/graph.json    (nós + arestas, ~32 KB — usado para desenhar)
                   data/content.json  (descrição/local/imagem por nó — carregado sob demanda)

Uso:
    python3 build.py            # valida e (re)gera os JSON
    python3 build.py --check    # valida e confere se os JSON commitados estão em sincronia
                                # (não escreve nada; sai com erro se divergirem) — usado na CI

Apenas biblioteca padrão. Rode sempre que a base mudar; commite os JSON junto com o CSV.
"""
import csv, json, os, sys, argparse

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(ROOT, "data", "lista-geral-do-mapeamento.csv")
GRAPH_OUT   = os.path.join(ROOT, "data", "graph.json")
CONTENT_OUT = os.path.join(ROOT, "data", "content.json")

# colunas das 15 interconexões
ICON_COLS = ["Interconexão %d" % i for i in range(1, 16)]


def read_rows():
    with open(SRC, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate(rows):
    """Retorna (errors, warnings). errors faz o build/CI falhar; warnings só avisam."""
    errors, warnings = [], []
    names = [r["Nome"].strip() for r in rows]
    nameset = set(names)

    # --- erros: quebram o grafo ---
    seen_id, seen_name = set(), set()
    for i, r in enumerate(rows, start=2):  # linha 2 = primeira de dados
        nome = r["Nome"].strip()
        rid  = (r.get("ID") or "").strip()
        if not nome:
            errors.append(f"linha {i}: Nome vazio")
        elif nome in seen_name:
            errors.append(f"linha {i}: Nome duplicado: {nome!r}")
        else:
            seen_name.add(nome)
        if rid:
            if rid in seen_id:
                errors.append(f"linha {i}: ID duplicado: {rid}")
            else:
                seen_id.add(rid)

    # --- avisos: qualidade / referências soltas ---
    dangling = {}
    for r in rows:
        for col in ICON_COLS:
            tgt = (r.get(col) or "").strip()
            if tgt and tgt not in nameset:
                dangling.setdefault(tgt, 0)
                dangling[tgt] += 1
    if dangling:
        warnings.append(
            "%d referências apontam para nomes que não são entradas (nós externos). "
            "Ex.: %s" % (len(dangling), ", ".join(sorted(dangling)[:6]))
        )
    no_desc = sum(1 for r in rows if not (r.get("Descrição") or "").strip())
    if no_desc:
        warnings.append("%d entradas sem Descrição" % no_desc)
    no_type = sum(1 for r in rows if not (r.get("Tipo") or "").strip())
    if no_type:
        warnings.append("%d entradas sem Tipo" % no_type)
    return errors, warnings


def build(rows):
    """Constrói os objetos graph e content (determinístico)."""
    names = [r["Nome"].strip() for r in rows]
    idx = {n: i for i, n in enumerate(names)}  # primeira ocorrência

    nodes = [{"n": r["Nome"].strip(), "t": (r.get("Tipo") or "").strip()} for r in rows]

    edges = set()
    for r in rows:
        a = idx.get(r["Nome"].strip())
        for col in ICON_COLS:
            b = idx.get((r.get(col) or "").strip())
            if a is not None and b is not None and a != b:
                edges.add((min(a, b), max(a, b)))
    graph = {"nodes": nodes, "edges": sorted(edges)}

    content = {}
    for r in rows:
        content[r["Nome"].strip()] = {
            "st":  (r.get("Sub-Tipo") or "").strip(),
            "l":   (r.get("Local") or "").strip(),
            "img": (r.get("Imagem") or "").strip(),
            "d":   (r.get("Descrição") or "").strip(),
        }
    return graph, content, len(edges)


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="não escreve; falha se os JSON commitados estiverem fora de sincronia")
    args = ap.parse_args()

    rows = read_rows()
    errors, warnings = validate(rows)
    graph, content, n_edges = build(rows)
    graph_txt, content_txt = dumps(graph), dumps(content)

    for w in warnings:
        print("  aviso:", w)
    for e in errors:
        print("  ERRO:", e)

    print(f"base: {len(rows)} entradas · {n_edges} conexões")

    if errors:
        print("FALHA: corrija os erros acima.")
        return 1

    if args.check:
        ok = True
        for path, txt in [(GRAPH_OUT, graph_txt), (CONTENT_OUT, content_txt)]:
            cur = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if cur != txt:
                print("FORA DE SINCRONIA:", os.path.relpath(path, ROOT), "— rode `python3 build.py` e commite.")
                ok = False
        if ok:
            print("OK: arquivos derivados em sincronia com a base.")
        return 0 if ok else 1

    with open(GRAPH_OUT, "w", encoding="utf-8") as f:
        f.write(graph_txt)
    with open(CONTENT_OUT, "w", encoding="utf-8") as f:
        f.write(content_txt)
    print("gerado:", os.path.relpath(GRAPH_OUT, ROOT), "+", os.path.relpath(CONTENT_OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Script de ingestão de documentos para sqlite-vec.
Compatível com n8n - pode ser chamado via CLI ou HTTP.

Uso CLI:
    python scripts/ingest_vectors.py --file data/meu_documento.md --source "meu_documento.md"
    python scripts/ingest_vectors.py --reindex  # Reindexa tudo

Uso como módulo:
    from scripts.ingest_vectors import ingest_file, reindex_all
    ingest_file("data/doc.md", "doc.md")
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from nr1_agent.vector_store import init_vector_table, insert_chunks, clear_vectors, count_vectors


_embeddings = None
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def get_embeddings():
    """Carrega o modelo somente quando uma ingestão for realmente solicitada."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _embeddings


def ingest_file(file_path: str, source: str | None = None) -> int:
    """Ingere um único arquivo no vector store."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    init_vector_table()

    # Escolher loader baseado na extensão
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        loader = PyPDFLoader(str(path))
    else:
        loader = TextLoader(str(path), encoding="utf-8")

    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    docs = text_splitter.split_documents(documents)

    source_name = source or path.name
    chunk_dicts = []
    for doc in docs:
        embedding = get_embeddings().embed_query(doc.page_content)
        chunk_dicts.append({
            "embedding": embedding,
            "content": doc.page_content,
            "source": source_name
        })

    inserted = insert_chunks(chunk_dicts)
    print(f"Ingeridos {inserted} chunks de {source_name}")
    return inserted


def reindex_all() -> int:
    """Reindexa todos os documentos conhecidos (limpa e reconstrói)."""
    clear_vectors()
    init_vector_table()

    default_file = "data/procedimentos_seguranca_ambientes_industriais.pdf"
    if not __import__("os").path.exists(default_file):
        print(f"Nenhum documento padrão encontrado em {default_file}. Reindexação concluída sem documentos base.")
        return 0
    return ingest_file(default_file)


def main():
    parser = argparse.ArgumentParser(description="Ingestão de vetores para sqlite-vec")
    parser.add_argument("--file", help="Caminho do arquivo para ingerir")
    parser.add_argument("--source", help="Nome da fonte (opcional, default: nome do arquivo)")
    parser.add_argument("--reindex", action="store_true", help="Reindexa tudo (limpa + reingere padrão)")
    parser.add_argument("--stats", action="store_true", help="Mostra estatísticas do vector store")

    args = parser.parse_args()

    if args.stats:
        print(f"Total de vetores: {count_vectors()}")
        return

    if args.reindex:
        inserted = reindex_all()
        print(f"Reindexação completa: {inserted} chunks")
        return

    if args.file:
        inserted = ingest_file(args.file, args.source)
        print(f"Sucesso: {inserted} chunks inseridos")
        return

    parser.print_help()


if __name__ == "__main__":
    main()

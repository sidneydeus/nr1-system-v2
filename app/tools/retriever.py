from langchain_community.document_loaders import TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.vector_store import init_vector_table, insert_chunks, search_similar, count_vectors, clear_vectors
from typing import Any


def create_retriever():
    """
    Cria um retriever para consultar os procedimentos de segurança usando SQLite + sqlite-vec.

    Esta função inicializa um retriever baseado em vetores para os documentos
    de procedimentos de segurança da empresa. Ele carrega o documento, divide-o
    em pedaços (chunks), cria embeddings e armazena tudo no SQLite com sqlite-vec.

    Returns:
        Um objeto retriever configurado pronto para uso.
    """
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    init_vector_table()

    if count_vectors() == 0:
        loader = TextLoader("data/procedimentos_seguranca_industria.md", encoding="utf-8")
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = text_splitter.split_documents(documents)

        chunk_dicts = []
        for doc in docs:
            embedding = embeddings.embed_query(doc.page_content)
            chunk_dicts.append({
                "embedding": embedding,
                "content": doc.page_content,
                "source": "procedimentos_seguranca_industria.md"
            })

        insert_chunks(chunk_dicts)
        print(f"Indexed {len(chunk_dicts)} chunks into sqlite-vec")

    class SqliteVecRetriever:
        def __init__(self, embeddings_model):
            self.embeddings = embeddings_model

        def invoke(self, query: str) -> list:
            from langchain_core.documents import Document
            query_embedding = self.embeddings.embed_query(query)
            results = search_similar(query_embedding, k=4)
            return [
                Document(page_content=r["content"], metadata={"source": r["source"], "distance": r["distance"]})
                for r in results
            ]

    return SqliteVecRetriever(embeddings)


def reindex_documents():
    """Force reindexing of all documents."""
    clear_vectors()
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    loader = TextLoader("data/procedimentos_seguranca_industria.md", encoding="utf-8")
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(documents)

    chunk_dicts = []
    for doc in docs:
        embedding = embeddings.embed_query(doc.page_content)
        chunk_dicts.append({
            "embedding": embedding,
            "content": doc.page_content,
            "source": "procedimentos_seguranca_industria.md"
        })

    inserted = insert_chunks(chunk_dicts)
    print(f"Reindexed {inserted} chunks into sqlite-vec")
    return inserted


if __name__ == '__main__':
    retriever = create_retriever()
    query = "O que fazer em caso de trabalho em altura sem permissão?"
    results = retriever.invoke(query)

    print(f"Query: {query}\n")
    print("Resultados encontrados:\n")
    for i, doc in enumerate(results):
        print(f"--- Resultado {i+1} (distance: {doc.metadata.get('distance', 'N/A'):.4f}) ---\n")
        print(doc.page_content)
        print("\n")
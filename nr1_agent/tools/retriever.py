from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from nr1_agent.vector_store import init_vector_table, insert_chunks, search_similar, count_vectors, clear_vectors
from typing import Any, List
from langchain_core.documents import Document


class SqliteVecRetriever:
    def __init__(self, embeddings_model=None):
        self.embeddings = embeddings_model

    def _ensure_ready(self) -> bool:
        if self.embeddings is not None:
            return True
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            if count_vectors() == 0:
                default_file = Path("data/procedimentos_seguranca_ambientes_industriais.pdf")
                if default_file.exists():
                    documents = PyPDFLoader(str(default_file)).load()
                    docs = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(documents)
                    insert_chunks([
                        {"embedding": self.embeddings.embed_query(doc.page_content),
                         "content": doc.page_content, "source": default_file.name}
                        for doc in docs
                    ])
            return True
        except Exception:
            # RAG é complementar; a aplicação continua funcional sem o modelo local.
            self.embeddings = None
            return False

    def invoke(self, query: str) -> List[Document]:
        if not self._ensure_ready():
            return []
        query_embedding = self.embeddings.embed_query(query)
        results = search_similar(query_embedding, k=4)
        return [
            Document(page_content=r["content"], metadata={"source": r["source"], "distance": r["distance"]})
            for r in results
        ]


def create_retriever():
    """
    Cria um retriever para consultar os procedimentos de segurança usando SQLite + sqlite-vec.

    Esta função inicializa um retriever baseado em vetores para os documentos
    de procedimentos de segurança da empresa. Ele carrega o documento, divide-o
    em pedaços (chunks), cria embeddings e armazena tudo no SQLite com sqlite-vec.

    Returns:
        Um objeto retriever configurado pronto para uso.
    """
    init_vector_table()
    return SqliteVecRetriever()


def reindex_documents():
    """Force reindexing of all documents."""
    clear_vectors()
    init_vector_table()

    default_file = "data/procedimentos_seguranca_ambientes_industriais.pdf"
    if not __import__("os").path.exists(default_file):
        print(f"Nenhum documento padrão encontrado em {default_file}. Reindexação concluída sem documentos base.")
        return 0

    documents = PyPDFLoader(default_file).load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(documents)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    chunk_dicts = []
    for doc in docs:
        embedding = embeddings.embed_query(doc.page_content)
        chunk_dicts.append({
            "embedding": embedding,
            "content": doc.page_content,
            "source": "procedimentos_seguranca_ambientes_industriais.pdf"
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

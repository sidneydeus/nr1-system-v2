import os
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

def create_retriever():
    """
    Cria um retriever para consultar os procedimentos de segurança usando ChromaDB.

    Esta função inicializa um retriever baseado em vetores persistentes para os documentos
    de procedimentos de segurança da empresa. Ele carrega o documento, divide-o
    em pedaços (chunks), cria embeddings e armazena tudo no ChromaDB.

    Returns:
        Um objeto retriever configurado pronto para uso.
    """
    # Configuração do ChromaDB
    chroma_host = os.getenv("CHROMA_HOST", "localhost")
    chroma_port = os.getenv("CHROMA_PORT", "8000")
    collection_name = "procedimentos_seguranca"

    # Carrega o documento de procedimentos
    loader = TextLoader("data/procedimentos_seguranca_industria.md", encoding="utf-8")
    documents = loader.load()

    # Divide o documento em chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(documents)

    # Cria os embeddings usando um modelo open-source
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Cria/Conecta ao ChromaDB persistente
    db = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=collection_name,
        client_settings={
            "chroma_api_impl": "chromadb.api.fastapi.FastAPI",
            "chroma_server_host": chroma_host,
            "chroma_server_http_port": chroma_port,
        } if chroma_host != "localhost" else None,
        persist_directory="./chroma_data" if chroma_host == "localhost" else None,
    )

    # Converte o banco de dados vetorial em um retriever
    retriever = db.as_retriever(search_kwargs={"k": 3})

    return retriever

if __name__ == '__main__':
    # Bloco para teste rápido e demonstração
    retriever = create_retriever()
    query = "O que fazer em caso de trabalho em altura sem permissão?"
    results = retriever.invoke(query)
    
    print(f"Query: {query}\n")
    print("Resultados encontrados:\n")
    for i, doc in enumerate(results):
        print(f"--- Resultado {i+1} ---\n")
        print(doc.page_content)
        print("\n")

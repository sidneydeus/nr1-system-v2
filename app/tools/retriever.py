from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

def create_retriever():
    """
    Cria um retriever para consultar os procedimentos de segurança.

    Esta função inicializa um retriever baseado em vetores para os documentos
    de procedimentos de segurança da empresa. Ele carrega o documento, divide-o
    em pedaços (chunks), cria embeddings e armazena tudo em um vector store
    em memória (FAISS).

    TODO: Evoluir para um banco de dados vetorial persistente.
    Para produção, o ideal é substituir o FAISS em memória por uma solução
    persistente como ChromaDB, PGVector ou Pinecone. Isso evitaria a necessidade
    de recriar o índice a cada inicialização da aplicação, além de permitir

    a atualização e o gerenciamento mais robusto dos documentos.

    Returns:
        Um objeto retriever configurado pronto para uso.
    """
    # Carrega o documento de procedimentos
    loader = TextLoader("data/procedimentos_seguranca_industria.md", encoding="utf-8")
    documents = loader.load()

    # Divide o documento em chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(documents)

    # Cria os embeddings usando um modelo open-source
    # (sentence-transformers/all-MiniLM-L6-v2 é uma boa escolha inicial)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Cria o vector store FAISS em memória com os documentos e embeddings
    # FAISS é uma biblioteca para busca de similaridade eficiente, ideal para prototipagem.
    db = FAISS.from_documents(docs, embeddings)

    # Converte o banco de dados vetorial em um retriever
    retriever = db.as_retriever()

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

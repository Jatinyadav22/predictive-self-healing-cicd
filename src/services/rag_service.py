from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


RAG_PERSIST_DIRECTORY = Path("data/rag_chroma")
RAG_COLLECTION_NAME = "repository_knowledge"

RAG_EMBEDDING_MODEL = "nomic-embed-text:latest"

RAG_IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "chroma_db",
    "rag_chroma",
}

RAG_SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".yaml",
    ".yml",
    ".json",
    ".md",
    ".txt",
    ".sh",
}


def load_repository_documents(repository_path: str) -> list[Document]:
    """Load supported repository files as LangChain documents."""

    root = Path(repository_path).resolve()

    if not root.exists():
        raise FileNotFoundError(f"Repository not found: {root}")

    documents: list[Document] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if any(
            part in RAG_IGNORED_DIRECTORIES
            for part in path.parts
        ):
            continue

        if path.suffix.lower() not in RAG_SUPPORTED_EXTENSIONS:
            continue

        try:
            relative_path = path.relative_to(root)
            content = path.read_text(encoding="utf-8")

            if not content.strip():
                continue

            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": str(relative_path),
                        "file_type": path.suffix.lower(),
                    },
                )
            )

        except (OSError, UnicodeDecodeError):
            continue

    documents.sort(
        key=lambda document: document.metadata["source"]
    )

    return documents


def split_repository_documents(
    documents: list[Document],
) -> list[Document]:
    """Split repository documents into retrieval-friendly chunks."""

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
    )

    return splitter.split_documents(documents)


def prepare_repository_chunks(
    repository_path: str,
) -> list[Document]:
    """Load and chunk repository documents for RAG indexing."""

    documents = load_repository_documents(repository_path)

    return split_repository_documents(documents)


def get_embedding_function() -> OllamaEmbeddings:
    """Create the local Ollama embedding function for RAG."""

    return OllamaEmbeddings(
        model=RAG_EMBEDDING_MODEL,
    )


def get_vector_store() -> Chroma:
    """Create or open the persistent ChromaDB repository."""

    RAG_PERSIST_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    return Chroma(
        collection_name=RAG_COLLECTION_NAME,
        embedding_function=get_embedding_function(),
        persist_directory=str(RAG_PERSIST_DIRECTORY),
    )


def index_repository(repository_path: str) -> dict[str, int]:
    """Index repository chunks into the persistent ChromaDB store."""

    chunks = prepare_repository_chunks(repository_path)
    vector_store = get_vector_store()

    if not chunks:
        return {
            "documents": 0,
            "chunks": 0,
            "indexed": 0,
        }

    ids = [
        f"{chunk.metadata['source']}::chunk-{index}"
        for index, chunk in enumerate(chunks)
    ]

    vector_store.add_documents(
        documents=chunks,
        ids=ids,
    )

    return {
        "documents": len({
            chunk.metadata["source"]
            for chunk in chunks
        }),
        "chunks": len(chunks),
        "indexed": len(chunks),
    }


def retrieve_repository_context(
    query: str,
    max_results: int = 5,
) -> list[dict[str, object]]:
    """Retrieve relevant repository chunks from ChromaDB."""

    if not query.strip():
        return []

    vector_store = get_vector_store()

    results = vector_store.similarity_search_with_score(
        query,
        k=max_results,
    )

    retrieved: list[dict[str, object]] = []

    for document, score in results:
        retrieved.append(
            {
                "source": document.metadata.get("source"),
                "file_type": document.metadata.get("file_type"),
                "score": round(float(score), 4),
                "content": document.page_content,
            }
        )

    return retrieved


def generate_rag_answer(
    query: str,
    max_results: int = 5,
) -> dict[str, object]:
    """Generate an answer grounded in retrieved repository context."""

    if not query.strip():
        return {
            "question": query,
            "answer": "",
            "sources": [],
        }

    retrieved = retrieve_repository_context(
        query,
        max_results=max_results,
    )

    if not retrieved:
        return {
            "question": query,
            "answer": "No relevant repository context was found.",
            "sources": [],
        }

    context_parts = []

    for index, result in enumerate(retrieved, start=1):
        context_parts.append(
            f"[Source {index}]\n"
            f"File: {result['source']}\n"
            f"Content:\n{result['content']}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
You are the RAG assistant for a software repository.

Answer the user's question using ONLY the retrieved repository
context provided below.

Rules:
- Do not invent files, functions, behavior, or configuration.
- If the retrieved context is insufficient, say so clearly.
- Mention relevant file names when useful.
- Keep the answer concise and technically accurate.

User question:
{query}

Retrieved repository context:
{context}

Answer:
""".strip()

    from src.services.llm_service import generate_explanation

    answer = generate_explanation(
        query,
        context,
    )

    return {
        "question": query,
        "answer": answer,
        "sources": [
            {
                "source": result["source"],
                "score": result["score"],
                "content": result["content"],
            }
            for result in retrieved
        ],
    }

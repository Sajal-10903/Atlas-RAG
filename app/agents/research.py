from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.contracts import Citation
from app.services.llm import complete
from app.services.retrieval import RetrievedChunk, retrieve


def citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    return [Citation(ref=f"S{i}", document_id=item.chunk.document_id, filename=item.filename, chunk_id=item.chunk.id, page=item.chunk.page, excerpt=item.chunk.content[:360], score=round(item.score, 5)) for i, item in enumerate(chunks, 1)]


def context(chunks: list[RetrievedChunk]) -> str:
    return "\n\n".join(f"[S{i}] file={item.filename}; page={item.chunk.page or 'n/a'}\n{item.chunk.content}" for i, item in enumerate(chunks, 1))


async def answer(session: AsyncSession, question: str, document_ids: list | None, top_k: int):
    chunks, trace = await retrieve(session, question, document_ids, top_k)
    refs = citations(chunks)
    if not chunks:
        return "I could not find relevant material in the indexed documents.", refs, trace
    prompt = f"Question: {question}\n\nRetrieved evidence:\n{context(chunks)}"
    system = """You answer only from the supplied evidence. Cite every factual claim with [S#].
If evidence is insufficient, say so plainly. Do not invent citations, sources, or facts.
Keep the response clear and concise."""
    return await complete(system, prompt), refs, trace


async def create_report(session: AsyncSession, topic: str, document_ids: list | None, report_format: str):
    # This explicit workflow is observable and deterministic at its tool boundary; it can be
    # expanded into a graph executor/Temporal activity without changing the API contract.
    steps = ["Planned research questions", "Retrieved hybrid evidence", "Synthesized cited report"]
    questions = [topic, f"key findings and evidence for {topic}", f"risks, limitations, and recommendations for {topic}"]
    all_chunks: dict = {}
    for question in questions:
        found, _ = await retrieve(session, question, document_ids, 4)
        all_chunks.update({item.chunk.id: item for item in found})
    chunks = list(all_chunks.values())[:10]
    refs = citations(chunks)
    if not chunks:
        return "# Report\n\nNo relevant evidence was found in the selected corpus.", refs, steps
    system = f"""You are a research agent producing a {report_format} report strictly from supplied evidence.
Use Markdown headings: Executive summary, Findings, Risks and limitations, Recommendations.
Cite factual statements using [S#]. Explicitly identify evidence gaps. Never add unsupported claims."""
    report = await complete(system, f"Topic: {topic}\n\nEvidence:\n{context(chunks)}", temperature=0.15)
    return report, refs, steps


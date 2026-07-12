from app.models.ask_response import AskResponse, SourceGroup
from app.services.context_builder import ContextBuilder
from app.services.openai_service import OpenAIService


class RagService:
    """Retrieve relevant documents and answer questions with GPT."""

    NO_CONTEXT_ANSWER = (
        "I could not find relevant documents in the local indexes for this question."
    )

    def __init__(
        self,
        context_builder: ContextBuilder,
        openai_service: OpenAIService,
    ) -> None:
        self._context_builder = context_builder
        self._openai_service = openai_service

    def ask(self, question: str) -> AskResponse:
        result = self._context_builder.build(question)
        if not result.chunks:
            return AskResponse(
                answer=self.NO_CONTEXT_ANSWER,
                confidence=0,
                source_groups=[],
                sources=[],
            )

        context = ContextBuilder.format_context(result.chunks)
        answer = self._openai_service.answer_with_context(question, context)
        source_groups = [
            SourceGroup(
                primary_path=group.primary.path,
                primary_filename=group.primary.filename,
                alternate_paths=list(group.alternate_paths),
            )
            for group in result.source_groups
            if any(chunk.path == group.primary.path for chunk in result.chunks)
        ]
        sources = [chunk.path for chunk in result.chunks]

        return AskResponse(
            answer=answer,
            confidence=result.confidence,
            source_groups=source_groups,
            sources=sources,
        )

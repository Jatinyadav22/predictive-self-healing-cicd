import json
import re
from pathlib import Path
from typing import Optional
from src.config.settings import settings
from src.models.schemas import FailureClassification, RCAAnalysis, EvidenceCitation
from src.services.ollama_client import ollama_client
from src.services.audit_service import audit_logger
from src.services.rag_service import retrieve_repository_context

class ExplainableRCAEngine:
    """Diagnoses failures, cites evidence from repository context, and computes confidence score."""

    def diagnose(self, classification: FailureClassification, run_id: Optional[str] = None) -> RCAAnalysis:
        # 1. Retrieve RAG context around the failing file and error
        query = f"{classification.failing_file or ''} {classification.failing_symbol or ''} {classification.error_message}"
        retrieved_docs = []
        try:
            retrieved_docs = retrieve_repository_context(query=query, max_results=4)
        except Exception:
            pass

        evidence_citations: list[EvidenceCitation] = []
        context_snippets = []

        for i, doc in enumerate(retrieved_docs, 1):
            src = str(doc.get("source", "unknown"))
            content = str(doc.get("content", ""))
            score = float(doc.get("score", 0.0))
            evidence_citations.append(EvidenceCitation(
                file_path=src,
                snippet=content[:300],
                similarity_score=score
            ))
            context_snippets.append(f"[Snippet {i} - {src}]\n{content[:400]}\n")

        # Fallback: check file directly in demo_repo if available
        if classification.failing_file:
            local_target = Path(settings.DEMO_REPO_PATH) / classification.failing_file
            if local_target.exists():
                try:
                    file_text = local_target.read_text(encoding="utf-8")
                    context_snippets.append(f"[Source File: {classification.failing_file}]\n{file_text[:1200]}")
                    evidence_citations.append(EvidenceCitation(
                        file_path=classification.failing_file,
                        snippet=file_text[:350],
                        similarity_score=1.0
                    ))
                except Exception:
                    pass

        context_text = "\n".join(context_snippets) if context_snippets else "No source context available."

        system_prompt = (
            "You are a Principal DevOps and Reliability Engineer. "
            "Analyze the following CI/CD test/build failure using the provided repository context. "
            "Output your analysis in VALID JSON format with exactly these four keys:\n"
            "{\n"
            '  "root_cause_summary": "Concise 1-2 sentence explanation of why the failure occurred",\n'
            '  "confidence_score": 0.95,\n'
            '  "fix_strategy": "Concrete step-by-step description of the exact change needed to fix it",\n'
            '  "offending_code": "The exact snippet causing the bug"\n'
            "}\n"
            "Do not include markdown or extra text outside the JSON object."
        )

        user_prompt = f"""FAILURE DETAILS:
Type: {classification.failure_type.value}
Error: {classification.error_message}
Failing File: {classification.failing_file} (Line: {classification.failing_line})
Failing Test: {classification.failing_test_name}

STACK TRACE SNIPPET:
{classification.stack_trace[:800]}

RETRIEVED CODE & REPOSITORY CONTEXT:
{context_text}

JSON DIAGNOSIS:"""

        raw_response = ollama_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            num_predict=220
        )

        # Parse JSON from response
        try:
            clean_json = raw_response.strip()
            if "```" in clean_json:
                clean_json = re.sub(r"```(?:json)?\s*\n?", "", clean_json)
                clean_json = re.sub(r"\n?```$", "", clean_json).strip()

            start_idx = clean_json.find("{")
            end_idx = clean_json.rfind("}")
            if start_idx != -1 and end_idx != -1:
                clean_json = clean_json[start_idx:end_idx + 1]

            data = json.loads(clean_json)
            rca = RCAAnalysis(
                root_cause_summary=data.get("root_cause_summary", f"Failure in {classification.failing_file}: {classification.error_message}"),
                confidence_score=float(data.get("confidence_score", 0.90)),
                fix_strategy=data.get("fix_strategy", "Inspect offending line and adjust logic to satisfy test conditions."),
                offending_code=data.get("offending_code"),
                evidence_citations=evidence_citations
            )
        except Exception:
            rca = RCAAnalysis(
                root_cause_summary=f"Root cause analysis: {classification.error_message} in {classification.failing_file or 'test execution'}.",
                confidence_score=0.80,
                fix_strategy=f"Correct the {classification.failure_type.value.lower().replace('_', ' ')} in {classification.failing_file or 'target code'}.",
                evidence_citations=evidence_citations
            )

        if run_id:
            audit_logger.record_event(
                event_type="RCA_ANALYSIS",
                summary=f"Run {run_id} RCA: {rca.root_cause_summary[:80]} (Confidence: {int(rca.confidence_score * 100)}%)",
                run_id=run_id,
                actor="RCA_ENGINE",
                payload=rca.model_dump(mode="json")
            )

        return rca

rca_engine = ExplainableRCAEngine()

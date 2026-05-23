"""
LLM-as-judge for RAG answer evaluation.
Scores generated answers on faithfulness, completeness, and citation accuracy.
Model: same Qwen3.6-35B used for generation.
"""
import os
import json
import re
from typing import List, Optional

_JUDGE_SYSTEM = (
    "You are an expert evaluator for Retrieval-Augmented Generation systems. "
    "You assess answer quality against the source context provided. "
    "Be strict and precise."
)

_JUDGE_TEMPLATE = """/no_thinking
Evaluate the following RAG system answer.

QUESTION:
{question}

RETRIEVED CONTEXT (what the system had access to):
{context}

GENERATED ANSWER:
{answer}

Score the answer on three criteria. Each score is an integer 1-5.

FAITHFULNESS — Are all claims in the answer supported by the retrieved context?
  5 = Every claim is directly supported
  4 = Core claims grounded, minor unsupported details
  3 = Some significant unsupported claims
  2 = Many unsupported claims
  1 = Answer contradicts or ignores context

COMPLETENESS — Does the answer fully address the question using available context?
  5 = Comprehensive, covers all relevant aspects present in context
  4 = Addresses main question, minor gaps
  3 = Partial answer, notable gaps
  2 = Minimal coverage
  1 = Does not address the question

CITATION_ACCURACY — Are company/section attributions in the answer correct?
  5 = All citations correct or no citations needed
  4 = Minor citation errors
  3 = Some incorrect citations
  2 = Frequent citation errors
  1 = No citations or entirely wrong

Respond with ONLY valid JSON (no markdown, no explanation outside JSON):
{{"faithfulness": <1-5>, "completeness": <1-5>, "citation_accuracy": <1-5>, "reasoning": "<one sentence>"}}
"""


class JudgeScores:
    def __init__(
        self,
        faithfulness: int,
        completeness: int,
        citation_accuracy: int,
        reasoning: str,
    ):
        self.faithfulness = faithfulness
        self.completeness = completeness
        self.citation_accuracy = citation_accuracy
        self.reasoning = reasoning

    @property
    def mean(self) -> float:
        return round((self.faithfulness + self.completeness + self.citation_accuracy) / 3, 3)

    def to_dict(self) -> dict:
        return {
            "faithfulness": self.faithfulness,
            "completeness": self.completeness,
            "citation_accuracy": self.citation_accuracy,
            "mean": self.mean,
            "reasoning": self.reasoning,
        }


def _extract_json(text: str) -> dict:
    # Strip any accidental markdown fences
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def judge_answer(
    query: str,
    chunks: list,
    answer: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> JudgeScores:
    from openai import OpenAI
    # Import here to avoid circular path issues at module level
    from src.generation.generate import format_context

    client = OpenAI(
        base_url=base_url or os.getenv("GEN_BASE_URL", "http://ai.scheidy.com:8082/v1"),
        api_key="not-needed",
    )
    model = model or os.getenv("GEN_MODEL", "Qwen3.6-35B-A3B-MXFP4_MOE.gguf")
    context = format_context(chunks)
    user_msg = _JUDGE_TEMPLATE.format(
        question=query,
        context=context,
        answer=answer,
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _JUDGE_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=200,
        temperature=0,
    )
    raw = resp.choices[0].message.content.strip()

    try:
        data = _extract_json(raw)
        return JudgeScores(
            faithfulness=int(data["faithfulness"]),
            completeness=int(data["completeness"]),
            citation_accuracy=int(data["citation_accuracy"]),
            reasoning=str(data.get("reasoning", "")),
        )
    except Exception as e:
        # Fallback: return neutral scores with error note
        return JudgeScores(
            faithfulness=3,
            completeness=3,
            citation_accuracy=3,
            reasoning=f"[parse error: {e}] raw={raw[:120]}",
        )

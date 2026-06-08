from app.adapters.openai_adapter import OpenAIAdapter


CONSENSUS_SYSTEM_PROMPT = """당신은 여러 AI의 토론 결과를 분석하여 최종 합의를 도출하는 AI입니다.
각 AI의 답변에서 공통점을 찾고, 가장 신뢰할 수 있는 최종 결론을 작성하세요.

다음 형식으로 응답하세요:

[최종 합의 결론]
(명확하고 실용적인 최종 답변)

[주요 합의 포인트]
- 포인트 1
- 포인트 2
- 포인트 3

[신뢰도]
(0-100 숫자만, AI들의 합의 수준을 나타냄)"""


class ConsensusEngine:
    def __init__(self):
        self._adapter = OpenAIAdapter()

    async def generate(
        self,
        topic: str,
        final_round_responses: list[dict],
    ) -> dict:
        responses_text = "\n\n".join(
            f"[{r['display_name']}의 최종 답변]\n{r['content']}"
            for r in final_round_responses
        )

        user_message = f"""토론 주제: {topic}

각 AI의 최종 라운드 답변:
{responses_text}

위 답변들을 종합하여 최종 합의를 도출하세요."""

        response = await self._adapter.generate(
            messages=[
                {"role": "system", "content": CONSENSUS_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=1200,
        )

        return self._parse_consensus(response.content, final_round_responses)

    def _parse_consensus(self, content: str, responses: list[dict]) -> dict:
        confidence = 75.0
        import re
        match = re.search(r'\[신뢰도\]\s*(\d+)', content)
        if match:
            confidence = min(100.0, max(0.0, float(match.group(1))))

        vote_distribution = {
            r["provider"]: round(1.0 / len(responses), 2) if responses else 0
            for r in responses
        }

        return {
            "final_answer": content,
            "confidence_score": confidence / 100.0,
            "vote_distribution": vote_distribution,
        }


consensus_engine = ConsensusEngine()

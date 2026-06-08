import json
import re
from app.adapters.openai_adapter import OpenAIAdapter
from app.core.config import settings


JUDGE_SYSTEM_PROMPT = """당신은 AI 토론의 공정한 심사위원입니다.
여러 AI의 토론 답변을 평가하여 각 AI에 대해 다음 5가지 항목을 0-10점으로 채점하고 승자를 선정하세요.

평가 항목:
1. accuracy (정확성): 사실에 기반한 정확한 정보 제공
2. logic (논리성): 논리적 일관성과 추론의 타당성
3. evidence (근거 수준): 구체적 근거와 출처 제시
4. creativity (창의성): 독창적이고 혁신적인 관점
5. feasibility (실현가능성): 현실적이고 실행 가능한 제안

반드시 다음 JSON 형식으로만 응답하세요:
{
  "scores": {
    "provider_name": {
      "accuracy": 8.5,
      "logic": 9.0,
      "evidence": 7.5,
      "creativity": 8.0,
      "feasibility": 8.5,
      "total": 41.5
    }
  },
  "winner": "provider_name",
  "summary": "전체 토론에 대한 평가 요약 (2-3문장)"
}"""


class JudgeEngine:
    def __init__(self):
        self._adapter = OpenAIAdapter()

    async def evaluate(
        self,
        topic: str,
        debate_rounds: list[dict],
    ) -> dict:
        debate_text = self._format_debate(debate_rounds)

        user_message = f"""토론 주제: {topic}

토론 내용:
{debate_text}

위 토론을 평가하고 지정된 JSON 형식으로 결과를 반환하세요."""

        response = await self._adapter.generate(
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=1500,
        )

        return self._parse_judge_response(response.content, debate_rounds)

    def _format_debate(self, debate_rounds: list[dict]) -> str:
        lines = []
        rounds = sorted(debate_rounds, key=lambda x: (x["round_no"], x["provider"]))
        current_round = 0

        for entry in rounds:
            if entry["round_no"] != current_round:
                current_round = entry["round_no"]
                lines.append(f"\n=== Round {current_round} ===")
            lines.append(f"\n[{entry['display_name']}]\n{entry['content']}")

        return "\n".join(lines)

    def _parse_judge_response(self, content: str, debate_rounds: list[dict]) -> dict:
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback: equal scores
        providers = list({r["provider"] for r in debate_rounds})
        scores = {}
        for p in providers:
            display = next((r["display_name"] for r in debate_rounds if r["provider"] == p), p)
            scores[p] = {
                "display_name": display,
                "accuracy": 7.0,
                "logic": 7.0,
                "evidence": 7.0,
                "creativity": 7.0,
                "feasibility": 7.0,
                "total": 35.0,
            }

        return {
            "scores": scores,
            "winner": providers[0] if providers else None,
            "summary": "자동 평가 중 오류가 발생하여 기본 점수가 적용되었습니다.",
        }


judge_engine = JudgeEngine()

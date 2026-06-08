import asyncio
from app.adapters.registry import get_adapters_by_providers
from app.adapters.base import AIResponse
from app.core.config import settings


ROUND_PROMPTS = {
    1: "당신은 AI 토론 참가자입니다. 다음 주제에 대해 당신의 입장을 명확히 밝히고, 근거를 들어 답변하세요. 다른 AI의 답변을 이후에 반박할 수 있도록 논리적으로 작성하세요.",
    2: "이전 라운드에서 다른 AI들의 답변을 검토했습니다. 각 답변의 강점과 약점을 분석하고, 당신의 입장을 보완하거나 수정하세요.",
    3: "이제 마지막 라운드입니다. 모든 토론을 종합하여 최종 입장을 명확히 하고, 가장 설득력 있는 결론을 도출하세요.",
}


class DebateEngine:
    async def run_initial_round(
        self,
        topic: str,
        providers: list[str],
    ) -> list[AIResponse]:
        adapters = get_adapters_by_providers(providers)
        system_prompt = ROUND_PROMPTS[1]

        tasks = [
            adapter.generate(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": topic},
                ],
                max_tokens=settings.MAX_TOKENS_PER_RESPONSE,
            )
            for adapter in adapters
        ]
        return await asyncio.gather(*tasks)

    async def run_debate_round(
        self,
        topic: str,
        round_no: int,
        providers: list[str],
        previous_responses: dict[str, str],
    ) -> list[AIResponse]:
        adapters = get_adapters_by_providers(providers)
        system_prompt = ROUND_PROMPTS.get(round_no, ROUND_PROMPTS[3])

        other_responses_text = "\n\n".join(
            f"[{provider.upper()} 의 이전 답변]\n{content}"
            for provider, content in previous_responses.items()
        )

        user_message = (
            f"토론 주제: {topic}\n\n"
            f"다른 AI들의 이전 라운드 답변:\n{other_responses_text}\n\n"
            f"위 답변들을 참고하여 Round {round_no} 토론을 진행하세요."
        )

        tasks = [
            adapter.generate(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=settings.MAX_TOKENS_PER_RESPONSE,
            )
            for adapter in adapters
        ]
        return await asyncio.gather(*tasks)

    async def run_full_debate(
        self,
        topic: str,
        providers: list[str],
        num_rounds: int = 3,
    ) -> list[dict]:
        all_rounds: list[dict] = []
        previous_responses: dict[str, str] = {}

        for round_no in range(1, num_rounds + 1):
            if round_no == 1:
                responses = await self.run_initial_round(topic, providers)
            else:
                responses = await self.run_debate_round(topic, round_no, providers, previous_responses)

            round_data = []
            previous_responses = {}
            for resp in responses:
                round_data.append({
                    "provider": resp.provider,
                    "display_name": resp.display_name,
                    "round_no": round_no,
                    "content": resp.content,
                    "tokens_used": resp.tokens_used,
                    "latency_ms": resp.latency_ms,
                })
                previous_responses[resp.provider] = resp.content

            all_rounds.extend(round_data)

        return all_rounds


debate_engine = DebateEngine()

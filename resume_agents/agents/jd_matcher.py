"""
JD matcher agent — dual-layer: light semantic match + deep rewrite.

Enhancements:
- Understand application strategies (same facts, different framing)
- Mine materials for experiences omitted from the current resume
"""

from __future__ import annotations

from typing import Any, Optional

from langchain_core.output_parsers import JsonOutputParser

from resume_agents.memory.models import (
    ApplicationStrategy,
    ForgottenExperienceHint,
    JDMatchResult,
    JDRequirements,
    MaterialRecord,
    Resume,
    ResumeSection,
)
from resume_agents.domain.profiles import get_domain


def _get_agents():
    from llm_wrapper import Agents
    return Agents


JD_EXTRACT_SYSTEM = """你是 JD 解析专家。从以下职位描述中提取关键要求。

输出 JSON:
{
  "keywords": ["关键词1", "关键词2", ...],
  "must_have": ["硬性要求1", "硬性要求2", ...],
  "nice_to_have": ["加分项1", "加分项2", ...],
  "years_of_experience": "X年",
  "education_level": "本科/硕士/博士"
}"""

JD_EXTRACT_PROMPT = "请解析以下 JD:\n\n{jd_text}"

JD_MATCH_SYSTEM = """你是一位资深招聘顾问和技术简历专家，同时理解候选人的投递策略：
候选人会把同一套真实经历，按不同岗位方向「一样话两样说」——事实不变，强调点与措辞会变，以提高入选率。

你的任务:
1. 将候选人的简历与职位描述 (JD) 进行逐项对比
2. 结合候选人已有投递策略，给出方向性改写建议
3. 从「素材库中有、但当前简历可能没写/写弱」的经历里挖出可补充点
4. 给出追问，帮助候选人回忆被遗忘的项目细节

分析维度:
- 关键词覆盖度
- 经验匹配度
- 措辞对齐与策略取景（同一事实如何换角度）
- 缺失项 / 被忽略经历

输出 JSON:
{
  "match_score": 0-100,
  "matched_keywords": ["匹配到的关键词"],
  "missing_keywords": ["缺失的关键词"],
  "section_suggestions": {"summary": "...", "work_experience": "...", "skills": "..."},
  "gap_analysis": "整体差距分析",
  "strategy_notes": "如何用既有策略/一样话两样说适配本 JD",
  "forgotten_experiences": [
    {
      "material_id": "...",
      "summary": "...",
      "why_relevant": "为何和本 JD 相关",
      "suggested_angle": "建议怎么说/怎么取景",
      "evidence": ["依据片段"],
      "confidence": 0.0
    }
  ],
  "probing_questions": ["帮候选人回忆遗漏经历的追问1", "追问2"]
}"""

JD_MATCH_PROMPT = """JD 解析结果:
{jd_requirements}

当前简历:
{resume_markdown}

领域: {domain_label}
领域关键词参考: {core_keywords}

候选人投递策略（一样话两样说）:
{strategy_context}

素材库（可能含简历未写入的经历，请挖掘）:
{materials_context}

历史改写取景参考（跨方向说法）:
{rewrite_variants_context}

请进行匹配分析，并挖掘被忽略的经历。"""

JD_REWRITE_SYSTEM = """你是简历改写专家。根据 JD 匹配结果、投递策略和修改建议，对简历进行精准改写。

候选人策略核心: 同一事实可按岗位方向换角度叙述，禁止编造未发生的经历。

要求:
1. 只修改需要调整的部分，保留其他模块不变
2. 缺失的关键词要自然地融入已有/被挖掘出的真实经历中
3. 措辞对齐 JD 风格与策略强调点
4. 量化指标保持真实可信
5. 若有 forgotten experiences，优先把高相关的角度写进合适模块（仍不编造）

输出 JSON:
{
  "sections": [{"name": "summary", "content": "..."}, ...],
  "raw_markdown": "完整 Markdown",
  "changes_summary": "修改说明"
}"""

JD_REWRITE_PROMPT = """原始简历:
{resume_markdown}

匹配分析结果:
{match_result}

修改建议:
{section_suggestions}

缺失关键词: {missing_keywords}

投递策略:
{strategy_context}

被挖掘的忽略经历:
{forgotten_context}

请改写简历，使其更适合该 JD。"""


class JDMatcherAgent:
    """JD match and resume rewrite agent (dual-layer)."""

    def __init__(self, model: Any, agents: Any = None):
        self.model = model
        self.agents = agents or _get_agents()

    def extract_jd_requirements(self, jd_text: str) -> JDRequirements:
        chain = self.agents.chain_create(
            model=self.model,
            system_prompt_template=JD_EXTRACT_SYSTEM,
            text_prompt_template=JD_EXTRACT_PROMPT,
            output_parser=JsonOutputParser(),
        )
        result = self.agents.chain_batch_generator(chain, {"jd_text": jd_text})
        return JDRequirements.model_validate(result)

    def match_and_analyze(
        self,
        resume_markdown: str,
        jd_text: str,
        domain: str = "",
        strategy: Optional[ApplicationStrategy] = None,
        materials: Optional[list[MaterialRecord]] = None,
        rewrite_variants_context: str = "",
    ) -> JDMatchResult:
        jd_req = self.extract_jd_requirements(jd_text)
        profile = get_domain(domain)
        chain = self.agents.chain_create(
            model=self.model,
            system_prompt_template=JD_MATCH_SYSTEM,
            text_prompt_template=JD_MATCH_PROMPT,
            output_parser=JsonOutputParser(),
        )
        result = self.agents.chain_batch_generator(
            chain,
            {
                "jd_requirements": jd_req.model_dump_json(indent=2),
                "resume_markdown": resume_markdown,
                "domain_label": profile["label"],
                "core_keywords": ", ".join(profile["core_keywords"]),
                "strategy_context": self._format_strategy(strategy),
                "materials_context": self._format_materials(materials or []),
                "rewrite_variants_context": rewrite_variants_context or "（暂无）",
            },
        )
        forgotten_raw = result.pop("forgotten_experiences", []) or []
        forgotten: list[ForgottenExperienceHint] = []
        for item in forgotten_raw:
            try:
                if isinstance(item, dict):
                    forgotten.append(ForgottenExperienceHint.model_validate(item))
            except Exception:
                continue

        score = result.get("match_score", 0)
        if isinstance(score, (int, float)) and score > 1:
            result["match_score"] = float(score) / 100.0

        return JDMatchResult(
            jd_text=jd_text,
            jd_requirements=jd_req,
            forgotten_experiences=forgotten,
            probing_questions=result.pop("probing_questions", []) or [],
            strategy_notes=result.pop("strategy_notes", "") or "",
            **{k: v for k, v in result.items() if k in {
                "match_score", "matched_keywords", "missing_keywords",
                "section_suggestions", "gap_analysis",
            }},
        )

    def rewrite_for_jd(
        self,
        resume: Resume,
        match_result: JDMatchResult,
        strategy: Optional[ApplicationStrategy] = None,
    ) -> Resume:
        chain = self.agents.chain_create(
            model=self.model,
            system_prompt_template=JD_REWRITE_SYSTEM,
            text_prompt_template=JD_REWRITE_PROMPT,
            output_parser=JsonOutputParser(),
        )
        suggestions_str = "\n".join(
            f"- {k}: {v}" for k, v in match_result.section_suggestions.items()
        )
        forgotten_context = "\n".join(
            f"- [{h.material_id}] {h.summary} | 角度: {h.suggested_angle} | 原因: {h.why_relevant}"
            for h in match_result.forgotten_experiences
        ) or "（无）"
        result = self.agents.chain_batch_generator(
            chain,
            {
                "resume_markdown": resume.raw_markdown,
                "match_result": match_result.model_dump_json(indent=2),
                "section_suggestions": suggestions_str,
                "missing_keywords": ", ".join(match_result.missing_keywords),
                "strategy_context": self._format_strategy(strategy),
                "forgotten_context": forgotten_context,
            },
        )
        sections = [
            ResumeSection(name=s["name"], content=s["content"])
            for s in result.get("sections", [])
        ]
        return Resume(
            domain=resume.domain,
            sections=sections,
            raw_markdown=result.get("raw_markdown", ""),
            version=resume.version + 1,
        )

    @staticmethod
    def _format_strategy(strategy: Optional[ApplicationStrategy]) -> str:
        if not strategy:
            return (
                "默认策略：同一套真实经历可按岗位方向重新取景；"
                "事实不变，强调点与措辞可变；禁止编造。"
            )
        variants = "\n".join(
            f"  - [{v.direction}] {v.angle}: {v.phrasing} （why: {v.why}）"
            for v in strategy.variants[:8]
        ) or "  （暂无具体 variant）"
        return (
            f"名称: {strategy.name}\n"
            f"方向: {strategy.domain} / {strategy.target_role}\n"
            f"核心信息: {strategy.core_message}\n"
            f"强调: {', '.join(strategy.emphasis)}\n"
            f"弱化: {', '.join(strategy.de_emphasis)}\n"
            f"规则: {'; '.join(strategy.framing_rules)}\n"
            f"为什么: {strategy.why}\n"
            f"历史取景:\n{variants}\n"
            f"备注: {strategy.notes}"
        )

    @staticmethod
    def _format_materials(materials: list[MaterialRecord]) -> str:
        if not materials:
            return "（素材库为空）"
        lines: list[str] = []
        for m in materials[:30]:
            tags = ", ".join(m.content.tags[:8])
            fields_preview = ", ".join(
                f"{k}={str(v)[:40]}" for k, v in list(m.content.fields.items())[:6]
            )
            lines.append(
                f"- id={m.id} type={m.content.type.value if hasattr(m.content.type, 'value') else m.content.type} "
                f"domain={m.domain} summary={m.content.summary} tags=[{tags}] fields={{{fields_preview}}}"
            )
        return "\n".join(lines)

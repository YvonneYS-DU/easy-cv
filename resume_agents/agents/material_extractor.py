"""
Material extractor agent — structured materials from chat/text.
"""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import JsonOutputParser

from resume_agents.memory.models import MaterialRecord, MaterialContent
from resume_agents.domain.profiles import get_domain


def _get_agents():
    """Lazy-import llm_wrapper to avoid top-level fitz import failures."""
    from llm_wrapper import Agents
    return Agents


MATERIAL_EXTRACTOR_SYSTEM = """你是一位专业的简历素材提取专家。将用户描述的工作经历、项目经验等转化为结构化简历素材。

素材是「事实库」：直接写入，不做 accept/ignore。用户偏好：**技术栈少删除**——原文出现的语言/框架/工具/中间件尽量完整保留。

## 输出格式
返回 JSON:
{
  "type": "素材类型",
  "summary": "一句话概括这段经历",
  "tags": ["关键词1", "关键词2", "关键词3"],
  "fields": { ... 根据素材类型和领域自由填充 ... }
}

## type 取值
work_experience / project / education / skill / certificate / other

## summary 要求
一句话说清这段经历的核心价值，让后续检索和索引能找到它。

## tags 要求
3-8 个关键词。技术名尽量保留，不要为了「简洁」删掉 stack。

## fields 填充建议（不是强制，有就填、没有就跳过）
- 工作经历: company, title, period, bullets, skills, tech_stack, metrics
- 项目经验: name, role, tech_stack, skills, outcomes, metrics, link, team_size, period
- 教育: school, degree, major, gpa, period
- 竞赛/开源: competition/repo, rank/role, solution, date
- 技能: category, items, proficiency, years
- 证书: name, issuer, date, credential_id
- 其他：按实际内容自行决定字段

## 技术栈偏好（必须遵守）
- 将原文中的技术栈尽量写入 fields.tech_stack（数组）和/或 fields.skills（数组）
- 宁可多保留，也不要合并成笼统的 "backend" / "AI" 而丢掉具体名
- 不要因为领域视角而删掉「看似不相关」的 stack，可放 tags 或 tech_stack 备查

## 关键原则
- 不用填满所有字段，有就填、没有就不填
- 量化指标（数字、百分比、规模）优先保留到 fields 相应的 key 里
- 一段文本如果包含多个独立经历，提取为多条素材（在 fields 里包含这些信息，调用方会逐条处理）
- 以 {domain_label} 领域视角突出重点，但 **stack 仍完整保留**。"""

MATERIAL_EXTRACTOR_PROMPT = """请将以下经历转化为结构化简历素材:

{raw_text}

领域视角: {domain_label}
领域关键词参考: {core_keywords}

以 {domain_label} 的视角提取，突出相关的技能和指标。"""


class MaterialExtractorAgent:
    """Extract structured resume materials from text."""

    def __init__(self, model: Any, agents: Any = None):
        self.model = model
        self.agents = agents or _get_agents()

    def _build_chain(self):
        return self.agents.chain_create(
            model=self.model,
            system_prompt_template=MATERIAL_EXTRACTOR_SYSTEM,
            text_prompt_template=MATERIAL_EXTRACTOR_PROMPT,
            output_parser=JsonOutputParser(),
        )

    def extract(self, raw_text: str, domain: str = "") -> MaterialRecord:
        """Extract structured material from raw text."""
        profile = get_domain(domain)
        chain = self._build_chain()
        result = self.agents.chain_batch_generator(
            chain,
            {
                "raw_text": raw_text,
                "domain_label": profile["label"],
                "core_keywords": ", ".join(profile["core_keywords"]),
            },
        )
        content = MaterialContent.model_validate(result)
        return MaterialRecord(domain=domain, content=content)

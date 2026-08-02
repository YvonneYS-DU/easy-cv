"""
Resume generator agent — section-wise or full resume.
"""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import StrOutputParser

from resume_agents.domain.profiles import get_domain
from resume_agents.memory.models import MaterialRecord, Resume, ResumeSection


def _get_agents():
    from llm_wrapper import Agents
    return Agents


# ── Per-section system prompts ──────────────────────────────

SUMMARY_SYSTEM = """你是一位资深简历写作顾问。根据用户提供的素材，撰写一段专业、有冲击力的 Personal Summary / Professional Summary。

{domain_guidance}

要求:
- 3-4 句话，简洁有力
- 第一句话定义核心方向和经验年限
- 突出最亮眼的成就和量化指标
- 使用主动语态，避免泛泛而谈
- 为 ATS 系统优化关键词密度

只输出 summary 内容，不要额外解释。"""

WORK_EXPERIENCE_SYSTEM = """你是一位资深简历写作顾问。根据用户提供的素材，撰写 "Work Experience" 模块。

{domain_guidance}

要求:
- 每条经历 3-5 个 bullet point
- 每个 bullet 以强动作动词开头（主导、设计、优化、实现、搭建、推动）
- 必须包含量化指标
- 使用 STAR 法则（情境-行动-结果）
- 按时间倒序排列
- 素材的 fields 字典中包含公司名、职位、时间、bullet 等，按标准简历格式渲染

只输出 work experience 内容，不要额外解释。"""

PROJECTS_SYSTEM = """你是一位资深简历写作顾问。根据用户提供的素材，撰写 "Projects" 模块。

{domain_guidance}

要求:
- 每个项目 2-4 个 bullet point
- 明确标注你的个人贡献和技术栈
- 包含量化成果
- GitHub / 线上链接（如有）
- 素材的 fields 中可能包含 name, role, tech_stack, outcomes, link 等，按标准格式渲染

只输出 projects 内容，不要额外解释。"""

SKILLS_SYSTEM = """你是一位资深简历写作顾问。根据用户素材中的技能信息，撰写 "Skills" 模块。

{domain_guidance}

技能分类: {skill_categories}

要求:
- 按给定的分类组织技能
- 技能名称应使用行业标准术语
- 按熟练程度从高到低排列（最擅长的在前）
- 排除过于陈旧或初级的技能

格式 (只用分类名和列表，不要用 markdown 表格):
**分类名1:** 技能1, 技能2, 技能3
**分类名2:** 技能4, 技能5

只输出 skills 内容，不要额外解释。"""

SECTION_SYSTEM_PROMPTS = {
    "summary": SUMMARY_SYSTEM,
    "work_experience": WORK_EXPERIENCE_SYSTEM,
    "projects": PROJECTS_SYSTEM,
    "skills": SKILLS_SYSTEM,
}

SECTION_LABELS = {
    "summary": "Professional Summary",
    "work_experience": "Work Experience",
    "projects": "Projects",
    "skills": "Skills",
    "education": "Education",
}


class ResumeGeneratorAgent:
    """Resume generation agent."""

    def __init__(self, model: Any, agents: Any = None):
        self.model = model
        self.agents = agents or _get_agents()

    def _materials_context(self, materials: list[MaterialRecord]) -> str:
        """Join materials into context text for flexible fields dicts."""
        parts = []
        for i, m in enumerate(materials):
            c = m.content
            header = f"### 素材 {i+1} [{c.id}] | {c.type.value} | {c.summary}"
            meta = [f"tags: {', '.join(c.tags)}", f"domain: {m.domain}"]
            # Surface important fields first for the LLM
            key_fields = {}
            remaining = {}
            priority_keys = {"company", "organization", "school", "name", "title", "role", "period"}
            for k, v in c.fields.items():
                if k in priority_keys:
                    key_fields[k] = v
                else:
                    remaining[k] = v
            if key_fields:
                meta.append(" | ".join(f"{k}: {v}" for k, v in key_fields.items()))
            meta.append(f"详细: {remaining}")
            parts.append(header + "\n" + "\n".join(meta) + "\n")
        return "\n".join(parts)

    def generate_section(
        self, domain: str, section: str,
        materials: list[MaterialRecord], jd_text: str = "",
    ) -> str:
        profile = get_domain(domain)
        system_prompt = SECTION_SYSTEM_PROMPTS.get(section)
        if not system_prompt:
            system_prompt = "你是简历顾问。根据素材生成 {section} 模块。\n{domain_guidance}"
        system_prompt = system_prompt.format(
            domain_guidance=profile.get("bullet_style", ""),
            skill_categories=", ".join(profile.get("skill_categories", [])),
        )
        prompt = f"""生成简历的 "{SECTION_LABELS.get(section, section)}" 模块。

领域: {profile["label"]}
{"JD 参考: " + jd_text if jd_text else ""}

可用素材（每条包含 id/type/summary/tags/fields）:
{self._materials_context(materials)}
"""
        chain = self.agents.chain_create(
            model=self.model,
            system_prompt_template=system_prompt,
            text_prompt_template=prompt,
            output_parser=StrOutputParser(),
        )
        return str(self.agents.chain_batch_generator(chain, {}))

    def generate_full(
        self, domain: str, materials: list[MaterialRecord], jd_text: str = "",
    ) -> Resume:
        profile = get_domain(domain)
        sections: list[ResumeSection] = []
        for section_name in profile["section_priority"]:
            content = self.generate_section(
                domain=domain, section=section_name,
                materials=materials, jd_text=jd_text,
            )
            sections.append(ResumeSection(name=section_name, content=content))
        markdown_parts = [f"# {s.name.upper()}\n\n{s.content}" for s in sections]
        raw_markdown = "\n\n".join(markdown_parts)
        return Resume(domain=domain, sections=sections, raw_markdown=raw_markdown)

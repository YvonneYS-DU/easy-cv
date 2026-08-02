"""
Local mock when no API key is set, so the frontend can be fully demoed.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from resume_agents.memory.models import (
    ApplicationStrategy,
    ChatMessage,
    ForgottenExperienceHint,
    JDMatchResult,
    JDRequirements,
    MaterialContent,
    MaterialRecord,
    MaterialStatus,
    MaterialType,
    Resume,
    ResumeSection,
)
from resume_agents.memory.store import MaterialStore


def _now() -> str:
    return datetime.now().isoformat()


def mock_add_material(
    store: MaterialStore, raw_text: str, domain: str = ""
) -> tuple[MaterialRecord, list[str]]:
    mid = str(uuid.uuid4())[:8]
    summary = re.sub(r"\s+", " ", raw_text).strip()[:120] or "未命名经历"
    lower = raw_text.lower()
    if any(k in lower for k in ("intern", "engineer", "公司", "工作")):
        mtype = MaterialType.WORK_EXPERIENCE
    elif any(k in lower for k in ("project", "项目")):
        mtype = MaterialType.PROJECT
    elif any(k in lower for k in ("university", "bachelor", "master", "学历", "大学")):
        mtype = MaterialType.EDUCATION
    elif any(k in lower for k in ("python", "skill", "技能")):
        mtype = MaterialType.SKILL
    else:
        mtype = MaterialType.OTHER

    # Rough tech-stack extraction; prefer keeping items
    stack = sorted(
        {
            t
            for t in re.findall(
                r"(?i)\b(?:python|java|go|rust|typescript|javascript|react|vue|fastapi|"
                r"django|flask|kafka|redis|postgres|mysql|docker|kubernetes|k8s|aws|gcp|"
                r"langchain|openai|rag|pytorch|tensorflow|spark|flink|graphql|grpc)\b",
                raw_text,
            )
        },
        key=str.lower,
    )
    tags = ["mock"] + stack[:8]
    fields: dict = {"source": "mock", "raw_preview": summary}
    if stack:
        fields["tech_stack"] = stack
        fields["skills"] = stack

    material = MaterialRecord(
        id=mid,
        domain=domain,
        status=MaterialStatus.EXTRACTED,
        content=MaterialContent(
            id=mid,
            type=mtype,
            summary=summary,
            tags=tags,
            fields=fields,
        ),
        chat_log=[],
        created_at=_now(),
        updated_at=_now(),
    )
    material.raw_ref = store.save_raw(raw_text, mid)
    store.save_material(material)
    questions = [
        "这段经历的核心成果能否补充一个量化指标？",
        "你的个人职责边界是什么？",
    ]
    material.chat_log.append(
        ChatMessage(role="ai", msg="\n".join(questions), timestamp=_now())
    )
    store.save_material(material)
    return material, questions


def mock_refine_material(
    material: MaterialRecord, user_response: str
) -> tuple[MaterialRecord, list[str], bool]:
    material.chat_log.append(
        ChatMessage(role="user", msg=user_response, timestamp=_now())
    )
    material.content.fields["user_notes"] = user_response
    material.content.summary = (material.content.summary + " · " + user_response[:40]).strip(" ·")
    material.status = MaterialStatus.REFINED
    material.updated_at = _now()
    material.chat_log.append(
        ChatMessage(role="ai", msg="已根据你的补充完成素材打磨。", timestamp=_now())
    )
    return material, [], True


def mock_rewrite_block(
    selected_text: str,
    instruction: str,
    chip: str = "",
    material_hints: str = "",
    target_role: str = "",
) -> str:
    text = selected_text.strip()
    inst = instruction.strip()
    lower = inst.lower()

    if "gpa" in lower:
        text = re.sub(r"GPA:\s*[^\n]+", "GPA: 3.9/4.0", text, flags=re.I)
        if "GPA" not in text.upper():
            text = text.rstrip() + "\nGPA: 3.9/4.0"
        return text

    if any(k in lower for k in ("精简", "concise", "shorter", "简短")):
        # Condense text but keep tech terms (preserve-stack preference)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        bullets = [ln for ln in lines if ln.startswith(("-", "•", "*")) or ln[:2].isdigit()]
        tech = re.findall(
            r"(?i)\b(?:python|java|go|kafka|redis|docker|rag|langchain|fastapi|react)\b",
            text,
        )
        if bullets:
            keep = bullets[: max(2, len(bullets) - 1)]
            head = [ln for ln in lines if ln not in bullets][:2]
            out = "\n".join(head + keep)
            if tech and not any(t.lower() in out.lower() for t in tech):
                out += "\n• Stack: " + ", ".join(dict.fromkeys(tech))
            return out
        return text[: max(80, int(len(text) * 0.7))].rstrip() + "…"

    if any(k in lower for k in ("量化", "metric", "数字", "impact")):
        if "by " not in text.lower() and "%" not in text:
            text = text.rstrip() + "\n• Delivered measurable impact, improving key outcome by 30%."

    elif any(k in lower for k in ("专业", "polish", "专业表达", "翻译", "english")):
        polished = text
        polished = polished.replace("负责", "Led")
        polished = polished.replace("参与", "Contributed to")
        polished = polished.replace("做了", "Delivered")
        if polished == text:
            text = f"{text.rstrip()}\n• Strengthened professional wording for ATS readability."
        else:
            text = polished
    else:
        label = f"[{chip}] " if chip else ""
        role = f" → {target_role}" if target_role else ""
        text = f"{text.rstrip()}\n• AI refinement applied: {label}{inst[:80]}{role}"

    # Fold in fillable material points (simulate mine → block suggestion)
    if material_hints.strip():
        first = material_hints.strip().splitlines()[0]
        m = re.search(r"\|\s*(.+)$", first)
        summary = (m.group(1).strip() if m else first)[:100]
        text = text.rstrip() + f"\n• Incorporated related experience: {summary}"

    return text


def mock_generate_section(
    domain: str,
    section: str,
    materials: list[MaterialRecord],
    jd_text: str = "",
) -> str:
    titles = {
        "summary": "Results-driven professional with hands-on delivery across AI systems and productized workflows.",
        "work_experience": "AI Engineer — Demo Company (2024 - Present)\n• Built production RAG agents adopted by multiple teams.\n• Improved extraction accuracy from 82% to 94%.",
        "projects": "Multi-Agent Resume Editor\n• Designed block-level AI editing with accept/reject diff flow.",
        "skills": "**GenAI:** RAG, LangChain, Prompt Engineering\n**Backend:** Python, FastAPI, Docker",
        "education": "National University of Singapore — Master of Technology\nCore: LLM | GenAI | ML | Analytics",
    }
    base = titles.get(section, f"{section.replace('_', ' ').title()} content")
    if materials:
        base += "\n\nBased on materials:\n" + "\n".join(
            f"- {m.content.summary}" for m in materials[:4]
        )
    if jd_text:
        base += "\n\nAligned to JD keywords from provided description."
    if domain:
        base += f"\n\nDomain focus: {domain}"
    return base


def mock_generate_full(
    domain: str, materials: list[MaterialRecord], jd_text: str = ""
) -> Resume:
    sections = []
    for name in ("summary", "education", "skills", "work_experience", "projects"):
        content = mock_generate_section(domain, name, materials, jd_text)
        sections.append(ResumeSection(name=name, content=content))
    raw = "\n\n".join(f"# {s.name.upper()}\n\n{s.content}" for s in sections)
    return Resume(domain=domain, sections=sections, raw_markdown=raw)


def mock_match_jd(
    resume_markdown: str,
    jd_text: str,
    domain: str = "",
    materials: list[MaterialRecord] | None = None,
    strategy: ApplicationStrategy | None = None,
) -> JDMatchResult:
    resume_tokens = set(re.findall(r"[A-Za-z\u4e00-\u9fff]{2,}", resume_markdown.lower()))
    jd_tokens = set(re.findall(r"[A-Za-z\u4e00-\u9fff]{2,}", jd_text.lower()))
    stop = {"and", "the", "with", "for", "you", "our", "will", "have", "from", "this", "that"}
    jd_kw = sorted([t for t in jd_tokens if t not in stop])[:12]
    matched = [k for k in jd_kw if k in resume_tokens]
    missing = [k for k in jd_kw if k not in resume_tokens]
    score = 0.55
    if jd_kw:
        score = round(0.4 + 0.6 * (len(matched) / max(1, len(jd_kw))), 2)

    forgotten: list[ForgottenExperienceHint] = []
    resume_l = resume_markdown.lower()
    for m in (materials or [])[:12]:
        summary = m.content.summary or ""
        if not summary:
            continue
        if summary[:20].lower() in resume_l:
            continue
        blob = " ".join(
            [summary, " ".join(m.content.tags), " ".join(str(v) for v in m.content.fields.values())]
        ).lower()
        hit = [k for k in jd_kw if k in blob]
        if not hit and domain and domain not in (m.domain or ""):
            # still surface cross-domain materials as memory prompts
            hit = list(m.content.tags[:3])
        forgotten.append(
            ForgottenExperienceHint(
                material_id=m.id,
                summary=summary,
                why_relevant=(
                    f"素材库有此经历，当前简历未充分体现。"
                    + (f" 与 JD 相关: {', '.join(hit[:4])}。" if hit else "")
                ),
                suggested_angle=(
                    f"按「{domain or '目标方向'}」重新取景，强调 {', '.join(hit[:4]) or '可迁移能力'}"
                ),
                evidence=hit[:5],
                confidence=0.72 if hit else 0.48,
            )
        )

    strategy_notes = (
        f"沿用策略「{strategy.name}」：同一事实按本 JD 换角度表述，不编造经历。"
        if strategy
        else "建议建立投递策略：同一经历在不同方向下强调不同成果。"
    )
    questions = [
        "还有哪些项目你做过但没写进这份简历？",
        "有没有可量化的业务结果（延迟、准确率、成本、转化）被你略过？",
    ]
    if forgotten:
        questions.insert(0, f"「{forgotten[0].summary[:40]}」这段经历能否补一句个人贡献？")

    return JDMatchResult(
        jd_text=jd_text,
        jd_requirements=JDRequirements(
            keywords=jd_kw,
            must_have=jd_kw[:4],
            nice_to_have=jd_kw[4:8],
            years_of_experience="",
            education_level="",
        ),
        match_score=score,
        matched_keywords=matched,
        missing_keywords=missing,
        section_suggestions={
            "summary": "前置与 JD 重合的关键词与业务场景；用策略取景，不要堆砌无关技术。",
            "work_experience": "补充可量化成果；同一项目可按本方向改主语与强调点。",
            "skills": "补齐 missing keywords 中的关键技术栈。",
        },
        gap_analysis=(
            f"Mock 匹配完成（domain={domain or 'general'}）。"
            f"命中 {len(matched)} 个关键词，缺口 {len(missing)} 个。"
            f" 挖出 {len(forgotten)} 条可能被忽略的素材经历。"
        ),
        strategy_notes=strategy_notes,
        forgotten_experiences=forgotten[:6],
        probing_questions=questions,
    )


def mock_rewrite_for_jd(resume: Resume, match: JDMatchResult) -> Resume:
    missing = ", ".join(match.missing_keywords[:6]) or "target keywords"
    forgotten_lines = "\n".join(
        f"- {h.summary} → {h.suggested_angle}" for h in match.forgotten_experiences[:4]
    ) or "- (none)"
    extra = (
        f"\n\n# JD ALIGNMENT\n\n"
        f"Emphasized keywords: {', '.join(match.matched_keywords[:6]) or 'N/A'}\n"
        f"Added coverage for: {missing}\n"
        f"Strategy: {match.strategy_notes or 'reframe same facts for this JD'}\n"
        f"Recovered experiences:\n{forgotten_lines}"
    )
    return Resume(
        domain=resume.domain,
        sections=list(resume.sections),
        raw_markdown=(resume.raw_markdown or "") + extra,
        version=resume.version + 1,
    )

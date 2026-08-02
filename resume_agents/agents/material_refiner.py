"""
Material refiner agent — polish materials via dialogue.
"""

from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import JsonOutputParser

from resume_agents.memory.models import MaterialRecord, MaterialContent, ChatMessage, MaterialStatus


def _get_agents():
    from llm_wrapper import Agents
    return Agents


MATERIAL_REFINER_SYSTEM = """你是一位专业的简历顾问，正在和用户一起优化他/她的简历素材记录。

素材是事实库：更新后直接生效，没有 accept/ignore。
用户偏好：**技术栈少删除**——除非用户明确要求删除，否则不要从 tech_stack/skills/tags 里拿掉已有技术名。

## 你的职责
1. 审视当前的结构化素材，找出缺失或模糊的地方
2. 每次提出 1-3 个针对性问题，引导用户补充
3. 用户回答后，更新素材的 fields（自由字典），并检查是否还需要更多信息
4. 当素材已经足够完善时，标记 is_complete = true

## 追问重点（按优先级）
- 量化指标缺失 → 问具体数字（提升百分比、用户规模、团队人数等）
- 技术栈可补充 → 可追问更多工具，但禁止为「干净」而删已有 stack
- 个人贡献不清晰 → 问"你具体负责什么"
- STAR 不完整 → 问情境和结果
- tags 可增加，不要靠删减 stack 来「精准」
- 需要拆分为多条素材 → 提醒用户

## 输出格式
返回 JSON:
{
  "updated_content": {
    "type": "...",
    "summary": "...",
    "tags": [...],
    "fields": { ... 更新后的所有字段 ... }
  },
  "questions": ["追问1", "追问2"],
  "is_complete": false
}

注意:
- updated_content 必须包含完整的 content（type/summary/tags/fields），而不是只返回修改的部分
- 合并更新时：原有 tech_stack/skills 与新补充做并集，默认不删
- fields 的内容由你根据素材类型自由组织，不用遵循固定 schema"""

MATERIAL_REFINER_PROMPT = """当前素材记录:
{current_material}

用户回复:
{user_response}

对话历史:
{chat_log}

请根据用户回复更新素材（完整 output），并判断是否需要继续追问。"""


class MaterialRefinerAgent:
    """Refine material via human–AI dialogue."""

    def __init__(self, model: Any, agents: Any = None):
        self.model = model
        self.agents = agents or _get_agents()

    def _build_chain(self):
        return self.agents.chain_create(
            model=self.model,
            system_prompt_template=MATERIAL_REFINER_SYSTEM,
            text_prompt_template=MATERIAL_REFINER_PROMPT,
            output_parser=JsonOutputParser(),
        )

    def refine(self, material: MaterialRecord, user_response: str) -> tuple[MaterialRecord, list[str], bool]:
        chat_log_str = "\n".join(f"[{m.role}] {m.msg}" for m in material.chat_log)
        chain = self._build_chain()
        result = self.agents.chain_batch_generator(
            chain,
            {
                "current_material": material.model_dump_json(indent=2),
                "user_response": user_response,
                "chat_log": chat_log_str,
            },
        )
        updated_content = MaterialContent.model_validate(result["updated_content"])
        if material.preferences.preserve_tech_stack:
            updated_content = self._merge_preserve_stack(material.content, updated_content)
        material.content = updated_content
        material.version += 1
        material.chat_log.append(ChatMessage(role="user", msg=user_response))
        ai_questions = result.get("questions", [])
        if ai_questions:
            material.chat_log.append(ChatMessage(role="ai", msg=" | ".join(ai_questions)))
        is_complete = result.get("is_complete", False)
        if is_complete:
            material.status = MaterialStatus.REFINED
        return material, ai_questions, is_complete

    @staticmethod
    def _as_str_list(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        if isinstance(value, str) and value.strip():
            return [p.strip() for p in value.split(",") if p.strip()]
        return []

    def _merge_preserve_stack(
        self,
        old: MaterialContent,
        new: MaterialContent,
    ) -> MaterialContent:
        """Preserve tech stack: union tech_stack / skills / tags so refine does not drop old stack."""
        fields = dict(new.fields or {})
        for key in ("tech_stack", "skills"):
            merged = list(
                dict.fromkeys(
                    self._as_str_list((old.fields or {}).get(key))
                    + self._as_str_list(fields.get(key))
                )
            )
            if merged:
                fields[key] = merged
        new.fields = fields
        new.tags = list(dict.fromkeys(list(old.tags or []) + list(new.tags or [])))
        return new

    def generate_initial_questions(self, material: MaterialRecord) -> list[str]:
        chain = self._build_chain()
        result = self.agents.chain_batch_generator(
            chain,
            {
                "current_material": material.model_dump_json(indent=2),
                "user_response": "（这是初始提取，请审视并提问）",
                "chat_log": "",
            },
        )
        questions = result.get("questions", [])
        if questions:
            material.chat_log.append(ChatMessage(role="ai", msg=" | ".join(questions)))
        return questions

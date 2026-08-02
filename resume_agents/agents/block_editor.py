"""
Block editor agent — AI rewrite for a selected resume block.
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.output_parsers import StrOutputParser


def _get_agents():
    from llm_wrapper import Agents

    return Agents


BLOCK_EDIT_SYSTEM = """你是一位资深简历写作顾问。用户选中简历某一区块后，你给出改写建议（由用户接受/忽略）。

规则:
- 只输出改写后的完整区块文本，不要解释、不要 markdown 代码块
- 以用户当前编辑稿为准进行完善，不要回退到更早版本
- 尽量保留原有字段结构（标题/时间/副标题/补充/要点列表），除非指令要求改变结构
- 若用户只改了个别词，请在此基础上润色，不要整盘重写
- 输出时尽量使用 Title:/Date:/Subtitle:/Meta: 与 - bullet 格式，便于回填结构
- 优先使用可量化、可验证的表述
- 中英文跟随原文为主；若指令要求切换语言则切换
- 不要编造用户未提供的硬事实（公司名、学历、时间）
- 若提供「源项目写法分支」：按目标方向取景，事实不变、角度可变
- 若提供「可补素材点」：把相关真实经历自然补进本区块（仍不编造）；技术栈倾向保留，少删
- 会话记忆仅作参考，以当前编辑稿和最新指令为准
"""


class BlockEditorAgent:
    """Targeted rewrite of a selected block (suggestion; user accepts/ignores)."""

    def __init__(self, model: Any, agents: Any = None):
        self.model = model
        self.agents = agents or _get_agents()

    def rewrite(
        self,
        selected_text: str,
        instruction: str,
        chip: str = "",
        domain: str = "",
        history: str = "",
        writing_branches: str = "",
        material_hints: str = "",
        target_role: str = "",
    ) -> str:
        extra_blocks = []
        if history.strip():
            extra_blocks.append(
                f"近期会话记忆（参考）:\n{history.strip()}"
            )
        if writing_branches.strip():
            extra_blocks.append(
                f"源项目写法分支（按方向复用，勿编造）:\n{writing_branches.strip()}"
            )
        if material_hints.strip():
            extra_blocks.append(
                f"可补进本区块的素材点（用户素材库已有、当前稿可能漏写）:\n{material_hints.strip()}"
            )
        extra = ("\n\n".join(extra_blocks) + "\n") if extra_blocks else ""
        prompt = f"""请基于用户当前编辑稿完善以下简历区块。

区块标签: {chip or "未命名"}
领域: {domain or "通用"}
投递方向: {target_role or "未指定"}
修改指令: {instruction}
{extra}
当前编辑稿:
{selected_text}
"""
        chain = self.agents.chain_create(
            model=self.model,
            system_prompt_template=BLOCK_EDIT_SYSTEM,
            text_prompt_template=prompt,
            output_parser=StrOutputParser(),
        )
        result = str(self.agents.chain_batch_generator(chain, {})).strip()
        result = re.sub(r"^```(?:\w+)?\n?", "", result)
        result = re.sub(r"\n?```$", "", result)
        return result.strip()

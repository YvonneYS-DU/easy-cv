"""
Domain profiles — resume generation strategy per role.
"""

from typing import Any


DOMAIN_PROFILES: dict[str, dict[str, Any]] = {
    "ai_engineer": {
        "label": "AI/ML 工程师",
        "core_keywords": [
            "机器学习", "深度学习", "推荐系统", "NLP", "CV",
            "模型部署", "特征工程", "A/B测试", "模型优化",
            "PyTorch", "TensorFlow", "Transformer", "LLM",
        ],
        "section_priority": ["summary", "work_experience", "projects", "skills", "education"],
        "bullet_style": (
            "以动作为开头，强烈偏向数据与指标导向（AUC、CTR、准确率、QPS、延迟）。"
            "每一段务必包含量化的模型效果、数据体量或系统规模。"
        ),
        "summary_guidance": (
            "聚焦 AI/ML 工程能力，突出模型全生命周期经验（数据→训练→评估→部署）。"
            "3-4 句话，第一句定义你的核心方向与年限，后续展示最亮眼的项目/指标。"
        ),
        "skill_categories": [
            "编程语言", "深度学习框架", "模型架构", "MLOps/部署", "数据处理", "云计算",
        ],
    },
    "backend_engineer": {
        "label": "后端工程师",
        "core_keywords": [
            "高并发", "微服务", "分布式系统", "数据库", "Kubernetes",
            "消息队列", "缓存", "API设计", "系统架构", "性能优化",
            "Go", "Java", "Python", "Redis", "MySQL", "Docker",
        ],
        "section_priority": ["summary", "work_experience", "skills", "projects", "education"],
        "bullet_style": (
            "强调系统规模（QPS/DAU）、架构设计决策和个人贡献。"
            "以强动词开头，量化性能提升、系统吞吐和稳定性指标。"
        ),
        "summary_guidance": (
            "突出系统设计能力和后端工程经验。"
            "3-4 句话，展示你搭建/优化过的最复杂系统、团队规模和核心指标。"
        ),
        "skill_categories": [
            "编程语言", "框架", "中间件/数据库", "云原生", "系统设计",
        ],
    },
    "frontend_engineer": {
        "label": "前端工程师",
        "core_keywords": [
            "React", "Vue", "TypeScript", "CSS", "性能优化",
            "工程化", "组件库", "跨端", "SSR", "微前端",
        ],
        "section_priority": ["summary", "work_experience", "projects", "skills", "education"],
        "bullet_style": (
            "强调页面性能（LCP/FID/CLS）、工程化建设和用户体验提升。"
            "量化性能提升、打包体积优化、开发效率提升等指标。"
        ),
        "summary_guidance": (
            "3-4 句话，突出前端技术栈深度和业务影响力。"
        ),
        "skill_categories": [
            "编程语言", "框架/库", "工程化", "性能优化", "跨端",
        ],
    },
    "data_engineer": {
        "label": "数据工程师",
        "core_keywords": [
            "Spark", "Flink", "ETL", "数据仓库", "数据湖",
            "Kafka", "Airflow", "SQL", "数据治理", "实时计算",
        ],
        "section_priority": ["summary", "work_experience", "skills", "projects", "education"],
        "bullet_style": (
            "强调数据规模（PB/TB级）、管道吞吐、延迟和可靠性。"
            "量化数据量、处理速度、降本效果。"
        ),
        "summary_guidance": (
            "3-4 句话，突出数据工程全链路能力。"
        ),
        "skill_categories": [
            "编程语言", "大数据框架", "调度/编排", "存储/数据湖", "云平台",
        ],
    },
    "product_manager": {
        "label": "产品经理",
        "core_keywords": [
            "产品规划", "需求分析", "用户研究", "数据分析",
            "PRD", "跨团队协作", "A/B测试", "增长",
        ],
        "section_priority": ["summary", "work_experience", "projects", "skills", "education"],
        "bullet_style": (
            "强调业务结果和用户价值，量化指标的提升（留存、转化、收入）。"
        ),
        "summary_guidance": (
            "3-4 句话，突出产品判断力和商业影响力。"
        ),
        "skill_categories": [
            "产品工具", "数据分析", "方法论", "垂直领域知识",
        ],
    },
}


def get_domain(domain: str) -> dict[str, Any]:
    """Return domain config, or a default if missing."""
    return DOMAIN_PROFILES.get(
        domain,
        {
            "label": domain,
            "core_keywords": [],
            "section_priority": ["summary", "work_experience", "skills", "projects", "education"],
            "bullet_style": "使用 STAR 法则，量化指标，动词开头。",
            "summary_guidance": "3-4 句话总结核心竞争力。",
            "skill_categories": ["编程语言", "框架/工具", "领域知识"],
        },
    )


def list_domains() -> list[dict[str, str]]:
    """List all supported domains."""
    return [{"key": k, "label": v["label"]} for k, v in DOMAIN_PROFILES.items()]

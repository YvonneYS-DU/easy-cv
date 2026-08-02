# Easy CV

[English](README.md) | [简体中文](README.zh-CN.md)

AI 简历编辑器：左侧简历纸张 + 右侧 AI 区块改写，复用多 Agent 后端（素材提取 / 简历生成 / JD 匹配）。

## 目录

```
easy-cv/
├── main.py                 # FastAPI 入口（API + 静态前端）
├── resume_agents/          # 后端包（agents / api / memory / domain）
├── frontend/               # React + Vite 前端
└── static/                 # 前端构建产物
```

## 快速启动

### 1) 后端

```bash
cd easy-cv
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
# 无 OPENAI_API_KEY 时自动 mock，可直接演示
python main.py
```

打开 http://127.0.0.1:8002  
（默认端口 `8002`，可用环境变量 `PORT` 覆盖；避免与本机其他 8000 服务冲突）

### 2) 前端开发（热更新）

```bash
# 终端 A
cd easy-cv && RESUME_MOCK=1 python main.py

# 终端 B
cd easy-cv/frontend
npm install
npm run dev
```

打开 http://127.0.0.1:5173（已代理到后端 8002）

### 3) 生产构建

```bash
cd easy-cv/frontend && npm run build
cd .. && python main.py
```

## 核心交互

- 点击简历区块 → 右侧 AI 面板选中
- 快捷指令 / 自定义指令 → 生成 diff 建议 → 应用 / 忽略
- 导入 `.txt/.md`、导出 Markdown / 文本 / 打印 PDF
- 素材库提取、按领域生成完整简历、JD 匹配改写
- 桌面双栏；窄屏右侧面板抽屉式；打印样式适配

## API（节选）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/meta` | 服务模式 mock/llm |
| POST | `/api/v1/resume/block-rewrite` | 区块 AI 改写 |
| POST | `/api/v1/materials` | 添加素材 |
| POST | `/api/v1/resume/full` | 生成完整简历 |
| POST | `/api/v1/resume/match` | JD 匹配与改写 |
| GET | `/api/v1/domains` | 领域列表 |

## 设计复用

视觉与布局对齐设计稿 *Resume AI Editor*：品牌色 `#4b3fe3`、顶栏 48px、左侧纸张 + 右侧 380px AI 面板、区块 hover/selected、diff 卡片。

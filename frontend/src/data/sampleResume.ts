import type { ResumeDocument } from '../types/resume'

export const sampleResume: ResumeDocument = {
  id: 'demo-resume',
  title: 'Zhang Wei',
  domain: 'ai_engineer',
  updatedAt: new Date().toISOString(),
  nodes: [
    {
      type: 'block',
      id: 'contact',
      chip: '基本信息',
      kind: 'contact',
      html: `<div class="cv-name">Zhang Wei</div>
<div class="cv-contact-line">zhangwei@example.com · +65 9123 4567 · Singapore · linkedin.com/in/zhangwei</div>`,
    },
    {
      type: 'section',
      id: 'sec-education',
      title: 'Education',
    },
    {
      type: 'block',
      id: 'edu-nus',
      chip: 'Education · NUS',
      kind: 'education',
      html: `<div class="cv-entry-head">
  <span class="cv-entry-title">National University of Singapore - ISS</span>
  <span class="cv-entry-date">Aug 2022 - Oct 2024</span>
</div>
<div class="cv-entry-sub">Master of Tech - Enterprise Business Analytics</div>
<div class="cv-entry-meta">Core courses: LLM | GenAI | Big Data Engineering | ML | FinTech | Data Analytics</div>`,
    },
    {
      type: 'block',
      id: 'edu-zufe',
      chip: 'Education · ZUFE',
      kind: 'education',
      html: `<div class="cv-entry-head">
  <span class="cv-entry-title">Zhejiang University of Finance and Economics</span>
  <span class="cv-entry-date">Sep 2018 - Jun 2022</span>
</div>
<div class="cv-entry-sub">Bachelor of Management - Financial Management</div>
<div class="cv-entry-meta">GPA: 4.67/5.0 (top 1%)</div>`,
    },
    {
      type: 'section',
      id: 'sec-skills',
      title: 'Professional Skills',
    },
    {
      type: 'block',
      id: 'skills-lang',
      chip: 'Skills · 编程语言',
      kind: 'skill',
      html: `<div class="cv-skill-line"><b>Programming Languages:</b> Python, Rust, R</div>`,
    },
    {
      type: 'block',
      id: 'skills-genai',
      chip: 'Skills · GenAI',
      kind: 'skill',
      html: `<div class="cv-skill-line"><b>GenAI:</b> RAG, LangChain, MCP, Prompt Engineering</div>`,
    },
    {
      type: 'block',
      id: 'skills-bigdata',
      chip: 'Skills · 大数据',
      kind: 'skill',
      html: `<div class="cv-skill-line"><b>Big Data:</b> SQL, Vector Databases, PySpark</div>`,
    },
    {
      type: 'block',
      id: 'skills-devops',
      chip: 'Skills · DevOps',
      kind: 'skill',
      html: `<div class="cv-skill-line"><b>DevOps:</b> Azure, AWS, Docker, K8s, CI/CD</div>`,
    },
    {
      type: 'section',
      id: 'sec-work',
      title: 'Work Experience',
    },
    {
      type: 'block',
      id: 'work-rightship',
      chip: 'Work · RightShip',
      kind: 'work',
      html: `<div class="cv-entry-head">
  <span class="cv-entry-title">AI Engineer - RightShip (Singapore)</span>
  <span class="cv-entry-date">Sep 2024 - Now</span>
</div>
<ul class="cv-bullets">
  <li>Built RAG-based maritime regulation agents, cutting compliance review time by 60%.</li>
  <li>Shipped an internal chatbot with RAG over 10k+ documents, adopted by 3 teams.</li>
  <li>Designed a multi-agent document processing system for charter-party extraction.</li>
  <li>Fine-tuned GPT-4o on domain data, improving extraction accuracy from 82% to 94%.</li>
</ul>`,
    },
    {
      type: 'block',
      id: 'work-goalsmapper',
      chip: 'Work · GoalsMapper',
      kind: 'work',
      html: `<div class="cv-entry-head">
  <span class="cv-entry-title">GenAI Developer Intern - GoalsMapper (Singapore)</span>
  <span class="cv-entry-date">Mar 2024 - Aug 2024</span>
</div>
<ul class="cv-bullets">
  <li>Prototyped a LangChain-based financial advisory assistant for client report drafting.</li>
  <li>Automated prompt evaluation pipelines, reducing manual QA effort by 40%.</li>
</ul>`,
    },
  ],
}

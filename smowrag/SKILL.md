---
name: smowrag
description: |
  基于 LightRAG 框架的知识图谱 RAG 技能，用于构建和查询文档知识库。

  触发条件：当用户需要加载文档、基于文档内容进行问答或查询特定信息时。

  执行：根据用户请求调用 load_documents() 加载文档或调用 query() 进行查询，返回处理结果。
category: skill
metadata:
  version: "1.0.0"
  author: "system"
  tags: ["rag", "knowledge-graph", "document", "qa", "lightrag"]
  tools: ["lightrag_cli"]
---

# Smowrag

基于 LightRAG 框架的知识图谱 RAG 技能，用于构建和查询文档知识库。

## ⚠️ 前置配置（必须）

**使用本 Skill 前，请先完成以下配置：**

编辑 `config.yaml`：

```yaml
llm:
  api_base_url: "https://api-inference.cn/v1"          # 大模型 API 地址
  api_key: "your-api-key"                                  # API 密钥
  api_model_id: "deepseek-ai/DeepSeek-V4-Flash"           # 大模型名称

embedding:
  provider: "local"                                        # 使用本地 Embedding
  model_name: "bge-m3"                                     # 模型名称
  local_model_path: "D:\\embedding\\bgem3"                  # 本地模型路径

document_parser:
  provider: "mineru_local"                                 # 文档解析器
```

**配置检查清单：**
- [ ] 大模型 API 可正常访问
- [ ] Embedding 模型已下载且路径正确
- [ ] MinerU 模型已配置（如使用 PDF 解析）

---

## 概述

**使用目的**：将文档（PDF、Word、TXT 等）构建为知识图谱，支持智能问答检索。

**调用时机**：当用户需要：
- 加载文档到知识库
- 基于文档内容进行问答
- 查询特定信息时

---

## 业务流程

### 统一流程：文档加载与查询

```
用户请求
    │
    ├─► 如果是加载文档请求 ──► 调用 load_documents() ──► 返回加载结果
    │                                                              │
    │                                                              ▼
    │                                                    成功：继续下一步
    │                                                    失败：返回错误信息
    │
    └─► 如果是查询请求 ──────► 调用 query() ───────────► 返回答案和来源
                                                                   │
                                                                   ▼
                                                          成功：生成回复
                                                          失败：返回错误信息
```

### 步骤详解

#### 步骤 1：判断用户意图

分析用户输入，确定是以下哪种请求：

| 请求类型 | 关键词 | 操作 |
|---------|-------|------|
| **加载文档** | "加载"、"导入"、"添加文档"、"构建知识库" | 进入步骤 2 |
| **查询问答** | "查询"、"搜索"、"问答"、"什么是"、"为什么" | 进入步骤 3 |

#### 步骤 2：加载文档（调用 Script）

**调用时机**：当用户需要加载文档时立即调用

**调用方式**：
```bash
python scripts/lightrag_cli.py load --data-path <文档路径>
```

**输入参数**：
- `data_path`: 文件路径或目录路径（支持 PDF、DOCX、TXT、MD）

**处理流程**：
1. Script 解析文档（MinerU 解析 PDF，python-docx 解析 Word）
2. Script 提取实体和关系（调用 LLM）
3. Script 构建知识图谱并保存到 `lightrag_db/`

**结束判断**：
- ✅ **成功**：Script 返回成功消息（包含实体数、关系数）
- ❌ **失败**：Script 返回错误信息（解析失败/API 错误/存储错误）

**你应该做的**：
- 成功：告知用户文档已加载，可以继续查询
- 失败：告知用户错误原因，建议检查配置或文档

#### 步骤 3：查询问答（调用 Script）

**调用时机**：当用户提出问题时立即调用

**调用方式**：
```bash
python scripts/lightrag_cli.py query "<问题>" --mode <模式>
```

**输入参数**：
- `query_text`: 用户的问题（自然语言）
- `mode`: 查询模式（可选，默认 hybrid）
  - `naive`：纯向量检索（快速）
  - `local`：局部图检索（基于实体）
  - `global`：全局图检索（跨社区）
  - `hybrid`：混合检索（推荐）

**处理流程**：
1. Script 生成查询关键词
2. Script 执行向量检索和图检索
3. Script 综合结果生成答案

**结束判断**：
- ✅ **成功**：Script 返回答案和引用来源
- ❌ **失败**：Script 返回错误信息（知识库为空/查询超时）

**你应该做的**：
- 成功：基于 Script 返回的答案和来源，生成完整的回复给用户
- 失败：告知用户错误原因，建议先加载文档或重试

---

## 接口定义

### 1. 加载文档接口

**函数**：`load_documents(data_path: str) -> Dict`

**输入**：
```json
{
  "data_path": "./reference"
}
```

**成功输出**：
```json
{
  "status": "success",
  "message": "成功加载 5 个文档，提取 128 个实体，256 条关系",
  "entities_count": 128,
  "relations_count": 256
}
```

**错误输出**：
```json
{
  "status": "error",
  "error_code": "PARSE_ERROR",
  "message": "文档解析失败: file1.pdf 无法读取"
}
```

### 2. 查询接口

**函数**：`query(query_text: str, mode: str = "hybrid") -> Dict`

**输入**：
```json
{
  "query_text": "GB/T 22239 对防火墙有什么要求？",
  "mode": "hybrid"
}
```

**成功输出**：
```json
{
  "status": "success",
  "answer": "根据 GB/T 22239-2019...",
  "sources": [
    {"file": "GB_T_22239-2019.pdf", "page": 15, "text": "..."}
  ],
  "entities_found": ["GB/T 22239", "防火墙"]
}
```

**错误输出**：
```json
{
  "status": "error",
  "error_code": "QUERY_ERROR",
  "message": "知识库为空，请先加载文档"
}
```

---

## 输入输出示例

### 示例 1：加载文档流程

**用户输入**："帮我加载 reference 目录下的文档"

**你的操作**：
1. 调用 Script：`python scripts/lightrag_cli.py load --data-path ./reference`
2. 接收 Script 返回结果

**Script 返回（成功）**：
```
[LightRAG] 成功加载 3 个文档
[LightRAG] 提取实体: 128 个
[LightRAG] 提取关系: 256 条
```

**你回复用户**：
"✅ 已成功加载 3 个文档，提取 128 个实体和 256 条关系。知识库已构建完成，现在可以进行查询了。"

---

### 示例 2：查询流程

**用户输入**："GB/T 22239 对防火墙有什么要求？"

**你的操作**：
1. 调用 Script：`python scripts/lightrag_cli.py query "GB/T 22239 对防火墙有什么要求？"`
2. 接收 Script 返回结果
3. 基于结果生成回复

**Script 返回（成功）**：
```json
{
  "answer": "根据 GB/T 22239-2019 标准，防火墙应满足以下要求：...",
  "sources": [
    {"file": "GB_T_22239-2019.pdf", "page": 15}
  ]
}
```

**你回复用户**：
"根据 GB/T 22239-2019 标准，防火墙应满足以下要求：

1. 访问控制：应在网络边界...（详细内容）

**来源**：GB_T_22239-2019.pdf 第 15 页"

---

## 错误处理

| 错误码 | 说明 | 你的回复 |
|--------|------|---------|
| `PARSE_ERROR` | 文档解析失败 | "文档解析失败，请检查文件格式是否正确" |
| `LLM_ERROR` | 大模型 API 错误 | "大模型 API 调用失败，请检查 API 密钥和网络" |
| `EMBED_ERROR` | Embedding 错误 | "Embedding 模型加载失败，请检查模型路径" |
| `QUERY_ERROR` | 查询失败 | "查询失败，知识库为空，请先加载文档" |
| `TIMEOUT` | 超时 | "请求超时，请减少文档大小或稍后重试" |

---

## 重要提醒

1. **必须先配置**：使用本 Skill 前确保 config.yaml 已正确配置
2. **先加载后查询**：查询前必须确保已有文档加载到知识库
3. **调用 Script**：所有实际操作都通过调用 lightrag_cli.py 完成
4. **基于结果回复**：根据 Script 返回的结果生成最终回复给用户

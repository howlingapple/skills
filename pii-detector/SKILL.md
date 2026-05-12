---
name: pii-detector
description: |
  PII检测技能。识别文本中的个人敏感信息。
  
  触发条件：用户需要识别文本中的个人信息时。
  
  执行：调用detect_pii工具，返回PII标记列表。
category: skill
metadata:
  version: "2.0.0"
  author: "system"
  tags: ["pii", "privacy", "detection"]
  tools: ["detect_pii"]
---

## 输入
- text: string - 待检测文本

## 输出
```json
{
  "markers": [
    {
      "type": "phone|id_card|name|email|bank_card|address",
      "value": "原始值",
      "position": [start, end],
      "confidence": 0.95
    }
  ]
}
```

## 检测类型
| 类型 | 正则 | 示例 |
|------|------|------|
| phone | 1[3-9]\d{9} | 13812345678 |
| id_card | \d{17}[\dXx] | 110101199001011234 |
| name | [\u4e00-\u9fa5]{2,4} | 张三 |
| email | [\w.-]+@[\w.-]+ | user@example.com |
| bank_card | \d{16,19} | 6222021234567890123 |
| address | 省市区+街道 | 北京市海淀区中关村 |

## 执行步骤
1. 重新读取用户输入的文本，将敏感数据按要求做成markers
2. 输出markers列表

## 完成标准
- [ ] 所有PII类型已识别
- [ ] 每个marker包含type/value/position/confidence
- [ ] confidence >= 0.7
- [ ] 无遗漏的明显PII

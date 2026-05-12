---
name: pii-masker
description: |
  PII脱敏技能。对识别的敏感信息进行脱敏处理。
  
  触发条件：用户需要对已识别的PII进行脱敏时。
  
  执行：根据markers列表自动选择策略并脱敏，返回脱敏后文本。
category: skill
metadata:
  version: "3.0.0"
  author: "system"
  tags: ["pii", "privacy", "masking", "deidentification"]
  tools: ["mask_pii"]
---

## 输入
- text: string - 原始文本
- markers: array - PII标记列表（来自pii-detector）

## 输出
```json
{
  "masked_text": "脱敏后的文本",
  "applied_rules": ["phone_partial_mask", "name_replacement"]
}
```

## 自动脱敏策略
由 Agent 根据每个 marker 的 type 自动选择最合适的策略，无需外部指定 strategy：

| 类型 | 自动策略 | 说明 | 示例 |
|------|----------|------|------|
| phone | partial_mask | 保留前3后4 | 13812345678 → 138****5678 |
| name | replacement | 标记替换 | 张三 →  张* |
| id_card | partial_mask | 保留前6后4 | 110101199001011234 → 110101********1234 |
| email | partial_mask | 保留首尾 | user@example.com → u***@example.com |
| bank_card | partial_mask | 保留前4后4 | 6222021234567890123 → 6222************0123 |
| address | generalize | 泛化到区/市 | 北京市海淀区中关村 → 北京市海淀区 |

## 执行步骤
1. 接收 text 和 markers 参数
2. 分析每个 marker 的 type，自动选择最佳脱敏策略
3. 将每个 marker 按策略脱敏
4. 回填覆盖到原始文本的对应位置
5. 返回 masked_text 和 applied_rules

## 完成标准
- [ ] 所有 markers 已脱敏
- [ ] 脱敏后文本可正常阅读
- [ ] 原始 PII 无法逆向恢复
- [ ] 数据格式和结构保持完整

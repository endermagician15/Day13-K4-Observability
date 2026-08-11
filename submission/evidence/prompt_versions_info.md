# Bằng chứng Prompt Versioning & Rollback trên Langfuse

## 1. Cấu hình Prompt `day13-chat`
- **Tên prompt**: `day13-chat`
- **Loại**: `text`
- **Variables**: `{{feature}}`, `{{docs}}`, `{{message}}`

### Phiên bản 1 (Baseline / Production ban đầu)
- **Version**: `1`
- **Labels**: `['baseline', 'production']`
- **Template**:
```text
Feature={{feature}}
Docs={{docs}}
Question={{message}}
```

### Phiên bản 2 (Candidate)
- **Version**: `2`
- **Labels**: `['candidate']`
- **Template**:
```text
[System: Answer concisely and accurately based strictly on the provided docs.]
Feature={{feature}}
Docs={{docs}}
Question={{message}}
```

---

## 2. Kết quả thực thi các bước kiểm thử

| Bước | Hành động | Prompt Label | Prompt Version | Trace ID | Trace URL |
|---|---|---|---|---|---|
| 1 | Chạy Baseline | `baseline` | `1` | `5b571bf0f646490be350064cd2f64c54` | [5b571bf0f646490be350064cd2f64c54](https://cloud.langfuse.com/project/cmsocubpa01okad0imtxk9f7m/traces/5b571bf0f646490be350064cd2f64c54) |
| 2 | Chạy Candidate | `candidate` | `2` | `effb2e1ee16b5b2c1eac6b80247f1e39` | [effb2e1ee16b5b2c1eac6b80247f1e39](https://cloud.langfuse.com/project/cmsocubpa01okad0imtxk9f7m/traces/effb2e1ee16b5b2c1eac6b80247f1e39) |
| 3 | Promote Candidate | `production` (sau khi update v2) | `2` | `a4c0545bcbf2139c339c845e2c48969a` | [a4c0545bcbf2139c339c845e2c48969a](https://cloud.langfuse.com/project/cmsocubpa01okad0imtxk9f7m/traces/a4c0545bcbf2139c339c845e2c48969a) |
| 4 | Rollback về Baseline | `production` (sau khi rollback về v1) | `1` | `2fb7baec439f129348242f4e391495b1` | [2fb7baec439f129348242f4e391495b1](https://cloud.langfuse.com/project/cmsocubpa01okad0imtxk9f7m/traces/2fb7baec439f129348242f4e391495b1) |

---

## 3. Xác minh Metadata & Trace Links
- Tất cả các trace trên đều được gắn đầy đủ metadata:
  - `prompt_name`: `day13-chat`
  - `prompt_label`: `baseline` / `candidate` / `production`
  - `prompt_version`: `1` / `2`
  - `prompt_source`: `langfuse`
  - `tags`: `['lab', 'qa', 'claude-sonnet-4-5']`
  - `user_id_hash` và `session_id`

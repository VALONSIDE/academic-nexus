# Phase 2：学术画像系统 / Academic Portraits

## 注册闭环 / Registration flow

1. 用户在 `/activate` 用账户名称、中文真实姓名、学工号、Access Key 和新密码完成身份核验。
2. 系统只创建一个不可登录的待完成账户，并颁发短时的“画像填写”令牌；用户必须完成第二页画像。
3. 提交完整画像后，账户变为启用状态，预注册记录标记为 `activated`，Access Key 随即失效，并签发正常登录令牌。

这使得未完成画像的账户不能登录，也允许用户在第二步中断后用原回执安全地重新开始。

## 数据模型 / Data model

`student_profiles` 新增：

- `research_interests`、`skills`：JSON 标签数组。
- `academic_performance`、`academic_goals`、`research_experience`：文本。
- `profile_completed_at`：画像完成时间。

`mentor_profiles` 新增：

- `research_directions`、`representative_papers`：JSON 标签数组。
- `research_projects`、`mentoring_style`：文本。
- `profile_completed_at`：画像完成时间。

标签数组保留结构化字段，长文本保留原始语义；后续可拼接为检索文档并写入向量数据库，不影响现有关系模型。

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/v1/auth/activate` | 校验回执并开启第二步注册。 |
| POST | `/api/v1/profiles/student/complete-registration` | 保存学生必填画像并启用账户。 |
| POST | `/api/v1/profiles/mentor/complete-registration` | 保存导师必填画像并启用账户。 |
| GET/PUT | `/api/v1/profiles/student/me` | 查询或更新自己的学生画像。 |
| GET/PUT | `/api/v1/profiles/mentor/me` | 查询或更新自己的导师画像。 |
| GET | `/api/v1/admin/users?role=student|mentor&search=` | 管理员检索学生或导师。 |
| PATCH | `/api/v1/admin/users/{user_id}` | 管理状态、姓名、电话和完整画像。 |
| POST | `/api/v1/admin/users/{user_id}/password` | 管理员重置密码；不会读取旧密码。 |

## 本地验收 / Local verification

```powershell
docker compose up --build -d
docker compose exec api pytest -q
docker compose exec web npm run build
```

浏览 `http://localhost`。管理员从左侧工作台导航进入预注册、学生管理和导师管理；学生或导师从左侧进入“学术画像”。

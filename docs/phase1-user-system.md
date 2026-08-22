# Phase 1 - User System / 用户系统

## Scope / 范围

- 合作院校管理员通过 Excel 批量预注册学生、导师；不提供公开注册。
- 学生/导师以账户回执的账户名称、中文真实姓名、学工号、一次性 Access Key 创建密码；管理员由 `.env` 初始化。
- 三类身份以不可变账户名称和密码登录，并使用 JWT Bearer 认证。
- 基于 `users -> user_roles -> roles` 的 RBAC；默认试点租户预置 student、mentor、admin 三种角色。
- Vue 认证界面支持中文/English 切换；注册和登录后的语言偏好写入用户记录。

## Database / 数据库

| Table / 表 | Purpose / 作用 |
|---|---|
| `tenants` | 高校租户；Phase 1 自动建立一个试点租户。 |
| `roles` | 租户级角色字典，包含中英文名称。 |
| `users` | 邮箱、Argon2id 密码哈希、状态、语言偏好与最后登录时间。 |
| `user_roles` | 用户与角色的多对多关联。 |
| `student_profiles` | 学生资料预留：学号、院校、学院、专业、年级。 |
| `mentor_profiles` | 导师资料预留：工号、院校、学院、职称。 |
| `pre_registration_batches` | 一次已校验的合作院校 Excel 导入批次与回执签发时间。 |
| `pre_registrations` | 预注册身份、固化账户名称、Argon2id Access Key 哈希、唯一指纹与激活状态。 |

Migration: `backend/alembic/versions/20260821_0001_phase1_user_system.py`.

## API / 接口

| Method | Endpoint | Access / 权限 | Description / 说明 |
|---|---|---|---|
| `POST` | `/api/v1/auth/activate` | Public / 公开 | 用回执四项身份字段和新密码完成第一步核验，返回仅用于填写画像的短时令牌。 |
| `POST` | `/api/v1/auth/login` | Public / 公开 | 仅账户名称 + 密码登录；Phase 2 画像未完成的账户不可登录。 |
| `GET` | `/api/v1/auth/me` | Bearer token | 获取当前用户与角色。 |
| `PATCH` | `/api/v1/auth/me/locale` | Bearer token | 更新 `zh-CN` 或 `en-US` 偏好。 |
| `GET` | `/api/v1/users` | Admin | 当前租户的用户列表。 |
| `GET` | `/api/v1/admin/pre-registrations/template` | Admin | 下载固定格式的预注册 Excel 模板。 |
| `POST` | `/api/v1/admin/pre-registrations/import` | Admin | 导入已填写的模板并直接下载 Excel 回执。 |
| `GET` | `/api/v1/health` | Public / 公开 | 服务健康检查。 |

Example activation body / 激活请求示例:

```json
{
  "username": "CUC_S20240001",
  "full_name": "张同学",
  "academic_id": "20240001",
  "access_key": "1234-ABCD-5678-9012",
  "password": "AcademicNexus2026",
  "preferred_locale": "zh-CN"
}
```

Passwords must have 12+ characters and include uppercase, lowercase, and a digit. The server stores only an Argon2id hash.

## Access Key uniqueness / Access Key 唯一性

The key is generated as `XXXX-ABCD-XXXX-XXXX`: 12 CSPRNG digits plus 4 CSPRNG uppercase letters, yielding about 59 bits of entropy. Before persistence, the backend calculates `HMAC-SHA-256(ACCESS_KEY_PEPPER, normalized_key)` and applies a **global database unique constraint** to that fingerprint. An Argon2id hash is stored separately to verify activation. On a collision, the database rejects it and the generator retries; a generated key is never reissued, including after it is consumed. The plaintext key exists only in the in-memory receipt response and is not stored on the server.

## Test / 测试

```powershell
# Frontend type check, production build, and i18n test / 前端类型、构建、双语文案测试
Set-Location frontend
npm ci
npm run build
npm run test:run

# Backend security and schema tests / 后端安全与数据模型测试
Set-Location ..
$env:PYTHONPATH = "$PWD\backend"
py -m pytest backend/tests -q

# Full container stack / 完整容器栈
docker compose up --build
# Then open http://localhost and http://localhost/docs
```

## Security / 安全

- `.env` is Git-ignored and restricted to the current Windows account; it contains the database password, JWT signing secret, Access Key Pepper, and initial administrator password.
- Never send `.env` to GitHub. CI uses dummy, non-production values.
- For Ubuntu production, migrate these values to a secret manager or Docker Secrets before deployment.
- The bootstrap administrator is created once only. Change its password immediately after the account-management feature is available.

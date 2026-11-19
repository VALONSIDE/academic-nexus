"""ORM models / ORM 模型。"""

# Import modules so clean-database bootstrap and test metadata creation include
# every table, including subscription tables introduced after the first Alpha.
from app.models import security, ai, pre_registration, ranking, resource, selection, subscription, tenant, user, workspace  # noqa: F401

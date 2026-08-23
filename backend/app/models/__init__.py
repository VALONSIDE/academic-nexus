"""ORM models / ORM 模型。"""

# Import modules so clean-database bootstrap and test metadata creation include
# every table, including subscription tables introduced after the first Alpha.
from app.models import ai, pre_registration, resource, selection, subscription, tenant, user  # noqa: F401

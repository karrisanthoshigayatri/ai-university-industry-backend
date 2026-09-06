from app.db.session import engine
from sqlalchemy import text, inspect as sa_inspect
with engine.connect() as conn:
    cols = sa_inspect(conn).get_columns("partner_capability", schema="public")
    for c in cols:
        print(c["name"], str(c["type"]))

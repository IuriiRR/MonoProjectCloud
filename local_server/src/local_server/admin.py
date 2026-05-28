from fastapi import Request
from fastapi.responses import RedirectResponse
from sqladmin import Admin, ModelView, action

from .models import Account, Transaction, User


class UserAdmin(ModelView, model=User):
    column_list = ["user_id", "username", "active", "created_at"]


class AccountAdmin(ModelView, model=Account):
    column_list = [
        "id",
        "title",
        "is_budget",
        "type",
        "balance",
        "is_active",
    ]

    @action(
        name="toggle_budget",
        label="Toggle Budget",
        add_in_detail=True,
        add_in_list=True,
    )
    async def toggle_budget(self, request: Request):
        pks = request.query_params.get("pks", "")
        pk_list = [pk.strip() for pk in pks.split(",") if pk.strip()]
        with self.session_maker() as session:
            for pk in pk_list:
                account = session.get(Account, pk)
                if account and account.type == "jar":
                    account.is_budget = not account.is_budget
                    session.add(account)
            session.commit()
        return RedirectResponse(
            request.url_for("admin:list", identity=self.identity), status_code=302
        )


class TransactionAdmin(ModelView, model=Transaction):
    column_list = [
        "id",
        "account.title",
        "comment",
        "amount",
        "time",
    ]


def setup_admin(app, engine):
    admin = Admin(app, engine)
    admin.add_view(UserAdmin)
    admin.add_view(AccountAdmin)
    admin.add_view(TransactionAdmin)
    return admin

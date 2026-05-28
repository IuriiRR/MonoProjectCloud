from fastapi import Request
from fastapi.responses import RedirectResponse
from sqladmin import Admin, ModelView, action
from sqlalchemy import func, select

from .models import Account, Transaction, User


class UserAdmin(ModelView, model=User):
    column_list = ["user_id", "username", "active", "created_at"]


class JarAccountAdmin(ModelView, model=Account):
    name = "Jar"
    name_plural = "Jars"
    icon = "fa-solid fa-piggy-bank"
    column_list = [
        "id",
        "title",
        "is_budget",
        "balance",
        "is_active",
    ]

    def list_query(self, request):
        return select(Account).where(Account.type == "jar")

    def count_query(self, request):
        return select(func.count(Account.id)).where(Account.type == "jar")

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


# sqladmin metaclass unconditionally sets identity from model.__name__; override after definition
JarAccountAdmin.identity = "jar"


class CardAccountAdmin(ModelView, model=Account):
    name = "Card"
    name_plural = "Cards"
    icon = "fa-solid fa-credit-card"
    column_list = [
        "id",
        "title",
        "type",
        "balance",
        "is_active",
    ]

    def list_query(self, request):
        return select(Account).where(Account.type == "card")

    def count_query(self, request):
        return select(func.count(Account.id)).where(Account.type == "card")


CardAccountAdmin.identity = "card"


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
    admin.add_view(JarAccountAdmin)
    admin.add_view(CardAccountAdmin)
    admin.add_view(TransactionAdmin)
    return admin

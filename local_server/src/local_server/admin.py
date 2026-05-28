import calendar
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request
from fastapi.responses import RedirectResponse
from sqladmin import Admin, BaseView, ModelView, action, expose
from sqlalchemy import func, select
from sqlalchemy.orm import Session as SASession

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


class MonthlyReportView(BaseView):
    name = "Monthly Report"
    icon = "fa-solid fa-chart-bar"

    @expose("/monthly-report", methods=["GET"])
    async def monthly_report(self, request: Request):
        month = request.query_params.get(
            "month", datetime.now(timezone.utc).strftime("%Y-%m")
        )

        try:
            dt = datetime.strptime(month, "%Y-%m")
        except ValueError:
            dt = datetime.now(timezone.utc)
            month = dt.strftime("%Y-%m")

        _, last_day = calendar.monthrange(dt.year, dt.month)
        month_start = int(
            datetime(dt.year, dt.month, 1, tzinfo=timezone.utc).timestamp()
        )
        month_end = (
            int(
                datetime(
                    dt.year, dt.month, last_day, 23, 59, 59, tzinfo=timezone.utc
                ).timestamp()
            )
            + 1
        )

        with SASession(self._admin_ref.engine) as session:
            jars = (
                session.execute(select(Account).where(Account.is_budget))
                .scalars()
                .all()
            )

            result = []
            for jar in jars:
                txs = (
                    session.execute(
                        select(Transaction)
                        .where(Transaction.account_id == jar.id)
                        .where(Transaction.time >= month_start)
                        .where(Transaction.time < month_end)
                        .order_by(Transaction.time)
                    )
                    .scalars()
                    .all()
                )

                if txs:
                    start_balance = txs[0].balance - txs[0].amount
                else:
                    start_balance = jar.balance

                budget = max((tx.amount for tx in txs if tx.amount > 0), default=0)
                total_deposits = sum(tx.amount for tx in txs if tx.amount > 0)
                spent = sum(tx.amount for tx in txs) - budget

                result.append(
                    {
                        "title": jar.title or jar.id,
                        "start_balance": start_balance,
                        "current_balance": jar.balance,
                        "budget": budget,
                        "total_deposits": total_deposits,
                        "spent": spent,
                        "transactions": [
                            {"time": tx.time, "balance": tx.balance} for tx in txs
                        ],
                    }
                )

        return await self.templates.TemplateResponse(
            request,
            "monthly_report.html",
            {"month": month, "jars": result},
        )


def setup_admin(app, engine):
    templates_dir = Path(__file__).parent / "templates"
    admin = Admin(app, engine, templates_dir=str(templates_dir))
    admin.add_view(UserAdmin)
    admin.add_view(JarAccountAdmin)
    admin.add_view(CardAccountAdmin)
    admin.add_view(TransactionAdmin)
    admin.add_base_view(MonthlyReportView)
    return admin

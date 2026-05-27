from sqladmin import Admin, ModelView
from .models import User, Account, Transaction

class UserAdmin(ModelView, model=User):
    column_list = [User.user_id, User.username, User.active, User.created_at]

class AccountAdmin(ModelView, model=Account):
    column_list = [Account.id, Account.user_id, Account.type, Account.balance, Account.is_active]

class TransactionAdmin(ModelView, model=Transaction):
    column_list = [Transaction.id, Transaction.account_id, Transaction.amount, Transaction.time]

def setup_admin(app, engine):
    admin = Admin(app, engine)
    admin.add_view(UserAdmin)
    admin.add_view(AccountAdmin)
    admin.add_view(TransactionAdmin)
    return admin

from django.contrib import admin
from transactions import models

@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'type', 'amount', 'status', 'created_at')
    list_filter = ('type', 'status')

@admin.register(models.Fee)
class FeeAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'fee_amount', 'refund_to_party', 'fee_level')

@admin.register(models.Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'updated_at')
    search_fields = ('user__username', 'user__email')

@admin.register(models.WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'type', 'amount', 'new_balance', 'created_at')
    list_filter = ('type',)

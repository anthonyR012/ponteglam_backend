from django.db import models
from core.models import MixinAudit

class Transaction(MixinAudit):
    TYPE_PAYMENT = 'payment'
    TYPE_REFUND = 'refund'
    TYPE_DEVOLUTION = 'devolution'
    
    TYPE_CHOICES = [
        (TYPE_PAYMENT, 'Pago'),
        (TYPE_REFUND, 'Reembolso parcial'),
        (TYPE_DEVOLUTION, 'Devolución total'),
    ]

    appointment = models.ForeignKey(
        'services.Appointment', on_delete=models.CASCADE,
        related_name='transactions'
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='pending')
    metadata = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Transaction {self.id}: {self.type} - {self.amount}"


class Fee(MixinAudit):
    """
    Stores penalties and commissions related to an appointment.
    """
    appointment = models.ForeignKey(
        'services.Appointment', on_delete=models.CASCADE,
        related_name='fees'
    )
    penalty_pct = models.FloatField()
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_commission = models.DecimalField(max_digits=10, decimal_places=2)
    refund_to_party = models.DecimalField(max_digits=10, decimal_places=2)
    fee_level = models.CharField(max_length=20) # low/middle/high

    def __str__(self):
        return f"Fee {self.id} for Appointment {self.appointment_id}"


class Wallet(MixinAudit):
    """
    Stores the current balance for a user (client or worker).
    """
    user = models.OneToOneField(
        'users.User', on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    def __str__(self):
        return f"Wallet for {self.user.username} - Balance: {self.balance}"

    def process_debt_payment(self, amount, created_by_user_id, appointment_id=None):
        """
        Settle debt with a given amount.
        """
        from django.db import transaction
        import decimal
        from transactions.models import WalletTransaction
        
        with transaction.atomic():
            previous_balance = self.balance
            new_balance = self.balance + decimal.Decimal(str(amount))
            
            WalletTransaction.objects.create(
                wallet=self,
                amount=amount,
                type=WalletTransaction.TYPE_DEPOSIT,
                description="Pago de deuda pendiente",
                previous_balance=previous_balance,
                new_balance=new_balance,
                created_by_user_id=created_by_user_id,
                appointment_id=appointment_id
            )
            
            self.balance = new_balance
            self.save()
            return self.balance


class WalletTransaction(MixinAudit):
    """
    Detailed history of wallet movements.
    """
    TYPE_DEPOSIT = 'deposit'    # Money added (refunds, payments)
    TYPE_WITHDRAWAL = 'withdrawal' # Money taken out (penalty, checkout)
    TYPE_DEBT = 'debt'          # Recorded debt for cash cancellation

    TYPE_CHOICES = [
        (TYPE_DEPOSIT, 'Depósito / Abono'),
        (TYPE_WITHDRAWAL, 'Retiro / Cargo'),
        (TYPE_DEBT, 'Deuda'),
    ]

    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE,
        related_name='wallet_transactions'
    )
    appointment = models.ForeignKey(
        'services.Appointment', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='wallet_transactions'
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(null=True, blank=True)
    previous_balance = models.DecimalField(max_digits=12, decimal_places=2)
    new_balance = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"WalletTx {self.id}: {self.type} - {self.amount}"

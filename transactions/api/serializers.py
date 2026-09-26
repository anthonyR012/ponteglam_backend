from rest_framework import serializers
from transactions import models

class WalletTransactionSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_display', read_only=True)
    created_at = serializers.DateTimeField(format="%d %b %Y, %I:%M %p")

    class Meta:
        model = models.WalletTransaction
        fields = [
            'id', 'type', 'type_label', 'amount', 'description', 
            'previous_balance', 'new_balance', 'created_at', 'appointment'
        ]

class WalletSerializer(serializers.ModelSerializer):
    transactions = WalletTransactionSerializer(
        source='wallet_transactions', many=True, read_only=True
    )

    class Meta:
        model = models.Wallet
        fields = ['id', 'balance', 'transactions']

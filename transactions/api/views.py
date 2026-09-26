from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from transactions import models
from transactions.api import serializers

class WalletViewSet(viewsets.ViewSet):
    """
    ViewSet to retrieve the current user's wallet and transactions.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        wallet, _ = models.Wallet.objects.get_or_create(
            user=request.user, 
            defaults={'created_by_user_id': 1}
        )
        
        # Prefetch transactions ordered by date
        # We manually order them here because many=True doesn't easily support ordering in the source
        # or we could use a SerializerMethodField
        
        serializer = serializers.WalletSerializer(wallet)
        
        # Sort transactions descending in the response
        data = serializer.data
        data['transactions'] = sorted(
            data['transactions'], key=lambda x: x['id'], reverse=True
        )
        
        return Response({'success': data}, status=status.HTTP_200_OK)

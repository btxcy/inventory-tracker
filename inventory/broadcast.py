# independent file
# views.py: may need to broadcast when managing backend
# services.py: no way it needs to know ws when it does not know http

# responsibility: push broadcast to client

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def broadcast_stock_update(product):
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        "stock", {
            "type": "stock.update",
            "payload": {
                "id": product.id,
                "sku": product.sku,
                "quantity": product.quantity,
                "is_low_stock": product.is_low_stock,
            }
        }
    )
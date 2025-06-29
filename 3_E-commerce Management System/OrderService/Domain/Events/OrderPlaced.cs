using System;

namespace OrderService.Domain.Events
{
    public class OrderPlaced
    {
        public Guid OrderId { get; set; }
        public DateTime PlacedAt { get; set; }

        public OrderPlaced(Guid orderId)
        {
            OrderId = orderId;
            PlacedAt = DateTime.UtcNow;
        }
    }
} 
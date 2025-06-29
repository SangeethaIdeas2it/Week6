using System;

namespace OrderService.Domain.Events
{
    public class OrderPaid
    {
        public Guid OrderId { get; set; }
        public DateTime PaidAt { get; set; }

        public OrderPaid(Guid orderId)
        {
            OrderId = orderId;
            PaidAt = DateTime.UtcNow;
        }
    }
} 
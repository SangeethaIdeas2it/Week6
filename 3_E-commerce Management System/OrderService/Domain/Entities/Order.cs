using System;
using System.Collections.Generic;
using OrderService.Domain.Enums;

namespace OrderService.Domain.Entities
{
    public class Order
    {
        public Guid Id { get; set; }
        public Guid CustomerId { get; set; }
        public OrderStatus Status { get; set; }
        public string PaymentInfo { get; set; }
        public List<OrderLineItem> LineItems { get; set; } = new List<OrderLineItem>();
    }
} 
namespace OrderService.Domain;

public enum OrderStatus { Pending, Paid, Shipped, Cancelled }

public class Order
{
    public int Id { get; set; }
    public string CustomerId { get; set; } = string.Empty;
    public OrderStatus Status { get; set; } = OrderStatus.Pending;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public List<OrderLineItem> Items { get; set; } = new();
}

public class OrderLineItem
{
    public int Id { get; set; }
    public int OrderId { get; set; }
    public int ProductId { get; set; }
    public int Quantity { get; set; }
    public decimal Price { get; set; }
    public Order? Order { get; set; }
}

namespace OrderService.Application.Orders.Dtos;

public class OrderDto
{
    public int Id { get; set; }
    public string CustomerId { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
    public List<OrderLineItemDto> Items { get; set; } = new();
}

public class OrderLineItemDto
{
    public int Id { get; set; }
    public int ProductId { get; set; }
    public int Quantity { get; set; }
    public decimal Price { get; set; }
} 
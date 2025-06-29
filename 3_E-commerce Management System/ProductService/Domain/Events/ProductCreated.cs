using System;

namespace ProductService.Domain.Events
{
    public class ProductCreated
    {
        public Guid ProductId { get; set; }
        public DateTime CreatedAt { get; set; }

        public ProductCreated(Guid productId)
        {
            ProductId = productId;
            CreatedAt = DateTime.UtcNow;
        }
    }
} 
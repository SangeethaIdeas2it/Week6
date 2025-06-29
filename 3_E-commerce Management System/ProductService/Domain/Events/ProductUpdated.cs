using System;

namespace ProductService.Domain.Events
{
    public class ProductUpdated
    {
        public Guid ProductId { get; set; }
        public DateTime UpdatedAt { get; set; }

        public ProductUpdated(Guid productId)
        {
            ProductId = productId;
            UpdatedAt = DateTime.UtcNow;
        }
    }
} 
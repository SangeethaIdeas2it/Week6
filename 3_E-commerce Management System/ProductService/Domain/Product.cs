using System;

namespace ProductService.Domain.Entities
{
    public class Product
    {
        public Guid Id { get; set; }
        public string Name { get; set; }
        public decimal Price { get; set; }
        public Guid CategoryId { get; set; }
        public int Stock { get; set; }

        public Category Category { get; set; }
    }
} 
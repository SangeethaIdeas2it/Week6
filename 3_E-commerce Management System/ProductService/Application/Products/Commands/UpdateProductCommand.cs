using System;
using MediatR;

namespace ProductService.Application.Products.Commands
{
    public class UpdateProductCommand : IRequest
    {
        public Guid Id { get; set; }
        public string Name { get; set; }
        public decimal Price { get; set; }
        public Guid CategoryId { get; set; }
        public int Stock { get; set; }
    }
} 
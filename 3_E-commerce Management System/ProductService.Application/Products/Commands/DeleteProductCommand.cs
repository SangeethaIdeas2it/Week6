using System;
using MediatR;

namespace ProductService.Application.Products.Commands
{
    public class DeleteProductCommand : IRequest<Unit>
    {
        public Guid Id { get; set; }
    }
} 
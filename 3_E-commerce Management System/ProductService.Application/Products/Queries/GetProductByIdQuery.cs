using System;
using MediatR;
using ProductService.Application.Products.Dtos;

namespace ProductService.Application.Products.Queries
{
    public class GetProductByIdQuery : IRequest<ProductDto>
    {
        public Guid Id { get; set; }
    }
} 
using System.Collections.Generic;
using MediatR;
using ProductService.Application.Products.Dtos;

namespace ProductService.Application.Products.Queries
{
    public class GetAllProductsQuery : IRequest<List<ProductDto>>
    {
    }
} 
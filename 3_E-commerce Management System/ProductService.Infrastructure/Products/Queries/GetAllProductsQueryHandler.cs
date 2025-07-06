using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using AutoMapper;
using MediatR;
using Microsoft.EntityFrameworkCore;
using ProductService.Application.Products.Dtos;
using ProductService.Infrastructure.Persistence;

namespace ProductService.Infrastructure.Products.Queries
{
    public class GetAllProductsQueryHandler : IRequestHandler<ProductService.Application.Products.Queries.GetAllProductsQuery, List<ProductDto>>
    {
        private readonly AppDbContext _context;
        private readonly IMapper _mapper;

        public GetAllProductsQueryHandler(AppDbContext context, IMapper mapper)
        {
            _context = context;
            _mapper = mapper;
        }

        public async Task<List<ProductDto>> Handle(ProductService.Application.Products.Queries.GetAllProductsQuery request, CancellationToken cancellationToken)
        {
            var products = await _context.Products.AsNoTracking().ToListAsync(cancellationToken);
            return _mapper.Map<List<ProductDto>>(products);
        }
    }
} 
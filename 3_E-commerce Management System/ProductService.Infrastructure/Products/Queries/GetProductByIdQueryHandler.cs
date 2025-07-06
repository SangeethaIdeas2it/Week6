using System;
using System.Threading;
using System.Threading.Tasks;
using AutoMapper;
using MediatR;
using Microsoft.EntityFrameworkCore;
using ProductService.Application.Products.Dtos;
using ProductService.Infrastructure.Persistence;

namespace ProductService.Infrastructure.Products.Queries
{
    public class GetProductByIdQueryHandler : IRequestHandler<ProductService.Application.Products.Queries.GetProductByIdQuery, ProductDto>
    {
        private readonly AppDbContext _context;
        private readonly IMapper _mapper;

        public GetProductByIdQueryHandler(AppDbContext context, IMapper mapper)
        {
            _context = context;
            _mapper = mapper;
        }

        public async Task<ProductDto> Handle(ProductService.Application.Products.Queries.GetProductByIdQuery request, CancellationToken cancellationToken)
        {
            var product = await _context.Products.AsNoTracking().FirstOrDefaultAsync(p => p.Id == request.Id, cancellationToken);
            if (product == null)
                return null;
            return _mapper.Map<ProductDto>(product);
        }
    }
} 
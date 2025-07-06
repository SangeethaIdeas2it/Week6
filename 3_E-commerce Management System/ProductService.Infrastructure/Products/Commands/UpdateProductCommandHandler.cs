using System;
using System.Threading;
using System.Threading.Tasks;
using AutoMapper;
using MediatR;
using Microsoft.EntityFrameworkCore;
using ProductService.Domain.Entities;
using ProductService.Infrastructure.Persistence;

namespace ProductService.Infrastructure.Products.Commands
{
    public class UpdateProductCommandHandler : IRequestHandler<ProductService.Application.Products.Commands.UpdateProductCommand, Unit>
    {
        private readonly AppDbContext _context;
        private readonly IMapper _mapper;

        public UpdateProductCommandHandler(AppDbContext context, IMapper mapper)
        {
            _context = context;
            _mapper = mapper;
        }

        public async Task<Unit> Handle(ProductService.Application.Products.Commands.UpdateProductCommand request, CancellationToken cancellationToken)
        {
            var product = await _context.Products.FirstOrDefaultAsync(p => p.Id == request.Id, cancellationToken);
            if (product == null)
                throw new Exception($"Product with Id {request.Id} not found.");

            _mapper.Map(request, product);
            await _context.SaveChangesAsync(cancellationToken);
            return Unit.Value;
        }
    }
} 
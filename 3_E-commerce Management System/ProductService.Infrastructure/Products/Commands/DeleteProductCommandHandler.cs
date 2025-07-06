using System;
using System.Threading;
using System.Threading.Tasks;
using MediatR;
using Microsoft.EntityFrameworkCore;
using ProductService.Infrastructure.Persistence;

namespace ProductService.Infrastructure.Products.Commands
{
    public class DeleteProductCommandHandler : IRequestHandler<ProductService.Application.Products.Commands.DeleteProductCommand, Unit>
    {
        private readonly AppDbContext _context;

        public DeleteProductCommandHandler(AppDbContext context)
        {
            _context = context;
        }

        public async Task<Unit> Handle(ProductService.Application.Products.Commands.DeleteProductCommand request, CancellationToken cancellationToken)
        {
            var product = await _context.Products.FirstOrDefaultAsync(p => p.Id == request.Id, cancellationToken);
            if (product == null)
                throw new Exception($"Product with Id {request.Id} not found.");

            _context.Products.Remove(product);
            await _context.SaveChangesAsync(cancellationToken);
            return Unit.Value;
        }
    }
} 
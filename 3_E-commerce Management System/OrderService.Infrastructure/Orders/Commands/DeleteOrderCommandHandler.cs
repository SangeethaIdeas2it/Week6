using MediatR;
using OrderService.Application.Orders.Commands;

namespace OrderService.Infrastructure.Orders.Commands;

public class DeleteOrderCommandHandler : IRequestHandler<DeleteOrderCommand>
{
    private readonly OrderDbContext _db;
    public DeleteOrderCommandHandler(OrderDbContext db) { _db = db; }
    public async Task<Unit> Handle(DeleteOrderCommand request, CancellationToken ct)
    {
        var entity = await _db.Orders.FindAsync(new object[] { request.Id }, ct);
        if (entity != null) { _db.Orders.Remove(entity); await _db.SaveChangesAsync(ct); }
        return Unit.Value;
    }
} 
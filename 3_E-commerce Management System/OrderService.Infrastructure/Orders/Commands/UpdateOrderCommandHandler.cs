using AutoMapper;
using MediatR;
using Microsoft.EntityFrameworkCore;
using OrderService.Application.Orders.Commands;
using OrderService.Domain;

namespace OrderService.Infrastructure.Orders.Commands;

public class UpdateOrderCommandHandler : IRequestHandler<UpdateOrderCommand>
{
    private readonly OrderDbContext _db;
    private readonly IMapper _mapper;
    public UpdateOrderCommandHandler(OrderDbContext db, IMapper mapper) { _db = db; _mapper = mapper; }
    public async Task<Unit> Handle(UpdateOrderCommand request, CancellationToken ct)
    {
        var entity = await _db.Orders.Include(o => o.Items).FirstOrDefaultAsync(o => o.Id == request.Id, ct);
        if (entity == null) return Unit.Value;
        _mapper.Map(request.Order, entity);
        await _db.SaveChangesAsync(ct);
        return Unit.Value;
    }
} 
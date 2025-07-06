using AutoMapper;
using MediatR;
using OrderService.Application.Orders.Commands;
using OrderService.Domain;

namespace OrderService.Infrastructure.Orders.Commands;

public class CreateOrderCommandHandler : IRequestHandler<CreateOrderCommand, int>
{
    private readonly OrderDbContext _db;
    private readonly IMapper _mapper;
    public CreateOrderCommandHandler(OrderDbContext db, IMapper mapper) { _db = db; _mapper = mapper; }
    public async Task<int> Handle(CreateOrderCommand request, CancellationToken ct)
    {
        var entity = _mapper.Map<Order>(request.Order);
        _db.Orders.Add(entity);
        await _db.SaveChangesAsync(ct);
        return entity.Id;
    }
} 
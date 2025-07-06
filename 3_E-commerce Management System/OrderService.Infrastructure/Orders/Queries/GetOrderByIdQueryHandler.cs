using AutoMapper;
using MediatR;
using Microsoft.EntityFrameworkCore;
using OrderService.Application.Orders.Queries;
using OrderService.Application.Orders.Dtos;

namespace OrderService.Infrastructure.Orders.Queries;

public class GetOrderByIdQueryHandler : IRequestHandler<GetOrderByIdQuery, OrderDto?>
{
    private readonly OrderDbContext _db;
    private readonly IMapper _mapper;
    public GetOrderByIdQueryHandler(OrderDbContext db, IMapper mapper) { _db = db; _mapper = mapper; }
    public async Task<OrderDto?> Handle(GetOrderByIdQuery request, CancellationToken ct)
    {
        var order = await _db.Orders.Include(o => o.Items).FirstOrDefaultAsync(o => o.Id == request.Id, ct);
        return order == null ? null : _mapper.Map<OrderDto>(order);
    }
} 
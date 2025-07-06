using AutoMapper;
using MediatR;
using Microsoft.EntityFrameworkCore;
using OrderService.Application.Orders.Queries;
using OrderService.Application.Orders.Dtos;

namespace OrderService.Infrastructure.Orders.Queries;

public class GetAllOrdersQueryHandler : IRequestHandler<GetAllOrdersQuery, List<OrderDto>>
{
    private readonly OrderDbContext _db;
    private readonly IMapper _mapper;
    public GetAllOrdersQueryHandler(OrderDbContext db, IMapper mapper) { _db = db; _mapper = mapper; }
    public async Task<List<OrderDto>> Handle(GetAllOrdersQuery request, CancellationToken ct)
    {
        var orders = await _db.Orders.Include(o => o.Items).ToListAsync(ct);
        return _mapper.Map<List<OrderDto>>(orders);
    }
} 
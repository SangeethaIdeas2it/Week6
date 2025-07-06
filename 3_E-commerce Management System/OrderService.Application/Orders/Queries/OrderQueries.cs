using MediatR;
using OrderService.Application.Orders.Dtos;
using System.Collections.Generic;

namespace OrderService.Application.Orders.Queries;

public record GetAllOrdersQuery() : IRequest<List<OrderDto>>;
public record GetOrderByIdQuery(int Id) : IRequest<OrderDto?>; 
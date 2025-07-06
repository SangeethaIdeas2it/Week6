using MediatR;
using OrderService.Application.Orders.Dtos;

namespace OrderService.Application.Orders.Commands;

public record CreateOrderCommand(OrderDto Order) : IRequest<int>;
public record UpdateOrderCommand(int Id, OrderDto Order) : IRequest;
public record DeleteOrderCommand(int Id) : IRequest; 
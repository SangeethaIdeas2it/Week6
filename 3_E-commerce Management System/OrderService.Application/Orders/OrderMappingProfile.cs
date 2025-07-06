using AutoMapper;
using OrderService.Domain;
using OrderService.Application.Orders.Dtos;

namespace OrderService.Application.Orders;

public class OrderMappingProfile : Profile
{
    public OrderMappingProfile()
    {
        CreateMap<Order, OrderDto>().ReverseMap();
        CreateMap<OrderLineItem, OrderLineItemDto>().ReverseMap();
    }
} 
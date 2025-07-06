using Microsoft.AspNetCore.Mvc;
using MediatR;
using OrderService.Application.Orders.Commands;
using OrderService.Application.Orders.Queries;
using OrderService.Application.Orders.Dtos;

namespace OrderService.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class OrderController : ControllerBase
{
    private readonly IMediator _mediator;
    public OrderController(IMediator mediator) => _mediator = mediator;

    [HttpGet]
    public async Task<List<OrderDto>> GetAll() => await _mediator.Send(new GetAllOrdersQuery());

    [HttpGet("{id}")]
    public async Task<ActionResult<OrderDto>> GetById(int id)
    {
        var order = await _mediator.Send(new GetOrderByIdQuery(id));
        return order == null ? NotFound() : Ok(order);
    }

    [HttpPost]
    public async Task<ActionResult<int>> Create(OrderDto dto)
    {
        var id = await _mediator.Send(new CreateOrderCommand(dto));
        return CreatedAtAction(nameof(GetById), new { id }, id);
    }

    [HttpPut("{id}")]
    public async Task<IActionResult> Update(int id, OrderDto dto)
    {
        await _mediator.Send(new UpdateOrderCommand(id, dto));
        return NoContent();
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        await _mediator.Send(new DeleteOrderCommand(id));
        return NoContent();
    }
} 
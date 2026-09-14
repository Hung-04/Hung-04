using Microsoft.AspNetCore.Mvc;
using OrderManagement.Application.DTOs.Orders;
using OrderManagement.Application.Services;
using FluentValidation;

namespace OrderManagement.API.Controllers;

[ApiController]
[Route("api/orders")]
public class OrdersController : ControllerBase
{
    private readonly IOrderService _orderService;

    public OrdersController(IOrderService orderService)
    {
        _orderService = orderService;
    }

    [HttpPost]
    public async Task<ActionResult<OrderResponse>> Create(
        [FromBody] CreateOrderRequest request)
    {
        try
        {
            var result = await _orderService.CreateAsync(request);

            return Ok(result);
        }
        catch (ValidationException ex)
        {
            return BadRequest(new
            {
                message = ex.Errors.First().ErrorMessage
            });
        }
        catch (KeyNotFoundException ex)
        {
            return NotFound(new
            {
                message = ex.Message
            });
        }
    }

    [HttpGet]
    public async Task<ActionResult<List<OrderResponse>>> GetAll(
        [FromQuery] DateTime? fromDate,
        [FromQuery] DateTime? toDate)
    {
        var result = await _orderService
            .GetAllAsync(fromDate, toDate);

        return Ok(result);
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<OrderResponse>> GetById(
        Guid id)
    {
        var result = await _orderService.GetByIdAsync(id);

        if (result == null)
        {
            return NotFound(new
            {
                message = "Order not found."
            });
        }

        return Ok(result);
    }
}
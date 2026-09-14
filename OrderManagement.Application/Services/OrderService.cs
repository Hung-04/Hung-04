using FluentValidation;
using OrderManagement.Application.DTOs.Orders;
using OrderManagement.Application.Interfaces;
using OrderManagement.Domain.Entities;

namespace OrderManagement.Application.Services;

public class OrderService : IOrderService
{
    private readonly IOrderRepository _orderRepository;
    private readonly IProductRepository _productRepository;
    private readonly IValidator<CreateOrderRequest> _validator;

    public OrderService(
        IOrderRepository orderRepository,
        IProductRepository productRepository,
        IValidator<CreateOrderRequest> validator)
    {
        _orderRepository = orderRepository;
        _productRepository = productRepository;
        _validator = validator;
    }

    public async Task<OrderResponse> CreateAsync(
        CreateOrderRequest request)
    {
        await _validator.ValidateAndThrowAsync(request);

        var order = new Order(request.CustomerName);

        foreach (var item in request.Items)
        {
            var product = await _productRepository
                .GetByCodeAsync(item.ProductCode);

            if (product == null)
            {
                throw new KeyNotFoundException(
                    $"Product '{item.ProductCode}' not found.");
            }

            order.AddItem(
                product.Id,
                product.ProductCode,
                product.Name,
                item.Quantity,
                item.UnitPrice);
        }

        await _orderRepository.AddAsync(order);

        return MapToResponse(order);
    }

    public async Task<List<OrderResponse>> GetAllAsync(
        DateTime? fromDate,
        DateTime? toDate)
    {
        var orders = await _orderRepository
            .GetAllAsync(fromDate, toDate);

        return orders
            .Select(MapToResponse)
            .ToList();
    }

    public async Task<OrderResponse?> GetByIdAsync(Guid id)
    {
        var order = await _orderRepository.GetByIdAsync(id);

        if (order == null)
            return null;

        return MapToResponse(order);
    }

    private static OrderResponse MapToResponse(Order order)
    {
        return new OrderResponse
        {
            Id = order.Id,
            CustomerName = order.CustomerName,
            CreatedAt = order.CreatedAt,

            Items = order.Items
                .Select(item => new OrderItemResponse
                {
                    ProductId = item.ProductId,
                    ProductCode = item.ProductCode,
                    ProductName = item.ProductName,
                    Quantity = item.Quantity,
                    UnitPrice = item.UnitPrice,
                    Subtotal = item.Subtotal
                })
                .ToList(),

            TotalAmount = order.TotalAmount,
            Vat = order.Vat,
            GrandTotal = order.GrandTotal
        };
    }
}
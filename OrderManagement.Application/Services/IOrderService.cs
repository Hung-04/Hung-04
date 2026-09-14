using OrderManagement.Application.DTOs.Orders;

namespace OrderManagement.Application.Services;

public interface IOrderService
{
    Task<OrderResponse> CreateAsync(CreateOrderRequest request);

    Task<List<OrderResponse>> GetAllAsync(
        DateTime? fromDate,
        DateTime? toDate);

    Task<OrderResponse?> GetByIdAsync(Guid id);
}
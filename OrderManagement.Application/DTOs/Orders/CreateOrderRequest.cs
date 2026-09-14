namespace OrderManagement.Application.DTOs.Orders;

public class CreateOrderRequest
{
    public string CustomerName { get; set; } = string.Empty;

    public List<CreateOrderItemRequest> Items { get; set; } = new();
}
namespace OrderManagement.Application.DTOs.Orders;

public class CreateOrderItemRequest
{
    public string ProductCode { get; set; } = string.Empty;

    public int Quantity { get; set; }

    public decimal UnitPrice { get; set; }
}
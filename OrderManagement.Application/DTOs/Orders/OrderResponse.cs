namespace OrderManagement.Application.DTOs.Orders;

public class OrderResponse
{
    public Guid Id { get; set; }

    public string CustomerName { get; set; } = string.Empty;

    public DateTime CreatedAt { get; set; }

    public List<OrderItemResponse> Items { get; set; } = new();

    public decimal TotalAmount { get; set; }

    public decimal Vat { get; set; }

    public decimal GrandTotal { get; set; }
}
namespace OrderManagement.Application.DTOs.Products;

public class ProductResponse
{
    public Guid Id { get; set; }

    public string ProductCode { get; set; } = string.Empty;

    public string Name { get; set; } = string.Empty;

    public decimal Price { get; set; }

    public string Unit { get; set; } = string.Empty;
}
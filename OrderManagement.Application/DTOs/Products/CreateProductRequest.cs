namespace OrderManagement.Application.DTOs.Products;

public class CreateProductRequest
{
    public string ProductCode { get; set; } = string.Empty;

    public string Name { get; set; } = string.Empty;

    public decimal Price { get; set; }

    public string Unit { get; set; } = string.Empty;
}
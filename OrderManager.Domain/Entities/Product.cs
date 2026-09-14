namespace OrderManagement.Domain.Entities;

public class Product
{
    public Guid Id { get; private set; }

    public string ProductCode { get; private set; } = string.Empty;
    public string Name { get; private set; } = string.Empty;
    public decimal Price { get; private set; }
    public string Unit { get; private set; } = string.Empty;
    private Product()
    {
    }

    public Product(
        string productCode,
        string name,
        decimal price,
        string unit)
    {
        if (string.IsNullOrWhiteSpace(productCode))
            throw new ArgumentException("Product code is required.");

        if (string.IsNullOrWhiteSpace(name))
            throw new ArgumentException("Product name is required.");

        if (price <= 0)
            throw new ArgumentException("Product price must be greater than 0.");

        if (string.IsNullOrWhiteSpace(unit))
            throw new ArgumentException("Product unit is required.");

        Id = Guid.NewGuid();
        ProductCode = productCode;
        Name = name;
        Price = price;
        Unit = unit;
    }

    public void Update(
        string name,
        decimal price,
        string unit)
    {
        if (string.IsNullOrWhiteSpace(name))
            throw new ArgumentException("Product name is required.");

        if (price <= 0)
            throw new ArgumentException("Product price must be greater than 0.");

        if (string.IsNullOrWhiteSpace(unit))
            throw new ArgumentException("Product unit is required.");

        Name = name;
        Price = price;
        Unit = unit;
    }
}
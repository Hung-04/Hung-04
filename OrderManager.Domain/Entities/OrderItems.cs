namespace OrderManagement.Domain.Entities;

public class OrderItem
{
    public Guid Id { get; private set; }

    public Guid OrderId { get; private set; }

    public Guid ProductId { get; private set; }

    public string ProductCode { get; private set; } = string.Empty;
    public string ProductName { get; private set; } = string.Empty;
    public int Quantity { get; private set; }

    public decimal UnitPrice { get; private set; }

    public decimal Subtotal => Quantity * UnitPrice;

    private OrderItem()
    {
    }

    internal OrderItem(
        Guid productId,
        string productCode,
        string productName,
        int quantity,
        decimal unitPrice)
    {
        if (productId == Guid.Empty)
            throw new ArgumentException("Product ID is required.");

        if (string.IsNullOrWhiteSpace(productCode))
            throw new ArgumentException("Product code is required.");

        if (string.IsNullOrWhiteSpace(productName))
            throw new ArgumentException("Product name is required.");

        if (quantity <= 0)
            throw new ArgumentException("Quantity must be greater than 0.");

        if (unitPrice <= 0)
            throw new ArgumentException("Unit price must be greater than 0.");

        Id = Guid.NewGuid();
        ProductId = productId;
        ProductCode = productCode;
        ProductName = productName;
        Quantity = quantity;
        UnitPrice = unitPrice;
    }
}
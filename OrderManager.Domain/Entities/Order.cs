namespace OrderManagement.Domain.Entities;

public class Order
{
    private const decimal VatRate = 0.10m;

    private readonly List<OrderItem> _items = new();

    public Guid Id { get; private set; }
    public string CustomerName { get; private set; } = string.Empty;
    public DateTime CreatedAt { get; private set; }

    public decimal TotalAmount { get; private set; }

    public decimal Vat { get; private set; }

    public decimal GrandTotal { get; private set; }

    public IReadOnlyCollection<OrderItem> Items => _items.AsReadOnly();

    private Order()
    {
    }

    public Order(string customerName)
    {
        if (string.IsNullOrWhiteSpace(customerName))
            throw new ArgumentException("Customer name is required.");

        Id = Guid.NewGuid();
        CustomerName = customerName;
        CreatedAt = DateTime.Now;

        TotalAmount = 0;
        Vat = 0;
        GrandTotal = 0;
    }

    public void AddItem(
        Guid productId,
        string productCode,
        string productName,
        int quantity,
        decimal unitPrice)
    {
        if (quantity <= 0)
            throw new ArgumentException("Quantity must be greater than 0.");

        if (unitPrice <= 0)
            throw new ArgumentException("Unit price must be greater than 0.");

        var item = new OrderItem(
            productId,
            productCode,
            productName,
            quantity,
            unitPrice);

        _items.Add(item);

        RecalculateTotals();
    }

    private void RecalculateTotals()
    {
        TotalAmount = _items.Sum(x => x.Subtotal);

        Vat = TotalAmount * VatRate;

        GrandTotal = TotalAmount + Vat;
    }
}
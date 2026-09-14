using OrderManagement.Domain.Entities;

namespace OrderManagement.Application.Interfaces;

public interface IProductRepository
{
    Task<Product?> GetByIdAsync(Guid id);

    Task<Product?> GetByCodeAsync(string productCode);

    Task<List<Product>> GetAllAsync();

    Task<bool> ExistsByCodeAsync(string productCode);

    Task AddAsync(Product product);
}
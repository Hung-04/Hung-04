using OrderManagement.Application.DTOs.Products;

namespace OrderManagement.Application.Services;

public interface IProductService
{
    Task<ProductResponse> CreateAsync(CreateProductRequest request);
    Task<List<ProductResponse>> GetAllAsync();
}
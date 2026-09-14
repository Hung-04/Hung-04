using FluentValidation;
using OrderManagement.Application.DTOs.Products;
using OrderManagement.Application.Interfaces;
using OrderManagement.Domain.Entities;

namespace OrderManagement.Application.Services;

public class ProductService : IProductService
{
    private readonly IProductRepository _productRepository;
    private readonly IValidator<CreateProductRequest> _validator;

    public ProductService(
        IProductRepository productRepository,
        IValidator<CreateProductRequest> validator)
    {
        _productRepository = productRepository;
        _validator = validator;
    }

    public async Task<ProductResponse> CreateAsync(
        CreateProductRequest request)
    {
        await _validator.ValidateAndThrowAsync(request);

        var exists = await _productRepository
            .ExistsByCodeAsync(request.ProductCode);

        if (exists)
            throw new InvalidOperationException(
                "Product code already exists.");

        var product = new Product(
            request.ProductCode,
            request.Name,
            request.Price,
            request.Unit);

        await _productRepository.AddAsync(product);

        return MapToResponse(product);
    }

    public async Task<List<ProductResponse>> GetAllAsync()
    {
        var products = await _productRepository.GetAllAsync();

        return products
            .Select(MapToResponse)
            .ToList();
    }

    private static ProductResponse MapToResponse(Product product)
    {
        return new ProductResponse
        {
            Id = product.Id,
            ProductCode = product.ProductCode,
            Name = product.Name,
            Price = product.Price,
            Unit = product.Unit
        };
    }
}
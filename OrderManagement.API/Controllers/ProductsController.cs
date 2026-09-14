using Microsoft.AspNetCore.Mvc;
using OrderManagement.Application.DTOs.Products;
using OrderManagement.Application.Services;
using FluentValidation;

namespace OrderManagement.API.Controllers;

[ApiController]
[Route("api/products")]
public class ProductsController : ControllerBase
{
    private readonly IProductService _productService;

    public ProductsController(IProductService productService)
    {
        _productService = productService;
    }

    [HttpPost]
public async Task<ActionResult<ProductResponse>> Create(
    [FromBody] CreateProductRequest request)
    {
        try
        {
            var result = await _productService.CreateAsync(request);

            return CreatedAtAction(
                nameof(GetAll),
                null,
                result);
        }
        catch (ValidationException ex)
        {
            return BadRequest(new
            {
                message = ex.Errors.First().ErrorMessage
            });
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new
            {
                message = ex.Message
            });
        }
    }

    [HttpGet]
    public async Task<ActionResult<List<ProductResponse>>> GetAll()
    {
        var result = await _productService.GetAllAsync();

        return Ok(result);
    }
}
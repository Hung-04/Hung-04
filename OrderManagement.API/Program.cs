using FluentValidation;
using OrderManagement.Application.DTOs.Orders;
using OrderManagement.Application.DTOs.Products;
using OrderManagement.Application.Services;
using OrderManagement.Application.Validators;
using OrderManagement.Infrastructure;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services.AddInfrastructure(
    builder.Configuration);

builder.Services.AddScoped<IProductService, ProductService>();
builder.Services.AddScoped<IOrderService, OrderService>();

builder.Services.AddScoped<
    IValidator<CreateProductRequest>,
    CreateProductValidator>();

builder.Services.AddScoped<
    IValidator<CreateOrderRequest>,
    CreateOrderValidator>();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();

app.UseAuthorization();

app.MapControllers();

app.Run();

using FluentValidation;
using OrderManagement.Application.DTOs.Orders;

namespace OrderManagement.Application.Validators;

public class CreateOrderValidator 
    : AbstractValidator<CreateOrderRequest>
{
    public CreateOrderValidator()
    {
        RuleFor(x => x.CustomerName)
            .NotEmpty()
            .MaximumLength(200);

        RuleFor(x => x.Items)
            .NotEmpty()
            .WithMessage("Order must contain at least one item.");

        RuleForEach(x => x.Items)
            .SetValidator(new CreateOrderItemValidator());
    }
}

public class CreateOrderItemValidator
    : AbstractValidator<CreateOrderItemRequest>
{
    public CreateOrderItemValidator()
    {
        RuleFor(x => x.ProductCode)
            .NotEmpty()
            .MaximumLength(50);

        RuleFor(x => x.Quantity)
            .GreaterThan(0)
            .WithMessage("Số lượng sản phẩm phải lớn hơn 0.");

        RuleFor(x => x.UnitPrice)
            .GreaterThan(0)
            .WithMessage("Đơn giá sản phẩm phải lớn hơn 0.");
            }
}
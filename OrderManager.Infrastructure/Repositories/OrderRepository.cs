using Microsoft.EntityFrameworkCore;
using OrderManagement.Application.Interfaces;
using OrderManagement.Domain.Entities;
using OrderManagement.Infrastructure.Persistence;

namespace OrderManagement.Infrastructure.Repositories;

public class OrderRepository : IOrderRepository
{
    private readonly AppDbContext _context;

    public OrderRepository(AppDbContext context)
    {
        _context = context;
    }

    public async Task AddAsync(Order order)
    {
        await _context.Orders.AddAsync(order);

        await _context.SaveChangesAsync();
    }

    public async Task<Order?> GetByIdAsync(Guid id)
    {
        return await _context.Orders
            .Include(x => x.Items)
            .FirstOrDefaultAsync(x => x.Id == id);
    }

    public async Task<List<Order>> GetAllAsync(
        DateTime? fromDate,
        DateTime? toDate)
    {
        var query = _context.Orders
            .Include(x => x.Items)
            .AsNoTracking()
            .AsQueryable();

        if (fromDate.HasValue)
        {
            query = query.Where(
                x => x.CreatedAt >= fromDate.Value);
        }

        if (toDate.HasValue)
        {
            var endDate = toDate.Value.Date.AddDays(1);

            query = query.Where(
                x => x.CreatedAt < endDate);
        }

        return await query
            .OrderByDescending(x => x.CreatedAt)
            .ToListAsync();
    }
}
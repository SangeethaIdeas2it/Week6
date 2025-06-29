using Microsoft.AspNetCore.SignalR;
using Microsoft.Extensions.Logging;
using System.Threading.Tasks;
using ProductService.Api.Hubs;

namespace ProductService.Infrastructure.SignalR
{
    public class InventoryHubNotifier
    {
        private readonly IHubContext<InventoryHub> _hubContext;
        private readonly ILogger<InventoryHubNotifier> _logger;

        public InventoryHubNotifier(IHubContext<InventoryHub> hubContext, ILogger<InventoryHubNotifier> logger)
        {
            _hubContext = hubContext;
            _logger = logger;
        }

        public async Task NotifyStockChange(string productId, int newStock)
        {
            _logger.LogInformation($"Publishing stock change for Product {productId}: {newStock}");
            await _hubContext.Clients.Group(productId).SendAsync("StockChanged", productId, newStock);
        }
    }
} 
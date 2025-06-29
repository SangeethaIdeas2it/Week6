using Microsoft.AspNetCore.SignalR;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace ProductService.Api.Hubs
{
    public class InventoryHub : Hub
    {
        private readonly ILogger<InventoryHub> _logger;
        public InventoryHub(ILogger<InventoryHub> logger)
        {
            _logger = logger;
        }

        // Called by server to notify clients of stock changes
        public async Task NotifyStockChange(string productId, int newStock)
        {
            _logger.LogInformation($"Notifying stock change for Product {productId}: {newStock}");
            await Clients.Group(productId).SendAsync("StockChanged", productId, newStock);
        }

        // Client joins a group for a specific product
        public async Task JoinProductGroup(string productId)
        {
            await Groups.AddToGroupAsync(Context.ConnectionId, productId);
            _logger.LogInformation($"Client {Context.ConnectionId} joined group {productId}");
        }

        // Client leaves a group for a specific product
        public async Task LeaveProductGroup(string productId)
        {
            await Groups.RemoveFromGroupAsync(Context.ConnectionId, productId);
            _logger.LogInformation($"Client {Context.ConnectionId} left group {productId}");
        }

        public override async Task OnConnectedAsync()
        {
            _logger.LogInformation($"Client connected: {Context.ConnectionId}");
            await base.OnConnectedAsync();
        }

        public override async Task OnDisconnectedAsync(System.Exception exception)
        {
            _logger.LogInformation($"Client disconnected: {Context.ConnectionId}");
            await base.OnDisconnectedAsync(exception);
        }
    }
} 
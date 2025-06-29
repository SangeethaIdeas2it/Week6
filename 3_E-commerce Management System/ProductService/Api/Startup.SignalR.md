# SignalR InventoryHub Client Example

## JavaScript Client Example

```js
const connection = new signalR.HubConnectionBuilder()
    .withUrl("/hubs/inventory")
    .configureLogging(signalR.LogLevel.Information)
    .build();

// Start the connection
connection.start()
    .then(() => {
        console.log("Connected to InventoryHub");
        // Join a product group to receive stock updates
        connection.invoke("JoinProductGroup", "PRODUCT_ID");
    })
    .catch(err => console.error(err.toString()));

// Listen for stock changes
connection.on("StockChanged", (productId, newStock) => {
    console.log(`Stock updated for product ${productId}: ${newStock}`);
    // Update UI accordingly
});

// Optionally, leave a group
// connection.invoke("LeaveProductGroup", "PRODUCT_ID");
```

## Logging and Metrics
- Server logs all connections, group joins/leaves, and stock notifications (see ILogger usage in InventoryHub).
- For production, integrate with Application Insights, Prometheus, or similar for metrics and monitoring SignalR events. 
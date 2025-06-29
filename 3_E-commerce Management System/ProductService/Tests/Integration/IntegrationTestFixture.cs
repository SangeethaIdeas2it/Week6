using System;
using System.Net.Http;
using System.Threading.Tasks;
using DotNet.Testcontainers.Builders;
using DotNet.Testcontainers.Containers;
using Xunit;

namespace ProductService.Tests.Integration
{
    public class IntegrationTestFixture : IAsyncLifetime
    {
        public HttpClient ProductApiClient { get; private set; }
        public HttpClient OrderApiClient { get; private set; }
        public IContainer RedisContainer { get; private set; }
        public IContainer SqlServerContainer { get; private set; }
        public IContainer MockStripeContainer { get; private set; }

        public async Task InitializeAsync()
        {
            SqlServerContainer = new TestcontainersBuilder<TestcontainersContainer>()
                .WithImage("mcr.microsoft.com/mssql/server:2019-latest")
                .WithEnvironment("SA_PASSWORD", "Your_password123")
                .WithEnvironment("ACCEPT_EULA", "Y")
                .WithPortBinding(1433, true)
                .Build();
            await SqlServerContainer.StartAsync();

            RedisContainer = new TestcontainersBuilder<TestcontainersContainer>()
                .WithImage("redis:latest")
                .WithPortBinding(6379, true)
                .Build();
            await RedisContainer.StartAsync();

            MockStripeContainer = new TestcontainersBuilder<TestcontainersContainer>()
                .WithImage("wiremock/wiremock")
                .WithPortBinding(8080, true)
                .Build();
            await MockStripeContainer.StartAsync();

            // TODO: Start ProductService and OrderService APIs (e.g., via docker-compose or WebApplicationFactory)
            // TODO: Initialize HttpClient for APIs
        }

        public async Task DisposeAsync()
        {
            await SqlServerContainer.StopAsync();
            await RedisContainer.StopAsync();
            await MockStripeContainer.StopAsync();
        }
    }
} 